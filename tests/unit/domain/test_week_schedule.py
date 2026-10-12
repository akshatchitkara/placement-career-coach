from datetime import date

import pytest

from pcc.domain.calendar_export import build_ics
from pcc.domain.schemas.weekly_plan_schemas import WeeklyPlan, WeeklyTask
from pcc.domain.week_schedule import schedule_week


def _task(task_id: str, kind: str = "coaching", minutes: int = 30) -> WeeklyTask:
    return WeeklyTask(
        task_id=task_id,
        kind=kind,  # type: ignore[arg-type]
        title=f"Task {task_id}",
        description="Do the thing, then check it.",
        estimated_minutes=minutes,
        completion_check="Explain it; no notes.",
    )


def _plan(n_study: int) -> WeeklyPlan:
    tasks = [_task(f"t{i}") for i in range(n_study)] + [_task("recheck_1", "recheck", 20)]
    return WeeklyPlan(
        week_start_date=date(2026, 10, 12), retest_due_date=date(2026, 10, 19), tasks=tasks
    )


@pytest.mark.parametrize("n_study", [1, 2, 3, 4])
def test_every_study_task_lands_on_exactly_one_of_seven_days(n_study):
    days, recheck = schedule_week(_plan(n_study))
    assert [d.day for d in days] == [date(2026, 10, 12 + i) for i in range(7)]
    placed = [t.task_id for d in days for t in d.tasks]
    assert placed == [f"t{i}" for i in range(n_study)]  # none lost, priority order kept
    assert recheck is not None and recheck.task_id == "recheck_1"


def test_tasks_are_spread_not_piled_on_one_day():
    days, _ = schedule_week(_plan(3))
    assert [len(d.tasks) for d in days] == [1, 0, 1, 0, 1, 0, 0]
    assert max(len(d.tasks) for d in days) == 1


def test_scheduling_is_deterministic_and_handles_no_recheck():
    plan = _plan(3).model_copy(update={"tasks": _plan(3).tasks[:-1]})
    assert schedule_week(plan) == schedule_week(plan)
    assert schedule_week(plan)[1] is None


def test_day_minutes_add_up():
    days, _ = schedule_week(_plan(2))
    assert sum(d.minutes for d in days) == 60


def test_ics_has_one_event_per_task_and_the_recheck_on_its_due_date():
    ics = build_ics(_plan(3), plan_id=7)
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert ics.count("BEGIN:VEVENT") == 4
    assert "DTSTART;VALUE=DATE:20261012" in ics  # first task, first day
    assert "DTSTART;VALUE=DATE:20261019" in ics  # re-check on the due date
    assert "DTEND;VALUE=DATE:20261020" in ics
    assert "UID:pcc-7-recheck_1@placement-career-coach" in ics
    assert build_ics(_plan(3), plan_id=7) == ics  # identical on every export


def test_ics_escapes_special_characters():
    plan = _plan(1)
    plan.tasks[0].description = "Read a, b; c\nthen d \\ e"
    assert "Read a\\, b\\; c\\nthen d \\\\ e" in build_ics(plan, plan_id=1)
