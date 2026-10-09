from pcc.persistence.database import get_connection, init_schema


def test_init_schema_is_idempotent(tmp_path):
    db_path = tmp_path / "pcc.db"
    conn = get_connection(str(db_path))

    init_schema(conn)
    init_schema(conn)

    table_count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='profiles'"
    ).fetchone()[0]
    conn.close()

    assert table_count == 1
