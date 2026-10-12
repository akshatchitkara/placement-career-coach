"""coaching_plans table access. One active plan per profile; older ones are superseded."""

import sqlite3
from datetime import UTC, datetime

from pcc.domain.schemas.coaching_schemas import CoachingPlan
from pcc.domain.schemas.tutor_schemas import TutorMessage


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


def get_active_plan_id(conn: sqlite3.Connection, profile_id: int) -> int | None:
    row = conn.execute(
        "SELECT id FROM coaching_plans WHERE profile_id = ? AND status = 'active' "
        "ORDER BY id DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    return int(row["id"]) if row else None


def add_message(
    conn: sqlite3.Connection,
    profile_id: int,
    plan_id: int,
    task_order: int,
    *,
    role: str,
    kind: str,
    content: str,
    generation_source: str,
) -> None:
    conn.execute(
        "INSERT INTO coaching_messages (profile_id, coaching_plan_id, task_order, role, kind, "
        "content, generation_source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            profile_id,
            plan_id,
            task_order,
            role,
            kind,
            content,
            generation_source,
            datetime.now(UTC).isoformat(),
        ),
    )


def list_messages(conn: sqlite3.Connection, plan_id: int, task_order: int) -> list[TutorMessage]:
    rows = conn.execute(
        "SELECT role, kind, content, generation_source FROM coaching_messages "
        "WHERE coaching_plan_id = ? AND task_order = ? ORDER BY id ASC",
        (plan_id, task_order),
    ).fetchall()
    return [TutorMessage(**dict(r)) for r in rows]
