"""The roadmap road: states, the module quiz, and the shortcut to the skills check."""

from tests.ui.test_student_happy_path import (  # noqa: F401 -- autouse fixture
    _run,
    _signed_in_with_roadmap,
    temp_db,
)

from pcc.content.content_loader import load_question_bank
from pcc.workflow.workflow_controller import get_controller

BANK = {q.question_id: q for q in load_question_bank("devops_engineer")}


def _road(at) -> str:
    return next(m.value for m in at.markdown if "pcc-road" in m.value)


def _button(at, key):
    return next((b for b in at.button if b.key == key), None)


def _first_module(at) -> str:
    return next(b.key.removeprefix("mq_start_") for b in at.button if b.key.startswith("mq_start_"))


def _answer_quiz(at, profile_id, skill_id, right: bool):
    for q in get_controller().get_module_quiz(profile_id, skill_id):
        correct = BANK[q.question_id].correct_option_id
        pick = next(o.option_id for o in q.options if (o.option_id == correct) == right)
        next(r for r in at.radio if r.key == f"mq_{skill_id}_{q.question_id}").set_value(pick)
    return at  # no rerun here: a form's answers only count when it is submitted


def test_road_starts_at_the_first_module_and_links_to_the_skills_check():
    profile_id = _signed_in_with_roadmap("Asha", "devops_engineer")
    at = _run("roadmap_page", profile_id)
    assert not at.exception
    road = _road(at)
    assert road.count("pcc-node current") == 1 and "pcc-node done" not in road
    assert road.index("pcc-node current") < road.index("pcc-node next")
    assert len(at.expander) == 16


def test_passing_the_module_quiz_completes_the_module_and_earns_xp():
    profile_id = _signed_in_with_roadmap("Ravi", "devops_engineer")
    at = _run("roadmap_page", profile_id)
    skill_id = _first_module(at)
    _button(at, f"mq_start_{skill_id}").click().run()
    at = _answer_quiz(at, profile_id, skill_id, right=True)
    next(b for b in at.button if b.label == "Check my answers").click().run()
    assert not at.exception
    assert any("Module complete" in s.value for s in at.success)

    state = get_controller().get_game_state(profile_id)
    assert state.xp == 50 and "First step" in [b.name for b in state.earned_badges]
    next(b for b in at.button if b.key == f"mq_next_{skill_id}").click().run()
    road = _road(at)
    assert road.count("pcc-node done") == 1 and road.count("pcc-node current") == 1


def test_failing_the_module_quiz_explains_and_offers_a_retry():
    profile_id = _signed_in_with_roadmap("Meera", "devops_engineer")
    at = _run("roadmap_page", profile_id)
    skill_id = _first_module(at)
    _button(at, f"mq_start_{skill_id}").click().run()
    at = _answer_quiz(at, profile_id, skill_id, right=False)
    next(b for b in at.button if b.label == "Check my answers").click().run()
    assert any("You need 2" in w.value for w in at.warning)
    assert get_controller().get_game_state(profile_id).xp == 0
    assert _button(at, f"mq_next_{skill_id}") is not None  # "Try again with new questions"
