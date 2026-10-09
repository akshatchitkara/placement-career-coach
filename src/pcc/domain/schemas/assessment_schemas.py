"""Scoring contracts. Scoring itself is pure code -- see domain/scoring/."""

from typing import Literal

from pydantic import BaseModel

from pcc.domain.enums import Difficulty, Level
from pcc.domain.schemas.question_schemas import Option
from pcc.domain.schemas.roadmap_schemas import RoadmapPosition


class Answer(BaseModel):
    question_id: str
    selected_option_id: str


class SkillScore(BaseModel):
    skill_id: str
    correct_count: int
    answered_count: int
    score: float  # correct_count / answered_count * 100, unrounded
    has_sufficient_evidence: bool
    is_weakest: bool = False


class WeakestSkillOutcome(BaseModel):
    """Section 10.5. status disambiguates "nothing qualifies" from "nothing needs fixing"."""

    status: Literal["weakest_found", "no_major_gap", "insufficient_evidence"]
    skill_id: str | None = None
    next_roadmap_skill_id: str | None = None


class PresentedQuestion(BaseModel):
    """What the UI sees: shuffled options, never the answer key."""

    question_id: str
    skill_id: str
    skill_name: str
    difficulty: Difficulty
    stem: str
    options: list[Option]


class QuestionReview(BaseModel):
    question_id: str
    skill_id: str
    stem: str
    selected_option_text: str
    correct_option_text: str
    is_correct: bool
    explanation: str


class AssessmentSession(BaseModel):
    attempt_id: int
    attempt_type: str = "baseline"
    scope_description: str
    questions: list[PresentedQuestion]


class AssessmentScope(BaseModel):
    """What a check would cover for the student's current semester (T-21, T-22)."""

    semester: int
    assessable_skill_ids: list[str]
    assessed_later_skill_ids: list[str]  # skill type has no built method yet
    coming_soon_skill_ids: list[str]  # quiz skill, but question bank too thin


class EvaluationResult(BaseModel):
    attempt_id: int
    attempt_type: str = "baseline"
    scope_description: str
    overall_score: float
    level: Level
    level_notes: list[str]
    coverage_ratio: float
    skill_scores: list[SkillScore]  # roadmap order; is_weakest marked
    weakest: WeakestSkillOutcome
    position: RoadmapPosition
    reviews: list[QuestionReview]
    level_lower_bounds: dict[str, float]
    mastery_threshold: float
    min_answered_for_evidence: int
