"""SQLite connection helper. No content or secrets live here -- see core/exceptions for errors."""

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schema" / "001_initial_schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    schema_sql = schema_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
    schema_sql = schema_sql.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ")
    conn.executescript(schema_sql)
    conn.commit()
