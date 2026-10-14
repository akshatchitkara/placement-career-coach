"""Drives the real M2 pages headlessly against a temp database."""

import pytest
from streamlit.testing.v1 import AppTest

from pcc.core.config import settings


def _page(module: str) -> None:
    import importlib

    importlib.import_module(f"pcc.ui.pages.{module}").render()


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "pcc.db"))


def _run(module: str, profile_id: int | None = None) -> AppTest:
    at = AppTest.from_function(_page, args=(module,), default_timeout=30)
    if profile_id is not None:
        at.session_state["profile_id"] = profile_id
    return at.run()


def _button(at, key):
    return next((b for b in at.button if b.key == key), None)


def test_profile_to_roadmap_journey():
    at = _run("profile_page")
    at.text_input[0].set_value("Asha")
    at.button[0].click().run()
    assert not at.exception
    profile_id = at.session_state["profile_id"]

    at = _run("career_selection_page", profile_id)
    assert not at.exception
    assert len(at.radio) == 1 and _button(at, "career_build") is None  # nothing chosen yet
    at = at.radio[0].set_value("devops_engineer").run()
    assert len(at.radio) == 2  # the semester choice appears once a career is chosen
    assert _button(at, "career_build") is None  # and the build button waits for the semester
    at = at.radio[1].set_value(3).run()
    _button(at, "career_build").click().run()
    at = _run("career_selection_page", profile_id)
    assert any("Your roadmap is ready" in s.value for s in at.success)
    assert not at.warning and not at.error  # a fallback is never shown as a warning

    at = _run("roadmap_page", profile_id)
    assert not at.exception
    assert len(at.expander) == 16
    assert [s.value.split("  ")[0] for s in at.header] == [f"Semester {n}" for n in (3, 4, 5, 6)]


def test_students_cannot_type_a_career_but_can_ask_for_one():
    at = _run("profile_page")
    at.text_input[0].set_value("Ravi")
    at.button[0].click().run()
    profile_id = at.session_state["profile_id"]

    at = _run("career_selection_page", profile_id)
    assert "__other__" not in at.radio[0].options and len(at.radio[0].options) == 4
    at.text_input[0].set_value("Doctor")
    _button(at, "career_wish_send").click().run()
    assert any("noted" in s.value for s in at.success)

    at = _run("roadmap_page", profile_id)
    assert any("No roadmap yet" in i.value for i in at.info)


def test_career_card_says_what_the_career_is_and_how_it_grows():
    at = _run("profile_page")
    at.text_input[0].set_value("Meera")
    at.button[0].click().run()
    at = _run("career_selection_page", at.session_state["profile_id"])
    at = at.radio[0].set_value("java_backend_developer").run()
    card = next(m.value for m in at.markdown if "pcc-career-card" in m.value)
    assert "What you will do" in card and "How you can grow" in card
    assert card.count("pcc-grow-step") == 4


def test_pages_ask_for_a_profile_first():
    for module in ("career_selection_page", "roadmap_page"):
        at = _run(module)
        assert any("Profile" in i.value for i in at.info)


def _signed_in_with_roadmap(name: str, career_id: str, semester: int = 3) -> int:
    at = _run("profile_page")
    at.text_input[0].set_value(name)
    at.button[0].click().run()
    profile_id = at.session_state["profile_id"]
    at = _run("career_selection_page", profile_id)
    at = at.radio[0].set_value(career_id).run()
    at = at.radio[1].set_value(semester).run()
    _button(at, "career_build").click().run()
    return profile_id


def _walk_check(at, bank, pick, *, submit: bool = True):
    """Answers the wizard one question at a time. pick(question) returns the option to select."""
    total = 12
    for step in range(total):
        radio = at.radio[0]
        question = bank[radio.key.split("_", 1)[1]]
        at = radio.set_value(pick(question)).run()
        if step < total - 1:
            at = next(b for b in at.button if b.label == "Next").click().run()
    if submit:
        at = next(b for b in at.button if b.label == "Submit answers").click().run()
    return at


def _per_skill_picker(correct_first_n: int):
    seen: dict[str, int] = {}

    def pick(q):
        n = seen.get(q.skill_id, 0)
        seen[q.skill_id] = n + 1
        right = q.correct_option_id
        return (
            right
            if n < correct_first_n
            else next(o.option_id for o in q.options if o.option_id != right)
        )

    return pick


