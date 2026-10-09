"""Recreates the database and seeds demo profiles (Asha, Ravi, Meera) for a repeatable demo.

Seeding is M1+ scope (needs careers/roadmaps to exist first) -- this stub
only resets the schema so `make db-reset` is safe to run from M0 onward.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pcc.core.config import settings
from pcc.persistence.database import get_connection, init_schema


def main() -> None:
    db_file = Path(settings.db_path)
    if db_file.exists():
        db_file.unlink()
    conn = get_connection(settings.db_path)
    init_schema(conn)
    conn.close()
    print(f"Database reset at {settings.db_path}. Demo profile seeding lands in M1+.")


if __name__ == "__main__":
    main()
