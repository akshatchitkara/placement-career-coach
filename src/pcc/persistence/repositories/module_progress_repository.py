"""Module quiz results and the career wish list. Neither is read by scoring."""

import sqlite3
from datetime import UTC, datetime

from pydantic import BaseModel


class ModuleProgress(BaseModel):
    skill_id: str
    best_correct: int
    attempts: int
    passed: bool


def get_module_progress(conn: sqlite3.Connection, profile_id: int) -> dict[str, ModuleProgress]:
    rows = conn.execute(
        "SELECT skill_id, best_correct, attempts, passed_at FROM module_progress "
        "WHERE profile_id = ?",
        (profile_id,),
    ).fetchall()
    return {
        r["skill_id"]: ModuleProgress(
            skill_id=r["skill_id"],
            best_correct=r["best_correct"],
            attempts=r["attempts"],
            passed=r["passed_at"] is not None,
        )
        for r in rows
    }


def record_module_attempt(
    conn: sqlite3.Connection, profile_id: int, skill_id: str, correct: int, passed: bool
) -> None:
    """Counts the attempt, keeps the best score, and stamps passed_at only the first time."""
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO module_progress "
        "(profile_id, skill_id, best_correct, attempts, passed_at, updated_at) "
        "VALUES (?, ?, ?, 1, ?, ?) "
        "ON CONFLICT(profile_id, skill_id) DO UPDATE SET "
        "best_correct = MAX(best_correct, excluded.best_correct), "
        "attempts = attempts + 1, "
        "passed_at = COALESCE(passed_at, excluded.passed_at), "
        "updated_at = excluded.updated_at",
        (profile_id, skill_id, correct, now if passed else None, now),
    )


def add_career_request(conn: sqlite3.Connection, profile_id: int, text: str) -> None:
    conn.execute(
        "INSERT INTO career_requests (profile_id, requested_text, created_at) VALUES (?, ?, ?)",
        (profile_id, text, datetime.now(UTC).isoformat()),
    )
