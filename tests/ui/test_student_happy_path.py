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
