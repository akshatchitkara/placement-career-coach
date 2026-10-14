"""The roadmap as a road: one stop per month, grouped by semester, with a quiz at each stop.

Stops are drawn as HTML (a road you can read at a glance); the details and the quiz sit in
Streamlit expanders under each semester's road so every control stays a real, accessible widget.
A module counts as complete when its quiz is passed (or it is marked done, for the few modules
that have no quiz questions).
"""

import html

import streamlit as st

from pcc.core.exceptions import PccError
from pcc.domain.gamification import MODULE_QUIZ_PASS, MODULE_QUIZ_QUESTIONS
from pcc.domain.schemas.roadmap_schemas import Roadmap, RoadmapMonth
from pcc.domain.schemas.tutor_schemas import ModuleQuizResult
from pcc.persistence.repositories.module_progress_repository import ModuleProgress
from pcc.ui.components.pill import pill
from pcc.ui.text import escape_md, safe_md
from pcc.workflow.workflow_controller import WorkflowController

_STATE_TEXT = {"done": "Completed", "current": "You are here", "next": "Up next"}


def _states(months: list[RoadmapMonth], progress: dict[str, ModuleProgress]) -> dict[str, str]:
    """done / current / next for every module; the first unfinished one is the current stop."""
    states: dict[str, str] = {}
    current_found = False
    for month in months:
        if progress.get(month.skill_id) and progress[month.skill_id].passed:
            states[month.skill_id] = "done"
        elif not current_found:
            states[month.skill_id] = "current"
            current_found = True
        else:
            states[month.skill_id] = "next"
    return states


def _road(months: list[RoadmapMonth], names: dict[str, str], states: dict[str, str]) -> None:
    stops = []
    for month in months:
        state = states[month.skill_id]
        mark = {"done": "&#10003;", "current": "&#9733;", "next": str(month.month_index)}[state]
        stops.append(
            f'<li class="pcc-node {state}"><span class="pcc-dot" aria-hidden="true">{mark}</span>'
            f'<span class="pcc-node-text"><small>Month {month.month_index} · '
            f"{_STATE_TEXT[state]}</small>"
            f"<b>{html.escape(names.get(month.skill_id, month.skill_id))}</b></span></li>"
        )
    st.markdown(f'<ol class="pcc-road">{"".join(stops)}</ol>', unsafe_allow_html=True)


def _quiz_result(
    controller: WorkflowController, profile_id: int, skill_id: str, result: ModuleQuizResult
) -> None:
    shown_key = f"mq_shown_{skill_id}"
    if result.passed:
        st.success(
            f"Module complete! You got {result.correct} of {result.total} right"
            + (f" and earned {result.xp_gained} XP." if result.xp_gained else ".")
        )
        if not st.session_state.get(shown_key):  # celebrate once, not on every rerun
            st.session_state[shown_key] = True
            st.balloons()
        if result.rank_after != result.rank_before:
            st.info(f"Rank up! You are now **{escape_md(result.rank_after)}**.")
    else:
        st.warning(
            f"You got {result.correct} of {result.total} right. You need {MODULE_QUIZ_PASS} to "
            "complete the module. Read the answers below and try again."
        )
    for r in result.results:
        pill("Correct", "good") if r.is_correct else pill("Not yet", "bad")
        st.markdown(safe_md(r.stem))
        if not r.is_correct:
            st.write(
                f"You chose: {safe_md(r.selected_option_text)}. "
                f"Right answer: {safe_md(r.correct_option_text)}"
            )
        st.caption(safe_md(r.explanation))
    label = "Continue" if result.passed else "Try again with new questions"
    if st.button(label, key=f"mq_next_{skill_id}", type="primary"):
        for key in (f"mq_result_{skill_id}", shown_key):
            st.session_state.pop(key, None)
        if result.passed:
            st.session_state.pop(f"mq_open_{skill_id}", None)
        st.rerun()


def _quiz(controller: WorkflowController, profile_id: int, skill_id: str) -> None:
    result = st.session_state.get(f"mq_result_{skill_id}")
    if result is not None:
        _quiz_result(controller, profile_id, skill_id, result)
        return
    questions = controller.get_module_quiz(profile_id, skill_id)
    st.caption(
        f"{MODULE_QUIZ_QUESTIONS} quick questions. Get {MODULE_QUIZ_PASS} right to complete the "
        "module. This is practice: it does not change your skills-check score or level."
    )
    with st.form(f"mq_form_{skill_id}"):
        picks = {}
        for q in questions:
            labels = {o.option_id: safe_md(o.text) for o in q.options}
            picks[q.question_id] = st.radio(
                safe_md(q.stem),
                list(labels),
                format_func=labels.__getitem__,
                index=None,
                key=f"mq_{skill_id}_{q.question_id}",
            )
        submitted = st.form_submit_button("Check my answers", type="primary")
    if not submitted:
        return
    answered = {qid: pick for qid, pick in picks.items() if pick is not None}
    if len(answered) < len(picks):
        st.error("Answer every question first.")
        return
    try:
        st.session_state[f"mq_result_{skill_id}"] = controller.grade_module_quiz(
            profile_id, skill_id, answered
        )
    except PccError as exc:
        st.error(escape_md(str(exc)))
        return
    st.rerun()


def _module(
    controller: WorkflowController,
    profile_id: int,
    month: RoadmapMonth,
    name: str,
    state: str,
    progress: ModuleProgress | None,
) -> None:
    skill_id = month.skill_id
    title = f"Month {month.month_index} · {name} · {_STATE_TEXT[state]}"
    with st.expander(
        title, expanded=state == "current" or f"mq_open_{skill_id}" in st.session_state
    ):
        st.markdown(f"**Focus:** {safe_md(month.focus)}")
        st.markdown("**Topics**\n" + "\n".join(f"- {safe_md(t)}" for t in month.topics))
        st.markdown(f"**Deliverable:** {safe_md(month.deliverable)}")
        if state == "done" and f"mq_open_{skill_id}" not in st.session_state:
            pill("Module complete", "good")
            return
        if f"mq_open_{skill_id}" in st.session_state:
            _quiz(controller, profile_id, skill_id)
            return
        has_quiz = bool(controller.get_module_quiz(profile_id, skill_id))
        if has_quiz:
            if st.button(
                "I finished this module: take the quiz", key=f"mq_start_{skill_id}", type="primary"
            ):
                st.session_state[f"mq_open_{skill_id}"] = True
                st.rerun()
        elif st.button("Mark this module as done", key=f"mq_done_{skill_id}", type="primary"):
            controller.complete_module_without_quiz(profile_id, skill_id)
            st.rerun()


def render_roadmap_road(
    controller: WorkflowController,
    profile_id: int,
    roadmap: Roadmap,
    skill_names: dict[str, str],
    current_semester: int | None,
) -> None:
    progress = controller.get_module_progress(profile_id)
    ordered = sorted(roadmap.months, key=lambda m: (m.semester, m.month_index))
    states = _states(ordered, progress)
    for semester in (3, 4, 5, 6):
        months = [m for m in ordered if m.semester == semester]
        done = sum(1 for m in months if states[m.skill_id] == "done")
        flag = "  ← your semester" if semester == current_semester else ""
        st.header(f"Semester {semester}{flag}")
        st.caption(f"{done} of {len(months)} modules complete")
        _road(months, skill_names, states)
        for month in months:
            _module(
                controller,
                profile_id,
                month,
                skill_names.get(month.skill_id, month.skill_id),
                states[month.skill_id],
                progress.get(month.skill_id),
            )
