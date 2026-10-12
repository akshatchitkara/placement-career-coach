"""Coaching plan (FR-09): 3-5 tasks for the weakest skill, each tied to a mistake."""

import streamlit as st

from pcc.ui.components.page_frame import require_profile
from pcc.workflow.workflow_controller import get_controller

_SOURCE_LABELS = {
    "template": "Curated plan built from your missed questions",
    "ai": "AI-drafted plan, checked against your results",
}


def render() -> None:
    st.title("Coaching Plan")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    view = controller.get_coaching_plan(profile.id)
    if view is None:
        if controller.get_latest_results(profile.id) is None:
            st.info(
                "Take the check on **Skills Check** first; your plan is built from your mistakes."
            )
        else:
            st.info(
                "No coaching plan: your results did not single out a weak skill "
                "(not enough evidence, or no major gap)."
            )
        return

    plan = view.plan
    st.subheader(f"Focus skill: {view.skill_name}")
    st.caption(_SOURCE_LABELS[plan.generation_source])
    st.write(plan.diagnosis)
    total = sum(t.estimated_minutes for t in plan.tasks)
    st.caption(
        f"{len(plan.tasks)} tasks · about {total} minutes · "
        f"re-check in {plan.retest_after_days} days"
    )

    for task in plan.tasks:
        with st.container(border=True):
            st.markdown(f"**{task.order}. {task.title}** · {task.estimated_minutes} min")
            if task.misconception:
                st.markdown(f"*What went wrong:* {task.misconception}")
            st.markdown(f"**Do this:** {task.action}")
            st.markdown(f"**You're done when:** {task.success_check}")
            if task.resource_hint:
                st.caption(f"Look up: {task.resource_hint}")
            if task.linked_question_id in view.question_stems:
                st.caption(
                    f"Linked to the question: {view.question_stems[task.linked_question_id]}"
                )
            elif task.concept_tag:
                st.caption(f"Concept: {task.concept_tag.replace('_', ' ')}")
