import json
import sqlite3

import pytest

from pcc.ai.ai_client import AiClient
from pcc.content.content_loader import load_question_bank
from pcc.core.exceptions import AiUnavailableError
from pcc.domain.enums import WorkflowState
from pcc.workflow.workflow_controller import WorkflowController

BANK = {q.question_id: q for q in load_question_bank("devops_engineer")}


class RoutingAi(AiClient):
    """Fails roadmap calls (so the template is used) and answers coaching calls as scripted."""

    def __init__(self, coaching_reply):
        self.coaching_reply = coaching_reply
        self.coaching_calls = 0

    def generate(self, prompt, *, system=None, temperature=0.2):
        if "study coach" in prompt:
            self.coaching_calls += 1
            if isinstance(self.coaching_reply, Exception):
                raise self.coaching_reply
            if callable(self.coaching_reply):
                return self.coaching_reply(prompt)
            return self.coaching_reply
        raise AiUnavailableError("roadmap not needed in this test")


def _take_check(controller, correct_per_skill, name="Asha"):
    profile = controller.open_profile(name)
    controller.select_career(profile.id, career_id="devops_engineer", custom_text="", semester=3)
    session = controller.start_assessment(profile.id)
    seen: dict[str, int] = {}
    selections = {}
    for q in session.questions:
        n = seen.get(q.skill_id, 0)
        seen[q.skill_id] = n + 1
        right = BANK[q.question_id].correct_option_id
        want_correct = n < correct_per_skill.get(q.skill_id, 0)
        selections[q.question_id] = next(
            o.option_id for o in q.options if (o.option_id == right) == want_correct
        )
    result = controller.submit_assessment(profile.id, session.attempt_id, selections)
    return profile, session, result


WORKED = {
    "linux_fundamentals": 1,
    "shell_scripting": 1,
    "python_for_automation": 2,
    "git_version_control": 2,
}


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def test_weakest_skill_gets_a_valid_plan_linked_to_missed_questions(db_path):
    controller = WorkflowController(db_path)
    profile, session, result = _take_check(controller, WORKED)

    view = controller.get_coaching_plan(profile.id)
    assert view.plan.skill_id == result.weakest.skill_id == "linux_fundamentals"
    assert view.skill_name == "Linux Fundamentals"
    assert 3 <= len(view.plan.tasks) <= 5
    assert view.plan.generation_source == "template"

    missed_linux = {
        r.question_id
        for r in result.reviews
        if r.skill_id == "linux_fundamentals" and not r.is_correct
    }
    assert len(missed_linux) == 2
    for task in view.plan.tasks:  # every task is traceable to a mistake
        assert task.linked_question_id in missed_linux
        assert task.linked_question_id in view.question_stems
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE


def test_plan_is_saved_and_restored_after_reopening(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)
    before = controller.get_coaching_plan(profile.id)
    assert WorkflowController(db_path).get_coaching_plan(profile.id) == before

    conn = sqlite3.connect(db_path)
    status, source = conn.execute("SELECT status, generation_source FROM coaching_plans").fetchone()
    conn.close()
    assert (status, source) == ("active", "template")


def test_no_coaching_when_there_is_no_major_gap(db_path):
    controller = WorkflowController(db_path)
    profile, _, result = _take_check(controller, dict.fromkeys(WORKED, 3))  # T-08
    assert result.weakest.status == "no_major_gap"
    assert controller.get_coaching_plan(profile.id) is None
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE


def _echo_valid_plan(prompt: str) -> str:
    """Builds a valid plan from the missed questions the prompt actually contains."""
    after_marker = prompt.split("(JSON):", 1)[1].strip()
    missed = json.loads(after_marker.splitlines()[0])
    tasks = [
        {
            "order": i,
            "title": f"AI step {i}",
            "linked_question_id": m["question_id"],
            "concept_tag": m["concept_tag"],
            "action": "Practise",
            "estimated_minutes": 30,
            "success_check": "Explain it",
        }
        for i, m in enumerate((missed * 3)[:3], start=1)
    ]
    return json.dumps(
        {
            "skill_id": "linux_fundamentals",
            "diagnosis": "AI diagnosis.",
            "tasks": tasks,
            "retest_after_days": 7,
        }
    )


def test_valid_ai_plan_is_used_and_validated(db_path):
    ai = RoutingAi(_echo_valid_plan)
    controller = WorkflowController(db_path, ai_client=ai)
    profile, _, _ = _take_check(controller, WORKED)
    view = controller.get_coaching_plan(profile.id)
    assert view.plan.generation_source == "ai"
    assert view.plan.diagnosis == "AI diagnosis."
    assert ai.coaching_calls == 1


def test_t12_ai_plan_for_the_wrong_skill_never_reaches_the_student(db_path):
    reply = json.dumps(
        {"skill_id": "git_version_control", "diagnosis": "x", "tasks": [], "retest_after_days": 7}
    )
    controller = WorkflowController(db_path, ai_client=RoutingAi(reply))
    profile, _, _ = _take_check(controller, WORKED)
    view = controller.get_coaching_plan(profile.id)
    assert view.plan.skill_id == "linux_fundamentals"
    assert view.plan.generation_source == "template"


def test_t15_t16_ai_down_or_garbage_still_completes_the_flow(db_path):
    for name, reply in (("A", AiUnavailableError("down")), ("B", "{}"), ("C", "<html>")):
        controller = WorkflowController(db_path, ai_client=RoutingAi(reply))
        profile, _, _ = _take_check(controller, WORKED, name=name)
        view = controller.get_coaching_plan(profile.id)
        assert view.plan.generation_source == "template"
        assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE


def test_scores_are_identical_whatever_the_ai_says(db_path, tmp_path):
    plain = WorkflowController(str(tmp_path / "a.db"))
    noisy = WorkflowController(
        str(tmp_path / "b.db"), ai_client=RoutingAi('{"overall_score": 100}')
    )
    _, _, a = _take_check(plain, WORKED)
    _, _, b = _take_check(noisy, WORKED)
    assert (a.overall_score, a.level, a.weakest) == (b.overall_score, b.level, b.weakest)
