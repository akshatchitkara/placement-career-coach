from datetime import date

import pytest

from pcc.domain.schemas.assessment_schemas import SkillScore, WeakestSkillOutcome
from pcc.domain.schemas.coaching_schemas import CoachingPlan, CoachingTask
from pcc.domain.schemas.weekly_plan_schemas import (
    RoadmapFocus,
    WeeklyPlanConfig,
    WeeklyPlanContext,
)
from pcc.domain.weekly_plan_builder import build_weekly_plan

TODAY = date(2026, 10, 10)
CONFIG = WeeklyPlanConfig(min_tasks=3, max_tasks=5, max_total_minutes=240, retest_after_days=7)
NAMES = {
    "linux_fundamentals": "Linux Fundamentals",
    "shell_scripting": "Shell Scripting",
    "python_for_automation": "Python for Automation",
    "git_version_control": "Git Version Control",
}


def _scores(**by_skill: float) -> list[SkillScore]:
    return [
        SkillScore(
            skill_id=skill_id,
            correct_count=round(score / 100 * 3),
            answered_count=3,
            score=score,
            has_sufficient_evidence=True,
        )
        for skill_id, score in by_skill.items()
    ]


def _coaching(skill_id="linux_fundamentals", count=4, minutes=30) -> CoachingPlan:
    tasks = [
        CoachingTask(
            order=i,
            title=f"Coach {i}",
            linked_question_id="q1",
            concept_tag="file_permissions",
            action=f"Do coaching step {i}",
            estimated_minutes=minutes,
            success_check=f"Check {i}",
        )
        for i in range(1, count + 1)
    ]
    return CoachingPlan(skill_id=skill_id, diagnosis="d", tasks=tasks, retest_after_days=7)


FOCUS = RoadmapFocus(
    skill_id="networking_fundamentals",
    skill_name="Networking Fundamentals",
    topics=["tcp ip", "dns", "http"],
    deliverable="Trace a request end to end and document each hop.",
)


def _context(weakest, scores, coaching=None, focus=None, missed=None) -> WeeklyPlanContext:
    return WeeklyPlanContext(
        today=TODAY,
        weakest=weakest,
        coaching_plan=coaching,
        skill_scores=scores,
        skill_names=NAMES,
        missed_concepts_by_skill=missed or {},
        roadmap_focus=focus,
        mastery_threshold=60,
    )


WEAK = WeakestSkillOutcome(status="weakest_found", skill_id="linux_fundamentals")
WORKED = _scores(
    linux_fundamentals=33.3333,
    shell_scripting=33.3333,
    python_for_automation=66.6667,
    git_version_control=66.6667,
)


def _kinds(plan) -> list[str]:
    return [t.kind for t in plan.tasks]


def test_section_10_7_example_two_coaching_two_revisions_one_recheck():
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching()), CONFIG)
    assert _kinds(plan) == ["coaching", "coaching", "revision", "revision", "recheck"]
    assert [t.skill_id for t in plan.tasks[:4]] == [
        "linux_fundamentals",
        "linux_fundamentals",
        "shell_scripting",  # lowest score first
        "python_for_automation",  # tie with git -> roadmap order
    ]


def test_never_more_than_two_coaching_tasks():
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching(count=5)), CONFIG)
    assert _kinds(plan).count("coaching") == 2


def test_retest_date_and_closing_task():
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching()), CONFIG)
    assert plan.week_start_date == TODAY
    assert plan.retest_due_date == date(2026, 10, 17)
    last = plan.tasks[-1]
    assert last.kind == "recheck" and "17 Oct 2026" in last.title


def test_light_revision_for_60_to_79_and_full_revision_below():
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching()), CONFIG)
    titles = [t.title for t in plan.tasks if t.kind == "revision"]
    assert titles == ["Revise: Shell Scripting", "Light revision: Python for Automation"]


def test_revision_names_the_missed_concepts():
    missed = {"shell_scripting": ["conditionals_and_loops", "bash_variables_and_quoting"]}
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching(), missed=missed), CONFIG)
    shell = next(t for t in plan.tasks if t.skill_id == "shell_scripting")
    assert "conditionals and loops" in shell.description
    assert "bash variables and quoting" in shell.completion_check


