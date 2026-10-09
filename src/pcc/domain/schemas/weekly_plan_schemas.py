"""Weekly plan contracts (blueprint Sections 4.5 and 9.5). Rules only; no AI involved."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from pcc.domain.schemas.assessment_schemas import SkillScore, WeakestSkillOutcome
from pcc.domain.schemas.coaching_schemas import CoachingPlan


class WeeklyPlanConfig(BaseModel):
    min_tasks: int
    max_tasks: int
    max_total_minutes: int
    retest_after_days: int


class RoadmapFocus(BaseModel):
    """The next roadmap month to work on when there is no weak skill to fix."""

    skill_id: str
    skill_name: str
    topics: list[str]
    deliverable: str


class WeeklyPlanContext(BaseModel):
    today: date
    weakest: WeakestSkillOutcome
    coaching_plan: CoachingPlan | None
    skill_scores: list[SkillScore]  # roadmap order
    skill_names: dict[str, str]
    missed_concepts_by_skill: dict[str, list[str]]
    roadmap_focus: RoadmapFocus | None
    mastery_threshold: float


class WeeklyTask(BaseModel):
    task_id: str
    kind: Literal["coaching", "roadmap", "revision", "recheck"]
    title: str
    description: str
    estimated_minutes: int
    completion_check: str
    skill_id: str | None = None


class WeeklyPlan(BaseModel):
    week_start_date: date
    retest_due_date: date
    tasks: list[WeeklyTask]


class WeeklyPlanView(BaseModel):
    plan_id: int
    plan: WeeklyPlan
    done_task_ids: list[str]
    retest_due: bool
    days_until_retest: int  # 0 when due or overdue
