"""weekly_plans table access. The newest row is the current week's plan."""

import json
import sqlite3
from datetime import UTC, datetime

from pcc.domain.schemas.weekly_plan_schemas import WeeklyPlan


def save_weekly_plan(
    conn: sqlite3.Connection, profile_id: int, attempt_id: int, plan: WeeklyPlan
) -> None:
    conn.execute(
        "INSERT INTO weekly_plans (profile_id, attempt_id, week_start_date, retest_due_date, "
        "plan_json, tasks_done_json, created_at) VALUES (?, ?, ?, ?, ?, '[]', ?)",
        (
            profile_id,
            attempt_id,
            plan.week_start_date.isoformat(),
            plan.retest_due_date.isoformat(),
            plan.model_dump_json(),
            datetime.now(UTC).isoformat(),
        ),
    )


def get_latest_weekly_plan(
    conn: sqlite3.Connection, profile_id: int
) -> tuple[int, WeeklyPlan, list[str]] | None:
    row = conn.execute(
        "SELECT id, plan_json, tasks_done_json FROM weekly_plans WHERE profile_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    if row is None:
        return None
    return (
        row["id"],
        WeeklyPlan.model_validate_json(row["plan_json"]),
        json.loads(row["tasks_done_json"]),
    )


def set_done_task_ids(conn: sqlite3.Connection, plan_id: int, done_task_ids: list[str]) -> None:
    conn.execute(
        "UPDATE weekly_plans SET tasks_done_json = ? WHERE id = ?",
        (json.dumps(sorted(set(done_task_ids))), plan_id),
    )


def update_weekly_plan(
    conn: sqlite3.Connection, plan_id: int, plan: WeeklyPlan, done_task_ids: list[str]
) -> None:
    """Replaces a week's tasks in place (same week, same re-check date), keeping valid ticks."""
    conn.execute(
        "UPDATE weekly_plans SET plan_json = ?, tasks_done_json = ? WHERE id = ?",
        (plan.model_dump_json(), json.dumps(sorted(set(done_task_ids))), plan_id),
    )


def list_weekly_plans(
    conn: sqlite3.Connection, profile_id: int
) -> list[tuple[int, WeeklyPlan, list[str]]]:
    """(attempt_id, plan, done task ids) for every saved week, oldest first."""
    rows = conn.execute(
        "SELECT attempt_id, plan_json, tasks_done_json FROM weekly_plans "
        "WHERE profile_id = ? ORDER BY id ASC",
        (profile_id,),
    ).fetchall()
    return [
        (
            row["attempt_id"],
            WeeklyPlan.model_validate_json(row["plan_json"]),
            json.loads(row["tasks_done_json"]),
        )
        for row in rows
    ]
