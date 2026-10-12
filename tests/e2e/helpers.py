"""Small helpers shared by the browser tests."""

import json
import re
import sqlite3
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[2] / "data" / "content"
CAREER_NAMES = {
    "devops_engineer": "DevOps Engineer",
    "mean_stack_developer": "MEAN Stack Developer",
    "java_backend_developer": "Java Backend Developer",
    "ai_developer": "AI Developer",
}


def norm(text: str) -> str:
    return " ".join(text.replace("`", "").replace("\\$", "$").split())


def bank(career_id: str) -> dict[str, dict]:
    questions = json.loads((CONTENT / "question_bank" / f"{career_id}.json").read_text("utf-8"))
    return {norm(q["stem"]): q for q in questions}


IDLE = '[data-testid="stApp"][data-test-script-state="notRunning"]'


def idle(page, timeout: int = 30000) -> None:
    """Waits until the app has finished its current update.

    Streamlit ignores a click that arrives while an update is still running, so a script that
    clicks the moment new content appears can lose that click.
    """
    try:
        page.wait_for_selector(IDLE, timeout=timeout)
    except Exception:  # noqa: BLE001 -- a page that never reports a state still gets the pause
        pass


def settle(page, ms: int = 1200) -> None:
    idle(page)
    page.wait_for_timeout(ms)
    idle(page)


def open_app(page, path: str = "") -> None:
    page.goto(f"{page.pcc_base}/{path}".rstrip("/"))
    page.wait_for_selector("[data-testid=stSidebar]", timeout=30000)
    settle(page, 1500)


def nav(page, title: str) -> None:
    page.get_by_role("link", name=title).first.click()
    settle(page, 1500)


def sign_in(page, name: str) -> None:
    if not page.url.startswith("http"):
        open_app(page)
    nav(page, "Profile")
    page.get_by_label("Display name").fill(name)
    page.get_by_role("button", name="Start / continue").click()
    settle(page)


def build_roadmap(page, career_id: str, semester: int = 3) -> None:
    nav(page, "Career & Semester")
    page.get_by_text(CAREER_NAMES[career_id], exact=True).first.click()
    settle(page, 800)
    slider = page.get_by_role("slider")
    if semester != 3:
        slider.focus()
        for _ in range(semester - 3):
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(250)
    page.get_by_role("button", name="Build my roadmap").click()
    page.wait_for_selector("text=Roadmap ready", timeout=60000)
    settle(page, 800)


def start_check(page) -> None:
    nav(page, "Skills Check")
    label = (
        "Start re-check"
        if page.get_by_role("button", name="Start re-check").count()
        else "Start skills check"
    )
    page.get_by_role("button", name=label).click()
    page.wait_for_selector("text=/Question 1 of \\d+/", timeout=30000)
    settle(page, 500)


def _position(page) -> tuple[int, int]:
    """(current question, total) read from the 'Question i of n' header."""
    header = page.get_by_text(re.compile(r"Question \d+ of \d+")).first.inner_text()
    i, n = (int(x) for x in re.findall(r"\d+", header)[:2])
    return i, n


def _answered(page) -> int:
    """The number in the 'k of n answered' counter."""
    text = page.get_by_text(re.compile(r"\d+ of \d+ answered")).first.inner_text()
    return int(re.findall(r"\d+", text)[0])


def answer_check(
    page, career_id: str, correct_per_skill: dict[str, int] | None = None, submit: bool = True
) -> int:
    """Answers every question on screen; a skill in correct_per_skill gets that many right.

    Each step waits for the app to show the next question instead of sleeping, so a slow
    server cannot make the script click on a question that is being replaced.
    """
    questions = bank(career_id)
    seen: dict[str, int] = {}
    total = 0
    while True:
        idle(page)
        index, count = _position(page)
        group = page.locator("[data-testid=stRadio]").first
        stem = norm(group.locator("[data-testid=stWidgetLabel]").first.inner_text())
        q = questions[stem]
        n = seen.get(q["skill_id"], 0)
        seen[q["skill_id"]] = n + 1
        right_count = 3 if correct_per_skill is None else correct_per_skill.get(q["skill_id"], 0)
        right = next(o["text"] for o in q["options"] if o["option_id"] == q["correct_option_id"])
        wrong = next(o["text"] for o in q["options"] if o["option_id"] != q["correct_option_id"])
        answered_before = _answered(page)
        group.get_by_text(norm(right if n < right_count else wrong), exact=True).first.click()
        # The counter is drawn at the end of the app's update, so once it moves the answer is
        # saved. Pressing Next earlier can be ignored: Streamlit drops a button click that
        # arrives while an earlier update is still running.
        page.wait_for_selector(f"text={answered_before + 1} of {count} answered", timeout=15000)
        total += 1
        if index == count:
            break
        page.get_by_role("button", name="Next").click()
        page.wait_for_selector(f"text=Question {index + 1} of {count}", timeout=20000)
    if submit:
        page.get_by_role("button", name="Submit answers").click()
        page.wait_for_selector("text=Submitted", timeout=60000)
        settle(page, 800)
    return total


def db_rows(db_path: str, sql: str, params: tuple = ()) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def body(page) -> str:
    return page.inner_text("body")
