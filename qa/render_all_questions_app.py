"""QA harness: shows every question's stem and options exactly as the skills check widgets do.

Run with `streamlit run qa/render_all_questions_app.py`; qa/check_question_rendering.py reads
the page in a real browser and compares what is displayed with the source text.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pcc.content.content_loader import load_careers, load_question_bank  # noqa: E402
from pcc.ui.text import safe_md  # noqa: E402

st.set_page_config(layout="wide")
seen: set[str] = set()
for career in load_careers():
    for q in load_question_bank(career.career_id):
        if q.question_id in seen:
            continue
        seen.add(q.question_id)
        labels = {o.option_id: safe_md(o.text) for o in q.options}
        st.radio(
            safe_md(q.stem),
            list(labels),
            format_func=labels.__getitem__,
            index=None,
            key=f"qa_{q.question_id}",
        )
