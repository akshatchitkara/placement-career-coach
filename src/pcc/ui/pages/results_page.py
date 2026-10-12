"""Results (FR-06..FR-08): level, per-skill breakdown with counts, position, weakest skill."""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.ui.components.level_badge import render_level_badge
from pcc.ui.components.page_frame import page_header, require_profile
from pcc.ui.components.results_visuals import level_ladder, skill_bars
from pcc.ui.components.skill_score_table import render_skill_score_table
from pcc.ui.navigation import go_button
from pcc.workflow.workflow_controller import get_controller


def render() -> None:
    page_header("Results")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    result = controller.get_latest_results(profile.id)
    if result is None:
        st.info("No results yet. Take the check on **Skills Check**.")
        go_button("Take the skills check", "assessment", key="results_to_check", primary=True)
        return

    names = {s.skill_id: s.name for s in load_skills()}
    st.caption("Re-check" if result.attempt_type == "retest" else "Baseline knowledge check")
    with st.container(border=True):
        render_level_badge(
            result.level, result.scope_description, result.overall_score, result.level_notes
        )
        level_ladder(result.level, result.overall_score, result.level_lower_bounds)
    st.caption(f"Coverage of the career's core skills: {result.coverage_ratio:.0%}")

    weakest = result.weakest
    st.subheader("What to focus on")
    if weakest.status == "weakest_found" and weakest.skill_id:
        st.warning(
            f"**Your biggest opportunity: {names[weakest.skill_id]}.** "
            "It scored lowest, so a little practice here moves your level the most."
        )
        go_button("Start coaching on it", "coaching", key="results_to_coaching", primary=True)
    elif weakest.status == "no_major_gap":
        nxt = names.get(weakest.next_roadmap_skill_id or "")
        st.success("No major gap found." + (f" Next on your roadmap: **{nxt}**." if nxt else ""))
    else:
        st.info("Not enough answers yet to name a skill to focus on. A re-check will help.")
    go_button("See my weekly plan", "weekly", key="results_to_weekly")

    st.subheader("Your skills")
    skill_bars(
        result.skill_scores, names, result.mastery_threshold, result.min_answered_for_evidence
    )
    with st.expander("Full numbers"):
        render_skill_score_table(result.skill_scores, names, result.min_answered_for_evidence)

    position = result.position
    skill = names.get(position.skill_id or "", "")
    if position.label == "in_progress":
        st.write(f"**Where you are on your roadmap:** {skill}")
    elif position.label == "advance_to_next_semester":
        st.write(f"**Everything tested is mastered.** Next up: {skill}")
    else:
        st.write("**Roadmap complete.**")

    with st.expander("Review your answers"):
        for review in result.reviews:
            badge = ":green-badge[Correct]" if review.is_correct else ":red-badge[Incorrect]"
            st.markdown(f"{badge} **{review.stem}**")
            st.write(f"Your answer: {review.selected_option_text}")
            if not review.is_correct:
                st.write(f"Correct answer: {review.correct_option_text}")
            st.caption(review.explanation)
