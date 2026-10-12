"""AI Settings must not hand a saved secret back to the browser or echo it in an error;
student-typed names must be shown literally."""

import sqlite3
from contextlib import closing

from streamlit.testing.v1 import AppTest
from tests.ui.test_student_happy_path import _run, temp_db  # noqa: F401 -- autouse fixture

from pcc.ai.provider_config import AiProviderConfig
from pcc.core.config import settings
from pcc.persistence.database import get_connection, init_schema
from pcc.persistence.repositories.ai_provider_settings_repository import save_config

SECRET = "FAKE-TEST-KEY-1234567890"


def _save_provider() -> None:
    conn = get_connection(settings.db_path)
    init_schema(conn)
    save_config(
        conn,
        AiProviderConfig(provider_type="anthropic", base_url=None, api_key=SECRET, model_name="m"),
    )
    conn.commit()
    conn.close()


def _page() -> None:
    from pcc.ui.pages import ai_settings_page

    ai_settings_page.render()


def test_the_saved_key_is_not_sent_back_to_the_browser():
    _save_provider()
    at = AppTest.from_function(_page, default_timeout=30).run()
    assert not at.exception
    key_box = next(t for t in at.text_input if t.label == "API key")
    assert key_box.value == ""
    assert "A key is saved" in key_box.proto.placeholder
    everything = repr([getattr(el, "value", "") for el in at.main]) + repr(at.get("text_input"))
    assert SECRET not in everything


def test_blank_key_keeps_the_saved_one_and_a_typed_key_replaces_it(monkeypatch):
    _save_provider()
    seen: list[str | None] = []

    def fake_build(config):
        seen.append(config.api_key)

        class Client:
            def generate(self, prompt, **kwargs):
                return "ok"

        return Client()

    monkeypatch.setattr("pcc.ui.pages.ai_settings_page.build_ai_client", fake_build)
    at = AppTest.from_function(_page, default_timeout=30).run()
    next(b for b in at.button if b.label == "Test connection").click().run()
    assert seen[-1] == SECRET  # blank box: the saved key is used

    next(t for t in at.text_input if t.label == "API key").set_value("sk-typed-new").run()
    next(b for b in at.button if b.label == "Test connection").click().run()
    assert seen[-1] == "sk-typed-new"


def test_a_provider_error_that_echoes_the_key_is_redacted(monkeypatch):
    _save_provider()

    def fake_build(config):
        class Client:
            def generate(self, prompt, **kwargs):
                raise RuntimeError(f"401 Incorrect API key provided: {SECRET}")

        return Client()

    monkeypatch.setattr("pcc.ui.pages.ai_settings_page.build_ai_client", fake_build)
    at = AppTest.from_function(_page, default_timeout=30).run()
    next(b for b in at.button if b.label == "Test connection").click().run()
    shown = " ".join(e.value for e in at.error)
    assert "Connection failed" in shown and "***" in shown
    assert SECRET not in shown


def test_a_display_name_that_looks_like_a_link_is_shown_literally():
    at = _run("profile_page")
    at.text_input[0].set_value("[free prize](http://evil.example)")
    at.button[0].click().run()
    profile_id = at.session_state["profile_id"]
    assert "\\[free prize\\]" in at.success[0].value  # escaped, so it renders as text
    home = _run("home_page", profile_id)
    assert "\\[free prize\\]" in home.title[0].value
    with closing(sqlite3.connect(settings.db_path)) as conn:
        stored = conn.execute("SELECT display_name FROM profiles").fetchall()
    assert stored == [
        ("[free prize](http://evil.example)",)
    ]  # stored as typed, only display is escaped
