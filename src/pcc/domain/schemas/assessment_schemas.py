"""Scoring contracts. Scoring itself is pure code -- see domain/scoring/."""

from typing import Literal

from pydantic import BaseModel


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
