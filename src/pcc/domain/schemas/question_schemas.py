"""Question bank contract (data/content/question_bank/<career_id>.json)."""

from pydantic import BaseModel, Field

from pcc.domain.enums import Difficulty


class Option(BaseModel):
    option_id: str
    text: str


class Question(BaseModel):
    question_id: str
    skill_id: str
    concept_tag: str
    difficulty: Difficulty
    stem: str
    options: list[Option] = Field(min_length=4, max_length=4)
    correct_option_id: str
    explanation: str
    review_status: str = "approved"
    source: str = "ai_drafted_human_reviewed"
    reviewed_on: str = ""
