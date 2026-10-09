import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from pcc.domain.enums import Level, WorkflowState
from pcc.workflow.demo_seed import DEMO_NAMES, seed_demo_profiles
from pcc.workflow.workflow_controller import WorkflowController

TODAY = date(2026, 10, 10)
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def seeded(tmp_path):
    db = str(tmp_path / "demo.db")
    seed_demo_profiles(db, TODAY)
    controller = WorkflowController(db, today=lambda: TODAY)
    profiles = {p.display_name: p for p in controller.list_profiles()}
    return controller, profiles


def test_three_demo_profiles_exist(seeded):
    _, profiles = seeded
    assert set(profiles) == set(DEMO_NAMES)


def test_asha_is_a_fresh_start(seeded):
    controller, profiles = seeded
    asha = profiles["Asha"]
    assert asha.career_id is None and asha.workflow_state == WorkflowState.PROFILE_READY
    assert controller.get_progress(asha.id).attempts == []


def test_ravi_matches_the_blueprint_worked_example(seeded):
    controller, profiles = seeded
    ravi = profiles["Ravi"]
    results = controller.get_latest_results(ravi.id)
    assert results.overall_score == pytest.approx(50.0) and results.level == Level.INTERMEDIATE
    assert results.weakest.skill_id == "linux_fundamentals"
    assert results.position.skill_id == "linux_fundamentals"
    assert controller.get_coaching_plan(ravi.id) is not None
    assert 3 <= len(controller.get_weekly_plan(ravi.id).plan.tasks) <= 5
    assert len(controller.get_progress(ravi.id).attempts) == 1


def test_meera_shows_improvement_and_an_advanced_position(seeded):
    controller, profiles = seeded
    progress = controller.get_progress(profiles["Meera"].id)
    assert [a.attempt_type for a in progress.attempts] == ["baseline", "retest"]
    assert progress.overall_delta > 40
    assert (progress.previous_level, progress.current_level) == (Level.INTERMEDIATE, Level.ADVANCED)
    assert {d.direction for d in progress.deltas} <= {"up", "same"}
    results = controller.get_latest_results(profiles["Meera"].id)
    assert results.position.skill_id == "networking_fundamentals"  # moved past Semester 3


def test_attempt_dates_come_from_the_seeded_clock(seeded):
    controller, profiles = seeded
    dates = [a.submitted_at[:10] for a in controller.get_progress(profiles["Meera"].id).attempts]
    assert dates == ["2026-09-30", "2026-10-07"]


def test_every_demo_profile_with_a_check_is_in_a_usable_state(seeded):
    controller, profiles = seeded
    for name in ("Ravi", "Meera"):
        assert profiles[name].workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE
        view = controller.get_weekly_plan(profiles[name].id)
        assert not view.retest_due and view.days_until_retest > 0


# --- the reset script and its safety guard ------------------------------------------------------
def _script(db_path, *args):
    env = {**os.environ, "PCC_DB_PATH": str(db_path)}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "reset_demo.py"), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=120,
    )


def test_reset_script_builds_the_demo_database_from_nothing(tmp_path):
    db = tmp_path / "fresh.db"
    result = _script(db)
    assert result.returncode == 0, result.stderr
    names = {p.display_name for p in WorkflowController(str(db)).list_profiles()}
    assert names == set(DEMO_NAMES)


def test_reset_script_can_be_run_again_over_its_own_demo_data(tmp_path):
    db = tmp_path / "again.db"
    assert _script(db).returncode == 0
    assert _script(db).returncode == 0
    assert len(WorkflowController(str(db)).list_profiles()) == 3


def test_reset_script_refuses_to_delete_real_profiles_without_force(tmp_path):
    db = tmp_path / "real.db"
    controller = WorkflowController(str(db))
    controller.open_profile("RealStudent")
    refused = _script(db)
    assert refused.returncode == 1 and "RealStudent" in refused.stdout
    assert [p.display_name for p in controller.list_profiles()] == ["RealStudent"]  # untouched

    forced = _script(db, "--force")
    assert forced.returncode == 0
    assert {p.display_name for p in WorkflowController(str(db)).list_profiles()} == set(DEMO_NAMES)
