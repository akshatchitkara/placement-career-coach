"""Streamlit entry point. UI pages hold no scoring rules, SQL or prompts (Section 7.3)."""

import sys
from pathlib import Path

import streamlit as st

# `streamlit run` puts only this file's folder on sys.path; make `pcc` importable without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pcc.core.config import settings
from pcc.core.logging_config import configure_logging
from pcc.persistence.database import get_connection, init_schema
from pcc.ui.pages import (
    ai_settings_page,
    assessment_page,
    career_selection_page,
    coaching_page,
    m1_preview_page,
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
        st.Page(m1_preview_page.render, title="M1 Preview", url_path="m1-preview"),
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
