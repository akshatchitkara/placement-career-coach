"""Loads data/content/ JSON into typed models. No business logic lives here."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pcc.domain.schemas.career_schemas import Career
from pcc.domain.schemas.question_schemas import Question
from pcc.domain.schemas.roadmap_schemas import Roadmap, Skill

_CONTENT_DIR = Path(__file__).resolve().parents[3] / "data" / "content"


class WeeklyPlanSettings(BaseModel):
    min_tasks: int
    max_tasks: int
    max_total_minutes: int


class AppSettings(BaseModel):
    """A loaded instance is a config snapshot -- store it verbatim per attempt (T-20)."""

    level_lower_bounds: dict[str, float]
    mastery_threshold: float
    industry_ready_min_skill_score: float
    min_answered_for_evidence: int
    questions_per_skill: int
    difficulty_mix_per_skill: dict[str, int]
    min_bank_questions_per_skill: int
    full_path_questions_per_skill: int
    learning_months_per_semester: int
    weekly_plan: WeeklyPlanSettings
    retest_after_days: int


def _read_json(relative_path: str) -> Any:
    path = _CONTENT_DIR / relative_path
    return json.loads(path.read_text(encoding="utf-8"))


def load_app_settings() -> AppSettings:
    return AppSettings.model_validate(_read_json("app_settings.json"))


def load_careers() -> list[Career]:
    return [Career.model_validate(item) for item in _read_json("careers.json")]


def load_skills() -> list[Skill]:
    return [Skill.model_validate(item) for item in _read_json("skills.json")]


def load_skills_for_career(career_id: str) -> list[Skill]:
    return [s for s in load_skills() if career_id in s.career_ids]


def load_roadmap_template(career_id: str) -> Roadmap:
    data = _read_json(f"roadmap_templates/{career_id}.json")
    return Roadmap.model_validate(data)


def load_question_bank(career_id: str) -> list[Question]:
    """Returns [] if no bank has been authored yet for this career (by design -- Tier B/C)."""
    path = _CONTENT_DIR / "question_bank" / f"{career_id}.json"
    if not path.exists():
        return []
    return [Question.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def compute_skill_assessability(
    skill_id: str, questions: list[Question], settings: AppSettings
) -> bool:
    """A skill is assessable only if its bank meets the minimum per-difficulty split (T-22).

    A thin bank is an expected state, not an error -- callers show
    "assessment coming soon" rather than failing.
    """
    skill_questions = [q for q in questions if q.skill_id == skill_id]
    if len(skill_questions) < settings.min_bank_questions_per_skill:
        return False
    for difficulty, required_count in settings.difficulty_mix_per_skill.items():
        available = sum(1 for q in skill_questions if q.difficulty == difficulty)
        if available < required_count * 2:  # x2 so a re-test can still pick unseen questions
            return False
    return True
