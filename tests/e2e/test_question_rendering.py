"""Every question must be displayed exactly as written (Streamlit reads Markdown in labels)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "qa"))

from check_question_rendering import compare_rendering  # noqa: E402


def test_every_question_stem_and_option_is_displayed_exactly_as_written(page, question_app):
    total, rendered, mismatches = compare_rendering(page, question_app.url)
    assert rendered == total, f"{rendered} of {total} questions were drawn"
    assert not mismatches, mismatches[:3]
