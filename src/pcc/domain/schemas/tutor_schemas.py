"""Tutor chat contracts. The tutor explains; it never scores, grades or changes the plan."""

from typing import Literal

from pydantic import BaseModel

from pcc.domain.schemas.coaching_schemas import CoachingTask, MissedQuestion

TutorKind = Literal["explain_differently", "example", "question"]

MAX_STUDENT_TEXT = 300
MAX_STUDENT_MESSAGES_PER_TASK = 12


class TutorMessage(BaseModel):
    role: Literal["student", "coach"]
    kind: TutorKind
    content: str
    generation_source: Literal["ai", "template", "student"]


class TutorContext(BaseModel):
    """Everything the tutor may see. No student identity, no scores, no other skills."""

    career_name: str
    skill_name: str
    task: CoachingTask
    missed: list[MissedQuestion]  # the mistakes this task is about
    history: list[TutorMessage]  # earlier turns on this task, oldest first


class TutorReply(BaseModel):
    text: str
    used_fallback: bool
    message: str = ""


class PracticeQuestionResult(BaseModel):
    question_id: str
    stem: str
    selected_option_text: str
    correct_option_text: str
    is_correct: bool
    explanation: str
