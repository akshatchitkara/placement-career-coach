"""Regression: pairs of dollar signs in content were read as maths and vanished from the page.

The first version of this test sampled a real check, so it only failed when the question with
dollar signs happened to be drawn. These tests build the question by hand instead.
"""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

BANK = Path(__file__).resolve().parents[2] / "data" / "content" / "question_bank"


def _wizard_with_dollars() -> None:
    from pcc.domain.enums import Difficulty
    from pcc.domain.schemas.assessment_schemas import PresentedQuestion
    from pcc.domain.schemas.question_schemas import Option
    from pcc.ui.components.check_wizard import render_check_wizard

    question = PresentedQuestion(
        question_id="q_dollars",
        skill_id="s",
        skill_name="Skill",
        difficulty=Difficulty.EASY,
        stem="Which stage totals with $group and $sum?",
        options=[
            Option(option_id="a", text="$group with a $sum of the amount"),
            Option(option_id="b", text="$match then $skip"),
            Option(option_id="c", text="No dollars here"),
            Option(option_id="d", text="Cost is $5"),
        ],
    )
    render_check_wizard(1, [question])


def test_the_check_wizard_escapes_dollar_signs_in_the_stem_and_every_option():
    at = AppTest.from_function(_wizard_with_dollars, default_timeout=30).run()
    assert not at.exception
    radio = at.radio[0]
    for text in [radio.label, *radio.options]:
        assert "$" not in text.replace("\\$", ""), text  # no bare dollar reaches Markdown
    assert radio.options[2] == "No dollars here"  # text without dollars is untouched


def test_the_question_that_contains_dollars_is_in_the_bank():
    """Keeps this regression meaningful: if the content changes, the test must be revisited."""
    questions = json.loads((BANK / "mean_stack_developer.json").read_text("utf-8"))
    dollar = [q for q in questions if any("$" in o["text"] for o in q["options"])]
    assert dollar and dollar[0]["skill_id"] == "mongodb_data_modeling"