def test_check_to_results_journey():
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    profile_id = _signed_in_with_roadmap("Asha", "devops_engineer")

    at = _run("assessment_page", profile_id)
    assert not at.exception
    at.button[0].click().run()  # Start skills check
    assert len(at.radio) == 1  # one question at a time
    assert "0 of 12" in at.get("progress")[0].proto.text

    # Submitting with questions unanswered is refused and says which (FR-05).
    for _ in range(11):
        at = next(b for b in at.button if b.label == "Next").click().run()
    at = next(b for b in at.button if b.label == "Submit answers").click().run()
    assert any("Answer every question" in e.value for e in at.error)
    assert any("unanswered" in c.value for c in at.caption)

    at = _run("assessment_page", profile_id)
    assert not any(b.label == "Start skills check" for b in at.button)  # resumed, not restarted
    at = _walk_check(at, bank, lambda q: q.correct_option_id)
    assert not at.exception

    results = _run("results_page", profile_id)
    assert not results.exception
    labels = [m.label for m in results.metric]
    assert "Level for Semester 3 skills" in labels
    assert [m.value for m in results.metric] == ["100.0%", "Advanced"]
    assert any("No major gap" in s.value for s in results.success)
    assert len(results.dataframe[0].value) == 4


def test_semester_without_a_bank_shows_coming_soon_on_the_check(monkeypatch):
    from pcc.workflow import workflow_controller

    real = workflow_controller.load_question_bank
    monkeypatch.setattr(
        workflow_controller,
        "load_question_bank",
        lambda career_id: [q for q in real(career_id) if q.skill_id == "java_core_oop"],
    )
    profile_id = _signed_in_with_roadmap("Ravi", "java_backend_developer", semester=4)
    at = _run("assessment_page", profile_id)
    assert not at.exception
    assert any("coming soon" in w.value for w in at.warning)
    assert not at.button


def test_results_page_before_any_check():
    profile_id = _signed_in_with_roadmap("Meera", "devops_engineer")
    at = _run("results_page", profile_id)
    assert any("No results yet" in i.value for i in at.info)


def _complete_check(profile_id: int, correct_first_n: int) -> None:
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    at = _run("assessment_page", profile_id)
    at = at.button[0].click().run()  # Start skills check
    at = _walk_check(at, bank, _per_skill_picker(correct_first_n))
    assert not at.exception


def test_weak_result_leads_to_a_coaching_plan_page():
    profile_id = _signed_in_with_roadmap("Asha", "devops_engineer")
    _complete_check(profile_id, correct_first_n=0)  # everything wrong

    at = _run("coaching_page", profile_id)
    assert not at.exception
    assert any("Focus skill" in s.value for s in at.header)
    assert 3 <= len(at.markdown) and sum("Do this:" in m.value for m in at.markdown) >= 3
    assert any("You're done when" in m.value for m in at.markdown)
    assert not any("http" in m.value for m in at.markdown)


def test_coaching_page_explains_when_there_is_no_plan():
    profile_id = _signed_in_with_roadmap("Ravi", "devops_engineer")
    at = _run("coaching_page", profile_id)
    assert any("Skills Check" in i.value for i in at.info)

    _complete_check(profile_id, correct_first_n=3)  # everything right -> no major gap
    at = _run("coaching_page", profile_id)
    assert any("No coaching plan" in i.value for i in at.info)


def test_weekly_plan_page_shows_tasks_and_remembers_ticks():
    profile_id = _signed_in_with_roadmap("Asha", "devops_engineer")
    at = _run("weekly_plan_page", profile_id)
    assert any("Skills Check" in i.value for i in at.info)  # nothing before the first check

    _complete_check(profile_id, correct_first_n=1)
    at = _run("weekly_plan_page", profile_id)
    assert not at.exception
    assert 2 <= len(at.checkbox) <= 4  # study tasks; the re-check is a card, not a tick
    assert any("Re-check on" in i.value for i in at.info)

    at.checkbox[0].check().run()
    assert not at.exception
    again = _run("weekly_plan_page", profile_id)
    assert again.checkbox[0].value is True and again.checkbox[1].value is False


