"""Home: where the student is in the journey and the single next thing to do."""

import streamlit as st

from pcc.ui.components.journey import next_step, next_step_button, render_stepper, state_label
from pcc.ui.components.level_badge import LEVEL_LABELS
from pcc.ui.components.progress_visuals import sparkline_svg
from pcc.ui.navigation import go_button
from pcc.workflow.workflow_controller import get_controller

_FEATURES = [
    ("1. Pick a career", "Choose from four placement-focused careers and your current semester."),
    ("2. Get a roadmap", "A month-by-month plan from semester 3 to 6, personalised to you."),
    ("3. Check your skills", "A short quiz graded by code, so your level is consistent and fair."),
    ("4. Fix your gaps", "Targeted coaching and a weekly plan, then a re-check to prove progress."),
]


def _welcome() -> None:
    st.markdown(
        '<div class="pcc-hero"><h1>Placement Career Coach</h1>'
        "<p>Find out where you stand for your target job, and get a clear weekly plan to close "
        "the gap before placements.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    for col, (title, text) in zip(cols, _FEATURES, strict=True):
        col.markdown(
            f'<div class="pcc-feature"><h4>{title}</h4><p>{text}</p></div>', unsafe_allow_html=True
        )
    st.write("")
    go_button("Get started", "profile", key="home_get_started", primary=True)
    st.caption("No password needed. Enter a display name on the Profile page to begin.")


def render() -> None:
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        _welcome()
        return

    controller.sync_state(profile.id)
    profile = controller.get_profile(profile.id) or profile
    st.title(f"Welcome back, {profile.display_name}")
    career_names = {c.career_id: c.name for c in controller.list_careers()}
    if profile.career_id:
        st.caption(
            f"{career_names.get(profile.career_id, profile.career_id)} · "
            f"Semester {profile.current_semester} · {state_label(profile.workflow_state)}"
        )
    render_stepper(profile.workflow_state)

    message, _, _ = next_step(profile.workflow_state)
    with st.container(border=True):
        st.subheader("Your next step")
        st.write(message)
        next_step_button(profile.workflow_state, key="home_next")

    result = controller.get_latest_results(profile.id)
    if result is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Latest score", f"{result.overall_score:.1f}%")
        c2.metric("Level", LEVEL_LABELS[result.level])
        view = controller.get_weekly_plan(profile.id)
        if view is not None:
            if view.retest_due:
                c3.metric("Re-check", "Due now")
            else:
                c3.metric("Re-check in", f"{view.days_until_retest} days")
        progress = controller.get_progress(profile.id)
        if len(progress.attempts) > 1:
            first, last = progress.attempts[0], progress.attempts[-1]
            change = last.overall_score - first.overall_score
            trend = sparkline_svg([a.overall_score for a in progress.attempts], 160, 40)
            if change == 0:
                headline = "No change"
            else:
                headline = f"{'Up' if change > 0 else 'Down'} {abs(change):.1f} points"
            st.markdown(
                f"{trend} &nbsp; **{headline}** since your baseline, "
                f"over {len(progress.attempts)} checks.",
                unsafe_allow_html=True,
            )
            go_button("See my progress", "progress", key="home_progress")
