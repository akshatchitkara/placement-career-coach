"""Section 10.6. "Where do I stand?" -- position within the full roadmap sequence."""

from pcc.domain.schemas.assessment_schemas import SkillScore
from pcc.domain.schemas.roadmap_schemas import RoadmapPosition


def locate_position(
    full_roadmap_order: list[str],
    tested_scope_skill_ids: set[str],
    skill_scores: dict[str, SkillScore],
    mastery_threshold: float,
) -> RoadmapPosition:
    for skill_id in full_roadmap_order:
        if skill_id not in tested_scope_skill_ids:
            # Everything in scope before this point was mastered -- this is the
            # first untested skill, i.e. the next semester to take on.
            return RoadmapPosition(label="advance_to_next_semester", skill_id=skill_id)

        score = skill_scores.get(skill_id)
        if score is None or not score.has_sufficient_evidence or score.score < mastery_threshold:
            return RoadmapPosition(label="in_progress", skill_id=skill_id)

    return RoadmapPosition(label="roadmap_complete")
