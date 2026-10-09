"""Skills check (FR-04, FR-05): current-semester quiz skills, every question required.

Also hosts the re-check (FR-13): same skills, unseen questions first.
"""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.core.exceptions import PccError
from pcc.domain.enums import WorkflowState
from pcc.ui.components.question_card import render_question_card
from pcc.workflow.workflow_controller import get_controller

_FLASH_KEY = "check_just_submitted"


def render() -> None:
    st.title("Skills Check")
    st.caption("Knowledge check. Graded by code, not AI.")
    controller = get_controller()
    profile_id = st.session_state.get("profile_id")
    profile = controller.get_profile(profile_id) if profile_id else None
    if profile is None:
        st.info("Create or pick a profile on the **Profile** page first.")
        return
    controller.sync_state(profile.id)
    profile = controller.get_profile(profile.id)
    assert profile is not None

    if st.session_state.pop(_FLASH_KEY, False):
        st.success(
            "Submitted. See **Results** for your level, **Coaching Plan** and **Weekly Plan** "
            "for what to do next."
        )
    state = profile.workflow_state
    if state in (WorkflowState.PROFILE_READY, WorkflowState.CAREER_SELECTED):
        st.info("Build your roadmap on **Career & Semester** before taking the check.")
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
        if state in (
            WorkflowState.ROADMAP_READY,
            WorkflowState.WEEKLY_PLAN_ACTIVE,
            WorkflowState.RETEST_DUE,
        ):
            label = "Start skills check"
            if state != WorkflowState.ROADMAP_READY:
                view = controller.get_weekly_plan(profile.id)
                if view is not None and view.retest_due:
                    st.warning("Your re-check is due. Unseen questions are used first.")
                elif view is not None:
                    st.info(
                        f"Your re-check is planned for {view.plan.retest_due_date:%d %b %Y}. "
                        "You can take it early; unseen questions are used first."
                    )
                label = "Start re-check"
            if not st.button(label, type="primary"):
                return
            controller.start_assessment(profile.id)
            st.rerun()  # redraw in the in-progress state so the Start button disappears
        session = controller.start_assessment(profile.id)  # resumes the open attempt
    except PccError as exc:
        st.error(str(exc))
        return

    kind = "Re-check" if session.attempt_type == "retest" else "Skills check"
    st.subheader(f"{kind} · {session.scope_description} · {len(session.questions)} questions")
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
    st.session_state[_FLASH_KEY] = True
    st.rerun()
