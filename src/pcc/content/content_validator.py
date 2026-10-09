"""Structural content validation (blueprint Section 11.1).

A thin question bank (fewer than the assessable minimum) is NOT a
validation failure here -- that's an expected, by-design state for
careers whose banks aren't authored yet (Tier B/C). Assessability is a
runtime question answered by content_loader.compute_skill_assessability,
not a build-time error.
"""

import re

from pcc.core.exceptions import ContentValidationError
from pcc.domain.schemas.career_schemas import Career
from pcc.domain.schemas.question_schemas import Question
from pcc.domain.schemas.roadmap_schemas import Roadmap, Skill

_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)


def validate_careers(careers: list[Career]) -> list[str]:
    issues = []
    seen = set()
    for career in careers:
        if career.career_id in seen:
            issues.append(f"careers.json: duplicate career_id '{career.career_id}'")
        seen.add(career.career_id)
    return issues


def validate_skills(skills: list[Skill], careers: list[Career]) -> list[str]:
    issues = []
    known_career_ids = {c.career_id for c in careers}
    seen = set()
    for skill in skills:
        if skill.skill_id in seen:
            issues.append(f"skills.json: duplicate skill_id '{skill.skill_id}'")
        seen.add(skill.skill_id)
        unknown = [cid for cid in skill.career_ids if cid not in known_career_ids]
        if unknown:
            issues.append(
                f"skills.json: skill '{skill.skill_id}' references unknown career_id(s) {unknown}"
            )
    return issues


def validate_roadmap(roadmap: Roadmap, career_skills: list[Skill]) -> list[str]:
    issues = []
    prefix = f"roadmap_templates/{roadmap.career_id}.json"

    semesters_present = sorted({m.semester for m in roadmap.months})
    if semesters_present != [3, 4, 5, 6]:
        issues.append(f"{prefix}: semesters must be exactly [3, 4, 5, 6], got {semesters_present}")

    for semester in (3, 4, 5, 6):
        months_in_semester = [m for m in roadmap.months if m.semester == semester]
        if len(months_in_semester) != 4:
            issues.append(
                f"{prefix}: semester {semester} has {len(months_in_semester)} months, expected 4"
            )

    known_skill_ids = {s.skill_id for s in career_skills}
    roadmap_skill_ids = [m.skill_id for m in roadmap.months]
    for month in roadmap.months:
        if month.skill_id not in known_skill_ids:
            issues.append(
                f"{prefix}: month (sem {month.semester}, month {month.month_index}) "
                f"references unknown skill_id '{month.skill_id}'"
            )
        if not month.focus.strip():
            issues.append(f"{prefix}: skill '{month.skill_id}' is missing a focus")
        if not month.deliverable.strip():
            issues.append(f"{prefix}: skill '{month.skill_id}' is missing a deliverable")

    if len(roadmap_skill_ids) != len(set(roadmap_skill_ids)):
        issues.append(f"{prefix}: a skill_id appears more than once in the roadmap")
    missing = known_skill_ids - set(roadmap_skill_ids)
    if missing:
        issues.append(f"{prefix}: catalog skills missing from the roadmap: {sorted(missing)}")

    return issues


def validate_question_bank(
    questions: list[Question], career_skills: list[Skill], career_id: str
) -> list[str]:
    issues = []
    prefix = f"question_bank/{career_id}.json"
    known_skill_ids = {s.skill_id for s in career_skills}
    seen_ids: set[str] = set()

    for q in questions:
        if q.question_id in seen_ids:
            issues.append(f"{prefix}: duplicate question_id '{q.question_id}'")
        seen_ids.add(q.question_id)

        if q.skill_id not in known_skill_ids:
            issues.append(
                f"{prefix}: question '{q.question_id}' references unknown skill_id '{q.skill_id}'"
            )

        option_ids = [o.option_id for o in q.options]
        if len(option_ids) != len(set(option_ids)):
            issues.append(f"{prefix}: question '{q.question_id}' has duplicate option_ids")
        if q.correct_option_id not in option_ids:
            issues.append(
                f"{prefix}: question '{q.question_id}' correct_option_id "
                f"'{q.correct_option_id}' is not one of its options"
            )

        for field_name, value in (("stem", q.stem), ("explanation", q.explanation)):
            if _URL_PATTERN.search(value):
                issues.append(f"{prefix}: question '{q.question_id}' has a URL in {field_name}")

    return issues


def validate_practice_templates(
    skills: list[Skill], question_banks: dict[str, list[Question]]
) -> list[str]:
    """Templates must target the skill's own tags, hold no URLs, and cover every tag a
    question tests (so the coaching fallback never has to invent content for a real bank)."""
    issues = []
    tested: dict[str, set[str]] = {}
    for questions in question_banks.values():
        for q in questions:
            tested.setdefault(q.skill_id, set()).add(q.concept_tag)

    for skill in skills:
        prefix = f"skills.json: skill '{skill.skill_id}'"
        have = set()
        for template in skill.practice_templates:
            have.add(template.concept_tag)
            if template.concept_tag not in skill.concept_tags:
                issues.append(
                    f"{prefix} template targets unknown concept_tag '{template.concept_tag}'"
                )
            fields = (
                template.title,
                template.action,
                template.success_check,
                template.resource_hint,
            )
            if any(_URL_PATTERN.search(f) for f in fields):
                issues.append(f"{prefix} template '{template.concept_tag}' contains a URL")
        missing = tested.get(skill.skill_id, set()) - have
        if missing:
            issues.append(f"{prefix} has questions but no practice template for {sorted(missing)}")
    return issues


def validate_all(
    careers: list[Career],
    skills: list[Skill],
    roadmaps: dict[str, Roadmap],
    question_banks: dict[str, list[Question]],
) -> None:
    """Raises ContentValidationError listing every issue found, or returns silently."""
    issues: list[str] = []
    issues += validate_careers(careers)
    issues += validate_skills(skills, careers)

    for career in careers:
        career_skills = [s for s in skills if career.career_id in s.career_ids]
        roadmap = roadmaps.get(career.career_id)
        if roadmap is not None:
            issues += validate_roadmap(roadmap, career_skills)
        questions = question_banks.get(career.career_id, [])
        issues += validate_question_bank(questions, career_skills, career.career_id)

    issues += validate_practice_templates(skills, question_banks)

    if issues:
        raise ContentValidationError("\n".join(issues))


def check_installed_content() -> list[str]:
    """Loads everything under data/content/ and returns every problem found (empty = healthy).

    Used at app start-up and by scripts/validate_content.py. Never raises: an unreadable file
    is reported as a problem so the app can show it instead of crashing.
    """
    from pcc.content.content_loader import (
        load_app_settings,
        load_careers,
        load_question_bank,
        load_roadmap_template,
        load_skills,
    )

    try:
        load_app_settings()
        careers = load_careers()
        skills = load_skills()
        roadmaps: dict[str, Roadmap] = {}
        banks: dict[str, list[Question]] = {}
        issues: list[str] = []
        for career in careers:
            try:
                roadmaps[career.career_id] = load_roadmap_template(career.career_id)
            except FileNotFoundError:
                issues.append(f"roadmap_templates/{career.career_id}.json is missing")
            banks[career.career_id] = load_question_bank(career.career_id)
        try:
            validate_all(careers, skills, roadmaps, banks)
        except ContentValidationError as exc:
            issues += str(exc).splitlines()
    except Exception as exc:  # noqa: BLE001 -- any unreadable or malformed file is a finding
        return [f"content could not be loaded ({type(exc).__name__}: {exc})"]
    return issues
