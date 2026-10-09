"""Creates data/runtime/pcc.db from schema/001_initial_schema.sql if it doesn't exist."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pcc.core.config import settings
from pcc.persistence.database import get_connection, init_schema


def main() -> None:
    conn = get_connection(settings.db_path)
    init_schema(conn)
    conn.close()
    print(f"Initialized database at {settings.db_path}")


if __name__ == "__main__":
    main()
