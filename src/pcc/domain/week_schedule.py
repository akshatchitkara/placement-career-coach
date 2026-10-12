"""Spreads a weekly plan over its seven days. Pure and deterministic; presentation only.

The plan's tasks and their order come from the builder; this only decides which day each one
sits on, so the week reads as a schedule instead of a list. The re-check is kept apart because
it falls on the due date, which is the day after the seven study days.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from pcc.domain.schemas.weekly_plan_schemas import WeeklyPlan, WeeklyTask

DAYS_IN_WEEK = 7


@dataclass(frozen=True)
class DayPlan:
    day: date
    tasks: list[WeeklyTask]

    @property
    def minutes(self) -> int:
        return sum(t.estimated_minutes for t in self.tasks)


def schedule_week(plan: WeeklyPlan) -> tuple[list[DayPlan], WeeklyTask | None]:
    """(seven days starting at week_start_date, the re-check task or None)."""
    study = [t for t in plan.tasks if t.kind != "recheck"]
    recheck = next((t for t in plan.tasks if t.kind == "recheck"), None)
    slots: list[list[WeeklyTask]] = [[] for _ in range(DAYS_IN_WEEK)]
    for index, task in enumerate(study):
        slots[index * DAYS_IN_WEEK // max(len(study), 1)].append(task)  # evenly spaced
    days = [
        DayPlan(plan.week_start_date + timedelta(days=offset), tasks)
        for offset, tasks in enumerate(slots)
    ]
    return days, recheck
