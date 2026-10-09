import pytest

from pcc.core.exceptions import WorkflowStateError
from pcc.domain.enums import WorkflowState as S
from pcc.workflow.workflow_transitions import ALLOWED_TRANSITIONS, assert_transition, can_transition


def test_every_state_has_a_rule():
    assert set(ALLOWED_TRANSITIONS) == set(S)


def test_happy_path_to_roadmap_ready():
    assert_transition(S.PROFILE_READY, S.CAREER_SELECTED)
    assert_transition(S.CAREER_SELECTED, S.ROADMAP_READY)
    assert_transition(S.ROADMAP_READY, S.ASSESSMENT_IN_PROGRESS)


def test_career_can_be_reselected_until_first_check():
    assert can_transition(S.ROADMAP_READY, S.CAREER_SELECTED)
    assert not can_transition(S.RESULTS_READY, S.CAREER_SELECTED)


def test_cannot_start_assessment_before_roadmap():
    with pytest.raises(WorkflowStateError):
        assert_transition(S.CAREER_SELECTED, S.ASSESSMENT_IN_PROGRESS)
    with pytest.raises(WorkflowStateError):
        assert_transition(S.PROFILE_READY, S.ASSESSMENT_IN_PROGRESS)
