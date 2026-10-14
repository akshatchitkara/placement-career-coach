"""Career catalog contract (data/content/careers.json)."""

from typing import Literal

from pydantic import BaseModel, Field


class Career(BaseModel):
    career_id: str
    name: str
    tier: Literal["A", "B", "C"]
    description: str = ""
    overview: str = ""
    day_to_day: list[str] = Field(default_factory=list)
    growth_path: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
