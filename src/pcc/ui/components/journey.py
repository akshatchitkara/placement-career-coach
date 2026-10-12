"""The student's journey: friendly step names, the stepper, and the 'what next' suggestion."""

import streamlit as st

from pcc.domain.enums import WorkflowState
from pcc.ui.navigation import go_button

STEPS = ["Profile", "Career", "Roadmap", "Skills check", "Weekly plan"]

# Number of steps finished for each workflow state.
_DONE = {
    WorkflowState.PROFILE_READY: 1,
    WorkflowState.CAREER_SELECTED: 2,
    WorkflowState.ROADMAP_READY: 3,
    WorkflowState.ASSESSMENT_IN_PROGRESS: 3,
    WorkflowState.RESULTS_READY: 4,
    WorkflowState.COACHING_READY: 4,
    WorkflowState.WEEKLY_PLAN_ACTIVE: 5,
    WorkflowState.RETEST_DUE: 5,
}

STATE_LABELS = {
    WorkflowState.PROFILE_READY: "Getting started",
    WorkflowState.CAREER_SELECTED: "Career chosen",
    WorkflowState.ROADMAP_READY: "Roadmap ready",
    WorkflowState.ASSESSMENT_IN_PROGRESS: "Skills check in progress",
    WorkflowState.RESULTS_READY: "Results ready",
    WorkflowState.COACHING_READY: "Coaching plan ready",
    WorkflowState.WEEKLY_PLAN_ACTIVE: "Following your weekly plan",
    WorkflowState.RETEST_DUE: "Re-check due",
}

# state -> (what to do, button label, page key)
_NEXT = {
    WorkflowState.PROFILE_READY: (
        "Pick your target career and semester.",
        "Choose my career",
        "career",
    ),
    WorkflowState.CAREER_SELECTED: ("Finish building your roadmap.", "Choose my career", "career"),
    WorkflowState.ROADMAP_READY: (
        "Your roadmap is ready. Take the skills check to see where you stand.",
        "Take the skills check",
        "assessment",
    ),
    WorkflowState.ASSESSMENT_IN_PROGRESS: (
        "You have a check in progress. Pick up where you left off.",
        "Continue my check",
        "assessment",
    ),
    WorkflowState.RESULTS_READY: ("Your results are in.", "See my results", "results"),
    WorkflowState.COACHING_READY: (
        "Your coaching plan is ready.",
        "Open my coaching plan",
        "coaching",
    ),
    WorkflowState.WEEKLY_PLAN_ACTIVE: (
        "Work through this week's tasks, then re-check to measure your progress.",
        "Open this week's plan",
        "weekly",
    ),
    WorkflowState.RETEST_DUE: (
        "Time to measure your progress with a re-check.",
        "Start my re-check",
        "assessment",
    ),
}


def state_label(state: WorkflowState) -> str:
    return STATE_LABELS[state]


def render_stepper(state: WorkflowState) -> None:
    done = _DONE[state]
    cells = []
    for i, name in enumerate(STEPS):
        css = "done" if i < done else "current" if i == done else ""
        mark = "Done" if i < done else "Now" if i == done else f"Step {i + 1}"
        cells.append(f'<div class="pcc-step {css}"><b>{mark}</b>{name}</div>')
    st.markdown(f'<div class="pcc-steps">{"".join(cells)}</div>', unsafe_allow_html=True)


def next_step(state: WorkflowState) -> tuple[str, str, str]:
    return _NEXT[state]


def next_step_button(state: WorkflowState, *, key: str) -> None:
    _, label, target = _NEXT[state]
    go_button(label, target, key=key, primary=True)
