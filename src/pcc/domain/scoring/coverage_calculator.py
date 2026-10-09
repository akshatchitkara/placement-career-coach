"""Section 10.4 coverage gate: share of a career's core skills with sufficient evidence.

Callers pass the full career's core (quiz-assessable) skill_ids as the
denominator -- a single-semester attempt only covers a quarter of them,
which is precisely why it caps at Advanced (T-03).
"""

from pcc.domain.schemas.assessment_schemas import SkillScore


def compute_coverage_ratio(skill_scores: dict[str, SkillScore], core_skill_ids: list[str]) -> float:
    if not core_skill_ids:
        return 0.0
    evidenced = sum(
        1
        for skill_id in core_skill_ids
        if skill_id in skill_scores and skill_scores[skill_id].has_sufficient_evidence
    )
    return evidenced / len(core_skill_ids)
