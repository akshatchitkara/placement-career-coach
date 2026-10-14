"""Career & semester selection (FR-02, FR-17). Builds and saves the roadmap on submit.

The page reveals itself in order: career, then what the career is about and how it grows,
then the semester, then the build button.
"""

import html

import streamlit as st

from pcc.core.exceptions import PccError, WorkflowStateError
from pcc.domain.enums import WorkflowState
from pcc.domain.schemas.career_schemas import Career
from pcc.ui.components.page_frame import require_profile
from pcc.ui.navigation import go_button
from pcc.ui.text import escape_md
from pcc.workflow.workflow_controller import get_controller


def _career_card(career: Career) -> None:
    """What the career is, what the days look like, and where it can lead."""
    steps = "".join(
        f'<li class="pcc-grow-step"><span>{i}</span>{html.escape(step)}</li>'
        for i, step in enumerate(career.growth_path, start=1)
    )
    days = "".join(f"<li>{html.escape(item)}</li>" for item in career.day_to_day)
    st.markdown(
        f'<div class="pcc-career-card"><h3>{html.escape(career.name)}</h3>'
        f"<p>{html.escape(career.overview or career.description)}</p>"
        f"<h4>What you will do</h4><ul>{days}</ul>"
        f'<h4>How you can grow</h4><ol class="pcc-grow">{steps}</ol></div>',
        unsafe_allow_html=True,
    )


def _wish_list(profile_id: int) -> None:
    with st.expander("Want a career we don't have yet?"):
        st.caption("Tell us which one and we will use it to decide what to add next.")
        wish = st.text_input("Career you would like", max_chars=60, key="career_wish")
        if st.button("Send request", key="career_wish_send"):
            try:
                st.success(escape_md(get_controller().request_career(profile_id, wish)))
            except PccError as exc:
                st.error(escape_md(str(exc)))


def render() -> None:
    st.title("Career & Semester")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return

    if profile.workflow_state not in (WorkflowState.PROFILE_READY, WorkflowState.CAREER_SELECTED):
        # Outside the Build branch so these buttons survive the rerun a click causes.
        st.success("Your roadmap is ready.")
        go_button("Start my journey", "roadmap", key="career_to_roadmap", primary=True)
        go_button("Go straight to the skills check", "assessment", key="career_to_check")

    careers = {c.career_id: c for c in controller.list_careers()}
    options = list(careers)
    default_index = options.index(profile.career_id) if profile.career_id in careers else None

    choice = st.radio(
        "Choose your career",
        options,
        format_func=lambda cid: careers[cid].name,
        index=default_index,
        key="career_choice",
    )
    if choice is None:
        st.caption("Pick a career to see what it involves and where it can take you.")
        _wish_list(profile.id)
        return

    _career_card(careers[choice])
    ready = controller.checkable_semesters(choice)
    if ready:
        st.caption("Skills check available for semester " + ", ".join(str(n) for n in ready) + ".")
    else:
        st.caption("Roadmap only for now: skills check questions are being added.")

    semester = st.radio(
        "Your current semester",
        [3, 4, 5, 6],
        format_func=lambda n: f"Semester {n}",
        index=[3, 4, 5, 6].index(profile.current_semester) if profile.current_semester else None,
        horizontal=True,
        key="career_semester",
    )
    if semester is None:
        _wish_list(profile.id)
        return
    if semester not in ready:
        st.info(
            f"Semester {semester} has a roadmap but no skills check questions yet. "
            "You can still build the roadmap, or pick a semester with a check."
        )

    if st.button("Build my roadmap", type="primary", key="career_build"):
        try:
            with st.spinner("Building your roadmap..."):
                result = controller.select_career(
                    profile.id, career_id=choice, custom_text="", semester=semester
                )
        except WorkflowStateError as exc:
            st.error(f"Career can't be changed at this stage: {exc}")
            return
        if result.status == "roadmap_ready":
            # How the roadmap was produced is logged, not shown: a fallback is a normal outcome.
            st.rerun()
        else:
            st.error(escape_md(result.message))
    _wish_list(profile.id)
