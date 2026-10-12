"""The full-path check in the interface: offered, labelled, and able to reach Industry-ready."""

from tests.ui.test_student_happy_path import (
    _run,
    _signed_in_with_roadmap,
    temp_db,  # noqa: F401 -- autouse fixture
)


def _answer_all(at, bank, total):
    for step in range(total):
        radio = at.radio[0]
        at = radio.set_value(bank[radio.key.split("_", 1)[1]].correct_option_id).run()
        if step < total - 1:
            at = next(b for b in at.button if b.label == "Next").click().run()
    return at


def test_the_full_path_check_is_offered_next_to_the_semester_check():
    profile_id = _signed_in_with_roadmap("Asha", "devops_engineer")
    at = _run("assessment_page", profile_id)
    labels = [b.label for b in at.button]
    assert "Start skills check" in labels and "Take the full-path check" in labels
    assert any("only check that can place you at Industry-ready" in c.value for c in at.caption)
    assert any("28 questions, two per skill" in c.value for c in at.caption)


def test_a_perfect_full_path_check_reaches_industry_ready_in_the_interface():
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    profile_id = _signed_in_with_roadmap("Meera", "devops_engineer")
    at = _run("assessment_page", profile_id)
    at = next(b for b in at.button if b.label == "Take the full-path check").click().run()
    assert any("Question 1 of 28" in m.value for m in at.markdown)
    assert any("Full-path check" in h.value for h in at.header)
    at = _answer_all(at, bank, 28)
    at = next(b for b in at.button if b.label == "Submit answers").click().run()
    assert not at.exception

    results = _run("results_page", profile_id)
    assert [m.value for m in results.metric] == ["100.0%", "Industry-ready"]
    assert any("Level for the full roadmap" in m.label for m in results.metric)
    assert any("Full-path check" in c.value for c in results.caption)
    assert not results.exception


def test_progress_explains_why_a_semester_check_and_a_full_path_check_are_not_compared():
    from pcc.content.content_loader import load_question_bank
    from pcc.core.config import settings
    from pcc.workflow.workflow_controller import WorkflowController

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    controller = WorkflowController(settings.db_path)
    profile = controller.open_profile("Scope mix")
    controller.select_career(profile.id, career_id="devops_engineer", custom_text="", semester=3)
    for full in (False, True):
        session = controller.start_assessment(profile.id, full_path=full)
        picks = {q.question_id: bank[q.question_id].correct_option_id for q in session.questions}
        controller.submit_assessment(profile.id, session.attempt_id, picks)

    at = _run("progress_page", profile.id)
    assert not at.exception
    assert any("covered different skills" in i.value for i in at.info)
    assert at.metric[0].delta in (None, "")  # no "+X points" across different scopes
    assert at.metric[1].value == "Industry-ready"
