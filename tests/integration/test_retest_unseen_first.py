import sqlite3
from datetime import date, timedelta

import pytest

from pcc.content.content_loader import load_question_bank
from pcc.core.exceptions import PccError
from pcc.domain.enums import Level, WorkflowState
from pcc.workflow.workflow_controller import WorkflowController

BANK = {q.question_id: q for q in load_question_bank("devops_engineer")}


class Clock:
    def __init__(self, today: date) -> None:
        self.today = today

    def __call__(self) -> date:
        return self.today

    def advance(self, days: int) -> None:
        self.today += timedelta(days=days)


@pytest.fixture
def clock():
    return Clock(date(2026, 10, 10))


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def _setup(db_path, clock, name="Asha"):
    controller = WorkflowController(db_path, today=clock)
    profile = controller.open_profile(name)
    controller.select_career(profile.id, career_id="devops_engineer", custom_text="", semester=3)
    return controller, profile


def _answer(session, correct_per_skill: int | dict[str, int]):
    seen: dict[str, int] = {}
    selections = {}
    for q in session.questions:
        n = seen.get(q.skill_id, 0)
        seen[q.skill_id] = n + 1
        limit = (
            correct_per_skill
            if isinstance(correct_per_skill, int)
            else correct_per_skill.get(q.skill_id, 0)
        )
        right = BANK[q.question_id].correct_option_id
        selections[q.question_id] = next(
            o.option_id for o in q.options if (o.option_id == right) == (n < limit)
        )
    return selections


def _take(controller, profile, correct_per_skill):
    session = controller.start_assessment(profile.id)
    result = controller.submit_assessment(
        profile.id, session.attempt_id, _answer(session, correct_per_skill)
    )
    return session, result


def _ids(session) -> list[str]:
    return [q.question_id for q in session.questions]


# --- T-17 ---------------------------------------------------------------------------------
def test_t17_retest_uses_unseen_questions_and_has_no_duplicates(db_path, clock):
    controller, profile = _setup(db_path, clock)
    first, _ = _take(controller, profile, 1)
    second, _ = _take(controller, profile, 3)
    assert not set(_ids(first)) & set(_ids(second))  # bank holds 2 per difficulty per skill
    assert len(_ids(second)) == len(set(_ids(second))) == 12


def test_t17_third_check_reuses_the_least_recently_seen_without_duplicates(db_path, clock):
    controller, profile = _setup(db_path, clock)
    first, _ = _take(controller, profile, 1)
    clock.advance(7)
    second, _ = _take(controller, profile, 2)
    third, _ = _take(controller, profile, 3)
    assert len(set(_ids(third))) == 12
    assert set(_ids(third)) == set(_ids(first))  # the oldest-seen questions come back first


