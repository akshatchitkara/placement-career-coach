"""Progress (FR-13): what changed between checks, in plain words."""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.workflow.workflow_controller import get_controller

_ARROWS = {"up": "▲", "down": "▼", "same": "■", "new": "●"}
_LEVEL_NAMES = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
    "industry_ready": "Industry-ready",
}


def render() -> None:
    st.title("Progress")
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        st.info("Create or pick a profile on the **Profile** page first.")
        return
    controller.sync_state(profile.id)
    progress = controller.get_progress(profile.id)
    if not progress.attempts:
        st.info("No checks yet. Take one on **Skills Check** to start tracking progress.")
        return

    names = {s.skill_id: s.name for s in load_skills()}
    latest = progress.attempts[-1]
    if len(progress.attempts) == 1:
        st.write(
            f"Your baseline is **{latest.overall_score:.1f}%** "
            f"({_LEVEL_NAMES[latest.level.value]}). "
            "Follow your weekly plan, then re-check to see what improved."
        )
    else:
        c1, c2 = st.columns(2)
        c1.metric(
            "Overall score",
            f"{latest.overall_score:.1f}%",
            delta=f"{progress.overall_delta:+.1f} points",
        )
        previous_level = (
            _LEVEL_NAMES[progress.previous_level.value] if progress.previous_level else ""
        )
        c2.metric(
            "Level",
            _LEVEL_NAMES[latest.level.value],
            delta="same level"
            if previous_level == _LEVEL_NAMES[latest.level.value]
            else f"was {previous_level}",
            delta_color="off",
        )

        st.subheader("Skill by skill")
        for delta in progress.deltas:
            name = names.get(delta.skill_id, delta.skill_id)
            arrow = _ARROWS[delta.direction]
            if delta.previous_score is None:
                st.write(f"{arrow} **{name}**: {delta.current_score:.0f}% (first time measured)")
            else:
                st.write(
                    f"{arrow} **{name}**: {delta.previous_score:.0f}% → {delta.current_score:.0f}%"
                )

    if progress.skills_below_mastery:
        count = progress.skills_below_mastery
        st.info(
            f"{count} skill{'s are' if count != 1 else ' is'} still below the mastery bar. "
            "Bring them up to move your roadmap marker forward."
        )
    else:
        st.success("Every skill you were tested on is at or above the mastery bar.")
    for skill_id in progress.mentor_skill_ids:
        st.warning(
            f"**{names.get(skill_id, skill_id)}** is below 40%. "
            "Consider asking a mentor or senior to walk you through it."
        )
    for skill_id in progress.repeated_drop_skill_ids:
        st.warning(f"**{names.get(skill_id, skill_id)}** has dropped on two checks in a row.")

    st.subheader("All checks")
    st.dataframe(
        [
            {
                "Check": i,
                "Type": "Baseline" if a.attempt_type == "baseline" else "Re-check",
                "Date": a.submitted_at[:10],
                "Score": f"{a.overall_score:.1f}%",
                "Level": _LEVEL_NAMES[a.level.value],
            }
            for i, a in enumerate(progress.attempts, start=1)
        ],
        hide_index=True,
        width="stretch",
    )
