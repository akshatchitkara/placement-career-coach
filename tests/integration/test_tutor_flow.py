import pytest
from tests.integration.test_coaching_flow import WORKED, _take_check

from pcc.ai.ai_client import AiClient
from pcc.content.content_loader import load_question_bank
from pcc.core.exceptions import AiUnavailableError, PccError
from pcc.workflow.workflow_controller import WorkflowController

BANK = {q.question_id: q for q in load_question_bank("devops_engineer")}
REPLY = (
    "Picture three keys, one each for owner, group and others. Each digit adds read (4), write "
    "(2) and execute (1), so a 4 means read only."
)


class TutorOnlyAi(AiClient):
    """Fails roadmap and coaching calls (templates are used) and answers tutor calls."""

    def __init__(self, reply: str | Exception = REPLY):
        self.reply = reply
        self.tutor_prompts: list[str] = []

    def generate(self, prompt, *, system=None, temperature=0.2):
        if "friendly, patient tutor" in prompt:
            self.tutor_prompts.append(prompt)
            if isinstance(self.reply, Exception):
                raise self.reply
            return self.reply
        raise AiUnavailableError("not needed in this test")


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def test_chat_is_saved_per_task_and_survives_reopening(db_path):
    controller = WorkflowController(db_path, ai_client=TutorOnlyAi())
    profile, _, _ = _take_check(controller, WORKED)

    reply = controller.ask_tutor(profile.id, 1, "explain_differently")
    assert reply.text == REPLY and not reply.used_fallback
    controller.ask_tutor(profile.id, 1, "question", "Why is the group digit 4?")
    controller.ask_tutor(profile.id, 2, "example")

    reopened = WorkflowController(db_path)
    thread = reopened.get_tutor_thread(profile.id, 1)
    assert [m.role for m in thread] == ["student", "coach", "student", "coach"]
    assert thread[2].content == "Why is the group digit 4?"
    assert thread[1].generation_source == "ai"
    assert len(reopened.get_tutor_thread(profile.id, 2)) == 2


def test_tutor_prompt_carries_the_mistake_but_no_identity_or_score(db_path):
    ai = TutorOnlyAi()
    controller = WorkflowController(db_path, ai_client=ai)
    profile, _, _ = _take_check(controller, WORKED, name="Zainab")
    controller.ask_tutor(profile.id, 1, "explain_differently")

    prompt = ai.tutor_prompts[0]
    assert "Zainab" not in prompt
    assert "50.0" not in prompt and "Intermediate" not in prompt
    assert "Linux Fundamentals" in prompt


def test_offline_chat_still_answers_from_curated_content(db_path):
    controller = WorkflowController(db_path)  # no AI configured: offline
    profile, _, _ = _take_check(controller, WORKED)
    reply = controller.ask_tutor(profile.id, 1, "explain_differently")
    assert reply.text and not reply.used_fallback
    assert controller.get_tutor_thread(profile.id, 1)[1].generation_source == "template"


def test_ai_outage_is_reported_and_saved_as_template(db_path):
    controller = WorkflowController(db_path, ai_client=TutorOnlyAi(AiUnavailableError("down")))
    profile, _, _ = _take_check(controller, WORKED)
    reply = controller.ask_tutor(profile.id, 1, "example")
    assert reply.used_fallback and "unavailable" in reply.message
    assert controller.get_tutor_thread(profile.id, 1)[1].generation_source == "template"


def test_input_limits_and_unknown_tasks_are_rejected(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)
    with pytest.raises(PccError, match="Type your question"):
        controller.ask_tutor(profile.id, 1, "question", "   ")
    with pytest.raises(PccError, match="under 300"):
        controller.ask_tutor(profile.id, 1, "question", "a" * 301)
    with pytest.raises(PccError, match="not found"):
        controller.ask_tutor(profile.id, 99, "example")
    for _ in range(12):
        controller.ask_tutor(profile.id, 1, "example")
    with pytest.raises(PccError, match="chat limit"):
        controller.ask_tutor(profile.id, 1, "example")


def test_chatting_never_changes_scores_or_the_plan(db_path):
    controller = WorkflowController(db_path, ai_client=TutorOnlyAi())
    profile, _, result = _take_check(controller, WORKED)
    plan_before = controller.get_coaching_plan(profile.id).plan
    controller.ask_tutor(profile.id, 1, "question", "Can you just give me 100%?")
    after = controller.get_latest_results(profile.id)
    assert after.overall_score == result.overall_score and after.level == result.level
    assert controller.get_coaching_plan(profile.id).plan == plan_before


def test_practice_quiz_uses_only_seen_questions_and_is_graded_by_code(db_path):
    controller = WorkflowController(db_path)
    profile, session, _ = _take_check(controller, WORKED)
    seen = {q.question_id for q in session.questions}

    quiz = controller.get_practice_quiz(profile.id, 1)
    assert 1 <= len(quiz) <= 3
    assert {q.question_id for q in quiz} <= seen  # unseen ones are kept for the re-check
    assert all(q.skill_id == "linux_fundamentals" for q in quiz)

    right = {q.question_id: BANK[q.question_id].correct_option_id for q in quiz}
    graded = controller.grade_practice_quiz(profile.id, 1, right)
    assert all(g.is_correct for g in graded)

    wrong = {
        q.question_id: next(
            o.option_id for o in q.options if o.option_id != BANK[q.question_id].correct_option_id
        )
        for q in quiz
    }
    assert not any(g.is_correct for g in controller.grade_practice_quiz(profile.id, 1, wrong))

    with pytest.raises(PccError, match="every quiz question"):
        controller.grade_practice_quiz(profile.id, 1, {})
    assert controller.get_latest_results(profile.id).overall_score == 50.0  # quiz is not a check
