"""The roadmap road in a real browser: states, the module quiz, XP, and a phone-sized screen."""

import pytest
from tests.e2e.helpers import bank, build_roadmap, db_rows, idle, nav, norm, settle, sign_in

pytestmark = pytest.mark.e2e


def _answer_module_quiz(page, career_id: str, right: bool) -> None:
    questions = bank(career_id)
    groups = page.locator("[data-testid=stRadio]")
    for i in range(groups.count()):
        group = groups.nth(i)
        stem = norm(group.locator("[data-testid=stWidgetLabel]").first.inner_text())
        q = questions[stem]
        options = {o["option_id"]: o["text"] for o in q["options"]}
        correct = options[q["correct_option_id"]]
        wrong = next(t for oid, t in options.items() if oid != q["correct_option_id"])
        group.get_by_text(norm(correct if right else wrong), exact=True).first.click()
        idle(page)


def test_module_quiz_completes_a_module_and_moves_the_road_on(page, app):
    sign_in(page, "Road tester")
    build_roadmap(page, "devops_engineer")
    nav(page, "Roadmap")
    assert "Rookie" in page.inner_text("body") and "0 XP" in page.inner_text("body")
    assert page.locator(".pcc-node.current").count() == 1
    assert page.locator(".pcc-node.done").count() == 0

    page.get_by_role("button", name="I finished this module: take the quiz").first.click()
    settle(page, 1000)
    _answer_module_quiz(page, "devops_engineer", right=False)
    page.get_by_role("button", name="Check my answers").click()
    page.wait_for_selector("text=You need 2", timeout=20000)
    assert db_rows(app.db_path, "SELECT passed_at FROM module_progress")[0][0] is None

    page.get_by_role("button", name="Try again with new questions").click()
    settle(page, 1000)
    _answer_module_quiz(page, "devops_engineer", right=True)
    page.get_by_role("button", name="Check my answers").click()
    page.wait_for_selector("text=Module complete!", timeout=20000)
    page.get_by_role("button", name="Continue").click()
    settle(page, 1200)

    assert page.locator(".pcc-node.done").count() == 1
    assert "50 XP" in page.inner_text("body")
    assert db_rows(app.db_path, "SELECT attempts FROM module_progress")[0][0] == 2
    assert not page.pcc_errors, page.pcc_errors


def test_road_and_career_page_fit_a_phone(page):
    sign_in(page, "Phone tester")
    build_roadmap(page, "devops_engineer")
    page.set_viewport_size({"width": 390, "height": 844})
    for path in ("career", "roadmap"):
        page.goto(f"{page.pcc_base}/{path}")
        settle(page, 2000)
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
        ), f"{path} scrolls sideways on a phone"
    # the road stacks into one column with every stop on its own row
    tops = page.evaluate(
        "[...document.querySelector('.pcc-road').querySelectorAll('.pcc-node')]"
        ".map(e => e.getBoundingClientRect().top)"
    )
    assert len(tops) == 4 and tops == sorted(set(tops))