def test_recheck_and_progress_journey():
    profile_id = _signed_in_with_roadmap("Ravi", "devops_engineer")
    at = _run("progress_page", profile_id)
    assert any("No checks yet" in i.value for i in at.info)

    _complete_check(profile_id, correct_first_n=0)
    at = _run("progress_page", profile_id)
    assert not at.exception
    assert any("This is your baseline" in m.value for m in at.markdown)
    assert any("below 40%" in w.value for w in at.warning)  # mentor prompt

    at = _run("assessment_page", profile_id)  # re-check offered, early
    assert any("re-check is planned" in i.value for i in at.info)
    assert at.button[0].label == "Start re-check"
    _complete_check_retest(profile_id, correct_first_n=3)

    at = _run("progress_page", profile_id)
    assert not at.exception
    assert [m.label for m in at.metric] == ["Latest score", "Level", "Checks taken"]
    text = " ".join(m.value for m in at.markdown)
    assert "Re-check 1" in text and "<svg" in text  # trend chart with both checks
    assert "points" in text  # per-skill change labels
    assert len(at.dataframe[0].value) == 2


def _complete_check_retest(profile_id: int, correct_first_n: int) -> None:
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    at = _run("assessment_page", profile_id)
    at = at.button[0].click().run()  # Start re-check
    at = _walk_check(at, bank, _per_skill_picker(correct_first_n))
    assert not at.exception


def test_results_page_labels_a_recheck():
    profile_id = _signed_in_with_roadmap("Meera", "devops_engineer")
    _complete_check(profile_id, correct_first_n=1)
    _complete_check_retest(profile_id, correct_first_n=3)
    at = _run("results_page", profile_id)
    assert any(c.value == "Re-check" for c in at.caption)


def test_home_welcomes_a_new_visitor_and_guides_a_signed_in_student():
    at = _run("home_page")
    assert not at.exception
    assert any("Placement Career Coach" in m.value for m in at.markdown)

    profile_id = _signed_in_with_roadmap("Neha", "mean_stack_developer")
    at = _run("home_page", profile_id)
    assert not at.exception
    assert any("Welcome back, Neha" in t.value for t in at.title)
    assert any("skills check" in m.value.lower() for m in at.markdown)


def test_every_state_has_a_stepper_position_label_and_next_step():
    from pcc.domain.enums import WorkflowState
    from pcc.ui.components.journey import next_step, state_label

    for state in WorkflowState:
        assert state_label(state)
        message, label, target = next_step(state)
        assert message and label and target


def test_answers_survive_a_reload_in_the_middle_of_a_check():
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    profile_id = _signed_in_with_roadmap("Reloader", "devops_engineer")
    at = _run("assessment_page", profile_id)
    at = at.button[0].click().run()  # start the check
    first = at.radio[0]
    question = bank[first.key.split("_", 1)[1]]
    at = first.set_value(question.correct_option_id).run()
    at = next(b for b in at.button if b.label == "Next").click().run()
    assert "1 of 12" in at.get("progress")[0].proto.text

    reloaded = _run("assessment_page", profile_id)  # a new browser session, same profile
    assert not reloaded.exception
    assert "1 of 12" in reloaded.get("progress")[0].proto.text  # the answer was kept
    assert any(
        "Question 2 of 12" in m.value for m in reloaded.markdown
    )  # resumes where it left off


def test_choosing_an_option_and_pressing_next_in_one_step_keeps_the_answer():
    """A quick click on Next (or a slow server) delivers both changes together; none may be lost."""
    from pcc.content.content_loader import load_question_bank

    bank = {q.question_id: q for q in load_question_bank("devops_engineer")}
    profile_id = _signed_in_with_roadmap("Quick clicker", "devops_engineer")
    at = _run("assessment_page", profile_id)
    at = at.button[0].click().run()  # start the check

    first = at.radio[0]
    question = bank[first.key.split("_", 1)[1]]
    first.set_value(question.correct_option_id)  # no run() in between: one combined update
    at = next(b for b in at.button if b.label == "Next").click().run()

    assert any("Question 2 of 12" in m.value for m in at.markdown)
    assert "1 of 12" in at.get("progress")[0].proto.text  # question 1 was kept
    back = next(b for b in at.button if b.label == "Back").click().run()
    assert back.radio[0].value == question.correct_option_id
