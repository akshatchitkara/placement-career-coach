"""Roadmap page (FR-03): the validated Sem 3-6 plan, shown as a road with a quiz at each stop."""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.ui.components.game_strip import render_game_strip
from pcc.ui.components.page_frame import require_profile
from pcc.ui.components.roadmap_road import render_roadmap_road
from pcc.ui.navigation import go_button
from pcc.workflow.workflow_controller import get_controller

_SOURCE_LABELS = {
    "template": "Curated roadmap",
    "ai_personalised": "Curated sequence, wording personalised by AI",
    "ai_drafted_unverified": "AI-drafted, unverified",
}


def render() -> None:
    st.title("Roadmap")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    roadmap = controller.get_roadmap(profile.id)
    if roadmap is None:
        st.info("No roadmap yet. Choose a career on **Career & Semester**.")
        go_button("Choose my career", "career", key="roadmap_to_career", primary=True)
        return

    career_names = {c.career_id: c.name for c in controller.list_careers()}
    st.caption(
        f"{career_names.get(roadmap.career_id, roadmap.career_id)} · Semesters 3-6 · "
        f"{len(roadmap.months)} months · {_SOURCE_LABELS[roadmap.generation_source]}"
    )
    render_game_strip(controller.get_game_state(profile.id))
    st.write("Finish a module, pass its quick quiz, and move along the road.")
    go_button("Take the skills check", "assessment", key="road_check_top", primary=True)
    skill_names = {s.skill_id: s.name for s in load_skills()}
    render_roadmap_road(controller, profile.id, roadmap, skill_names, profile.current_semester)
    st.divider()
    st.subheader("Ready to see where you stand?")
    go_button("Take the skills check", "assessment", key="road_check_bottom", primary=True)
