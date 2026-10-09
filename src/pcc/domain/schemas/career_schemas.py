"""Career catalog contract (data/content/careers.json)."""

from typing import Literal

from pydantic import BaseModel, Field


class Career(BaseModel):
    career_id: str
    name: str
    tier: Literal["A", "B", "C"]
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
