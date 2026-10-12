"""Month-by-month roadmap view with a highlighted current semester."""

import streamlit as st

from pcc.domain.schemas.roadmap_schemas import Roadmap
from pcc.ui.text import safe_md


def render_roadmap_timeline(
    roadmap: Roadmap, skill_names: dict[str, str], current_semester: int | None
) -> None:
    for semester in (3, 4, 5, 6):
        marker = "  ← you are in this semester" if semester == current_semester else ""
        st.header(f"Semester {semester}{marker}")
        months = sorted(
            (m for m in roadmap.months if m.semester == semester), key=lambda m: m.month_index
        )
        for month in months:
            title = f"Month {month.month_index} · {skill_names.get(month.skill_id, month.skill_id)}"
            with st.expander(title, expanded=semester == current_semester):
                st.markdown(f"**Focus:** {safe_md(month.focus)}")
                st.markdown("**Topics**\n" + "\n".join(f"- {safe_md(t)}" for t in month.topics))
                st.markdown(f"**Deliverable:** {safe_md(month.deliverable)}")
