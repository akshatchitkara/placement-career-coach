"""Workflow state machine (blueprint Section 7.4). Pure: no I/O."""

from pcc.core.exceptions import WorkflowStateError
from pcc.domain.enums import WorkflowState as S

# Re-selecting a career is allowed only until the first check starts; later it would
# orphan attempts, so it is deliberately not offered here.
ALLOWED_TRANSITIONS: dict[S, frozenset[S]] = {
    S.PROFILE_READY: frozenset({S.CAREER_SELECTED}),
    S.CAREER_SELECTED: frozenset({S.CAREER_SELECTED, S.ROADMAP_READY}),
    S.ROADMAP_READY: frozenset({S.CAREER_SELECTED, S.ASSESSMENT_IN_PROGRESS}),
    S.ASSESSMENT_IN_PROGRESS: frozenset({S.RESULTS_READY}),
    S.RESULTS_READY: frozenset({S.COACHING_READY, S.WEEKLY_PLAN_ACTIVE}),
    S.COACHING_READY: frozenset({S.WEEKLY_PLAN_ACTIVE}),
    S.WEEKLY_PLAN_ACTIVE: frozenset({S.RETEST_DUE}),
    S.RETEST_DUE: frozenset({S.ASSESSMENT_IN_PROGRESS}),
}


def can_transition(current: S, target: S) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def assert_transition(current: S, target: S) -> None:
    if not can_transition(current, target):
        raise WorkflowStateError(f"cannot move from {current.value} to {target.value}")
