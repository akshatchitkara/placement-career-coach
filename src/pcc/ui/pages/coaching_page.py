"""Coaching plan (FR-09): 3-5 tasks for the weakest skill, each with a tutor you can talk to."""

import streamlit as st

from pcc.core.exceptions import PccError
from pcc.domain.schemas.coaching_schemas import CoachingTask
from pcc.domain.schemas.tutor_schemas import MAX_STUDENT_TEXT, TutorKind
from pcc.ui.components.page_frame import page_header, require_profile
from pcc.ui.components.pill import pill
from pcc.ui.navigation import go_button
from pcc.ui.text import safe_md
from pcc.workflow.workflow_controller import WorkflowController, get_controller

_SOURCE_LABELS = {
    "template": "Curated plan built from your missed questions",
    "ai": "AI-drafted plan, checked against your results",
}
_QUICK_ACTIONS: list[tuple[TutorKind, str]] = [
    ("explain_differently", "Explain it differently"),
    ("example", "Show me an example"),
]


def _ask(
    controller: WorkflowController, profile_id: int, order: int, kind: TutorKind, text: str
) -> None:
    st.session_state[f"coach_open_{order}"] = True
    try:
        with st.spinner("Your coach is thinking..."):
            reply = controller.ask_tutor(profile_id, order, kind, text)
    except PccError as exc:
        st.session_state[f"coach_error_{order}"] = str(exc)
    else:
        if reply.used_fallback:
            st.session_state[f"coach_note_{order}"] = reply.message
    st.rerun()


def _quiz(controller: WorkflowController, profile_id: int, order: int) -> None:
    result_key = f"quiz_result_{order}"
    results = st.session_state.get(result_key)
    if results is not None:
        right = sum(r.is_correct for r in results)
        st.markdown(f"**Quiz result: {right} of {len(results)} right.**")
        for r in results:
            pill("Correct", "good") if r.is_correct else pill("Not yet", "bad")
            st.markdown(safe_md(r.stem))
            if not r.is_correct:
                st.write(
                    f"You chose: {safe_md(r.selected_option_text)}. "
                    f"Right answer: {safe_md(r.correct_option_text)}"
                )
            st.caption(safe_md(r.explanation))
        st.caption("Practice only: this does not change your score or level.")
        if st.button("Close quiz", key=f"quiz_close_{order}"):
            st.session_state.pop(f"quiz_open_{order}", None)
            st.session_state.pop(result_key, None)
            st.rerun()
        return
    questions = controller.get_practice_quiz(profile_id, order)
    if not questions:
        st.info("There are no earlier questions to practise on for this task yet.")
        return
    with st.form(f"quiz_form_{order}"):
        picks = {}
        for q in questions:
            labels = {o.option_id: safe_md(o.text) for o in q.options}
            picks[q.question_id] = st.radio(
                safe_md(q.stem),
                list(labels),
                format_func=labels.__getitem__,
                index=None,
                key=f"quiz_{order}_{q.question_id}",
            )
        submitted = st.form_submit_button("Check my answers", type="primary")
    if not submitted:
        return
    answered = {qid: pick for qid, pick in picks.items() if pick is not None}
    if len(answered) < len(picks):
        st.error("Answer every quiz question first.")
        return
    st.session_state[result_key] = controller.grade_practice_quiz(profile_id, order, answered)
    st.rerun()


