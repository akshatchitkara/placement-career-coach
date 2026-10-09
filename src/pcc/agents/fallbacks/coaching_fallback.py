"""Coaching fallback: a plan built only from curated practice templates and the missed questions.

Always valid against V-CO-01..06 by construction, so it is safe to show with no AI at all.
"""

from collections import Counter

from pcc.domain.schemas.coaching_schemas import (
    CoachingInput,
    CoachingPlan,
    CoachingTask,
    MissedQuestion,
)
from pcc.domain.schemas.roadmap_schemas import PracticeTemplate

_MAX_TASKS = 5
_REVIEW_MINUTES = 15
_TEACH_BACK_MINUTES = 15


def _humanise(tag: str) -> str:
    return tag.replace("_", " ")


def _template_for(tag: str, context: CoachingInput) -> PracticeTemplate:
    for template in context.practice_templates:
        if template.concept_tag == tag:
            return template
    return PracticeTemplate(  # generic stand-in for tags without curated content
        concept_tag=tag,
        title=f"Practice: {_humanise(tag)}",
        action=(
            f"Study {_humanise(tag)} for {context.skill_name} using the official documentation, "
            "then write and run a small worked example of your own."
        ),
        success_check=f"Explain {_humanise(tag)} aloud without notes.",
        resource_hint=f"{context.skill_name} {_humanise(tag)}",
        estimated_minutes=30,
    )


def _mistake(q: MissedQuestion) -> str:
    return f"Chose '{q.selected_option_text}' instead of '{q.correct_option_text}'"


def template_plan(context: CoachingInput) -> CoachingPlan:
    misses = Counter(m.concept_tag for m in context.missed)
    tags = sorted(misses, key=lambda tag: (-misses[tag], tag))
    first_missed = {t: next(m for m in context.missed if m.concept_tag == t) for t in tags}

    tasks: list[CoachingTask] = []
    for tag in tags:
        template = _template_for(tag, context)
        tasks.append(
            CoachingTask(
                order=0,
                title=template.title,
                linked_question_id=first_missed[tag].question_id,
                concept_tag=tag,
                misconception=_mistake(first_missed[tag]),
                action=template.action,
                resource_hint=template.resource_hint,
                estimated_minutes=template.estimated_minutes,
                success_check=template.success_check,
            )
        )

    teach_back = CoachingTask(
        order=0,
        title=f"Teach-back: {context.skill_name}",
        linked_question_id=first_missed[tags[0]].question_id,
        concept_tag=tags[0],
        misconception="",
        action=(
            f"Without notes, explain the main ideas of {_humanise(tags[0])} in your own words "
            "as if teaching a classmate, then check yourself against your notes."
        ),
        resource_hint=f"{context.skill_name} {_humanise(tags[0])}",
        estimated_minutes=_TEACH_BACK_MINUTES,
        success_check="Give a correct two-minute explanation including one example.",
    )
    reviews = [
        CoachingTask(
            order=0,
            title=f"Re-work a missed question ({_humanise(m.concept_tag)})",
            linked_question_id=m.question_id,
            concept_tag=m.concept_tag,
            misconception=_mistake(m),
            action=(
                f"Re-read this question and explain why '{m.correct_option_text}' is correct: "
                f"{m.stem} Then note why '{m.selected_option_text}' is not."
            ),
            resource_hint=f"{context.skill_name} {_humanise(m.concept_tag)}",
            estimated_minutes=_REVIEW_MINUTES,
            success_check="State the rule behind the correct answer without looking at it.",
        )
        for m in context.missed
    ]

    # Priority: concept practice, then teach-back, then per-question reviews to fill up to 5.
    tasks = (tasks + [teach_back] + reviews)[:_MAX_TASKS]
    while sum(t.estimated_minutes for t in tasks) > context.max_total_minutes and len(tasks) > 3:
        tasks.pop()
    tasks = [t.model_copy(update={"order": i}) for i, t in enumerate(tasks, start=1)]

    missed_total = len(context.missed)
    diagnosis = (
        f"You missed {missed_total} question{'s' if missed_total != 1 else ''} in "
        f"{context.skill_name}, mostly around {', '.join(_humanise(t) for t in tags)}."
    )
    return CoachingPlan(
        skill_id=context.skill_id,
        diagnosis=diagnosis,
        tasks=tasks,
        retest_after_days=context.retest_after_days,
        generation_source="template",
    )
