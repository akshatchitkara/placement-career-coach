"""Section 10.5. Never invent a weakest skill when the evidence doesn't support one."""

from pcc.domain.schemas.assessment_schemas import SkillScore, WeakestSkillOutcome


def select_weakest_skill(
    skill_scores: dict[str, SkillScore],
    roadmap_order: list[str],
    mastery_threshold: float,
) -> WeakestSkillOutcome:
    candidates = [s for s in skill_scores.values() if s.has_sufficient_evidence]
    if not candidates:
        return WeakestSkillOutcome(status="insufficient_evidence")

    def roadmap_rank(skill: SkillScore) -> int:
        if skill.skill_id in roadmap_order:
            return roadmap_order.index(skill.skill_id)
        return len(roadmap_order)

    weakest = min(candidates, key=lambda s: (s.score, roadmap_rank(s)))

    if weakest.score >= mastery_threshold:
        next_skill_id = None
        if weakest.skill_id in roadmap_order:
            idx = roadmap_order.index(weakest.skill_id)
            if idx + 1 < len(roadmap_order):
                next_skill_id = roadmap_order[idx + 1]
        return WeakestSkillOutcome(status="no_major_gap", next_roadmap_skill_id=next_skill_id)

    return WeakestSkillOutcome(status="weakest_found", skill_id=weakest.skill_id)
