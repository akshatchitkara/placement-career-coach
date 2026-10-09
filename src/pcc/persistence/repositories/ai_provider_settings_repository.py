"""Reads/writes the single active row in ai_provider_settings. Never logs api_key."""

import sqlite3
from datetime import UTC, datetime

from pcc.ai.provider_config import AiProviderConfig


def get_active_config(conn: sqlite3.Connection) -> AiProviderConfig:
    row = conn.execute(
        "SELECT provider_type, base_url, api_key, model_name FROM ai_provider_settings "
        "WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return AiProviderConfig()
    return AiProviderConfig(
        provider_type=row["provider_type"],
        base_url=row["base_url"],
        api_key=row["api_key"],
        model_name=row["model_name"],
    )


def save_config(conn: sqlite3.Connection, config: AiProviderConfig) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute("UPDATE ai_provider_settings SET is_active = 0")
    conn.execute(
        "INSERT INTO ai_provider_settings "
        "(provider_type, base_url, api_key, model_name, is_active, updated_at, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?, ?)",
        (config.provider_type, config.base_url, config.api_key, config.model_name, now, now),
    )
    conn.commit()
