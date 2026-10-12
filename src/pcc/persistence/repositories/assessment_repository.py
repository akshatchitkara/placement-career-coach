"""assessment_attempts / assessment_responses / skill_scores access."""

import json
import sqlite3
from datetime import UTC, datetime

from pydantic import BaseModel

from pcc.domain.schemas.assessment_schemas import Answer, EvaluationResult


class AttemptRecord(BaseModel):
    id: int
    profile_id: int
    attempt_type: str
    scope_description: str
    shuffle_seed: int
    config_snapshot_json: str
    submitted: bool
    submitted_at: str | None = None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_record(row: sqlite3.Row) -> AttemptRecord:
    return AttemptRecord(
        id=row["id"],
        profile_id=row["profile_id"],
        attempt_type=row["attempt_type"],
        scope_description=row["scope_description"] or "",
        shuffle_seed=row["shuffle_seed"],
        config_snapshot_json=row["config_snapshot_json"],
        submitted=row["submitted_at"] is not None,
        submitted_at=row["submitted_at"],
    )


def create_attempt(
    conn: sqlite3.Connection,
    profile_id: int,
    *,
    attempt_type: str,
    scope_description: str,
    shuffle_seed: int,
    config_snapshot_json: str,
    started_at: str | None = None,
) -> int:
    now = started_at or _now()
    cursor = conn.execute(
        "INSERT INTO assessment_attempts (profile_id, attempt_type, scope_description, "
        "shuffle_seed, started_at, config_snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (profile_id, attempt_type, scope_description, shuffle_seed, now, config_snapshot_json, now),
    )
    return int(cursor.lastrowid or 0)


def get_attempt(conn: sqlite3.Connection, attempt_id: int) -> AttemptRecord | None:
    row = conn.execute("SELECT * FROM assessment_attempts WHERE id = ?", (attempt_id,)).fetchone()
    return _to_record(row) if row else None


def get_open_attempt(conn: sqlite3.Connection, profile_id: int) -> AttemptRecord | None:
    row = conn.execute(
        "SELECT * FROM assessment_attempts WHERE profile_id = ? AND submitted_at IS NULL "
        "ORDER BY id DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    return _to_record(row) if row else None


def get_latest_submitted_attempt(conn: sqlite3.Connection, profile_id: int) -> AttemptRecord | None:
    row = conn.execute(
        "SELECT * FROM assessment_attempts WHERE profile_id = ? AND submitted_at IS NOT NULL "
        "ORDER BY submitted_at DESC, id DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    return _to_record(row) if row else None


def list_submitted_attempts(conn: sqlite3.Connection, profile_id: int) -> list[AttemptRecord]:
    rows = conn.execute(
        "SELECT * FROM assessment_attempts WHERE profile_id = ? AND submitted_at IS NOT NULL "
        "ORDER BY submitted_at ASC, id ASC",
        (profile_id,),
    ).fetchall()
    return [_to_record(r) for r in rows]


def seen_question_ids_oldest_first(conn: sqlite3.Connection, profile_id: int) -> list[str]:
    """Question ids from submitted attempts, ordered by when each was last seen."""
    rows = conn.execute(
        "SELECT r.question_id AS question_id, MAX(a.submitted_at) AS last_seen "
        "FROM assessment_responses r JOIN assessment_attempts a ON a.id = r.attempt_id "
        "WHERE a.profile_id = ? AND a.submitted_at IS NOT NULL "
        "GROUP BY r.question_id ORDER BY last_seen ASC, r.question_id ASC",
        (profile_id,),
    ).fetchall()
    return [r["question_id"] for r in rows]


def load_answers(conn: sqlite3.Connection, attempt_id: int) -> list[Answer]:
    rows = conn.execute(
        "SELECT question_id, selected_option_id FROM assessment_responses "
        "WHERE attempt_id = ? ORDER BY id",
        (attempt_id,),
    ).fetchall()
    return [
        Answer(question_id=r["question_id"], selected_option_id=r["selected_option_id"])
        for r in rows
    ]


def save_submission(
    conn: sqlite3.Connection,
    attempt_id: int,
    *,
    answers: list[Answer],
    correct_by_question: dict[str, bool],
    displayed_order_by_question: dict[str, list[str]],
    result: EvaluationResult,
    submitted_at: str | None = None,
) -> None:
    now = submitted_at or _now()
    for answer in answers:
        conn.execute(
            "INSERT INTO assessment_responses (attempt_id, question_id, selected_option_id, "
            "is_correct, displayed_order_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                attempt_id,
                answer.question_id,
                answer.selected_option_id,
                int(correct_by_question[answer.question_id]),
                json.dumps(displayed_order_by_question[answer.question_id]),
                now,
            ),
        )
    for score in result.skill_scores:
        conn.execute(
            "INSERT INTO skill_scores (attempt_id, skill_id, correct_count, answered_count, "
            "score, has_sufficient_evidence, is_weakest, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt_id,
                score.skill_id,
                score.correct_count,
                score.answered_count,
                score.score,
                int(score.has_sufficient_evidence),
                int(score.is_weakest),
                now,
            ),
        )
    conn.execute(
        "UPDATE assessment_attempts SET submitted_at = ?, overall_score = ?, level = ?, "
        "level_notes_json = ?, coverage_ratio = ? WHERE id = ?",
        (
            now,
            result.overall_score,
            result.level.value,
            json.dumps(result.level_notes),
            result.coverage_ratio,
            attempt_id,
        ),
    )


def save_draft(conn: sqlite3.Connection, attempt_id: int, answers: dict[str, str]) -> None:
    conn.execute(
        "INSERT INTO assessment_drafts (attempt_id, answers_json, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(attempt_id) DO UPDATE SET answers_json = excluded.answers_json, "
        "updated_at = excluded.updated_at",
        (attempt_id, json.dumps(answers, sort_keys=True), _now()),
    )


def load_draft(conn: sqlite3.Connection, attempt_id: int) -> dict[str, str]:
    row = conn.execute(
        "SELECT answers_json FROM assessment_drafts WHERE attempt_id = ?", (attempt_id,)
    ).fetchone()
    if row is None:
        return {}
    try:
        loaded = json.loads(row["answers_json"])
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in loaded.items()} if isinstance(loaded, dict) else {}


def delete_draft(conn: sqlite3.Connection, attempt_id: int) -> None:
    conn.execute("DELETE FROM assessment_drafts WHERE attempt_id = ?", (attempt_id,))
