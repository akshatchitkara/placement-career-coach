"""PCC_DEMO_MODE=true is for hosted demos: an empty disk gets the demo profiles, and the
AI Settings page (which would store a key on a shared, throwaway disk) is not offered."""

from pathlib import Path

from streamlit.testing.v1 import AppTest
from tests.ui.test_student_happy_path import temp_db  # noqa: F401 -- autouse fixture

from pcc.core.config import settings
from pcc.workflow.workflow_controller import get_controller

MAIN = str(Path(__file__).resolve().parents[2] / "src" / "pcc" / "main.py")


def _names() -> list[str]:
    return sorted(p.display_name for p in get_controller().list_profiles())


def test_demo_mode_seeds_an_empty_database_once(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    at = AppTest.from_file(MAIN, default_timeout=60).run()
    assert not at.exception
    assert _names() == ["Asha", "Meera", "Ravi"]

    AppTest.from_file(MAIN, default_timeout=60).run()  # a second start must not add duplicates
    assert _names() == ["Asha", "Meera", "Ravi"]


def test_normal_mode_does_not_seed(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    at = AppTest.from_file(MAIN, default_timeout=60).run()
    assert not at.exception
    assert _names() == []


def test_seeded_demo_profiles_show_progress_on_the_road(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    AppTest.from_file(MAIN, default_timeout=60).run()
    controller = get_controller()
    by_name = {p.display_name: p.id for p in controller.list_profiles()}
    passed = {n: sum(v.passed for v in controller.get_module_progress(i).values())
              for n, i in by_name.items()}  # fmt: skip
    assert passed == {"Asha": 0, "Ravi": 1, "Meera": 3}
    assert (
        controller.get_game_state(by_name["Meera"]).xp
        > controller.get_game_state(by_name["Ravi"]).xp
    )


def test_a_new_visitor_is_not_signed_in_as_the_previous_visitor(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    AppTest.from_file(MAIN, default_timeout=60).run()  # seeds the demo profiles
    ravi = next(p for p in get_controller().list_profiles() if p.display_name == "Ravi")
    first = AppTest.from_file(MAIN, default_timeout=60)
    first.session_state["profile_id"] = ravi.id
    first.run()
    assert first.session_state["profile_id"] == ravi.id  # a visitor who picked Ravi stays Ravi

    second = AppTest.from_file(MAIN, default_timeout=60).run()  # a different visitor
    assert "profile_id" not in second.session_state  # not handed Ravi's progress

    monkeypatch.setattr(settings, "demo_mode", False)
    local = AppTest.from_file(MAIN, default_timeout=60).run()  # local use keeps the reload memory
    assert "profile_id" in local.session_state
