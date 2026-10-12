"""One question at a time, with progress, Back/Next and a review step before submitting.

Answers live in session state per attempt, so going Back or reloading within the session keeps
them. The component only collects answers; grading stays in the controller.
"""

import streamlit as st

from pcc.domain.enums import Difficulty
from pcc.domain.schemas.assessment_schemas import PresentedQuestion

_BADGE = {
    Difficulty.EASY: ":green-badge[Easy]",
    Difficulty.MEDIUM: ":orange-badge[Medium]",
    Difficulty.HARD: ":red-badge[Hard]",
}


def _state(attempt_id: int) -> tuple[str, str]:
    return f"chk{attempt_id}_idx", f"chk{attempt_id}_ans"


def _go(idx_key: str, index: int) -> None:
    st.session_state[idx_key] = index


def _question(attempt_id: int, index: int, total: int, question: PresentedQuestion) -> None:
    idx_key, ans_key = _state(attempt_id)
    answers: dict[str, str] = st.session_state[ans_key]
    st.markdown(
        f"**Question {index + 1} of {total}** · {question.skill_name} "
        f"{_BADGE.get(question.difficulty, '')}"
    )
    labels = {o.option_id: o.text for o in question.options}
    options = list(labels)
    saved = answers.get(question.question_id)
    with st.container(border=True):
        picked = st.radio(
            question.stem,
            options,
            format_func=labels.__getitem__,
            index=options.index(saved) if saved in options else None,
            key=f"chk{attempt_id}_{question.question_id}",
        )
    if picked is not None:
        answers[question.question_id] = picked


def render_check_wizard(
    attempt_id: int, questions: list[PresentedQuestion]
) -> dict[str, str] | None:
    """Returns the full answer map once the student submits with every question answered."""
    idx_key, ans_key = _state(attempt_id)
    st.session_state.setdefault(idx_key, 0)
    st.session_state.setdefault(ans_key, {})
    total = len(questions)
    index = min(max(st.session_state[idx_key], 0), total - 1)
    answers: dict[str, str] = st.session_state[ans_key]

    _question(attempt_id, index, total, questions[index])
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
