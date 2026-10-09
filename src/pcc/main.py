"""Streamlit entry point. UI pages hold no scoring rules, SQL or prompts (Section 7.3)."""

import streamlit as st

from pcc.core.config import settings
from pcc.core.logging_config import configure_logging
from pcc.persistence.database import get_connection, init_schema
from pcc.ui.pages import (
    ai_settings_page,
    assessment_page,
    career_selection_page,
    coaching_page,
    profile_page,
    progress_page,
    results_page,
    roadmap_page,
    weekly_plan_page,
)


def _ensure_db() -> None:
    conn = get_connection(settings.db_path)
    init_schema(conn)
    conn.close()


def main() -> None:
    configure_logging(settings.log_level)
    _ensure_db()

    st.set_page_config(page_title="Placement Career Coach", layout="wide")

    pages = [
        st.Page(profile_page.render, title="Profile", default=True, url_path="profile"),
        st.Page(career_selection_page.render, title="Career & Semester", url_path="career"),
        st.Page(roadmap_page.render, title="Roadmap", url_path="roadmap"),
        st.Page(assessment_page.render, title="Skills Check", url_path="assessment"),
        st.Page(results_page.render, title="Results", url_path="results"),
        st.Page(coaching_page.render, title="Coaching Plan", url_path="coaching"),
        st.Page(weekly_plan_page.render, title="Weekly Plan", url_path="weekly-plan"),
        st.Page(progress_page.render, title="Progress", url_path="progress"),
        st.Page(ai_settings_page.render, title="AI Settings", url_path="ai-settings"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
