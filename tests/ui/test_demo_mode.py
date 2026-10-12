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
