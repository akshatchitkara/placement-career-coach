"""Validates data/content/ against the rules in blueprint Section 11.1.

Fails the build (non-zero exit) on any structural issue. A thin
question bank is not an issue -- see content_loader.compute_skill_assessability.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pcc.content.content_loader import (
    load_careers,
    load_question_bank,
    load_roadmap_template,
    load_skills,
)
from pcc.content.content_validator import validate_all
from pcc.core.exceptions import ContentValidationError


def main() -> int:
    careers = load_careers()
    skills = load_skills()
    roadmaps = {}
    question_banks = {}
    for career in careers:
        try:
            roadmaps[career.career_id] = load_roadmap_template(career.career_id)
        except FileNotFoundError:
            print(f"WARNING: no roadmap template for '{career.career_id}' yet")
        question_banks[career.career_id] = load_question_bank(career.career_id)

    try:
        validate_all(careers, skills, roadmaps, question_banks)
    except ContentValidationError as exc:
        print("Content validation FAILED:\n")
        print(str(exc))
        return 1

    print(f"Content validation passed: {len(careers)} careers, {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
