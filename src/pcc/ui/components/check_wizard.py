"""One question at a time, with progress, Back/Next and a review step before submitting.

Answers live in session state per attempt, so going Back or reloading within the session keeps
them. The component only collects answers; grading stays in the controller.
"""

import html
from collections.abc import Callable

import streamlit as st

from pcc.domain.enums import Difficulty
from pcc.domain.schemas.assessment_schemas import PresentedQuestion
from pcc.ui.components.pill import pill_html
from pcc.ui.text import safe_md

_BADGE = {
    Difficulty.EASY: ("Easy", "good"),
    Difficulty.MEDIUM: ("Medium", "warn"),
    Difficulty.HARD: ("Hard", "bad"),
}


def _state(attempt_id: int) -> tuple[str, str]:
    return f"chk{attempt_id}_idx", f"chk{attempt_id}_ans"


def _go(idx_key: str, index: int) -> None:
    st.session_state[idx_key] = index


def _remember(ans_key: str, widget_key: str, question_id: str) -> None:
    """Runs before the page is redrawn, so a quick click on Next cannot drop the answer.

    Without this the answer was stored only when the question was drawn. If the student chose
    an option and pressed Next before the server had finished its first update, both changes
    arrived together, the page moved on, and the earlier question was never drawn again.
    """
    value = st.session_state.get(widget_key)
    if value is not None:
        st.session_state[ans_key][question_id] = value


def _question(attempt_id: int, index: int, total: int, question: PresentedQuestion) -> None:
    idx_key, ans_key = _state(attempt_id)
    answers: dict[str, str] = st.session_state[ans_key]
    label, tone = _BADGE.get(question.difficulty, ("", "info"))
    st.markdown(
        f"<strong>Question {index + 1} of {total}</strong> · {html.escape(question.skill_name)} "
        f"{pill_html(label, tone) if label else ''}",
        unsafe_allow_html=True,
    )
    labels = {o.option_id: safe_md(o.text) for o in question.options}
    options = list(labels)
    saved = answers.get(question.question_id)
    widget_key = f"chk{attempt_id}_{question.question_id}"
    with st.container(border=True):
        picked = st.radio(
            safe_md(question.stem),
            options,
            format_func=labels.__getitem__,
            index=options.index(saved) if saved in options else None,
            key=widget_key,
            on_change=_remember,
            args=(ans_key, widget_key, question.question_id),
        )
    if picked is not None:
        answers[question.question_id] = picked


def render_check_wizard(
    attempt_id: int,
    questions: list[PresentedQuestion],
    load_draft: Callable[[], dict[str, str]] | None = None,
    save_draft: Callable[[dict[str, str]], None] | None = None,
) -> dict[str, str] | None:
    """Returns the full answer map once the student submits with every question answered."""
    idx_key, ans_key = _state(attempt_id)
    saved_key = f"chk{attempt_id}_saved"
    if ans_key not in st.session_state:  # first run in this browser session: restore any draft
        valid = {q.question_id for q in questions}
        draft = {k: v for k, v in (load_draft() if load_draft else {}).items() if k in valid}
        st.session_state[ans_key] = dict(draft)
        st.session_state[saved_key] = dict(draft)
        unanswered = [i for i, q in enumerate(questions) if q.question_id not in draft]
        st.session_state[idx_key] = unanswered[0] if unanswered else len(questions) - 1
    st.session_state.setdefault(idx_key, 0)
    total = len(questions)
    index = min(max(st.session_state[idx_key], 0), total - 1)
    answers: dict[str, str] = st.session_state[ans_key]

    _question(attempt_id, index, total, questions[index])
    if save_draft is not None and answers != st.session_state.get(saved_key):
        save_draft(dict(answers))
        st.session_state[saved_key] = dict(answers)
    answered = sum(q.question_id in answers for q in questions)
    st.progress(answered / total, text=f"{answered} of {total} answered")

    back_col, forward_col, note_col = st.columns([1, 1, 4])
    if index > 0:
        back_col.button(
            "Back", key=f"chk{attempt_id}_back", on_click=_go, args=(idx_key, index - 1)
        )
    # Keep the forward button in the first free slot so it does not jump on question 1.
    forward = forward_col if index > 0 else back_col
    last = index == total - 1
    if not last:
        forward.button(
            "Next",
            key=f"chk{attempt_id}_next",
            type="primary",
            on_click=_go,
            args=(idx_key, index + 1),
        )
        return None

    submitted = forward.button("Submit answers", key=f"chk{attempt_id}_submit", type="primary")
    missing = [i for i, q in enumerate(questions) if q.question_id not in answers]
    if missing:
        numbers = ", ".join(str(i + 1) for i in missing)
        note_col.caption(f"Still unanswered: question {numbers}.")
        if submitted:
            st.error(f"Answer every question before submitting ({len(missing)} left).")
            st.button(
                f"Go to question {missing[0] + 1}",
                key=f"chk{attempt_id}_first_missing",
                on_click=_go,
                args=(idx_key, missing[0]),
            )
        return None
    return dict(answers) if submitted else None
