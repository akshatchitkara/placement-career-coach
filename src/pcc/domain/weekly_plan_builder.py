"""Weekly Plan Builder (blueprint Sections 4.5 and 9.5). Pure and deterministic.

Priority when filling the week: coaching tasks (max 2), then the next roadmap topic,
then revision of other skills that still need it, then a second roadmap task. The
closing re-check task is always kept, and lower-priority tasks are dropped first when
the total time limit would be exceeded.
"""

from datetime import timedelta

from pcc.domain.schemas.weekly_plan_schemas import (
    WeeklyPlan,
    WeeklyPlanConfig,
    WeeklyPlanContext,
    WeeklyTask,
)

_MAX_COACHING_TASKS = 2
_ROADMAP_STUDY_MINUTES = 60
_ROADMAP_BUILD_MINUTES = 90
_REVISION_MINUTES = 30
_LIGHT_REVISION_MINUTES = 20
_RECHECK_MINUTES = 20
_REVISION_BELOW_SCORE = 80  # section 4.4: 80+ is mastered outright
_GENERIC_MINUTES = 30

_FILLER_TASKS = [
    WeeklyTask(
        task_id="review_1",
        kind="revision",
        title="Review your last check",
        description="Re-read the explanations for every question you missed.",
        estimated_minutes=_GENERIC_MINUTES,
        completion_check="List three things you will do differently next time.",
    ),
    WeeklyTask(
        task_id="review_2",
        kind="revision",
        title="Plan your next study block",
        description="Look at your roadmap and pick the next topic you want to start.",
        estimated_minutes=_GENERIC_MINUTES,
        completion_check="Write down the topic, a goal and when you will study it.",
    ),
]


def _humanise(tag: str) -> str:
    return tag.replace("_", " ")


def _coaching_tasks(context: WeeklyPlanContext) -> list[WeeklyTask]:
    if context.weakest.status != "weakest_found" or context.coaching_plan is None:
        return []
    return [
        WeeklyTask(
            task_id=f"coaching_{i}",
            kind="coaching",
            title=task.title,
            description=task.action,
            estimated_minutes=task.estimated_minutes,
            completion_check=task.success_check,
            skill_id=context.coaching_plan.skill_id,
        )
        for i, task in enumerate(context.coaching_plan.tasks[:_MAX_COACHING_TASKS], start=1)
    ]


def _roadmap_tasks(context: WeeklyPlanContext) -> tuple[WeeklyTask | None, WeeklyTask | None]:
    focus = context.roadmap_focus
    if focus is None or context.weakest.status == "weakest_found":
        return None, None
    study = WeeklyTask(
        task_id="roadmap_1",
        kind="roadmap",
        title=f"Start next: {focus.skill_name}",
        description="Work through these topics: " + ", ".join(focus.topics) + ".",
        estimated_minutes=_ROADMAP_STUDY_MINUTES,
        completion_check=f"Write a short summary of each topic in {focus.skill_name}.",
        skill_id=focus.skill_id,
    )
    build = WeeklyTask(
        task_id="roadmap_2",
        kind="roadmap",
        title=f"Build: {focus.skill_name}",
        description=focus.deliverable,
        estimated_minutes=_ROADMAP_BUILD_MINUTES,
        completion_check="Show the finished result and explain one decision you made.",
        skill_id=focus.skill_id,
    )
    return study, build


def _revision_tasks(context: WeeklyPlanContext) -> list[WeeklyTask]:
    weakest_id = context.weakest.skill_id if context.weakest.status == "weakest_found" else None
    candidates = [
        s
        for s in context.skill_scores
        if s.has_sufficient_evidence
        and s.skill_id != weakest_id
        and s.score < _REVISION_BELOW_SCORE
    ]
    candidates.sort(key=lambda s: s.score)  # stable: ties keep roadmap order
    tasks = []
    for n, score in enumerate(candidates, start=1):
        name = context.skill_names.get(score.skill_id, score.skill_id)
        concepts = [_humanise(t) for t in context.missed_concepts_by_skill.get(score.skill_id, [])]
        light = score.score >= context.mastery_threshold
        focus = ", ".join(concepts) if concepts else name
        tasks.append(
            WeeklyTask(
                task_id=f"revision_{n}",
                kind="revision",
                title=f"{'Light revision' if light else 'Revise'}: {name}",
                description=(
                    f"Go back over {focus} in your notes and redo any example you got wrong."
                ),
                estimated_minutes=_LIGHT_REVISION_MINUTES if light else _REVISION_MINUTES,
                completion_check=f"Explain {focus} without notes.",
                skill_id=score.skill_id,
            )
        )
    return tasks


def build_weekly_plan(context: WeeklyPlanContext, config: WeeklyPlanConfig) -> WeeklyPlan:
    due = context.today + timedelta(days=config.retest_after_days)
    recheck = WeeklyTask(
        task_id="recheck_1",
        kind="recheck",
        title=f"Re-check on {due.strftime('%d %b %Y')}",
        description="Take the skills check again to see what improved.",
        estimated_minutes=_RECHECK_MINUTES,
        completion_check="Submit the re-check and compare your scores on the Progress page.",
    )

    study, build = _roadmap_tasks(context)
    core = _coaching_tasks(context) + ([study] if study else []) + _revision_tasks(context)
    if build:
        core.append(build)

    for filler in _FILLER_TASKS:  # nothing specific to do: keep the week meaningful
        if len(core) + 1 >= config.min_tasks:
            break
        core.append(filler)

    core = core[: config.max_tasks - 1]
    while len(core) + 1 > config.min_tasks and (
        sum(t.estimated_minutes for t in core) + recheck.estimated_minutes
        > config.max_total_minutes
    ):
        core.pop()  # drop the lowest-priority task first

    return WeeklyPlan(week_start_date=context.today, retest_due_date=due, tasks=[*core, recheck])
