import pytest
from tests.integration.test_coaching_flow import WORKED, _take_check

from pcc.core.exceptions import PccError
from pcc.workflow.workflow_controller import WorkflowController


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def _minutes(view) -> int:
    return sum(t.estimated_minutes for t in view.plan.tasks)


def test_a_smaller_budget_drops_tasks_but_keeps_the_week_and_the_recheck(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)
    before = controller.get_weekly_plan(profile.id)

    controller.set_weekly_capacity(profile.id, 90)
    after = controller.get_weekly_plan(profile.id)

    assert after.plan_id == before.plan_id  # same week, edited in place
    assert after.plan.week_start_date == before.plan.week_start_date
    assert after.plan.retest_due_date == before.plan.retest_due_date
    assert after.plan.tasks[-1].kind == "recheck"
    assert 3 <= len(after.plan.tasks) <= len(before.plan.tasks)
    assert _minutes(after) <= _minutes(before)


def test_the_same_budget_rebuilds_the_identical_plan(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)
    before = controller.get_weekly_plan(profile.id).plan
    controller.set_weekly_capacity(profile.id, 240)  # the configured default
    assert controller.get_weekly_plan(profile.id).plan == before


def test_ticks_survive_for_tasks_that_remain_and_vanish_for_dropped_ones(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)
    view = controller.get_weekly_plan(profile.id)
    for task in view.plan.tasks:
        controller.set_task_done(profile.id, view.plan_id, task.task_id, True)

    controller.set_weekly_capacity(profile.id, 90)
    after = controller.get_weekly_plan(profile.id)
    ids = {t.task_id for t in after.plan.tasks}
    assert set(after.done_task_ids) == ids  # every remaining task is still ticked


def test_budget_outside_the_allowed_range_is_refused(db_path):
    controller = WorkflowController(db_path)
    profile, _, _ = _take_check(controller, WORKED)
    for bad in (0, 89, 301):
        with pytest.raises(PccError, match="Choose between"):
            controller.set_weekly_capacity(profile.id, bad)


def test_no_plan_yet_is_a_clear_error(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Asha")
    with pytest.raises(PccError, match="no weekly plan"):
        controller.set_weekly_capacity(profile.id, 120)