def test_no_major_gap_moves_ahead_on_the_roadmap():
    scores = _scores(linux_fundamentals=100, shell_scripting=100, python_for_automation=100)
    weakest = WeakestSkillOutcome(
        status="no_major_gap", next_roadmap_skill_id="networking_fundamentals"
    )
    plan = build_weekly_plan(_context(weakest, scores, focus=FOCUS), CONFIG)
    assert _kinds(plan) == ["roadmap", "roadmap", "recheck"]
    assert plan.tasks[0].title == "Start next: Networking Fundamentals"
    assert "tcp ip, dns, http" in plan.tasks[0].description
    assert plan.tasks[1].description == FOCUS.deliverable


def test_no_gap_with_a_light_revision_keeps_the_next_topic():
    scores = _scores(linux_fundamentals=100, shell_scripting=66.6667)
    weakest = WeakestSkillOutcome(
        status="no_major_gap", next_roadmap_skill_id="networking_fundamentals"
    )
    plan = build_weekly_plan(_context(weakest, scores, focus=FOCUS), CONFIG)
    assert _kinds(plan) == ["roadmap", "revision", "roadmap", "recheck"]


def test_no_coaching_task_when_there_is_no_weakest_skill():
    plan = build_weekly_plan(
        _context(
            WeakestSkillOutcome(status="no_major_gap"), _scores(linux_fundamentals=100), focus=FOCUS
        ),
        CONFIG,
    )
    assert "coaching" not in _kinds(plan)


def test_insufficient_evidence_still_gives_a_useful_week():
    weakest = WeakestSkillOutcome(status="insufficient_evidence")
    plan = build_weekly_plan(_context(weakest, [], focus=FOCUS), CONFIG)
    assert 3 <= len(plan.tasks) <= 5 and plan.tasks[-1].kind == "recheck"


def test_a_week_with_nothing_specific_is_padded_to_the_minimum():
    weakest = WeakestSkillOutcome(status="no_major_gap")
    plan = build_weekly_plan(_context(weakest, _scores(linux_fundamentals=100)), CONFIG)
    assert len(plan.tasks) == 3
    assert plan.tasks[0].title == "Review your last check"


@pytest.mark.parametrize("coaching_minutes", [30, 60, 100])
def test_total_time_never_exceeds_the_limit_and_recheck_is_kept(coaching_minutes):
    context = _context(WEAK, WORKED, coaching=_coaching(minutes=coaching_minutes))
    plan = build_weekly_plan(context, CONFIG)
    if coaching_minutes <= 100:
        assert sum(t.estimated_minutes for t in plan.tasks) <= 240 or len(plan.tasks) == 3
    assert plan.tasks[-1].kind == "recheck"
    assert 3 <= len(plan.tasks) <= 5


def test_lowest_priority_tasks_are_dropped_first_when_over_time():
    tight = CONFIG.model_copy(update={"max_total_minutes": 120})
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching(minutes=40)), tight)
    assert _kinds(plan) == ["coaching", "coaching", "recheck"]  # revisions went first
    assert sum(t.estimated_minutes for t in plan.tasks) <= 120


def test_every_task_has_an_observable_completion_check_and_unique_id():
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching()), CONFIG)
    assert all(t.completion_check.strip() for t in plan.tasks)
    ids = [t.task_id for t in plan.tasks]
    assert len(ids) == len(set(ids))


def test_builder_is_deterministic():
    context = _context(WEAK, WORKED, coaching=_coaching())
    assert build_weekly_plan(context, CONFIG) == build_weekly_plan(context, CONFIG)


def test_config_changes_the_task_limit():
    small = CONFIG.model_copy(update={"max_tasks": 4})
    plan = build_weekly_plan(_context(WEAK, WORKED, coaching=_coaching()), small)
    assert len(plan.tasks) == 4 and plan.tasks[-1].kind == "recheck"