def _coach_panel(controller: WorkflowController, profile_id: int, task: CoachingTask) -> None:
    order = task.order
    thread = controller.get_tutor_thread(profile_id, order)
    opened = bool(thread) or st.session_state.get(f"coach_open_{order}", False)
    with st.expander("Ask your coach about this task", expanded=opened):
        for message in thread:
            with st.chat_message("user" if message.role == "student" else "assistant"):
                st.write(safe_md(message.content))
        error = st.session_state.pop(f"coach_error_{order}", "")
        if error:
            st.warning(error)
        note = st.session_state.pop(f"coach_note_{order}", "")
        if note:
            st.caption(note)

        cols = st.columns(3)
        for col, (kind, label) in zip(cols, _QUICK_ACTIONS, strict=False):
            if col.button(label, key=f"coach_{kind}_{order}"):
                _ask(controller, profile_id, order, kind, "")
        if cols[2].button("Quiz me", key=f"coach_quiz_{order}"):
            st.session_state[f"quiz_open_{order}"] = True
            st.session_state[f"coach_open_{order}"] = True
            st.session_state.pop(f"quiz_result_{order}", None)
            st.rerun()

        with st.form(f"coach_form_{order}", clear_on_submit=True):
            text = st.text_input(
                "Or ask your own question",
                max_chars=MAX_STUDENT_TEXT,
                placeholder="For example: why is the group digit 4 and not 6?",
                key=f"coach_text_{order}",
            )
            asked = st.form_submit_button("Ask")
        if asked:
            _ask(controller, profile_id, order, "question", text)

        if st.session_state.get(f"quiz_open_{order}"):
            st.divider()
            _quiz(controller, profile_id, order)


def _done_toggle(controller: WorkflowController, profile_id: int, order: int) -> None:
    """Coaching tasks 1-2 are also in this week's plan; one checkbox keeps both in step."""
    view = controller.get_weekly_plan(profile_id)
    task_id = f"coaching_{order}"
    if view is None or task_id not in {t.task_id for t in view.plan.tasks}:
        st.caption("Planned for a later week.")
        return
    done = task_id in view.done_task_ids
    ticked = st.checkbox("Done this week", value=done, key=f"coach_done_{order}")
    if ticked != done:
        controller.set_task_done(profile_id, view.plan_id, task_id, ticked)
        st.rerun()


def render() -> None:
    page_header("Coaching Plan")
    controller = get_controller()
    profile = require_profile()
    if profile is None:
        return
    view = controller.get_coaching_plan(profile.id)
    if view is None:
        if controller.get_latest_results(profile.id) is None:
            st.info(
                "Take the check on **Skills Check** first; your plan is built from your mistakes."
            )
            go_button("Take the skills check", "assessment", key="coach_to_check", primary=True)
        else:
            st.info(
                "No coaching plan: your results did not single out a weak skill "
                "(not enough evidence, or no major gap)."
            )
        return

    plan = view.plan
    st.header(f"Focus skill: {view.skill_name}")
    st.caption(_SOURCE_LABELS[plan.generation_source])
    if plan.generation_source == "template" and not controller.get_ai_status().offline:
        st.info(
            "This plan was built from curated material because the AI's draft was unavailable "
            "or did not pass checks. It is still based on your own mistakes."
        )
    st.write(safe_md(plan.diagnosis))
    total = sum(t.estimated_minutes for t in plan.tasks)
    st.caption(
        f"{len(plan.tasks)} tasks · about {total} minutes · "
        f"re-check in {plan.retest_after_days} days"
    )

    for task in plan.tasks:
        with st.container(border=True):
            st.markdown(f"**{task.order}. {safe_md(task.title)}** · {task.estimated_minutes} min")
            if task.misconception:
                st.markdown(f"*What went wrong:* {safe_md(task.misconception)}")
            st.markdown(f"**Do this:** {safe_md(task.action)}")
            st.markdown(f"**You're done when:** {safe_md(task.success_check)}")
            if task.resource_hint:
                st.caption(f"Look up: {safe_md(task.resource_hint)}")
            if task.linked_question_id in view.question_stems:
                st.caption(
                    f"Linked to the question: "
                    f"{safe_md(view.question_stems[task.linked_question_id])}"
                )
            elif task.concept_tag:
                st.caption(f"Concept: {task.concept_tag.replace('_', ' ')}")
            _done_toggle(controller, profile.id, task.order)
            _coach_panel(controller, profile.id, task)
    go_button("See this week's plan", "weekly", key="coach_to_weekly")
