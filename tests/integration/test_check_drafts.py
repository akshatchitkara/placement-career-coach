from contextlib import closing

import pytest
from tests.integration.test_assessment_flow import BANK, _ready

from pcc.core.exceptions import PccError
from pcc.workflow.workflow_controller import WorkflowController


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def _first_two(session):
    q1, q2 = session.questions[0], session.questions[1]
    return q1, q2


def test_a_draft_survives_reopening_the_app(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    q1, q2 = _first_two(session)
    controller.save_check_draft(
        profile.id, session.attempt_id, {q1.question_id: q1.options[0].option_id}
    )
    reopened = WorkflowController(db_path)
    assert reopened.get_check_draft(profile.id, session.attempt_id) == {
        q1.question_id: q1.options[0].option_id
    }
    assert q2.question_id not in reopened.get_check_draft(profile.id, session.attempt_id)


def test_the_draft_is_replaced_not_appended_and_can_shrink(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    q1, q2 = _first_two(session)
    both = {q1.question_id: q1.options[0].option_id, q2.question_id: q2.options[1].option_id}
    controller.save_check_draft(profile.id, session.attempt_id, both)
    controller.save_check_draft(
        profile.id, session.attempt_id, {q1.question_id: q1.options[2].option_id}
    )
    assert controller.get_check_draft(profile.id, session.attempt_id) == {
        q1.question_id: q1.options[2].option_id
    }


def test_unknown_questions_and_options_are_dropped_not_stored(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    q1, _ = _first_two(session)
    controller.save_check_draft(
        profile.id,
        session.attempt_id,
        {
            q1.question_id: "opt_zzz",  # not one of the options
            "q_not_in_this_check": "opt_a",
            "'); DROP TABLE profiles;--": "opt_a",
        },
    )
    assert controller.get_check_draft(profile.id, session.attempt_id) == {}


def test_another_profile_cannot_read_or_write_a_draft(db_path):
    controller, profile = _ready(db_path, name="Asha")
    session = controller.start_assessment(profile.id)
    intruder = controller.open_profile("Mallory")
    with pytest.raises(PccError, match="not open"):
        controller.get_check_draft(intruder.id, session.attempt_id)
    with pytest.raises(PccError, match="not open"):
        controller.save_check_draft(intruder.id, session.attempt_id, {})


def test_submitting_removes_the_draft_and_closes_it(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    picks = {q.question_id: BANK[q.question_id].correct_option_id for q in session.questions}
    controller.save_check_draft(profile.id, session.attempt_id, picks)
    controller.submit_assessment(profile.id, session.attempt_id, picks)
    with pytest.raises(PccError, match="not open"):
        controller.get_check_draft(profile.id, session.attempt_id)
    with pytest.raises(PccError, match="not open"):
        controller.save_check_draft(profile.id, session.attempt_id, picks)
    import sqlite3

    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute("SELECT count(*) FROM assessment_drafts").fetchone()
    assert rows[0] == 0


def test_a_draft_never_changes_what_is_graded(db_path):
    controller, profile = _ready(db_path)
    session = controller.start_assessment(profile.id)
    wrong = {
        q.question_id: next(
            o.option_id for o in q.options if o.option_id != BANK[q.question_id].correct_option_id
        )
        for q in session.questions
    }
    controller.save_check_draft(
        profile.id,
        session.attempt_id,
        {q.question_id: BANK[q.question_id].correct_option_id for q in session.questions},
    )
    result = controller.submit_assessment(profile.id, session.attempt_id, wrong)  # submission wins
    assert result.overall_score == 0.0
