"""Streamlit entry point. UI pages hold no scoring rules, SQL or prompts (Section 7.3)."""

import sys
from pathlib import Path

import streamlit as st

# `streamlit run` puts only this file's folder on sys.path; make `pcc` importable without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pcc.content.content_validator import check_installed_content
from pcc.core.config import settings
from pcc.core.logging_config import configure_logging
from pcc.persistence.database import get_connection, init_schema
from pcc.ui.error_boundary import safe_page
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
from pcc.workflow.workflow_controller import get_controller


def _ensure_db() -> None:
    conn = get_connection(settings.db_path)
    init_schema(conn)
    conn.close()


@st.cache_resource
def _content_issues() -> list[str]:
    """Checked once per server start; restart the app after editing content."""
    return check_installed_content()


def _show_ai_status() -> None:
    status = get_controller().get_ai_status()
    st.sidebar.caption(status.label)
    if status.warning:
        st.sidebar.warning(f"{status.warning} Running in offline mode instead.")


def _restore_session() -> None:
    """A reload starts a new browser session; reopen the last profile so progress is not 'lost'."""
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    if profile_id is not None and controller.get_profile(profile_id) is not None:
        return
    last = controller.last_active_profile()
    if last is not None:
        st.session_state["profile_id"] = last.id
    else:
        st.session_state.pop("profile_id", None)


def _show_signed_in(slot) -> None:
    """Filled after the page has run, so it never names a profile just switched away from."""
    profile_id = st.session_state.get("profile_id")
    profile = get_controller().get_profile(profile_id) if profile_id is not None else None
    if profile is not None:
        slot.caption(f"Signed in as **{profile.display_name}** (change on the Profile page)")


def main() -> None:
    configure_logging(settings.log_level)
    st.set_page_config(page_title="Placement Career Coach", layout="wide")

    issues = _content_issues()
    if issues:
        st.error("The app's content files have problems, so it cannot start safely.")
        st.code("\n".join(issues[:20]))
        st.caption("Fix data/content/ and run `python scripts/validate_content.py`, then reload.")
        st.stop()

    try:
        _ensure_db()
    except Exception:  # noqa: BLE001 -- show a clear message rather than a stack trace
        st.error(
            f"Could not open the database at {settings.db_path}. "
            "Check that the folder exists and is writable, then reload."
        )
        st.stop()

    pages = [
        st.Page(safe_page(profile_page.render), title="Profile", default=True, url_path="profile"),
        st.Page(
            safe_page(career_selection_page.render), title="Career & Semester", url_path="career"
        ),
        st.Page(safe_page(roadmap_page.render), title="Roadmap", url_path="roadmap"),
        st.Page(safe_page(assessment_page.render), title="Skills Check", url_path="assessment"),
        st.Page(safe_page(results_page.render), title="Results", url_path="results"),
        st.Page(safe_page(coaching_page.render), title="Coaching Plan", url_path="coaching"),
        st.Page(safe_page(weekly_plan_page.render), title="Weekly Plan", url_path="weekly-plan"),
        st.Page(safe_page(progress_page.render), title="Progress", url_path="progress"),
        st.Page(safe_page(ai_settings_page.render), title="AI Settings", url_path="ai-settings"),
    ]
    if settings.show_dev_pages:
        pages.append(
            st.Page(safe_page(m1_preview_page.render), title="M1 Preview", url_path="m1-preview")
        )
    nav = st.navigation(pages)
    _restore_session()
    signed_in_slot = st.sidebar.empty()
    _show_ai_status()
    nav.run()
    _show_signed_in(signed_in_slot)


if __name__ == "__main__":
    main()
