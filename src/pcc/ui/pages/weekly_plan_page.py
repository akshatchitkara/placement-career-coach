"""Weekly plan (FR-10): rule-built tasks laid out day by day, with links and a re-check date."""

from datetime import timedelta

import streamlit as st

from pcc.core.exceptions import PccError
from pcc.domain.calendar_export import build_ics
from pcc.domain.schemas.weekly_plan_schemas import WeeklyPlanView, WeeklyTask
from pcc.domain.week_schedule import DayPlan, schedule_week
from pcc.ui.components.page_frame import page_header, require_profile
from pcc.ui.components.pill import pill_html
from pcc.ui.navigation import go_button
from pcc.ui.text import safe_md
from pcc.workflow.workflow_controller import WorkflowController, get_controller

_KIND_LABELS = {
    "coaching": "Fix your weak spot",
    "roadmap": "Move ahead on the roadmap",
    "revision": "Revision",
    "recheck": "Re-check",
}
# kind -> (button label, page key)
_TASK_LINKS = {
    "coaching": ("Open the coaching task", "coaching"),
    "roadmap": ("Open my roadmap", "roadmap"),
    "revision": ("Review my answers", "results"),
}
_BUDGETS = {120: "About 2 hours", 180: "About 3 hours", 240: "About 4 hours"}
_ERROR_KEY = "weekly_capacity_error"


def _apply_capacity(controller: WorkflowController, profile_id: int, key: str) -> None:
    try:
        controller.set_weekly_capacity(profile_id, st.session_state[key])
    except PccError as exc:
        st.session_state[_ERROR_KEY] = str(exc)


def _capacity_picker(controller: WorkflowController, profile_id: int, view: WeeklyPlanView) -> None:
    total = sum(t.estimated_minutes for t in view.plan.tasks)
    options = list(_BUDGETS)
    default = next((m for m in options if m >= total), options[-1])
    key = f"weekly_budget_{view.plan_id}"
    with st.expander("How much time do you have this week?"):
        st.radio(
            "Study time",
            options,
            format_func=_BUDGETS.__getitem__,
            index=options.index(default),
            key=key,
            horizontal=True,
            on_change=_apply_capacity,
            args=(controller, profile_id, key),
        )
        st.caption("A smaller budget drops the lowest-priority tasks. The re-check date stays put.")
        error = st.session_state.pop(_ERROR_KEY, "")
        if error:
            st.warning(error)


def _task_card(
    controller: WorkflowController, profile_id: int, view: WeeklyPlanView, task: WeeklyTask
) -> None:
    done_ids = set(view.done_task_ids)
    checked = st.checkbox(
        f"**{safe_md(task.title)}** · {task.estimated_minutes} min",
        value=task.task_id in done_ids,
        key=f"task_{view.plan_id}_{task.task_id}",
    )
    st.caption(_KIND_LABELS[task.kind])
    st.write(safe_md(task.description))
    st.markdown(f"**You're done when:** {safe_md(task.completion_check)}")
    link = _TASK_LINKS.get(task.kind)
    if link is not None:
        go_button(link[0], link[1], key=f"wk_go_{view.plan_id}_{task.task_id}")
    if checked != (task.task_id in done_ids):
        controller.set_task_done(profile_id, view.plan_id, task.task_id, checked)
        st.rerun()


def _day(
    controller: WorkflowController,
    profile_id: int,
    view: WeeklyPlanView,
    day: DayPlan,
    is_today: bool,
) -> None:
    label = f"{day.day:%a %d %b}"
    today = f" {pill_html('Today', 'info')}" if is_today else ""
    if not day.tasks:
        st.caption(f"{label}{' (today)' if is_today else ''} · rest or catch up")
        return
    st.markdown(f"<strong>{label}</strong>{today} · {day.minutes} min", unsafe_allow_html=True)
    with st.container(border=True):
        for index, task in enumerate(day.tasks):
            if index:
                st.divider()
            _task_card(controller, profile_id, view, task)


def _recheck_card(view: WeeklyPlanView, task: WeeklyTask) -> None:
    due = view.plan.retest_due_date
    st.markdown(f"**{due:%a %d %b}** · re-check day")
    with st.container(border=True):
        st.markdown(f"**{safe_md(task.title)}** · {task.estimated_minutes} min")
        st.write(safe_md(task.description))
        if view.retest_due:
            go_button("Start my re-check", "assessment", key="wk_recheck", primary=True)
        else:
            go_button("Take it early", "assessment", key="wk_recheck")


def render() -> None:
    page_header("Weekly Plan")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    view = controller.get_weekly_plan(profile.id)
    if view is None:
        st.info("Your weekly plan appears after you finish a check on **Skills Check**.")
        go_button("Take the skills check", "assessment", key="wk_to_check", primary=True)
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

    days, recheck = schedule_week(plan)
    study = [t for t in plan.tasks if t.kind != "recheck"]
    done_ids = set(view.done_task_ids)
    done = sum(t.task_id in done_ids for t in study)
    left = sum(t.estimated_minutes for t in study if t.task_id not in done_ids)

    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks done", f"{done} of {len(study)}")
    c2.metric("Study time left", f"{left} min")
    c3.metric("Re-check", "Due now" if view.retest_due else f"in {view.days_until_retest} days")
    st.progress(done / len(study) if study else 0.0)
    if study and done == len(study):
        st.success(
            "All of this week's tasks are done. Take your re-check when it's due, "
            "or early if you feel ready, to see what improved."
        )
    elif done:
        st.caption("Good progress. Each tick moves you closer to your re-check.")

    _capacity_picker(controller, profile.id, view)

    today = (
        None if view.retest_due else plan.retest_due_date - timedelta(days=view.days_until_retest)
    )
    for day in days:
        _day(controller, profile.id, view, day, is_today=day.day == today)
    if recheck is not None:
        _recheck_card(view, recheck)

    st.download_button(
        "Add this week to my calendar (.ics)",
        data=build_ics(plan, view.plan_id),
        file_name="placement-weekly-plan.ics",
        mime="text/calendar",
        key=f"wk_ics_{view.plan_id}",
    )
