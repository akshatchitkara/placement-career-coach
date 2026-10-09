"""One multiple-choice question. Returns the selected option_id, or None if unanswered."""

import streamlit as st

from pcc.domain.schemas.assessment_schemas import PresentedQuestion


def render_question_card(number: int, question: PresentedQuestion, key_prefix: str) -> str | None:
    st.markdown(f"**Q{number}. {question.skill_name}** · _{question.difficulty.value}_")
    labels = {o.option_id: o.text for o in question.options}
    return st.radio(
        question.stem,
        list(labels),
        format_func=labels.__getitem__,
        index=None,
        key=f"{key_prefix}_{question.question_id}",
    )
