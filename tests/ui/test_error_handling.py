"""No page may ever show a stack trace; the app must explain problems and stay usable."""

import shutil
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pcc.content import content_loader
from pcc.content.content_validator import check_installed_content
from pcc.core.config import settings
from pcc.ui.error_boundary import GENERIC_MESSAGE

MAIN = Path(__file__).resolve().parents[2] / "src" / "pcc" / "main.py"


def _boundary_app(kind: str) -> None:
    import streamlit as st

    from pcc.core.exceptions import PccError, WorkflowStateError
    from pcc.ui.error_boundary import safe_page

    def page() -> None:
        st.write("page body")
        if kind == "pcc":
            raise PccError("Choose a career first.")
        if kind == "workflow":
            raise WorkflowStateError("cannot move from profile_ready to results_ready")
        if kind == "bug":
            raise RuntimeError("secret internal detail")
        if kind == "rerun":
            if not st.session_state.get("done"):
                st.session_state["done"] = True
                st.rerun()
            st.write("after rerun")

    safe_page(page)()


def _run(kind: str) -> AppTest:
    return AppTest.from_function(_boundary_app, args=(kind,), default_timeout=30).run()


def test_expected_problems_show_their_own_message():
    at = _run("pcc")
    assert [e.value for e in at.error] == ["Choose a career first."]
    assert not at.exception


def test_workflow_errors_are_shown_not_raised():
    at = _run("workflow")
    assert any("cannot move" in e.value for e in at.error) and not at.exception


def test_unexpected_bugs_show_a_calm_message_and_hide_internals():
    at = _run("bug")
    assert [e.value for e in at.error] == [GENERIC_MESSAGE]
    assert not at.exception
    assert "secret internal detail" not in at.error[0].value


def test_streamlit_rerun_passes_through_the_boundary():
    at = _run("rerun")
    assert not at.error and not at.exception
    assert any(m.value == "after rerun" for m in at.markdown)


def test_the_boundary_keeps_the_page_identity():
    def my_page() -> None:
        pass

    from pcc.ui.error_boundary import safe_page

    assert safe_page(my_page).__name__ == "my_page"


# --- start-up health --------------------------------------------------------------------------
@pytest.fixture
def broken_content(tmp_path, monkeypatch):
    copy = tmp_path / "content"
    shutil.copytree(content_loader._CONTENT_DIR, copy)
    monkeypatch.setattr(content_loader, "_CONTENT_DIR", copy)
    return copy


def test_healthy_content_has_no_issues():
    assert check_installed_content() == []


def test_unreadable_content_is_reported_not_raised(broken_content):
    (broken_content / "skills.json").write_text("{ not json", encoding="utf-8")
    issues = check_installed_content()
    assert issues and "could not be loaded" in issues[0]


def test_structural_problems_are_listed(broken_content):
    skills = (broken_content / "skills.json").read_text(encoding="utf-8")
    (broken_content / "skills.json").write_text(
        skills.replace('"linux_fundamentals"', '"shell_scripting"', 1), encoding="utf-8"
    )
    assert any("duplicate skill_id" in i for i in check_installed_content())


def test_a_missing_roadmap_template_is_a_problem(broken_content):
    (broken_content / "roadmap_templates" / "ai_developer.json").unlink()
    assert any("ai_developer.json is missing" in i for i in check_installed_content())


def test_app_refuses_to_start_on_broken_content_and_explains(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pcc.db"))
    monkeypatch.setattr(
        "pcc.content.content_validator.check_installed_content",
        lambda: ["skills.json: duplicate skill_id 'x'"],
    )
    st.cache_resource.clear()
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    st.cache_resource.clear()
    assert any("content files have problems" in e.value for e in at.error)
    assert any("duplicate skill_id" in c.value for c in at.code)
    assert not at.exception
    assert not at.sidebar.caption  # nothing else rendered


def test_app_starts_normally_with_healthy_content(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pcc.db"))
    st.cache_resource.clear()
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    st.cache_resource.clear()
    assert not at.exception and not at.error
    assert any("Offline mode" in c.value for c in at.sidebar.caption)


def test_app_survives_an_unusable_database_path(monkeypatch, tmp_path):
    blocker = tmp_path / "a_file"
    blocker.write_text("x")
    monkeypatch.setattr(settings, "db_path", str(blocker / "pcc.db"))  # parent is a file
    st.cache_resource.clear()
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    st.cache_resource.clear()
    assert any("Could not open the database" in e.value for e in at.error)
    assert not at.exception


# --- reopening the app restores the last profile -------------------------------------------------
def test_a_new_session_reopens_the_most_recent_profile(monkeypatch, tmp_path):
    from pcc.workflow.workflow_controller import WorkflowController

    db = str(tmp_path / "pcc.db")
    monkeypatch.setattr(settings, "db_path", db)
    controller = WorkflowController(db)
    controller.open_profile("Asha")
    controller.open_profile("Ravi")  # the most recent
    st.cache_resource.clear()
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    st.cache_resource.clear()
    assert not at.exception
    assert at.session_state["profile_id"] == controller.open_profile("Ravi").id
    assert any("Signed in as **Ravi**" in c.value for c in at.sidebar.caption)


def test_a_fresh_database_has_no_signed_in_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pcc.db"))
    st.cache_resource.clear()
    at = AppTest.from_file(str(MAIN), default_timeout=30).run()
    st.cache_resource.clear()
    assert "profile_id" not in at.session_state
    assert not any("Signed in as" in c.value for c in at.sidebar.caption)


def test_a_profile_that_no_longer_exists_is_dropped(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pcc.db"))
    st.cache_resource.clear()
    at = AppTest.from_file(str(MAIN), default_timeout=30)
    at.session_state["profile_id"] = 999  # e.g. the database was reset under an open tab
    at.run()
    st.cache_resource.clear()
    assert not at.exception and "profile_id" not in at.session_state
