"""Results (FR-06..FR-08): level, per-skill breakdown with counts, position, weakest skill."""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.ui.components.level_badge import render_level_badge, render_level_rules
from pcc.ui.components.skill_score_table import render_skill_score_table
from pcc.workflow.workflow_controller import get_controller


def render() -> None:
    st.title("Results")
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        st.info("Create or pick a profile on the **Profile** page first.")
        return
    result = controller.get_latest_results(profile.id)
    if result is None:
        st.info("No results yet. Take the check on **Skills Check**.")
        return

    names = {s.skill_id: s.name for s in load_skills()}
    st.caption("Baseline knowledge check")
    render_level_badge(
        result.level, result.scope_description, result.overall_score, result.level_notes
    )
    render_level_rules(result.level_lower_bounds)
    st.caption(f"Coverage of the career's core skills: {result.coverage_ratio:.0%}")

    st.subheader("Skill breakdown")
    render_skill_score_table(result.skill_scores, names, result.min_answered_for_evidence)

    st.subheader("Where you stand")
    position = result.position
    skill = names.get(position.skill_id or "", "")
    if position.label == "in_progress":
        st.write(f"You are here: **{skill}**")
    elif position.label == "advance_to_next_semester":
        st.write(f"Everything tested is mastered. Next up: **{skill}**")
    else:
        st.write("Roadmap complete.")

    st.subheader("Weakest skill")
    weakest = result.weakest
    if weakest.status == "weakest_found" and weakest.skill_id:
        st.error(f"**{names[weakest.skill_id]}** is your weakest skill.")
        st.caption("Your practice plan for it is on the **Coaching Plan** page.")
    elif weakest.status == "no_major_gap":
        nxt = names.get(weakest.next_roadmap_skill_id or "")
        st.success("No major gap found." + (f" Next on your roadmap: **{nxt}**." if nxt else ""))
    else:
        st.warning("Not enough evidence yet to name a weakest skill.")

    with st.expander("Review your answers"):
        for review in result.reviews:
            icon = "✅" if review.is_correct else "❌"
            st.markdown(f"{icon} **{review.stem}**")
            st.write(f"Your answer: {review.selected_option_text}")
            if not review.is_correct:
                st.write(f"Correct answer: {review.correct_option_text}")
            st.caption(review.explanation)
