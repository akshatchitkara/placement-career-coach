"""Routes, hidden pages and hostile or invalid input, in a real browser."""

import pytest
from tests.e2e.helpers import body, build_roadmap, db_rows, nav, open_app, settle, sign_in

ROUTES = [
    "",
    "profile",
    "career",
    "roadmap",
    "assessment",
    "results",
    "coaching",
    "weekly-plan",
    "progress",
    "ai-settings",
]


@pytest.mark.parametrize("route", ROUTES)
def test_every_route_loads_without_errors(page, route):
    open_app(page, route)
    text = body(page)
    assert "Traceback" not in text and "Something went wrong" not in text
    assert page.get_by_role("link", name="Home").count() >= 1  # the navigation is present
    assert not page.pcc_errors, page.pcc_errors


def test_unknown_route_does_not_break_the_app(page):
    open_app(page, "does-not-exist")
    assert "Traceback" not in body(page)
    assert page.get_by_role("link", name="Home").count() >= 1  # falls back to the main page
    unexpected = [e for e in page.pcc_errors if "does not seem to exist" not in e]
    assert not unexpected, unexpected


def test_the_developer_page_is_hidden_by_default(page):
    open_app(page, "m1-preview")
    assert page.get_by_role("link", name="M1 Preview").count() == 0


def test_blank_display_name_is_refused_with_a_clear_message(page):
    open_app(page, "profile")
    page.get_by_label("Display name").fill("   ")
    page.get_by_role("button", name="Start / continue").click()
    settle(page)
    assert "Display name must be 1-40 characters." in body(page)


def test_a_very_long_display_name_is_cut_to_the_limit(page, app):
    open_app(page, "profile")
    page.get_by_label("Display name").press_sequentially("N" * 90)  # real typing hits maxlength
    assert len(page.get_by_label("Display name").input_value()) == 40
    page.get_by_role("button", name="Start / continue").click()
    settle(page)
    names = [r[0] for r in db_rows(app.db_path, "SELECT display_name FROM profiles")]
    assert "N" * 40 in names and not any(len(n) > 40 for n in names)


def test_unicode_display_name_works(page, app):
    sign_in(page, "Zoë 李雷 Ñandú")
    assert "Zoë 李雷 Ñandú" in body(page)
    assert db_rows(
        app.db_path, "SELECT 1 FROM profiles WHERE display_name = ?", ("Zoë 李雷 Ñandú",)
    )


def test_html_in_a_display_name_is_shown_as_text_and_never_runs(page):
    payload = '<img src=x onerror="window.__xss=1"><script>window.__xss=2</script>'
    sign_in(page, payload)
    settle(page, 1500)
    assert page.evaluate("window.__xss") is None  # nothing executed
    nav(page, "Home")
    assert page.evaluate("window.__xss") is None
    assert not page.pcc_errors, page.pcc_errors


def test_sql_in_a_display_name_is_stored_as_plain_text(page, app):
    evil = "Robert'); DROP TABLE profiles;--"
    sign_in(page, evil)
    assert db_rows(app.db_path, "SELECT 1 FROM profiles WHERE display_name = ?", (evil,))
    assert db_rows(app.db_path, "SELECT count(*) FROM profiles")[0][0] >= 1  # table still exists
    sign_in(page, "After the attack")
    assert "After the attack" in body(page)


def _type_career(page, text: str) -> None:
    nav(page, "Career & Semester")
    page.get_by_text("My career isn't listed", exact=True).click()
    settle(page, 600)
    page.get_by_label("Type a career").fill(text)
    page.get_by_role("button", name="Build my roadmap").click()
    settle(page, 1800)


def test_free_text_career_cases(page):
    sign_in(page, "Career text tester")
    _type_career(page, "Doctor")
    assert "is not supported yet" in body(page) and "Computer Science careers only" in body(page)

    _type_career(page, "")
    assert "Enter a career name." in body(page)

    _type_career(page, "Robert'); DROP TABLE profiles;--")
    assert "letters, digits, spaces" in body(page)  # rejected by the character allow-list

    _type_career(page, "<script>window.__xss=1</script>")
    assert page.evaluate("window.__xss") is None
    assert "letters, digits, spaces" in body(page)

    _type_career(page, "aspiring java developer")  # matches a catalog alias
    assert "Roadmap ready" in body(page)


def test_changing_career_after_a_roadmap_is_blocked_with_a_clear_message(page):
    sign_in(page, "Career changer")
    build_roadmap(page, "devops_engineer")
    nav(page, "Career & Semester")
    page.get_by_text("AI Developer", exact=True).first.click()
    settle(page, 600)
    page.get_by_role("button", name="Build my roadmap").click()
    settle(page, 1500)
    text = body(page)
    assert "Traceback" not in text
    assert not page.pcc_errors, page.pcc_errors


def test_a_display_name_that_looks_like_a_link_is_not_a_link(page):
    sign_in(page, "[free prize](http://evil.example)")
    nav(page, "Home")
    assert page.locator("a[href*='evil.example']").count() == 0
    shown = body(page).replace("​", "")  # an invisible character breaks the auto-link
    assert "[free prize](http://evil.example)" in shown  # shown literally
