"""Skills check (FR-04, FR-05): current-semester quiz skills, every question required."""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.core.exceptions import PccError
from pcc.domain.enums import WorkflowState
from pcc.ui.components.question_card import render_question_card
from pcc.workflow.workflow_controller import get_controller


def render() -> None:
    st.title("Skills Check")
    st.caption("Baseline knowledge check. Graded by code, not AI.")
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        st.info("Create or pick a profile on the **Profile** page first.")
        return
    if profile.workflow_state in (WorkflowState.PROFILE_READY, WorkflowState.CAREER_SELECTED):
        st.info("Build your roadmap on **Career & Semester** before taking the check.")
        return
    if profile.workflow_state not in (
        WorkflowState.ROADMAP_READY,
        WorkflowState.ASSESSMENT_IN_PROGRESS,
    ):
        st.success("Your check is done. See **Results** in the sidebar.")
        return

    names = {s.skill_id: s.name for s in load_skills()}
    scope = controller.get_assessment_scope(profile.id)
    st.write(f"**Semester {scope.semester} scope**")
    if scope.assessable_skill_ids:
        st.write("Assessed now: " + ", ".join(names[s] for s in scope.assessable_skill_ids))
    if scope.coming_soon_skill_ids:
        st.write(
            "Assessment coming soon: " + ", ".join(names[s] for s in scope.coming_soon_skill_ids)
        )
    if scope.assessed_later_skill_ids:
        st.write(
            "Assessed later (needs a hands-on or interview method): "
            + ", ".join(names[s] for s in scope.assessed_later_skill_ids)
        )
    if not scope.assessable_skill_ids:
        st.warning(
            "Assessment coming soon: no skill in this semester has a reviewed question bank yet."
        )
        return

    try:
        if profile.workflow_state == WorkflowState.ROADMAP_READY:
            if not st.button("Start skills check", type="primary"):
                return
            controller.start_assessment(profile.id)
            st.rerun()  # redraw in the in-progress state so the Start button disappears
        session = controller.start_assessment(profile.id)  # resumes the open attempt
    except PccError as exc:
        st.error(str(exc))
        return

    st.subheader(f"{session.scope_description} · {len(session.questions)} questions")
    with st.form(f"check_{session.attempt_id}"):
        selections = {
            q.question_id: render_question_card(i, q, f"a{session.attempt_id}")
            for i, q in enumerate(session.questions, start=1)
        }
        submitted = st.form_submit_button("Submit answers", type="primary")
    if not submitted:
        return
    unanswered = sum(v is None for v in selections.values())
    if unanswered:
        st.error(f"Answer every question before submitting ({unanswered} left).")
        return
    try:
        controller.submit_assessment(profile.id, session.attempt_id, selections)
    except PccError as exc:
        st.error(str(exc))
        return
    st.success("Submitted. Open **Results** in the sidebar to see your level.")
    st.rerun()
