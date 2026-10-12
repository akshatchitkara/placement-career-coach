"""Skills check (FR-04, FR-05): current-semester quiz skills, every question required.

Also hosts the re-check (FR-13): same skills, unseen questions first.
"""

import streamlit as st

from pcc.content.content_loader import load_skills
from pcc.core.exceptions import PccError
from pcc.domain.enums import WorkflowState
from pcc.ui.components.check_wizard import render_check_wizard
from pcc.ui.components.page_frame import require_profile
from pcc.ui.navigation import go_button
from pcc.workflow.workflow_controller import get_controller

_FLASH_KEY = "check_just_submitted"


def render() -> None:
    st.title("Skills Check")
    st.caption(
        "A short knowledge check. Your score is calculated by fixed rules, the same for everyone."
    )
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    controller.sync_state(profile.id)
    profile = controller.get_profile(profile.id)
    if profile is None:
        raise PccError("Profile not found.")

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
    with st.expander(f"What's covered in semester {scope.semester}", expanded=False):
        if scope.assessable_skill_ids:
            st.write(
                "**In this check:** " + ", ".join(names[s] for s in scope.assessable_skill_ids)
            )
        if scope.coming_soon_skill_ids:
            st.write(
                "**Questions coming soon:** "
                + ", ".join(names[s] for s in scope.coming_soon_skill_ids)
            )
        if scope.assessed_later_skill_ids:
            st.write(
                "**Not a quiz topic (project or interview based):** "
                + ", ".join(names[s] for s in scope.assessed_later_skill_ids)
            )
    if not scope.assessable_skill_ids:
        ready = controller.checkable_semesters(profile.career_id) if profile.career_id else []
        hint = (
            " Skills checks are ready for semester "
            + ", ".join(str(n) for n in ready)
            + "."
            + " Change your semester on **Career & Semester** to try one."
            if ready
            else ""
        )
        st.warning(
            "Assessment coming soon: no skill in this semester has a reviewed question bank yet."
            + hint
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
                go_button("See my latest results", "results", key="check_to_results")
                view = controller.get_weekly_plan(profile.id)
                if view is not None and view.retest_due:
                    st.warning("Your re-check is due. Unseen questions are used first.")
                elif view is not None:
                    st.info(
                        f"Your re-check is planned for {view.plan.retest_due_date:%d %b %Y}. "
                        "You can take it early; unseen questions are used first."
                    )
                label = "Start re-check"
            start = st.button(label, type="primary")
            full_path = False
            if controller.can_take_full_path(profile.id):
                full_scope = controller.get_assessment_scope(profile.id, full_path=True)
                questions = 2 * len(full_scope.assessable_skill_ids)
                st.caption(
                    f"Or check every skill on your roadmap, Semesters 3 to 6 ({questions} "
                    "questions, two per skill). It is the only check that can place you at "
                    "Industry-ready."
                )
                full_path = st.button("Take the full-path check", key="start_full_path")
            if not (start or full_path):
                return
            controller.start_assessment(profile.id, full_path=full_path)
            st.rerun()  # redraw in the in-progress state so the Start button disappears
        session = controller.start_assessment(profile.id)  # resumes the open attempt
    except PccError as exc:
        st.error(str(exc))
        return

    kind = {"retest": "Re-check", "full_path": "Full-path check"}.get(
        session.attempt_type, "Skills check"
    )
    st.header(f"{kind} · {session.scope_description} · {len(session.questions)} questions")

    def save_draft(answers: dict[str, str]) -> None:
        try:
            controller.save_check_draft(profile.id, session.attempt_id, answers)
        except PccError:
            pass  # for example the check was submitted in another tab; the page catches up

    selections = render_check_wizard(
        session.attempt_id,
        session.questions,
        load_draft=lambda: controller.get_check_draft(profile.id, session.attempt_id),
        save_draft=save_draft,
    )
    if selections is None:
        return
    try:
        controller.submit_assessment(profile.id, session.attempt_id, selections)
    except PccError as exc:
        st.error(str(exc))
        return
    st.session_state[_FLASH_KEY] = True
    st.rerun()
