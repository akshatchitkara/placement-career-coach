"""Roadmap page (FR-03): the validated Sem 3-6, month-by-month plan."""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.ui.components.page_frame import require_profile
from pcc.ui.components.roadmap_timeline import render_roadmap_timeline
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
        return

    career_names = {c.career_id: c.name for c in controller.list_careers()}
    st.caption(
        f"{career_names.get(roadmap.career_id, roadmap.career_id)} · Semesters 3-6 · "
        f"{len(roadmap.months)} months · {_SOURCE_LABELS[roadmap.generation_source]}"
    )
    skill_names = {s.skill_id: s.name for s in load_skills()}
    render_roadmap_timeline(roadmap, skill_names, profile.current_semester)
