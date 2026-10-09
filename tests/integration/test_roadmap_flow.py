import pytest

from pcc.core.exceptions import PccError
from pcc.domain.enums import WorkflowState
from pcc.workflow.workflow_controller import WorkflowController


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "pcc.db")


def test_devops_flow_builds_16_month_roadmap(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Asha")
    result = controller.select_career(
        profile.id, career_id="devops_engineer", custom_text="", semester=3
    )
    assert result.status == "roadmap_ready"
    roadmap = controller.get_roadmap(profile.id)
    assert len(roadmap.months) == 16
    assert sorted({m.semester for m in roadmap.months}) == [3, 4, 5, 6]
    assert roadmap.generation_source == "template"
    saved = controller.get_profile(profile.id)
    assert saved.workflow_state == WorkflowState.ROADMAP_READY
    assert (saved.career_id, saved.current_semester) == ("devops_engineer", 3)


def test_t15_flow_completes_when_ai_is_down(db_path, unavailable_ai):
    controller = WorkflowController(db_path, ai_client=unavailable_ai)
    profile = controller.open_profile("Ravi")
    result = controller.select_career(
        profile.id, career_id="devops_engineer", custom_text="", semester=4
    )
    assert result.status == "roadmap_ready"
    assert "unavailable" in result.message
    assert controller.get_roadmap(profile.id).generation_source == "template"


def test_t19_non_cs_career_gives_message_and_no_roadmap(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Meera")
    result = controller.select_career(profile.id, career_id=None, custom_text="Doctor", semester=3)
    assert result.status == "unsupported"
    assert "DevOps Engineer" in result.message
    assert controller.get_roadmap(profile.id) is None
    assert controller.get_profile(profile.id).workflow_state == WorkflowState.PROFILE_READY


def test_typed_alias_selects_catalog_career(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Kiran")
    result = controller.select_career(profile.id, career_id=None, custom_text="SRE", semester=5)
    assert result.status == "roadmap_ready"
    assert result.roadmap.career_id == "devops_engineer"


def test_t18_state_survives_a_new_controller(db_path):
    first = WorkflowController(db_path)
    profile = first.open_profile("Asha")
    first.select_career(profile.id, career_id="java_backend_developer", custom_text="", semester=6)

    reopened = WorkflowController(db_path)
    again = reopened.open_profile("Asha")
    assert again.id == profile.id
    assert again.career_id == "java_backend_developer"
    assert again.current_semester == 6
    assert reopened.get_roadmap(profile.id).career_id == "java_backend_developer"


def test_changing_career_replaces_the_active_roadmap(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Asha")
    controller.select_career(profile.id, career_id="devops_engineer", custom_text="", semester=3)
    controller.select_career(profile.id, career_id="ai_developer", custom_text="", semester=3)
    assert controller.get_roadmap(profile.id).career_id == "ai_developer"


def test_invalid_inputs_are_rejected(db_path):
    controller = WorkflowController(db_path)
    profile = controller.open_profile("Asha")
    assert (
        controller.select_career(
            profile.id, career_id="devops_engineer", custom_text="", semester=2
        ).status
        == "invalid_input"
    )
    assert (
        controller.select_career(profile.id, career_id="nope", custom_text="", semester=3).status
        == "invalid_input"
    )
    with pytest.raises(PccError):
        controller.open_profile("   ")
    with pytest.raises(PccError):
        controller.open_profile("x" * 41)
