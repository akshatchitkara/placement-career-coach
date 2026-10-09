"""Profile page (FR-01): pick or create a profile by display name. No password."""

import streamlit as st

from pcc.core.exceptions import PccError
from pcc.workflow.workflow_controller import get_controller


def render() -> None:
    st.title("Profile")
    st.caption("Enter a display name to start or continue. No password, no other personal data.")
    controller = get_controller()

    with st.form("open_profile"):
        name = st.text_input("Display name", max_chars=40)
        submitted = st.form_submit_button("Start / continue")
    if submitted:
        try:
            profile = controller.open_profile(name)
        except PccError as exc:
            st.error(str(exc))
        else:
            st.session_state["profile_id"] = profile.id

    existing = controller.list_profiles()
    if existing:
        labels = {p.id: p.display_name for p in existing}
        picked = st.selectbox("Or continue as", list(labels), format_func=labels.get, index=None)
        if picked is not None:
            st.session_state["profile_id"] = picked

    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        return
    st.success(f"Signed in as **{profile.display_name}**.")
    if profile.career_id:
        career_names = {c.career_id: c.name for c in controller.list_careers()}
        st.write(
            f"Career: **{career_names.get(profile.career_id, profile.career_id)}** · "
            f"Semester **{profile.current_semester}** · "
            f"Progress: `{profile.workflow_state.value}`"
        )
    else:
        st.write("Next: open **Career & Semester** in the sidebar.")
