"""Orchestrates the student journey. UI calls this; it calls agents, content and persistence.

Scope so far: profiles, career selection, roadmap (M2); skills check and results (M3);
coaching plan (M4).
"""

import secrets
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import Literal

from pcc.agents.coaching_agent import generate_coaching_plan
from pcc.agents.evaluation_agent import (
    evaluate,
    present,
    select_questions,
    shuffled_option_order,
)
from pcc.agents.roadmap_agent import generate_roadmap
from pcc.ai.ai_client import AiClient
from pcc.ai.ai_client_factory import build_ai_client
from pcc.ai.mock_ai_client import MockAiClient
from pcc.content.content_loader import (
    AppSettings,
    compute_skill_assessability,
    load_app_settings,
    load_careers,
    load_question_bank,
    load_roadmap_template,
    load_skills,
)
from pcc.core.constants import SEMESTERS
from pcc.core.exceptions import PccError
from pcc.domain.career_resolver import resolve_career
from pcc.domain.enums import WorkflowState, is_quiz_assessable
from pcc.domain.schemas.assessment_schemas import (
    Answer,
    AssessmentScope,
    AssessmentSession,
    EvaluationResult,
)
from pcc.domain.schemas.career_schemas import Career
from pcc.domain.schemas.coaching_schemas import (
    CoachingInput,
    CoachingPlan,
    CoachingPlanView,
    MissedQuestion,
)
from pcc.domain.schemas.question_schemas import Question
from pcc.domain.schemas.roadmap_schemas import Roadmap, Skill
from pcc.persistence.database import get_connection, init_schema
from pcc.persistence.repositories.ai_provider_settings_repository import get_active_config
from pcc.persistence.repositories.assessment_repository import (
    AttemptRecord,
    create_attempt,
    get_attempt,
    get_latest_submitted_attempt,
    get_open_attempt,
    load_answers,
    save_submission,
    seen_question_ids_oldest_first,
)
from pcc.persistence.repositories.coaching_repository import get_active_plan, save_active_plan
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

    # --- skills check (M3) ------------------------------------------------------------------
    def _check_context(self, conn: sqlite3.Connection, profile_id: int) -> "_CheckContext":
        profile = get_profile(conn, profile_id)
        if profile is None or not profile.career_id or not profile.current_semester:
            raise PccError("Choose a career and semester first.")
        roadmap = get_active_roadmap(conn, profile_id)
        if roadmap is None:
            raise PccError("Build your roadmap first.")
        months = sorted(roadmap.months, key=lambda m: m.month_index)
        return _CheckContext(
            profile=profile,
            skills_by_id={
                s.skill_id: s for s in load_skills() if profile.career_id in s.career_ids
            },
            roadmap_order=roadmap.skill_ids_in_order(),
            semester_skill_ids={
                sem: [m.skill_id for m in months if m.semester == sem] for sem in SEMESTERS
            },
            bank=load_question_bank(profile.career_id),
        )

    @staticmethod
    def _scope(ctx: "_CheckContext", settings: AppSettings) -> AssessmentScope:
        semester = ctx.profile.current_semester or 3
        ready: list[str] = []
        later: list[str] = []
        soon: list[str] = []
        for skill_id in ctx.semester_skill_ids[semester]:
            if not is_quiz_assessable(ctx.skills_by_id[skill_id].skill_type):
                later.append(skill_id)  # T-21: method not built, never scored
            elif not compute_skill_assessability(skill_id, ctx.bank, settings):
                soon.append(skill_id)  # T-22: bank too thin
            else:
                ready.append(skill_id)
        return AssessmentScope(
            semester=semester,
            assessable_skill_ids=ready,
            assessed_later_skill_ids=later,
            coming_soon_skill_ids=soon,
        )

    def get_assessment_scope(self, profile_id: int) -> AssessmentScope:
        with closing(self._connect()) as conn:
            ctx = self._check_context(conn, profile_id)
        return self._scope(ctx, load_app_settings())

    @staticmethod
    def _questions_for(
        ctx: "_CheckContext", attempt: AttemptRecord, seen: list[str]
    ) -> tuple[AppSettings, AssessmentScope, list[Question]]:
        settings = AppSettings.model_validate_json(attempt.config_snapshot_json)
        scope = WorkflowController._scope(ctx, settings)
        questions = select_questions(
            scope.assessable_skill_ids, ctx.bank, settings, seen, attempt.shuffle_seed
        )
        return settings, scope, questions

    def start_assessment(self, profile_id: int) -> AssessmentSession:
        """Starts a baseline check, or resumes the open one (same seed -> same questions)."""
        with closing(self._connect()) as conn:
            ctx = self._check_context(conn, profile_id)
            attempt = get_open_attempt(conn, profile_id)
            if attempt is None:
                settings = load_app_settings()
                scope = self._scope(ctx, settings)
                if not scope.assessable_skill_ids:
                    raise PccError(
                        "Assessment coming soon: no skill in this semester has a reviewed "
                        "question bank yet."
                    )
                assert_transition(ctx.profile.workflow_state, WorkflowState.ASSESSMENT_IN_PROGRESS)
                attempt_id = create_attempt(
                    conn,
                    profile_id,
                    attempt_type="baseline",
                    scope_description=f"Semester {scope.semester} skills",
                    shuffle_seed=secrets.randbits(31),
                    config_snapshot_json=settings.model_dump_json(),
                )
                set_workflow_state(conn, profile_id, WorkflowState.ASSESSMENT_IN_PROGRESS)
                conn.commit()
                attempt = get_attempt(conn, attempt_id)
                assert attempt is not None
            seen = seen_question_ids_oldest_first(conn, profile_id)
            _, _, questions = self._questions_for(ctx, attempt, seen)
        return AssessmentSession(
            attempt_id=attempt.id,
            scope_description=attempt.scope_description,
            questions=present(questions, ctx.skills_by_id, attempt.shuffle_seed),
        )

    @staticmethod
    def _evaluate(
        ctx: "_CheckContext",
        attempt: AttemptRecord,
        answers: list[Answer],
        settings: AppSettings,
        scope: AssessmentScope,
    ) -> EvaluationResult:
        return evaluate(
            attempt_id=attempt.id,
            scope_description=attempt.scope_description,
            answers=answers,
            questions_by_id={q.question_id: q for q in ctx.bank},
            scope_skill_ids=scope.assessable_skill_ids,
            core_skill_ids=[
                s.skill_id for s in ctx.skills_by_id.values() if is_quiz_assessable(s.skill_type)
            ],
            roadmap_order=ctx.roadmap_order,
            current_semester=ctx.profile.current_semester or 3,
            semester_skill_ids=ctx.semester_skill_ids,
            settings=settings,
        )

    def submit_assessment(
        self, profile_id: int, attempt_id: int, selections: dict[str, str | None]
    ) -> EvaluationResult:
        """Grades by code. Every presented question must be answered (FR-05)."""
        with closing(self._connect()) as conn:
            ctx = self._check_context(conn, profile_id)
            attempt = get_attempt(conn, attempt_id)
            if attempt is None or attempt.profile_id != profile_id or attempt.submitted:
                raise PccError("This check is not open for submission.")
            seen = seen_question_ids_oldest_first(conn, profile_id)
            settings, scope, questions = self._questions_for(ctx, attempt, seen)

            expected = {q.question_id: q for q in questions}
            if set(selections) != set(expected) or any(v is None for v in selections.values()):
                raise PccError("Answer every question before submitting.")
            answers = []
            for qid in expected:  # presentation order
                option_id = str(selections[qid])
                if option_id not in {o.option_id for o in expected[qid].options}:
                    raise PccError("An answer does not match the question's options.")
                answers.append(Answer(question_id=qid, selected_option_id=option_id))

            result = self._evaluate(ctx, attempt, answers, settings, scope)
            save_submission(
                conn,
                attempt_id,
                answers=answers,
                correct_by_question={
                    a.question_id: a.selected_option_id == expected[a.question_id].correct_option_id
                    for a in answers
                },
                displayed_order_by_question={
                    qid: shuffled_option_order(q, attempt.shuffle_seed)
                    for qid, q in expected.items()
                },
                result=result,
            )
            set_workflow_state(conn, profile_id, WorkflowState.RESULTS_READY)
            if result.weakest.status == "weakest_found" and result.weakest.skill_id:
                plan = self._coach(conn, ctx, result, settings)
                save_active_plan(conn, profile_id, attempt_id, plan)
                assert_transition(WorkflowState.RESULTS_READY, WorkflowState.COACHING_READY)
                set_workflow_state(conn, profile_id, WorkflowState.COACHING_READY)
            conn.commit()
        return result

    # --- coaching (M4) ------------------------------------------------------------------------
    def _coach(
        self,
        conn: sqlite3.Connection,
        ctx: "_CheckContext",
        result: EvaluationResult,
        settings: AppSettings,
    ) -> CoachingPlan:
        """Coaching receives the computed weakest skill; it can never pick or change it."""
        skill = ctx.skills_by_id[str(result.weakest.skill_id)]
        tags = {q.question_id: q.concept_tag for q in ctx.bank}
        career = next(c for c in load_careers() if c.career_id == ctx.profile.career_id)
        context = CoachingInput(
            career_name=career.name,
            skill_id=skill.skill_id,
            skill_name=skill.name,
            level=result.level.value,
            missed=[
                MissedQuestion(
                    question_id=r.question_id,
                    concept_tag=tags[r.question_id],
                    stem=r.stem,
                    selected_option_text=r.selected_option_text,
                    correct_option_text=r.correct_option_text,
                    explanation=r.explanation,
                )
                for r in result.reviews
                if r.skill_id == skill.skill_id and not r.is_correct
            ],
            practice_templates=skill.practice_templates,
            max_total_minutes=settings.weekly_plan.max_total_minutes,
            retest_after_days=settings.retest_after_days,
        )
        return generate_coaching_plan(context, self._resolve_ai_client(conn)).plan

    def get_coaching_plan(self, profile_id: int) -> CoachingPlanView | None:
        with closing(self._connect()) as conn:
            plan = get_active_plan(conn, profile_id)
            if plan is None:
                return None
            ctx = self._check_context(conn, profile_id)
        return CoachingPlanView(
            plan=plan,
            skill_name=ctx.skills_by_id[plan.skill_id].name,
            question_stems={q.question_id: q.stem for q in ctx.bank},
        )

    def get_latest_results(self, profile_id: int) -> EvaluationResult | None:
        """Re-derives results from stored answers + the attempt's config snapshot (T-18, T-20)."""
        with closing(self._connect()) as conn:
            attempt = get_latest_submitted_attempt(conn, profile_id)
            if attempt is None:
                return None
            ctx = self._check_context(conn, profile_id)
            settings = AppSettings.model_validate_json(attempt.config_snapshot_json)
            answers = load_answers(conn, attempt.id)
        scope = self._scope(ctx, settings)
        return self._evaluate(ctx, attempt, answers, settings, scope)


@dataclass(frozen=True)
class _CheckContext:
    profile: Profile
    skills_by_id: dict[str, Skill]
    roadmap_order: list[str]
    semester_skill_ids: dict[int, list[str]]
    bank: list[Question]


def get_controller() -> WorkflowController:
    from pcc.core.config import settings

    return WorkflowController(settings.db_path)
