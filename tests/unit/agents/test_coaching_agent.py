import json

import pytest
from tests.conftest import ScriptedAiClient

from pcc.agents.coaching_agent import generate_coaching_plan
from pcc.agents.fallbacks.coaching_fallback import template_plan
from pcc.agents.validators.coaching_validator import validate_coaching_plan
from pcc.content.content_loader import load_skills
from pcc.core.exceptions import AiUnavailableError
from pcc.domain.schemas.coaching_schemas import CoachingInput, MissedQuestion

SKILL = next(s for s in load_skills() if s.skill_id == "linux_fundamentals")


def _missed(qid, tag) -> MissedQuestion:
    return MissedQuestion(
        question_id=qid,
        concept_tag=tag,
        stem=f"Question {qid}?",
        selected_option_text="wrong",
        correct_option_text="right",
        explanation="because",
    )


def _context(*missed: MissedQuestion) -> CoachingInput:
    return CoachingInput(
        career_name="DevOps Engineer",
        skill_id=SKILL.skill_id,
        skill_name=SKILL.name,
        level="beginner",
        missed=list(missed),
        practice_templates=SKILL.practice_templates,
        max_total_minutes=240,
        retest_after_days=7,
    )


TWO = (_missed("q1", "file_permissions"), _missed("q2", "process_management"))
ONE = (_missed("q1", "file_permissions"),)
THREE_SAME_TAG = tuple(_missed(f"q{i}", "file_permissions") for i in (1, 2, 3))
THREE_TAGS = (
    _missed("q1", "file_permissions"),
    _missed("q2", "process_management"),
    _missed("q3", "filesystem_navigation"),
)


@pytest.mark.parametrize("missed", [ONE, TWO, THREE_SAME_TAG, THREE_TAGS])
def test_template_plan_is_always_valid(missed):
    context = _context(*missed)
    plan = template_plan(context)
    assert validate_coaching_plan(plan, SKILL.skill_id, context) == []
    assert 3 <= len(plan.tasks) <= 5
    assert [t.order for t in plan.tasks] == list(range(1, len(plan.tasks) + 1))
    assert plan.generation_source == "template"


def test_template_plan_uses_curated_content_for_missed_concepts():
    plan = template_plan(_context(*TWO))
    titles = [t.title for t in plan.tasks]
    assert "Permission digits drill" in titles and "Process control lab" in titles
    assert all(t.linked_question_id in {"q1", "q2"} for t in plan.tasks)
    assert plan.tasks[0].misconception == "Chose 'wrong' instead of 'right'"


def test_template_plan_prioritises_the_most_missed_concept():
    context = _context(
        _missed("q1", "process_management"),
        _missed("q2", "file_permissions"),
        _missed("q3", "file_permissions"),
    )
    assert template_plan(context).tasks[0].concept_tag == "file_permissions"


def test_template_plan_has_generic_task_for_tags_without_curated_content():
    context = _context(_missed("q1", "brand_new_tag")).model_copy(update={"practice_templates": []})
    plan = template_plan(context)
    assert validate_coaching_plan(plan, SKILL.skill_id, context) == []
    assert plan.tasks[0].title == "Practice: brand new tag"


def test_template_plan_is_deterministic():
    assert template_plan(_context(*THREE_TAGS)) == template_plan(_context(*THREE_TAGS))


def test_no_ai_client_uses_template_without_fallback_flag():
    result = generate_coaching_plan(_context(*TWO), None)
    assert result.plan.generation_source == "template" and not result.used_fallback


def _ai_plan(**changes) -> str:
    task = {
        "order": 1,
        "title": "Fix permissions",
        "linked_question_id": "q1",
        "concept_tag": "file_permissions",
        "misconception": "Mixed up digits",
        "action": "Practise chmod on five files",
        "resource_hint": "man chmod",
        "estimated_minutes": 30,
        "success_check": "Explain 755",
    }
    plan = {
        "skill_id": "linux_fundamentals",
        "diagnosis": "Permission digits are shaky.",
        "tasks": [{**task, "order": i, "title": f"Step {i}"} for i in (1, 2, 3)],
        "retest_after_days": 30,
    }
    plan.update(changes)
    return json.dumps(plan)


def test_valid_ai_plan_is_accepted_and_config_decides_retest_days():
    client = ScriptedAiClient(_ai_plan())
    result = generate_coaching_plan(_context(*TWO), client)
    assert result.plan.generation_source == "ai" and not result.used_fallback
    assert result.plan.retest_after_days == 7  # model said 30; config wins
    assert client.calls == 1


def test_t12_ai_plan_for_another_skill_is_rejected():
    client = ScriptedAiClient(_ai_plan(skill_id="shell_scripting"))
    result = generate_coaching_plan(_context(*TWO), client)
    assert result.used_fallback and result.plan.generation_source == "template"
    assert result.plan.skill_id == "linux_fundamentals"
    assert client.calls == 2  # first try + one repair


def test_t13_ai_task_with_no_link_is_rejected():
    tasks = json.loads(_ai_plan())["tasks"]
    tasks[2].update(linked_question_id=None, concept_tag="unrelated_topic")
    result = generate_coaching_plan(_context(*TWO), ScriptedAiClient(_ai_plan(tasks=tasks)))
    assert result.used_fallback


def test_t14_ai_url_is_rejected():
    tasks = json.loads(_ai_plan())["tasks"]
    tasks[0]["resource_hint"] = "https://example.com/linux"
    result = generate_coaching_plan(_context(*TWO), ScriptedAiClient(_ai_plan(tasks=tasks)))
    assert result.used_fallback
    assert "https://" not in result.plan.model_dump_json()


def test_t16_empty_or_malformed_ai_response_never_crashes():
    for bad in ("", "{}", "not json", '{"tasks": "x"}', "[]", '{"skill_id": 5}'):
        result = generate_coaching_plan(_context(*TWO), ScriptedAiClient(bad))
        assert result.used_fallback and result.plan.generation_source == "template"


def test_t15_ai_unavailable_falls_back_to_template():
    result = generate_coaching_plan(_context(*TWO), ScriptedAiClient(AiUnavailableError("down")))
    assert result.used_fallback and "unavailable" in result.message


def test_repair_attempt_can_succeed():
    client = ScriptedAiClient(_ai_plan(skill_id="other"), _ai_plan())
    result = generate_coaching_plan(_context(*TWO), client)
    assert result.plan.generation_source == "ai" and client.calls == 2


def test_prompt_sends_no_identity_and_names_the_fixed_skill():
    seen = {}

    class Spy(ScriptedAiClient):
        def generate(self, prompt, **kwargs):
            seen["prompt"] = prompt
            return super().generate(prompt, **kwargs)

    generate_coaching_plan(_context(*TWO), Spy(_ai_plan()))
    assert "linux_fundamentals" in seen["prompt"] and "q1" in seen["prompt"]
    assert "display_name" not in seen["prompt"]
