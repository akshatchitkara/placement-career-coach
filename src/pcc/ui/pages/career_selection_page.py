"""Career & semester selection (FR-02, FR-17). Builds and saves the roadmap on submit."""

import streamlit as st

from pcc.core.exceptions import WorkflowStateError
from pcc.domain.enums import WorkflowState
from pcc.ui.components.page_frame import require_profile
from pcc.ui.navigation import go_button
from pcc.ui.text import escape_md
from pcc.workflow.workflow_controller import get_controller

_OTHER = "__other__"
_NOTICE_KEY = "career_notice"


def render() -> None:
    st.title("Career & Semester")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return

    notice = st.session_state.pop(_NOTICE_KEY, "")
    if notice:
        st.warning(notice)
    if profile.workflow_state not in (WorkflowState.PROFILE_READY, WorkflowState.CAREER_SELECTED):
        # Outside the Build branch so these buttons survive the rerun a click causes.
        st.success("Roadmap ready.")
        go_button("View my roadmap", "roadmap", key="career_to_roadmap", primary=True)
        go_button("Go straight to the skills check", "assessment", key="career_to_check")

    careers = {c.career_id: c for c in controller.list_careers()}
    options = [*careers, _OTHER]
    labels = {**{cid: c.name for cid, c in careers.items()}, _OTHER: "My career isn't listed"}
    default_index = options.index(profile.career_id) if profile.career_id in careers else 0

    choice = st.radio(
        "Career", options, format_func=labels.get, index=default_index, key="career_choice"
    )
    if choice in careers:
        st.caption(careers[choice].description)
        ready = controller.checkable_semesters(choice)
        if ready:
            st.caption(
                "Skills check available for semester " + ", ".join(str(n) for n in ready) + "."
            )
        else:
            st.caption("Roadmap only for now: skills check questions are being added.")
    custom_text = ""
    if choice == _OTHER:
        custom_text = st.text_input("Type a career", max_chars=60, key="career_custom")
    semester = st.select_slider(
        "Current semester", options=[3, 4, 5, 6], value=profile.current_semester or 3
    )
    if choice in careers and semester not in controller.checkable_semesters(choice):
        st.info(
            f"Semester {semester} has a roadmap but no skills check questions yet. "
            "You can still build the roadmap, or pick a semester with a check."
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
        st.session_state[_NOTICE_KEY] = result.message
        st.rerun()
    else:
        st.error(escape_md(result.message))
