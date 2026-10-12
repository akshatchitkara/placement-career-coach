"""Progress dashboard and the Home trend, driven headlessly (offline mode)."""

from tests.ui.test_student_happy_path import (
    _complete_check,
    _complete_check_retest,
    _run,
    _signed_in_with_roadmap,
    temp_db,  # noqa: F401 -- autouse fixture
)


def _two_checks(name: str) -> int:
    profile_id = _signed_in_with_roadmap(name, "devops_engineer")
    _complete_check(profile_id, correct_first_n=0)
    weekly = _run("weekly_plan_page", profile_id)
    weekly.checkbox[0].check().run()  # one task done before the re-check
    _complete_check_retest(profile_id, correct_first_n=3)
    return profile_id


def test_effort_is_shown_next_to_the_score_change():
    profile_id = _two_checks("Asha")
    at = _run("progress_page", profile_id)
    assert not at.exception
    assert any("Did the effort show up?" in s.value for s in at.subheader)
    text = " ".join(m.value for m in at.markdown)
    assert "Week after your baseline" in text and "1 of" in text and "points" in text
    assert any("not proof" in c.value for c in at.caption)


def test_mentor_message_is_offered_for_a_skill_under_40_percent():
    profile_id = _signed_in_with_roadmap("Ravi", "devops_engineer")
    _complete_check(profile_id, correct_first_n=0)
    at = _run("progress_page", profile_id)
    assert any("below 40%" in w.value for w in at.warning)
    assert any("DevOps Engineer" in c.value and "30 minutes" in c.value for c in at.code)
    assert not any("Ravi" in c.value for c in at.code)  # nothing identifying in a shared message


def test_single_check_progress_points_to_the_weekly_plan():
    profile_id = _signed_in_with_roadmap("Meera", "devops_engineer")
    _complete_check(profile_id, correct_first_n=1)
    at = _run("progress_page", profile_id)
    assert not at.exception
    assert [m.label for m in at.metric] == ["Latest score", "Level", "Checks taken"]
    assert not any("Did the effort show up?" in s.value for s in at.subheader)
    assert "first time measured" in " ".join(m.value for m in at.markdown)


def test_home_shows_the_trend_once_there_are_two_checks():
    profile_id = _two_checks("Kiran")
    at = _run("home_page", profile_id)
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "since your baseline" in text and "<svg" in text
