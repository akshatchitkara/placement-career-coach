"""Shared page chrome: header and the 'pick a profile first' guard."""

from typing import TYPE_CHECKING

import streamlit as st

from pcc.ui.navigation import go_button
from pcc.workflow.workflow_controller import get_controller

if TYPE_CHECKING:
    from pcc.persistence.repositories.profile_repository import Profile


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def require_profile() -> "Profile | None":
    """Returns the signed-in profile, or shows a friendly prompt and returns None."""
    profile_id = st.session_state.get("profile_id")
    profile = get_controller().get_profile(profile_id) if profile_id else None
    if profile is None:
        st.info("Create or pick a profile on the **Profile** page first.")
        go_button("Go to Profile", "profile", key="guard_to_profile", primary=True)
    return profile
