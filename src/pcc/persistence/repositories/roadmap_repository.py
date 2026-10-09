"""roadmaps table access. One active roadmap per profile."""

import sqlite3
from datetime import UTC, datetime

from pcc.domain.schemas.roadmap_schemas import Roadmap


def save_active_roadmap(conn: sqlite3.Connection, profile_id: int, roadmap: Roadmap) -> None:
    conn.execute("UPDATE roadmaps SET is_active = 0 WHERE profile_id = ?", (profile_id,))
    conn.execute(
        "INSERT INTO roadmaps (profile_id, career_id, generation_source, roadmap_json, "
        "is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (
            profile_id,
            roadmap.career_id,
            roadmap.generation_source,
            roadmap.model_dump_json(),
            datetime.now(UTC).isoformat(),
        ),
    )


def get_active_roadmap(conn: sqlite3.Connection, profile_id: int) -> Roadmap | None:
    row = conn.execute(
        "SELECT roadmap_json FROM roadmaps WHERE profile_id = ? AND is_active = 1 "
        "ORDER BY id DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    return Roadmap.model_validate_json(row["roadmap_json"]) if row else None
