"""profiles table access. Display names only -- no other personal data is stored."""

import sqlite3
from datetime import UTC, datetime

from pydantic import BaseModel

from pcc.domain.enums import WorkflowState


class Profile(BaseModel):
    id: int
    display_name: str
    career_id: str | None
    current_semester: int | None
    workflow_state: WorkflowState


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_profile(row: sqlite3.Row) -> Profile:
    return Profile(
        id=row["id"],
        display_name=row["display_name"],
        career_id=row["career_id"],
        current_semester=row["current_semester"],
        workflow_state=WorkflowState(row["workflow_state"].lower()),
    )


def get_profile(conn: sqlite3.Connection, profile_id: int) -> Profile | None:
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return _to_profile(row) if row else None


def list_profiles(conn: sqlite3.Connection) -> list[Profile]:
    rows = conn.execute("SELECT * FROM profiles ORDER BY last_active_at DESC, id DESC").fetchall()
    return [_to_profile(r) for r in rows]


def get_or_create_profile(conn: sqlite3.Connection, display_name: str) -> Profile:
    row = conn.execute("SELECT * FROM profiles WHERE display_name = ?", (display_name,)).fetchone()
    if row is None:
        now = _now()
        conn.execute(
            "INSERT INTO profiles (display_name, workflow_state, last_active_at, created_at) "
            "VALUES (?, ?, ?, ?)",
            (display_name, WorkflowState.PROFILE_READY.value, now, now),
        )
    else:
        conn.execute("UPDATE profiles SET last_active_at = ? WHERE id = ?", (_now(), row["id"]))
    conn.commit()
    row = conn.execute("SELECT * FROM profiles WHERE display_name = ?", (display_name,)).fetchone()
    return _to_profile(row)


def update_career_and_state(
    conn: sqlite3.Connection,
    profile_id: int,
    *,
    career_id: str,
    semester: int,
    state: WorkflowState,
) -> None:
    conn.execute(
        "UPDATE profiles SET career_id = ?, current_semester = ?, workflow_state = ?, "
        "last_active_at = ? WHERE id = ?",
        (career_id, semester, state.value, _now(), profile_id),
    )


def set_workflow_state(conn: sqlite3.Connection, profile_id: int, state: WorkflowState) -> None:
    conn.execute(
        "UPDATE profiles SET workflow_state = ?, last_active_at = ? WHERE id = ?",
        (state.value, _now(), profile_id),
    )
