"""Roadmap validation rules V-RM-01..08 (blueprint Section 9.2). Pure; returns rule violations.

V-RM-06 (prerequisites before dependants) is enforced through V-RM-04: the skill
sequence is fixed to the curated template, which already respects prerequisites.
"""

import re

from pcc.domain.schemas.roadmap_schemas import Roadmap

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)


def validate_roadmap(
    candidate: Roadmap, template: Roadmap, catalog_skill_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    months = candidate.months

    if sorted({m.semester for m in months}) != [3, 4, 5, 6]:
        errors.append("V-RM-01: semesters must be exactly 3, 4, 5, 6")
    if len(months) != 16 or any(
        sum(1 for m in months if m.semester == s) != 4 for s in (3, 4, 5, 6)
    ):
        errors.append("V-RM-02: exactly 4 months per semester (16 total) are required")

    unknown = sorted({m.skill_id for m in months if m.skill_id not in catalog_skill_ids})
    if unknown:
        errors.append(f"V-RM-03: unknown skill_id(s) {unknown}")

    if candidate.skill_ids_in_order() != template.skill_ids_in_order():
        errors.append("V-RM-04: skill sequence differs from the curated template")

    ids = [m.skill_id for m in months]
    if len(ids) != len(set(ids)) or set(ids) != catalog_skill_ids:
        errors.append("V-RM-05: every catalog skill must appear exactly once")

    for m in months:
        where = f"sem {m.semester} month {m.month_index}"
        if not m.focus.strip() or not m.deliverable.strip() or len(m.topics) < 2:
            errors.append(f"V-RM-07: {where} needs a focus, 2+ topics and a deliverable")
        text = " ".join([m.focus, m.deliverable, *m.topics])
        if _URL.search(text):
            errors.append(f"V-RM-08: {where} contains a URL")
    return errors
