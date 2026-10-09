import sqlite3

import pytest

from pcc.domain.enums import WorkflowState
from pcc.persistence.database import get_connection, init_schema
from pcc.persistence.repositories.profile_repository import (
    get_or_create_profile,
    list_profiles,
    set_workflow_state,
)
from pcc.persistence.repositories.roadmap_repository import (
    get_active_roadmap,
    save_active_roadmap,
)


@pytest.fixture
def conn(tmp_path):
    connection = get_connection(str(tmp_path / "pcc.db"))
    init_schema(connection)
    yield connection
    connection.close()


def test_profile_is_unique_by_display_name(conn):
    first = get_or_create_profile(conn, "Asha")
    again = get_or_create_profile(conn, "Asha")
    assert first.id == again.id
    assert len(list_profiles(conn)) == 1
    assert first.workflow_state == WorkflowState.PROFILE_READY


def test_workflow_state_round_trips(conn):
    profile = get_or_create_profile(conn, "Ravi")
    set_workflow_state(conn, profile.id, WorkflowState.RESULTS_READY)
    conn.commit()
    assert get_or_create_profile(conn, "Ravi").workflow_state == WorkflowState.RESULTS_READY


def test_only_one_active_roadmap_per_profile(conn, devops_template):
    profile = get_or_create_profile(conn, "Asha")
    save_active_roadmap(conn, profile.id, devops_template)
    save_active_roadmap(conn, profile.id, devops_template)
    conn.commit()
    active = conn.execute("SELECT COUNT(*) FROM roadmaps WHERE is_active = 1").fetchone()[0]
    assert active == 1
    assert get_active_roadmap(conn, profile.id) == devops_template


def test_foreign_keys_are_enforced(conn):
    try:
        conn.execute(
            "INSERT INTO roadmaps (profile_id, career_id, generation_source, roadmap_json, "
            "created_at) VALUES (999, 'x', 'template', '{}', 'now')"
        )
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised
