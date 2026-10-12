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
from pcc.ui.navigation import register_pages
from pcc.ui.pages import (
    ai_settings_page,
    assessment_page,
    career_selection_page,
    coaching_page,
    home_page,
    m1_preview_page,
    profile_page,
    progress_page,
    results_page,
    roadmap_page,
    weekly_plan_page,
)
from pcc.ui.text import escape_md
from pcc.ui.theme import inject_css
from pcc.workflow.workflow_controller import get_controller

APP_NAME = "Placement Career Coach"


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
        slot.caption(
            f"Signed in as **{escape_md(profile.display_name)}** (change on the Profile page)"
        )


def main() -> None:
    configure_logging(settings.log_level)
    st.set_page_config(page_icon=":material/school:", layout="wide")

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

    def page(render, title, path, **kwargs):
        guarded = safe_page(render)
        tab_title = APP_NAME if kwargs.get("default") else f"{title} · {APP_NAME}"

        def run() -> None:
            st.set_page_config(page_title=tab_title)  # each page gets its own browser-tab title
            guarded()

        return st.Page(run, title=title, url_path=path, **kwargs)

    registry = {
        "home": page(home_page.render, "Home", "", default=True, icon=":material/home:"),
        "profile": page(profile_page.render, "Profile", "profile", icon=":material/person:"),
        "career": page(
            career_selection_page.render, "Career & Semester", "career", icon=":material/work:"
        ),
        "roadmap": page(roadmap_page.render, "Roadmap", "roadmap", icon=":material/map:"),
        "assessment": page(
            assessment_page.render, "Skills Check", "assessment", icon=":material/quiz:"
        ),
        "results": page(results_page.render, "Results", "results", icon=":material/insights:"),
        "coaching": page(
            coaching_page.render, "Coaching Plan", "coaching", icon=":material/school:"
        ),
        "weekly": page(
            weekly_plan_page.render, "Weekly Plan", "weekly-plan", icon=":material/checklist:"
        ),
        "progress": page(
            progress_page.render, "Progress", "progress", icon=":material/trending_up:"
        ),
        "ai": page(
            ai_settings_page.render, "AI Settings", "ai-settings", icon=":material/settings:"
        ),
    }
    sections = {
        "": [registry["home"]],
        "Plan": [registry["career"], registry["roadmap"]],
        "Assess": [registry["assessment"], registry["results"]],
        "Improve": [registry["coaching"], registry["weekly"], registry["progress"]],
        "Account": [registry["profile"], registry["ai"]],
    }
    if settings.show_dev_pages:
        sections["Developer"] = [page(m1_preview_page.render, "M1 Preview", "m1-preview")]
    register_pages(registry)
    inject_css()
    nav = st.navigation(sections)
    _restore_session()
    signed_in_slot = st.sidebar.empty()
    _show_ai_status()
    nav.run()
    _show_signed_in(signed_in_slot)


if __name__ == "__main__":
    main()
