"""Drives the real M2 pages headlessly against a temp database."""

import pytest
from streamlit.testing.v1 import AppTest

from pcc.core.config import settings


def _page(module: str) -> None:
    import importlib

    importlib.import_module(f"pcc.ui.pages.{module}").render()


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pcc.db"))


def _run(module: str, profile_id: int | None = None) -> AppTest:
    at = AppTest.from_function(_page, args=(module,), default_timeout=30)
    if profile_id is not None:
        at.session_state["profile_id"] = profile_id
    return at.run()


def test_profile_to_roadmap_journey():
    at = _run("profile_page")
    at.text_input[0].set_value("Asha")
    at.button[0].click().run()
    assert not at.exception
    profile_id = at.session_state["profile_id"]

    at = _run("career_selection_page", profile_id)
    assert not at.exception
    at.radio[0].set_value("devops_engineer")
    at.button[0].click().run()
    assert not at.exception
    assert any("Roadmap ready" in s.value for s in at.success)

    at = _run("roadmap_page", profile_id)
    assert not at.exception
    assert len(at.expander) == 16
    assert [s.value.split("  ")[0] for s in at.subheader] == [f"Semester {n}" for n in (3, 4, 5, 6)]


def test_non_cs_career_shows_unsupported_message():
    at = _run("profile_page")
    at.text_input[0].set_value("Ravi")
    at.button[0].click().run()
    profile_id = at.session_state["profile_id"]

    at = _run("career_selection_page", profile_id)
    at.radio[0].set_value("__other__").run()
    at.text_input[0].set_value("Doctor")
    at.button[0].click().run()
    assert any("not supported yet" in e.value for e in at.error)

    at = _run("roadmap_page", profile_id)
    assert any("No roadmap yet" in i.value for i in at.info)


def test_pages_ask_for_a_profile_first():
    for module in ("career_selection_page", "roadmap_page"):
        at = _run(module)
        assert any("Profile" in i.value for i in at.info)


def _signed_in_with_roadmap(name: str, career_id: str, semester: int = 3) -> int:
    at = _run("profile_page")
    at.text_input[0].set_value(name)
    at.button[0].click().run()
    profile_id = at.session_state["profile_id"]
    at = _run("career_selection_page", profile_id)
    at.radio[0].set_value(career_id)
    at.select_slider[0].set_value(semester)
    at.button[0].click().run()
    return profile_id


def test_check_to_results_journey():
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    profile_id = _signed_in_with_roadmap("Asha", "devops_engineer")

    at = _run("assessment_page", profile_id)
    assert not at.exception
    at.button[0].click().run()  # Start skills check
    assert len(at.radio) == 12

    # Submitting with nothing answered is refused (FR-05).
    at.button[-1].click().run()  # the form's submit button
    assert any("Answer every question" in e.value for e in at.error)

    for radio in at.radio:
        question = bank[radio.key.split("_", 1)[1]]
        radio.set_value(question.correct_option_id)
    at.button[-1].click().run()
    assert not at.exception

    results = _run("results_page", profile_id)
    assert not results.exception
    labels = [m.label for m in results.metric]
    assert "Level for Semester 3 skills" in labels
    assert [m.value for m in results.metric] == ["100.0%", "Advanced"]
    assert any("No major gap" in s.value for s in results.success)
    assert len(results.dataframe[0].value) == 4


def test_tier_b_career_shows_coming_soon_on_the_check():
    profile_id = _signed_in_with_roadmap("Ravi", "java_backend_developer")
    at = _run("assessment_page", profile_id)
    assert not at.exception
    assert any("coming soon" in w.value for w in at.warning)
    assert not at.button


def test_results_page_before_any_check():
    profile_id = _signed_in_with_roadmap("Meera", "devops_engineer")
    at = _run("results_page", profile_id)
    assert any("No results yet" in i.value for i in at.info)
