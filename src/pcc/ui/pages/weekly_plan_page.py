"""Weekly plan (FR-10): 3-5 rule-built tasks with observable checks and a re-check date."""

import streamlit as st

from pcc.ui.components.page_frame import require_profile
from pcc.workflow.workflow_controller import get_controller

_KIND_LABELS = {
    "coaching": "Fix your weak spot",
    "roadmap": "Move ahead on the roadmap",
    "revision": "Revision",
    "recheck": "Re-check",
}


def render() -> None:
    st.title("Weekly Plan")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    view = controller.get_weekly_plan(profile.id)
    if view is None:
        st.info("Your weekly plan appears after you finish a check on **Skills Check**.")
        return

    plan = view.plan
    if view.retest_due:
        st.warning(
            f"Your re-check is due (planned for {plan.retest_due_date:%d %b %Y}). "
            "Open **Skills Check** to take it."
        )
    else:
        st.info(
            f"Re-check on {plan.retest_due_date:%d %b %Y} "
            f"({view.days_until_retest} day{'s' if view.days_until_retest != 1 else ''} to go). "
            "You can also take it early on **Skills Check**."
        )

    total = len(plan.tasks)
    done_ids = set(view.done_task_ids)
    minutes = sum(t.estimated_minutes for t in plan.tasks)
    st.caption(f"Week of {plan.week_start_date:%d %b %Y} · {total} tasks · about {minutes} minutes")
    st.progress(len(done_ids) / total, text=f"{len(done_ids)} of {total} tasks done")

    for task in plan.tasks:
        with st.container(border=True):
            checked = st.checkbox(
                f"**{task.title}** · {task.estimated_minutes} min",
                value=task.task_id in done_ids,
                key=f"task_{view.plan_id}_{task.task_id}",
            )
            st.caption(_KIND_LABELS[task.kind])
            st.write(task.description)
            st.markdown(f"**You're done when:** {task.completion_check}")
        if checked != (task.task_id in done_ids):
            controller.set_task_done(profile.id, view.plan_id, task.task_id, checked)
            st.rerun()
