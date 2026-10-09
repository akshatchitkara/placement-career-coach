"""Orchestrates the student journey. UI calls this; it calls agents, content and persistence.

M2 scope: profiles, career selection, roadmap generation and restore.
"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import Literal

from pcc.agents.roadmap_agent import generate_roadmap
from pcc.ai.ai_client import AiClient
from pcc.ai.ai_client_factory import build_ai_client
from pcc.ai.mock_ai_client import MockAiClient
from pcc.content.content_loader import load_careers, load_roadmap_template, load_skills
from pcc.core.constants import SEMESTERS
from pcc.core.exceptions import PccError
from pcc.domain.career_resolver import resolve_career
from pcc.domain.enums import WorkflowState
from pcc.domain.schemas.career_schemas import Career
from pcc.domain.schemas.roadmap_schemas import Roadmap
from pcc.persistence.database import get_connection, init_schema
from pcc.persistence.repositories.ai_provider_settings_repository import get_active_config
from pcc.persistence.repositories.profile_repository import (
    Profile,
    get_or_create_profile,
    get_profile,
    list_profiles,
    set_workflow_state,
    update_career_and_state,
)
from pcc.persistence.repositories.roadmap_repository import (
    get_active_roadmap,
    save_active_roadmap,
)
from pcc.workflow.workflow_transitions import assert_transition

MAX_DISPLAY_NAME_LENGTH = 40


@dataclass(frozen=True)
class CareerSelectionResult:
    status: Literal["roadmap_ready", "unsupported", "invalid_input"]
    message: str = ""
    roadmap: Roadmap | None = None


class WorkflowController:
    def __init__(self, db_path: str, ai_client: AiClient | None = None) -> None:
        self._db_path = db_path
        self._ai_client = ai_client  # None -> resolved from saved provider settings per call
        with closing(self._connect()) as conn:
            init_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def _resolve_ai_client(self, conn: sqlite3.Connection) -> AiClient | None:
        client = self._ai_client or build_ai_client(get_active_config(conn))
        return None if isinstance(client, MockAiClient) else client

    # --- profiles -------------------------------------------------------------------------
    def open_profile(self, display_name: str) -> Profile:
        name = " ".join(display_name.split())
        if not name or len(name) > MAX_DISPLAY_NAME_LENGTH:
            raise PccError(f"Display name must be 1-{MAX_DISPLAY_NAME_LENGTH} characters.")
        with closing(self._connect()) as conn:
            return get_or_create_profile(conn, name)

    def list_profiles(self) -> list[Profile]:
        with closing(self._connect()) as conn:
            return list_profiles(conn)

    def get_profile(self, profile_id: int) -> Profile | None:
        with closing(self._connect()) as conn:
            return get_profile(conn, profile_id)

    # --- careers & roadmap ------------------------------------------------------------------
    def list_careers(self) -> list[Career]:
        return load_careers()

    def get_roadmap(self, profile_id: int) -> Roadmap | None:
        with closing(self._connect()) as conn:
            return get_active_roadmap(conn, profile_id)

    def select_career(
        self, profile_id: int, *, career_id: str | None, custom_text: str, semester: int
    ) -> CareerSelectionResult:
        """Pick a catalog career (career_id) or type one (custom_text); builds the roadmap."""
        if semester not in SEMESTERS:
            return CareerSelectionResult("invalid_input", "Semester must be 3, 4, 5 or 6.")
        careers = load_careers()
        if career_id is not None:
            career = next((c for c in careers if c.career_id == career_id), None)
            if career is None:
                return CareerSelectionResult("invalid_input", "Unknown career.")
        else:
            resolution = resolve_career(custom_text, careers)
            if resolution.career is None:
                return CareerSelectionResult(resolution.status, resolution.message)  # type: ignore[arg-type]
            career = resolution.career

        with closing(self._connect()) as conn:
            profile = get_profile(conn, profile_id)
            if profile is None:
                raise PccError("Profile not found.")
            assert_transition(profile.workflow_state, WorkflowState.CAREER_SELECTED)

            catalog_ids = {s.skill_id for s in load_skills() if career.career_id in s.career_ids}
            result = generate_roadmap(
                career.name,
                load_roadmap_template(career.career_id),
                catalog_ids,
                self._resolve_ai_client(conn),
            )
            # Roadmap is validated (or the template) before anything is saved.
            save_active_roadmap(conn, profile_id, result.roadmap)
            update_career_and_state(
                conn,
                profile_id,
                career_id=career.career_id,
                semester=semester,
                state=WorkflowState.CAREER_SELECTED,
            )
            set_workflow_state(conn, profile_id, WorkflowState.ROADMAP_READY)
            conn.commit()
        return CareerSelectionResult("roadmap_ready", result.message, result.roadmap)


def get_controller() -> WorkflowController:
    from pcc.core.config import settings

    return WorkflowController(settings.db_path)
