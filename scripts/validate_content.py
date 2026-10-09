"""Validates data/content/ against the rules in blueprint Section 11.1.

Fails the build (non-zero exit) on any structural issue. A thin
question bank is not an issue -- see content_loader.compute_skill_assessability.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pcc.content.content_loader import load_careers, load_skills
from pcc.content.content_validator import check_installed_content


def main() -> int:
    issues = check_installed_content()
    if issues:
        print("Content validation FAILED:\n")
        print("\n".join(issues))
        return 1
    print(f"Content validation passed: {len(load_careers())} careers, {len(load_skills())} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
