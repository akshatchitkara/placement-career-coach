"""Shared enums. Business thresholds live in app_settings.json, not here."""

from enum import StrEnum


class Level(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    INDUSTRY_READY = "industry_ready"


class SkillType(StrEnum):
    """Maps to an assessment method via ASSESSMENT_METHOD_BY_SKILL_TYPE (Section 10.1).

    Only CONCEPTUAL is quiz-assessable in the MVP; the others are shown as
    "assessed later" and excluded from scoring and coverage (T-21).
    """

    CONCEPTUAL = "conceptual"
    REASONING = "reasoning"
    BUILD = "build"
    COMMUNICATION = "communication"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class WorkflowState(StrEnum):
    PROFILE_READY = "profile_ready"
    CAREER_SELECTED = "career_selected"
    ROADMAP_READY = "roadmap_ready"
    ASSESSMENT_IN_PROGRESS = "assessment_in_progress"
    RESULTS_READY = "results_ready"
    COACHING_READY = "coaching_ready"
    WEEKLY_PLAN_ACTIVE = "weekly_plan_active"
    RETEST_DUE = "retest_due"


# Section 10.1's method-selection rule: a skill_type maps to exactly one
# assessment method. Only methods in BUILT_ASSESSMENT_METHODS are actually
# implemented in the MVP; the rest are shown as "assessed later" (T-21) --
# never silently substituted with a quiz.
ASSESSMENT_METHOD_BY_SKILL_TYPE: dict[SkillType, str] = {
    SkillType.CONCEPTUAL: "quiz_mcq",
    SkillType.REASONING: "written_response",
    SkillType.BUILD: "hands_on_assignment",
    SkillType.COMMUNICATION: "voice_interview",
}

BUILT_ASSESSMENT_METHODS: frozenset[str] = frozenset({"quiz_mcq"})


def is_quiz_assessable(skill_type: SkillType) -> bool:
    return ASSESSMENT_METHOD_BY_SKILL_TYPE[skill_type] in BUILT_ASSESSMENT_METHODS
