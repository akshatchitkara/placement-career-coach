"""Section 10.4. Lower-bound level rule plus the Industry-ready skill and coverage gates."""

from pcc.domain.enums import Level
from pcc.domain.schemas.assessment_schemas import SkillScore


def classify_level(
    overall_score: float,
    skill_scores: dict[str, SkillScore],
    coverage_ratio: float,
    level_lower_bounds: dict[str, float],
    industry_ready_min_skill_score: float,
) -> tuple[Level, list[str]]:
    if overall_score >= level_lower_bounds["industry_ready"]:
        level = Level.INDUSTRY_READY
    elif overall_score >= level_lower_bounds["advanced"]:
        level = Level.ADVANCED
    elif overall_score >= level_lower_bounds["intermediate"]:
        level = Level.INTERMEDIATE
    else:
        level = Level.BEGINNER

    notes: list[str] = []
    if level != Level.INDUSTRY_READY:
        return level, notes

    failing_skills = sorted(
        s.skill_id
        for s in skill_scores.values()
        if s.has_sufficient_evidence and s.score < industry_ready_min_skill_score
    )
    coverage_gate_passed = coverage_ratio >= 1.0

    if failing_skills:
        notes.append(
            "Industry-ready requires every evidenced skill to score at least "
            f"{industry_ready_min_skill_score}; {', '.join(failing_skills)} did not meet this bar."
        )
    if not coverage_gate_passed:
        notes.append(
            "Industry-ready requires evidence across 100% of the career's core skills; "
            "this attempt's scope did not cover them all -- take the full-path check."
        )

    if failing_skills or not coverage_gate_passed:
        return Level.ADVANCED, notes
    return Level.INDUSTRY_READY, notes
