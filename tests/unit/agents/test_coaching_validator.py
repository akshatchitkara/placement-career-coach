import pytest

from pcc.agents.validators.coaching_validator import validate_coaching_plan
from pcc.domain.schemas.coaching_schemas import (
    CoachingInput,
    CoachingPlan,
    CoachingTask,
    MissedQuestion,
)


def _missed(qid: str, tag: str) -> MissedQuestion:
    return MissedQuestion(
        question_id=qid,
        concept_tag=tag,
        stem="A stem?",
        selected_option_text="wrong",
        correct_option_text="right",
        explanation="because",
    )


@pytest.fixture
def context() -> CoachingInput:
    return CoachingInput(
        career_name="DevOps Engineer",
        skill_id="linux_fundamentals",
        skill_name="Linux Fundamentals",
        level="beginner",
        missed=[_missed("q1", "file_permissions"), _missed("q2", "process_management")],
        practice_templates=[],
        max_total_minutes=240,
        retest_after_days=7,
    )


def _task(order: int, **overrides) -> CoachingTask:
    fields = {
        "order": order,
        "title": f"Task {order}",
        "linked_question_id": "q1",
        "concept_tag": "file_permissions",
        "action": "Do the thing",
        "estimated_minutes": 30,
        "success_check": "Explain it without notes",
    }
    return CoachingTask(**{**fields, **overrides})


def _plan(tasks: list[CoachingTask], skill_id: str = "linux_fundamentals") -> CoachingPlan:
    return CoachingPlan(skill_id=skill_id, diagnosis="d", tasks=tasks, retest_after_days=7)


def _rules(errors: list[str]) -> set[str]:
    return {e.split(":")[0] for e in errors}


def _validate(plan: CoachingPlan, context: CoachingInput) -> list[str]:
    return validate_coaching_plan(plan, "linux_fundamentals", context)


def test_valid_plan_passes(context):
    assert _validate(_plan([_task(1), _task(2), _task(3)]), context) == []


@pytest.mark.parametrize("count", [0, 2, 6])
def test_v_co_01_task_count(context, count):
    plan = _plan([_task(i) for i in range(1, count + 1)])
    assert "V-CO-01" in _rules(_validate(plan, context))


def test_t13_task_without_link_or_missed_tag_is_rejected(context):
    unlinked = _task(3, linked_question_id=None, concept_tag="networking_basics")
    assert "V-CO-02" in _rules(_validate(_plan([_task(1), _task(2), unlinked]), context))
    nothing = _task(3, linked_question_id=None, concept_tag=None)
    assert "V-CO-02" in _rules(_validate(_plan([_task(1), _task(2), nothing]), context))


def test_link_to_a_question_that_was_not_missed_is_rejected(context):
    bad = _task(3, linked_question_id="q99", concept_tag="file_permissions")
    assert "V-CO-02" in _rules(_validate(_plan([_task(1), _task(2), bad]), context))


def test_concept_tag_alone_is_enough(context):
    tag_only = _task(3, linked_question_id=None, concept_tag="process_management")
    assert _validate(_plan([_task(1), _task(2), tag_only]), context) == []


def test_t12_plan_for_a_different_skill_is_rejected(context):
    plan = _plan([_task(1), _task(2), _task(3)], skill_id="shell_scripting")
    assert "V-CO-03" in _rules(_validate(plan, context))


def test_v_co_04_total_time_limit(context):
    plan = _plan([_task(i, estimated_minutes=90) for i in (1, 2, 3)])
    assert "V-CO-04" in _rules(_validate(plan, context))


def test_v_co_05_blank_success_check(context):
    plan = _plan([_task(1), _task(2), _task(3, success_check="  ")])
    assert "V-CO-05" in _rules(_validate(plan, context))


@pytest.mark.parametrize(
    "field", ["action", "resource_hint", "title", "misconception", "success_check"]
)
def test_t14_url_in_any_text_field_is_rejected(context, field):
    plan = _plan([_task(1), _task(2), _task(3, **{field: "see https://evil.example/x"})])
    assert "V-CO-06" in _rules(_validate(plan, context))


def test_url_in_diagnosis_is_rejected(context):
    plan = _plan([_task(1), _task(2), _task(3)]).model_copy(update={"diagnosis": "visit www.x.com"})
    assert "V-CO-06" in _rules(_validate(plan, context))
