"""Recreates the database and seeds the demo profiles (Asha, Ravi, Meera).

DELETES the database file. To avoid wiping real work by accident it refuses to run if the
database holds any profile other than the three demo ones, unless --force is given.
"""

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pcc.core.config import settings
from pcc.workflow.demo_seed import DEMO_NAMES, seed_demo_profiles


def _other_profiles(db_file: Path) -> list[str]:
    if not db_file.exists():
        return []
    try:
        conn = sqlite3.connect(db_file)
        names = [r[0] for r in conn.execute("SELECT display_name FROM profiles")]
        conn.close()
    except sqlite3.Error:
        return []  # unreadable or not our schema: nothing worth protecting
    return [n for n in names if n not in DEMO_NAMES]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--force", action="store_true", help="delete even if other profiles exist")
    args = parser.parse_args()

    db_file = Path(settings.db_path)
    others = _other_profiles(db_file)
    if others and not args.force:
        print(
            f"Refusing to delete {db_file}: it holds other profiles ({', '.join(others)}).\n"
            "Re-run with --force if you really want to discard them."
        )
        return 1

    for suffix in ("", "-wal", "-shm"):
        Path(str(db_file) + suffix).unlink(missing_ok=True)
    seed_demo_profiles(settings.db_path, datetime.now(UTC).date())
    print(f"Database reset at {db_file} with demo profiles: {', '.join(DEMO_NAMES)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
