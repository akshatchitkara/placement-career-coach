from datetime import date

import pytest
from tests.integration.test_coaching_flow import BANK, WORKED, _take_check

from pcc.workflow.workflow_controller import WorkflowController


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def _retest(controller, profile, correct_first_n):
    session = controller.start_assessment(profile.id)
    seen: dict[str, int] = {}
    picks = {}
    for q in session.questions:
        n = seen.get(q.skill_id, 0)
        seen[q.skill_id] = n + 1
        right = BANK[q.question_id].correct_option_id
        picks[q.question_id] = next(
            o.option_id for o in q.options if (o.option_id == right) == (n < correct_first_n)
        )
    return controller.submit_assessment(profile.id, session.attempt_id, picks)


def test_effort_pairs_ticked_tasks_with_the_next_checks_score_change(tmp_path):
    db = str(tmp_path / "pcc.db")
    controller = WorkflowController(db, today=lambda: date(2026, 10, 1))
    profile, _, first = _take_check(controller, WORKED)
    assert controller.get_effort(profile.id) == []  # one check: nothing to compare yet

    view = controller.get_weekly_plan(profile.id)
    study = [t for t in view.plan.tasks if t.kind != "recheck"]
    for task in study[:2]:
        controller.set_task_done(profile.id, view.plan_id, task.task_id, True)

    late = WorkflowController(db, today=lambda: date(2026, 10, 9))
    second = _retest(late, profile, correct_first_n=3)

    (week,) = late.get_effort(profile.id)
    assert week.tasks_done == 2 and week.tasks_total == len(study)
    assert week.minutes_done == sum(t.estimated_minutes for t in study[:2])
    assert week.score_change == pytest.approx(second.overall_score - first.overall_score)
    assert week.score_change > 0


def test_mentor_notes_exist_only_for_skills_under_the_bar(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(
        controller,
        {
            "linux_fundamentals": 0,
            "shell_scripting": 3,
            "python_for_automation": 3,
            "git_version_control": 3,
        },
    )
    notes = controller.get_mentor_notes(profile.id)
    assert list(notes) == ["linux_fundamentals"]
    assert "Linux Fundamentals at 0%" in notes["linux_fundamentals"]
    assert "DevOps Engineer" in notes["linux_fundamentals"]
    assert "Asha" not in notes["linux_fundamentals"]  # no identity in a message to share


def test_no_mentor_notes_when_nothing_is_below_the_bar(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)  # weakest is 33%, i.e. below 40
    assert controller.get_mentor_notes(profile.id)
    fine = WorkflowController(str(db_path) + "2")
    ok, _, _ = _take_check(fine, {k: 3 for k in WORKED}, name="Meera")
    assert fine.get_mentor_notes(ok.id) == {}
