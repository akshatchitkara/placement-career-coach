"""Career & semester selection (FR-02, FR-17). Builds and saves the roadmap on submit."""

import streamlit as st

from pcc.core.exceptions import WorkflowStateError
from pcc.workflow.workflow_controller import get_controller

_OTHER = "__other__"


def render() -> None:
    st.title("Career & Semester")
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        st.info("Create or pick a profile on the **Profile** page first.")
        return

    careers = {c.career_id: c for c in controller.list_careers()}
    options = [*careers, _OTHER]
    labels = {**{cid: c.name for cid, c in careers.items()}, _OTHER: "My career isn't listed"}
    default_index = options.index(profile.career_id) if profile.career_id in careers else 0

    choice = st.radio(
        "Career", options, format_func=labels.get, index=default_index, key="career_choice"
    )
    if choice in careers:
        st.caption(careers[choice].description)
    custom_text = ""
    if choice == _OTHER:
        custom_text = st.text_input("Type a career", max_chars=60, key="career_custom")
    semester = st.select_slider(
        "Current semester", options=[3, 4, 5, 6], value=profile.current_semester or 3
    )

    if not st.button("Build my roadmap", type="primary"):
        return
    try:
        with st.spinner("Building your roadmap..."):
            result = controller.select_career(
                profile.id,
                career_id=None if choice == _OTHER else choice,
                custom_text=custom_text,
                semester=semester,
            )
    except WorkflowStateError as exc:
        st.error(f"Career can't be changed at this stage: {exc}")
        return

    if result.status == "roadmap_ready":
        if result.message:
            st.warning(result.message)
        st.success("Roadmap ready. Open **Roadmap** in the sidebar.")
    else:
        st.error(result.message)