def test_retest_is_recorded_as_a_retest_attempt(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    session, result = _take(controller, profile, 2)
    assert session.attempt_type == "retest" and result.attempt_type == "retest"
    conn = sqlite3.connect(db_path)
    types = [r[0] for r in conn.execute("SELECT attempt_type FROM assessment_attempts ORDER BY id")]
    conn.close()
    assert types == ["baseline", "retest"]


def test_an_open_retest_resumes_with_the_same_questions(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    opened = controller.start_assessment(profile.id)
    assert WorkflowController(db_path, today=clock).start_assessment(profile.id) == opened


# --- weekly plan --------------------------------------------------------------------------
def test_weekly_plan_is_created_with_the_check_and_ends_in_weekly_state(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(
        controller,
        profile,
        {
            "linux_fundamentals": 1,
            "shell_scripting": 1,
            "python_for_automation": 2,
            "git_version_control": 2,
        },
    )
    view = controller.get_weekly_plan(profile.id)
    assert 3 <= len(view.plan.tasks) <= 5
    assert view.plan.tasks[-1].kind == "recheck"
    assert view.plan.retest_due_date == date(2026, 10, 17)
    assert sum(t.estimated_minutes for t in view.plan.tasks) <= 240
    assert [t.kind for t in view.plan.tasks].count("coaching") == 2
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE
    assert not view.retest_due and view.days_until_retest == 7


def test_weekly_plan_with_no_gap_moves_ahead_on_the_roadmap(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 3)
    titles = [t.title for t in controller.get_weekly_plan(profile.id).plan.tasks]
    assert "Start next: Networking Fundamentals" in titles


def test_t18_everything_is_restored_after_reopening(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _, result = _take(controller, profile, 1)
    plan_id = controller.get_weekly_plan(profile.id).plan_id
    controller.set_task_done(profile.id, plan_id, "coaching_1", True)

    reopened = WorkflowController(db_path, today=clock)
    again = reopened.open_profile("Asha")
    assert again.career_id == "devops_engineer" and again.current_semester == 3
    assert reopened.get_roadmap(profile.id) is not None
    assert reopened.get_latest_results(profile.id) == result
    assert reopened.get_coaching_plan(profile.id) is not None
    restored = reopened.get_weekly_plan(profile.id)
    assert restored.plan == controller.get_weekly_plan(profile.id).plan
    assert restored.done_task_ids == ["coaching_1"]


def test_task_completion_can_be_ticked_and_unticked(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    plan_id = controller.get_weekly_plan(profile.id).plan_id
    controller.set_task_done(profile.id, plan_id, "coaching_1", True)
    controller.set_task_done(profile.id, plan_id, "recheck_1", True)
    assert controller.get_weekly_plan(profile.id).done_task_ids == ["coaching_1", "recheck_1"]
    controller.set_task_done(profile.id, plan_id, "coaching_1", False)
    assert controller.get_weekly_plan(profile.id).done_task_ids == ["recheck_1"]
    with pytest.raises(PccError, match="Unknown task"):
        controller.set_task_done(profile.id, plan_id, "nope", True)
    with pytest.raises(PccError, match="no longer current"):
        controller.set_task_done(profile.id, plan_id + 99, "coaching_1", True)


def test_a_retest_replaces_the_weekly_plan_and_progress_is_tracked(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    old_plan = controller.get_weekly_plan(profile.id)
    clock.advance(7)
    _take(controller, profile, 2)
    new_plan = controller.get_weekly_plan(profile.id)
    assert new_plan.plan_id != old_plan.plan_id
    assert new_plan.plan.week_start_date == date(2026, 10, 17)
    with pytest.raises(PccError, match="no longer current"):
        controller.set_task_done(profile.id, old_plan.plan_id, "coaching_1", True)


# --- re-check timing ----------------------------------------------------------------------
def test_recheck_becomes_due_after_the_retest_interval(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    clock.advance(6)
    assert not controller.get_weekly_plan(profile.id).retest_due
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE
    clock.advance(1)
    view = controller.get_weekly_plan(profile.id)
    assert view.retest_due and view.days_until_retest == 0
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.RETEST_DUE


def test_a_due_recheck_can_be_started_and_submitted(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    clock.advance(8)
    controller.sync_state(profile.id)
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.RETEST_DUE
    session, _ = _take(controller, profile, 2)
    assert session.attempt_type == "retest"
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE


def test_an_early_recheck_is_allowed(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)  # same day: re-check is 7 days away
    session, _ = _take(controller, profile, 2)
    assert session.attempt_type == "retest"


def test_cannot_start_a_second_baseline_or_check_before_a_first(db_path, clock):
    controller = WorkflowController(db_path, today=clock)
    profile = controller.open_profile("Ravi")
    with pytest.raises(PccError):
        controller.start_assessment(profile.id)


# --- progress -----------------------------------------------------------------------------
def test_progress_after_a_baseline_has_no_comparison(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    view = controller.get_progress(profile.id)
    assert len(view.attempts) == 1 and view.deltas == [] and view.overall_delta is None


def test_progress_shows_improvement_between_checks(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 0)  # everything wrong -> below 40, mentor prompt
    after_baseline = controller.get_progress(profile.id)
    assert sorted(after_baseline.mentor_skill_ids) == sorted(
        ["linux_fundamentals", "shell_scripting", "python_for_automation", "git_version_control"]
    )
    clock.advance(7)
    _take(controller, profile, 3)  # everything right
    view = controller.get_progress(profile.id)
    assert [a.attempt_type for a in view.attempts] == ["baseline", "retest"]
    assert (view.previous_level, view.current_level) == (Level.BEGINNER, Level.ADVANCED)
    assert view.overall_delta == pytest.approx(100.0)
    assert {d.direction for d in view.deltas} == {"up"}
    assert view.mentor_skill_ids == [] and view.skills_below_mastery == 0


def test_progress_is_empty_before_any_check(db_path, clock):
    controller, profile = _setup(db_path, clock)
    assert controller.get_progress(profile.id).attempts == []


# --- profiles saved before the weekly plan existed ------------------------------------------
def test_a_profile_stuck_at_coaching_ready_gets_its_weekly_plan(db_path, clock):
    controller, profile = _setup(db_path, clock)
    _take(controller, profile, 1)
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM weekly_plans")
    conn.execute("UPDATE profiles SET workflow_state = 'coaching_ready'")
    conn.commit()
    conn.close()

    view = WorkflowController(db_path, today=clock).get_weekly_plan(profile.id)
    assert view is not None and 3 <= len(view.plan.tasks) <= 5
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE
