"""iCalendar (.ics) export of a weekly plan. Pure: the caller supplies everything, no clock."""

from datetime import date, timedelta

from pcc.domain.schemas.weekly_plan_schemas import WeeklyPlan
from pcc.domain.week_schedule import schedule_week


def _escape(text: str) -> str:
    """RFC 5545 text escaping: backslash first, then separators and line breaks."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _event(
    plan_id: int, task_id: str, day: date, summary: str, description: str, stamp: str
) -> list[str]:
    return [
        "BEGIN:VEVENT",
        f"UID:pcc-{plan_id}-{task_id}@placement-career-coach",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "END:VEVENT",
    ]


def build_ics(plan: WeeklyPlan, plan_id: int) -> str:
    """One all-day event per task on its scheduled day, plus the re-check on its due date."""
    stamp = f"{plan.week_start_date:%Y%m%d}T000000Z"  # fixed, so the same plan exports identically
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Placement Career Coach//EN"]
    days, recheck = schedule_week(plan)
    for day in days:
        for task in day.tasks:
            lines += _event(
                plan_id,
                task.task_id,
                day.day,
                f"PCC: {task.title} ({task.estimated_minutes} min)",
                f"{task.description}\nYou're done when: {task.completion_check}",
                stamp,
            )
    if recheck is not None:
        lines += _event(
            plan_id,
            recheck.task_id,
            plan.retest_due_date,
            f"PCC: {recheck.title}",
            f"{recheck.description}\nYou're done when: {recheck.completion_check}",
            stamp,
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
