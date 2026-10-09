"""Skill catalog and roadmap contracts (data/content/skills.json, roadmap_templates/)."""

from typing import Literal

from pydantic import BaseModel, Field

from pcc.domain.enums import SkillType


class Skill(BaseModel):
    """career_ids is a list, not a single id: a few skills (e.g. git_version_control,
    interview_preparation) are legitimately shared across multiple roadmaps rather
    than re-authored per career."""

    skill_id: str
    name: str
    career_ids: list[str] = Field(min_length=1)
    skill_type: SkillType
    concept_tags: list[str] = Field(default_factory=list)
    practice_templates: list[dict[str, str]] = Field(default_factory=list)
    resources: list[dict[str, str]] = Field(default_factory=list)


class RoadmapMonth(BaseModel):
    semester: int = Field(ge=3, le=6)
    month_index: int = Field(ge=1, le=4)
    skill_id: str
    focus: str
    topics: list[str] = Field(min_length=2)
    deliverable: str


class Roadmap(BaseModel):
    career_id: str
    months: list[RoadmapMonth] = Field(min_length=16, max_length=16)
    generation_source: Literal["template", "ai_personalised", "ai_drafted_unverified"] = "template"

    def skill_ids_in_order(self) -> list[str]:
        ordered = sorted(self.months, key=lambda m: (m.semester, m.month_index))
        return [m.skill_id for m in ordered]


class RoadmapPosition(BaseModel):
    """Section 10.6. "You are here" marker within the full roadmap sequence."""

    label: Literal["in_progress", "advance_to_next_semester", "roadmap_complete"]
    skill_id: str | None = None
