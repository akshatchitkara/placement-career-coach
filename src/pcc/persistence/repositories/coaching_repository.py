"""coaching_plans table access. One active plan per profile; older ones are superseded."""

import sqlite3
from datetime import UTC, datetime

from pcc.domain.schemas.coaching_schemas import CoachingPlan


def save_active_plan(
    conn: sqlite3.Connection, profile_id: int, attempt_id: int, plan: CoachingPlan
) -> None:
    conn.execute(
        "UPDATE coaching_plans SET status = 'superseded' "
        "WHERE profile_id = ? AND status = 'active'",
        (profile_id,),
    )
    conn.execute(
        "INSERT INTO coaching_plans (profile_id, attempt_id, skill_id, generation_source, "
        "plan_json, status, created_at) VALUES (?, ?, ?, ?, ?, 'active', ?)",
        (
            profile_id,
            attempt_id,
            plan.skill_id,
            plan.generation_source,
            plan.model_dump_json(),
            datetime.now(UTC).isoformat(),
        ),
    )


def get_active_plan(conn: sqlite3.Connection, profile_id: int) -> CoachingPlan | None:
    row = conn.execute(
        "SELECT plan_json FROM coaching_plans WHERE profile_id = ? AND status = 'active' "
        "ORDER BY id DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    return CoachingPlan.model_validate_json(row["plan_json"]) if row else None
