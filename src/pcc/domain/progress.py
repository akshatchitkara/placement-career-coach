"""Progress comparison between checks and the post-check rules of blueprint Section 4.4. Pure."""

from typing import Literal

from pydantic import BaseModel

from pcc.domain.enums import Level
from pcc.domain.schemas.assessment_schemas import SkillScore

_SAME_TOLERANCE = 0.05  # scores are n/3 fractions; treat float noise as "same"
_MENTOR_BELOW = 40.0


class SkillDelta(BaseModel):
    skill_id: str
    previous_score: float | None
    current_score: float
    delta: float | None
    direction: Literal["up", "down", "same", "new"]


class AttemptSummary(BaseModel):
    attempt_id: int
    attempt_type: str
    submitted_at: str
    overall_score: float
    level: Level
    skill_scores: list[SkillScore]


class ProgressView(BaseModel):
    attempts: list[AttemptSummary]  # oldest first
    deltas: list[SkillDelta]  # latest vs previous; empty with a single attempt
    overall_delta: float | None
    previous_level: Level | None
    current_level: Level | None
    mentor_skill_ids: list[str]  # latest score below 40
    repeated_drop_skill_ids: list[str]  # dropped in each of the last two comparisons
    skills_below_mastery: int


def compare_skill_scores(previous: list[SkillScore], current: list[SkillScore]) -> list[SkillDelta]:
    before = {s.skill_id: s for s in previous if s.has_sufficient_evidence}
    deltas = []
    for score in current:
        old = before.get(score.skill_id)
        if old is None or not score.has_sufficient_evidence:
            deltas.append(
                SkillDelta(
                    skill_id=score.skill_id,
                    previous_score=None,
                    current_score=score.score,
                    delta=None,
                    direction="new",
                )
            )
            continue
        change = score.score - old.score
        direction: Literal["up", "down", "same"] = (
            "same" if abs(change) < _SAME_TOLERANCE else "up" if change > 0 else "down"
        )
        deltas.append(
            SkillDelta(
                skill_id=score.skill_id,
                previous_score=old.score,
                current_score=score.score,
                delta=change,
                direction=direction,
            )
        )
    return deltas


def repeated_drop_skill_ids(history: list[list[SkillScore]]) -> list[str]:
    """Skills that dropped in both of the last two comparisons (needs 3+ attempts)."""
    if len(history) < 3:
        return []
    last = {
        d.skill_id for d in compare_skill_scores(history[-2], history[-1]) if d.direction == "down"
    }
    before = {
        d.skill_id for d in compare_skill_scores(history[-3], history[-2]) if d.direction == "down"
    }
    return sorted(last & before)


def mentor_skill_ids(scores: list[SkillScore]) -> list[str]:
    return [s.skill_id for s in scores if s.has_sufficient_evidence and s.score < _MENTOR_BELOW]


def build_progress(attempts: list[AttemptSummary], mastery_threshold: float) -> ProgressView:
    if not attempts:
        return ProgressView(
            attempts=[],
            deltas=[],
            overall_delta=None,
            previous_level=None,
            current_level=None,
            mentor_skill_ids=[],
            repeated_drop_skill_ids=[],
            skills_below_mastery=0,
        )
    latest = attempts[-1]
    previous = attempts[-2] if len(attempts) > 1 else None
    return ProgressView(
        attempts=attempts,
        deltas=compare_skill_scores(previous.skill_scores, latest.skill_scores) if previous else [],
        overall_delta=latest.overall_score - previous.overall_score if previous else None,
        previous_level=previous.level if previous else None,
        current_level=latest.level,
        mentor_skill_ids=mentor_skill_ids(latest.skill_scores),
        repeated_drop_skill_ids=repeated_drop_skill_ids([a.skill_scores for a in attempts]),
        skills_below_mastery=sum(
            1
            for s in latest.skill_scores
            if s.has_sufficient_evidence and s.score < mastery_threshold
        ),
    )
