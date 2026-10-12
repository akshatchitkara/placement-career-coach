"""The coaching page's tutor, quiz and done-checkbox, driven headlessly (offline mode)."""

from tests.ui.test_student_happy_path import (
    _complete_check,
    _run,
    _signed_in_with_roadmap,
    temp_db,  # noqa: F401 -- autouse fixture
)


def _coached_profile(name: str) -> int:
    profile_id = _signed_in_with_roadmap(name, "devops_engineer")
    _complete_check(profile_id, correct_first_n=1)
    return profile_id


def test_quick_action_adds_a_coach_reply_that_persists():
    profile_id = _coached_profile("Asha")
    at = _run("coaching_page", profile_id)
    assert not at.exception
    assert not at.chat_message

    at.button(key="coach_explain_differently_1").click().run()
    assert not at.exception
    assert len(at.chat_message) == 2
    assert "Explain it differently" in at.chat_message[0].markdown[0].value

    again = _run("coaching_page", profile_id)  # a new session sees the saved thread
    assert len(again.chat_message) == 2


def test_free_text_question_and_validation():
    profile_id = _coached_profile("Ravi")
    at = _run("coaching_page", profile_id)
    at.text_input(key="coach_text_1").set_value("Why is the group digit 4?")
    at.button[[b.key for b in at.button].index("FormSubmitter:coach_form_1-Ask")].click().run()
    assert not at.exception
    assert any("Why is the group digit 4?" in m.markdown[0].value for m in at.chat_message)


def test_quiz_is_graded_and_labelled_practice_only():
    profile_id = _coached_profile("Meera")
    at = _run("coaching_page", profile_id)
    at.button(key="coach_quiz_1").click().run()
    assert not at.exception
    radios = [r for r in at.radio if r.key and r.key.startswith("quiz_1_")]
    assert 1 <= len(radios) <= 3
    for radio in radios:
        radio.set_value(radio.options[0])
    submit = next(b for b in at.button if b.label == "Check my answers")
    submit.click().run()
    assert not at.exception
    assert any("Quiz result" in m.value for m in at.markdown)
    assert any("does not change your score" in c.value for c in at.caption)


def test_done_checkbox_is_shared_with_the_weekly_plan():
    profile_id = _coached_profile("Kiran")
    at = _run("coaching_page", profile_id)
    at.checkbox(key="coach_done_1").check().run()
    assert not at.exception

    weekly = _run("weekly_plan_page", profile_id)
    ticked = [c for c in weekly.checkbox if c.value]
    assert len(ticked) == 1
