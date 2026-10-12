"""The weekly plan page: day layout, progress feedback, time budget and calendar export."""

from tests.ui.test_student_happy_path import (
    _complete_check,
    _run,
    _signed_in_with_roadmap,
    temp_db,  # noqa: F401 -- autouse fixture
)


def _page(name: str):
    profile_id = _signed_in_with_roadmap(name, "devops_engineer")
    _complete_check(profile_id, correct_first_n=1)
    return profile_id, _run("weekly_plan_page", profile_id)


def test_week_is_laid_out_by_day_with_a_recheck_day_and_summary():
    _, at = _page("Asha")
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert labels == ["Tasks done", "Study time left", "Re-check"]
    text = " ".join(m.value for m in at.markdown)
    assert "re-check day" in text
    assert text.count("min") >= 2
    assert any("Today" in m.value for m in at.markdown)


def test_ticking_every_task_shows_the_week_complete_message():
    profile_id, at = _page("Ravi")
    for index in range(len(at.checkbox)):
        at = _run("weekly_plan_page", profile_id)
        at.checkbox[index].check().run()
    at = _run("weekly_plan_page", profile_id)
    assert any("All of this week's tasks are done" in s.value for s in at.success)
    assert at.metric[0].value.split()[0] == at.metric[0].value.split()[-1]  # "N of N"


def test_choosing_less_time_rebuilds_the_week_in_place():
    profile_id, at = _page("Meera")
    before = len(at.checkbox)
    at.radio[0].set_value(120).run()
    assert not at.exception
    again = _run("weekly_plan_page", profile_id)
    assert 2 <= len(again.checkbox) <= before
    assert any("re-check day" in m.value for m in again.markdown)


def test_calendar_download_is_offered():
    _, at = _page("Kiran")
    assert len(at.get("download_button")) == 1
