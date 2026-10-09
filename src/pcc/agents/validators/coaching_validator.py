"""Coaching validation rules V-CO-01..06 (blueprint Section 9.4). Pure; returns violations."""

import re

from pcc.domain.schemas.coaching_schemas import CoachingInput, CoachingPlan

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)


def validate_coaching_plan(
    plan: CoachingPlan, weakest_skill_id: str, context: CoachingInput
) -> list[str]:
    errors: list[str] = []
    missed_ids = {m.question_id for m in context.missed}
    missed_tags = {m.concept_tag for m in context.missed}

    if not 3 <= len(plan.tasks) <= 5:
        errors.append(f"V-CO-01: plan has {len(plan.tasks)} tasks, expected 3-5")

    if plan.skill_id != weakest_skill_id:
        errors.append(
            f"V-CO-03: plan is for '{plan.skill_id}', weakest skill is '{weakest_skill_id}'"
        )

    total = sum(t.estimated_minutes for t in plan.tasks)
    if total > context.max_total_minutes:
        errors.append(
            f"V-CO-04: total {total} min exceeds the {context.max_total_minutes} min limit"
        )

    for task in plan.tasks:
        where = f"task {task.order} '{task.title}'"
        linked = task.linked_question_id in missed_ids if task.linked_question_id else False
        tagged = task.concept_tag in missed_tags if task.concept_tag else False
        if not (linked or tagged):
            errors.append(f"V-CO-02: {where} is not linked to a missed question or concept")
        if task.linked_question_id and not linked:
            errors.append(f"V-CO-02: {where} links to a question that was not missed")
        if not task.success_check.strip():
            errors.append(f"V-CO-05: {where} has no success check")
        text = " ".join(
            [plan.diagnosis, task.title, task.misconception, task.action, task.resource_hint]
        )
        if _URL.search(text + " " + task.success_check):
            errors.append(f"V-CO-06: {where} contains a URL")
    return errors
