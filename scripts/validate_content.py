"""Validates data/content/ against the rules in blueprint Section 11.1.

No curated content exists yet (M1 scope) -- this stub runs cleanly as a
no-op so `make validate-content` never breaks the build before M1 lands.
"""

import sys
from pathlib import Path

_CONTENT_DIR = Path(__file__).resolve().parents[1] / "data" / "content"


def main() -> int:
    if not any(_CONTENT_DIR.glob("*.json")):
        print("No content files yet (M1 scope) -- nothing to validate.")
        return 0
    print("Content validation rules are not implemented yet (M1 scope).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
