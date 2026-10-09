"""Coaching contracts (blueprint Section 9.4). Plans are advisory text; scoring never uses them."""

from typing import Literal

from pydantic import BaseModel, Field

from pcc.domain.schemas.roadmap_schemas import PracticeTemplate


class CoachingTask(BaseModel):
    order: int
    title: str
    linked_question_id: str | None = None
    concept_tag: str | None = None
    misconception: str = ""
    action: str
    resource_hint: str = ""
    estimated_minutes: int = Field(gt=0)
    success_check: str


class CoachingPlan(BaseModel):
    skill_id: str
    diagnosis: str
    tasks: list[CoachingTask]  # 3-5 is enforced by the validator (V-CO-01), not the type
    retest_after_days: int
    generation_source: Literal["ai", "template"] = "template"


class MissedQuestion(BaseModel):
    """What the coaching module is allowed to see about a mistake (no student identity)."""

    question_id: str
    concept_tag: str
    stem: str
    selected_option_text: str
    correct_option_text: str
    explanation: str


class CoachingInput(BaseModel):
    career_name: str
    skill_id: str
    skill_name: str
    level: str
    missed: list[MissedQuestion]
    practice_templates: list[PracticeTemplate]
    max_total_minutes: int
    retest_after_days: int


class CoachingPlanView(BaseModel):
    """A saved plan plus the display text the page needs (names and missed-question stems)."""

    plan: CoachingPlan
    skill_name: str
    question_stems: dict[str, str]
