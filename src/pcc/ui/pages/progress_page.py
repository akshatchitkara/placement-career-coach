"""Progress (FR-13): what changed between checks, and whether the effort showed up in the scores."""

import streamlit as st

from pcc.content.content_loader import load_app_settings, load_skills
from pcc.domain.progress import AttemptSummary
from pcc.ui.components.game_strip import render_badge_shelf
from pcc.ui.components.level_badge import LEVEL_LABELS
from pcc.ui.components.page_frame import page_header, require_profile
from pcc.ui.components.progress_visuals import render_skill_changes, render_trend
from pcc.ui.navigation import go_button
from pcc.workflow.workflow_controller import WorkflowController, get_controller


def _effort(
    controller: WorkflowController, profile_id: int, attempts: list[AttemptSummary]
) -> None:
    weeks = controller.get_effort(profile_id)
    if not weeks:
        return
    st.header("Did the effort show up?")
    order = {a.attempt_id: i for i, a in enumerate(attempts)}
    for week in weeks:
        index = order[week.from_attempt_id]
        before = "your baseline" if index == 0 else f"re-check {index}"
        change = (
            "not compared (the two checks covered different skills)"
            if week.score_change is None
            else "no change"
            if abs(week.score_change) < 0.05
            else f"{week.score_change:+.1f} points"
        )
        st.markdown(
            f"**Week after {before}:** {week.tasks_done} of {week.tasks_total} tasks done "
            f"({week.minutes_done} min) · score {change} at the next check"
        )
    st.caption("This is context, not proof: many things affect a score.")


def render() -> None:
    page_header("Progress")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    controller.sync_state(profile.id)
    progress = controller.get_progress(profile.id)
    if not progress.attempts:
        st.info("No checks yet. Take one on **Skills Check** to start tracking progress.")
        go_button("Take the skills check", "assessment", key="progress_to_check", primary=True)
        return

    names = {s.skill_id: s.name for s in load_skills()}
    settings = load_app_settings()
    attempts = progress.attempts
    latest = attempts[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Latest score",
        f"{latest.overall_score:.1f}%",
        delta=f"{progress.overall_delta:+.1f} points"
        if progress.overall_delta is not None
        else None,
    )
    if progress.scope_changed:
        st.info(
            "Your last two checks covered different skills (a semester check and a full-path "
            "check), so the overall score change is not shown. Compare skill by skill below."
        )
    previous = progress.previous_level
    c2.metric(
        "Level",
        LEVEL_LABELS[latest.level],
        delta=(
            None
            if previous is None
            else "same level"
            if previous == latest.level
            else f"was {LEVEL_LABELS[previous]}"
        ),
        delta_color="off",
    )
    c3.metric("Checks taken", len(attempts))

    view = controller.get_weekly_plan(profile.id)
    with st.container(border=True):
        if len(attempts) == 1:
            st.write(
                "This is your baseline. Follow your weekly plan, then re-check to see "
                "what improved."
            )
        if view is not None and view.retest_due:
            st.write("Your re-check is due.")
            go_button("Start my re-check", "assessment", key="progress_recheck", primary=True)
        elif view is not None:
            st.write(f"Your re-check is in {view.days_until_retest} days.")
            go_button("Open this week's plan", "weekly", key="progress_weekly", primary=True)

    st.header("Your badges")
    render_badge_shelf(controller.get_game_state(profile.id))

    st.header("Your score over time")
    render_trend(attempts, settings.level_lower_bounds)

    st.header("Skill by skill")
    render_skill_changes(attempts, names, settings.mastery_threshold)

    _effort(controller, profile.id, attempts)

    if progress.skills_below_mastery:
        count = progress.skills_below_mastery
        st.info(
            f"{count} skill{'s are' if count != 1 else ' is'} still below the mastery bar. "
            "Bring them up to move your roadmap marker forward."
        )
    else:
        st.success("Every skill you were tested on is at or above the mastery bar.")
    for skill_id in progress.repeated_drop_skill_ids:
        st.warning(f"**{names.get(skill_id, skill_id)}** has dropped on two checks in a row.")

    notes = controller.get_mentor_notes(profile.id)
    for skill_id, message in notes.items():
        st.warning(
            f"**{names.get(skill_id, skill_id)}** is below 40%. "
            "A mentor or senior can save you a lot of time here."
        )
        with st.expander(f"A message you can send about {names.get(skill_id, skill_id)}"):
            st.code(message, language=None, wrap_lines=True)

    with st.expander("All checks"):
        st.dataframe(
            [
                {
                    "Check": i,
                    "Type": {"baseline": "Baseline", "full_path": "Full-path check"}.get(
                        a.attempt_type, "Re-check"
                    ),
                    "Date": a.submitted_at[:10],
                    "Score": f"{a.overall_score:.1f}%",
                    "Level": LEVEL_LABELS[a.level],
                }
                for i, a in enumerate(attempts, start=1)
            ],
            hide_index=True,
            width="stretch",
        )
