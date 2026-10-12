"""Real-browser tests: start the app on a free port with a throwaway database and drive it.

Run with:  PCC_E2E=1 python -m pytest tests/e2e
Needs Playwright (pip install playwright) and Microsoft Edge or Google Chrome. They are skipped
otherwise, so the normal test run stays fast and needs no browser.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = {"width": 1440, "height": 900}


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, f"rep_{call.when}", outcome.get_result())  # lets fixtures see if the test failed


def pytest_collection_modifyitems(config, items):
    if os.environ.get("PCC_E2E") == "1":
        return
    skip = pytest.mark.skip(
        reason="real-browser tests: set PCC_E2E=1 (needs Playwright and a browser)"
    )
    for item in items:
        if "e2e" in Path(str(item.fspath)).parts:
            item.add_marker(skip)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class App:
    url: str
    db_path: str
    process: subprocess.Popen = field(repr=False)


def _start(script: str, db_path: str, env_extra: dict[str, str] | None = None) -> App:
    port = _free_port()
    logs = ROOT / "test-reports" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = open(logs / f"server-{Path(script).stem}-{port}.log", "w", encoding="utf-8")  # noqa: SIM115
    env = {
        **os.environ,
        "PCC_DB_PATH": db_path,
        "PCC_AI_MODE": "offline",
        "PCC_SHOW_DEV_PAGES": "false",
        "PYTHONIOENCODING": "utf-8",
        **(env_extra or {}),
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            script,
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            if urllib.request.urlopen(f"{url}/_stcore/health", timeout=1).status == 200:
                return App(url, db_path, process)
        except OSError:
            time.sleep(0.5)
    process.kill()
    raise RuntimeError("the app did not start")


@pytest.fixture(scope="module")
def app(tmp_path_factory) -> Iterator[App]:
    server = _start("src/pcc/main.py", str(tmp_path_factory.mktemp("e2e") / "pcc.db"))
    yield server
    server.process.terminate()


@pytest.fixture(scope="module")
def question_app(tmp_path_factory) -> Iterator[App]:
    """A page that shows every question with the same widgets the skills check uses."""
    server = _start(
        "qa/render_all_questions_app.py", str(tmp_path_factory.mktemp("q") / "unused.db")
    )
    yield server
    server.process.terminate()


@pytest.fixture(scope="session")
def browser() -> Iterator[object]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        launched = None
        for channel in ("msedge", "chrome", None):
            try:
                launched = (
                    p.chromium.launch(channel=channel, headless=True)
                    if channel
                    else p.chromium.launch(headless=True)
                )
                break
            except Exception:  # noqa: BLE001 -- try the next browser
                continue
        if launched is None:
            pytest.skip("no Edge, Chrome or Chromium available")
        yield launched
        launched.close()


# Streamlit's own front end asks for /<page>/_stcore/health and /host-config when a page is opened
# by its URL, and gets a 404. Reproduced in a minimal Streamlit app with none of this project's
# code, so it is not counted. Everything else logged as a console error is.
_FRAMEWORK_404 = ("/_stcore/health", "/_stcore/host-config")


def _record_console(page, message) -> None:
    if message.type != "error":
        return
    url = (message.location or {}).get("url", "")
    if "status of 404" in message.text and url.endswith(_FRAMEWORK_404):
        return
    page.pcc_errors.append(f"console: {message.text} ({url})")


@pytest.fixture
def page(browser, app, request) -> Iterator[object]:
    context = browser.new_context(viewport=DESKTOP, accept_downloads=True)
    page = context.new_page()
    page.pcc_errors = []  # uncaught page errors and console errors, checked by tests
    page.on("pageerror", lambda e: page.pcc_errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: _record_console(page, m))
    page.pcc_base = app.url
    yield page
    report = getattr(request.node, "rep_call", None)
    if report is not None and report.failed:  # keep evidence of what the browser showed
        folder = ROOT / "test-reports" / "screenshots" / "failures"
        folder.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in request.node.name)
        for index, open_page in enumerate(context.pages):
            try:
                open_page.screenshot(path=str(folder / f"{safe}_{index}.png"), full_page=True)
            except Exception:  # noqa: BLE001 -- a screenshot must never mask the real failure
                pass
    context.close()
