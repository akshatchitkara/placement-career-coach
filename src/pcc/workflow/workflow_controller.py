"""Orchestrates the student journey. UI calls this; it calls agents, content and persistence.

Scope so far: profiles, career selection, roadmap (M2); skills check and results (M3);
coaching plan (M4); weekly plan, re-checks and progress (M5).
"""

import secrets
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from pcc.agents.coaching_agent import generate_coaching_plan
from pcc.agents.evaluation_agent import (
    evaluate,
    present,
    select_questions,
    shuffled_option_order,
)
from pcc.agents.roadmap_agent import generate_roadmap
from pcc.agents.tutor_agent import tutor_reply
from pcc.ai.ai_client import AiClient
from pcc.ai.ai_client_factory import build_ai_client
from pcc.ai.mock_ai_client import MockAiClient
from pcc.ai.provider_config import AiStatus, resolve_provider_config
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
from pcc.domain.progress import AttemptSummary, ProgressView, build_progress
from pcc.domain.schemas.assessment_schemas import (
    Answer,
    AssessmentScope,
    AssessmentSession,
    EvaluationResult,
    PresentedQuestion,
)
from pcc.domain.schemas.career_schemas import Career
from pcc.domain.schemas.coaching_schemas import (
    CoachingInput,
    CoachingPlan,
    CoachingPlanView,
    CoachingTask,
    MissedQuestion,
)
from pcc.domain.schemas.question_schemas import Question
from pcc.domain.schemas.roadmap_schemas import Roadmap, RoadmapMonth, Skill
from pcc.domain.schemas.tutor_schemas import (
    MAX_STUDENT_MESSAGES_PER_TASK,
    MAX_STUDENT_TEXT,
    PracticeQuestionResult,
    TutorContext,
    TutorKind,
    TutorMessage,
    TutorReply,
)
from pcc.domain.schemas.weekly_plan_schemas import (
    RoadmapFocus,
    WeeklyPlanConfig,
    WeeklyPlanContext,
    WeeklyPlanView,
)
from pcc.domain.weekly_plan_builder import build_weekly_plan
from pcc.persistence.database import get_connection, init_schema
from pcc.persistence.repositories.ai_provider_settings_repository import get_saved_config
from pcc.persistence.repositories.assessment_repository import (
    AttemptRecord,
    create_attempt,
    get_attempt,
    get_latest_submitted_attempt,
    get_open_attempt,
    list_submitted_attempts,
    load_answers,
    save_submission,
    seen_question_ids_oldest_first,
)
from pcc.persistence.repositories.coaching_repository import (
    add_message,
    get_active_plan,
    get_active_plan_id,
    list_messages,
    save_active_plan,
)
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
from pcc.persistence.repositories.weekly_plan_repository import (
    get_latest_weekly_plan,
    save_weekly_plan,
    set_done_task_ids,
)
from pcc.workflow.workflow_transitions import assert_transition

MAX_DISPLAY_NAME_LENGTH = 40


@dataclass(frozen=True)
class CareerSelectionResult:
    status: Literal["roadmap_ready", "unsupported", "invalid_input"]
    message: str = ""
    roadmap: Roadmap | None = None


class WorkflowController:
    def __init__(
        self,
        db_path: str,
        ai_client: AiClient | None = None,
        today: Callable[[], date] | None = None,
    ) -> None:
        self._db_path = db_path
        self._today = today or (lambda: datetime.now(UTC).date())  # injectable for tests
        self._ai_client = ai_client  # None -> resolved from saved provider settings per call
        with closing(self._connect()) as conn:
            init_schema(conn)

    def _now_iso(self) -> str:
        """Timestamp on the controller's clock, so seeded or test data carries sensible dates."""
        return datetime.combine(self._today(), datetime.now(UTC).time(), tzinfo=UTC).isoformat()

    def _connect(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    def _resolve_ai(self, conn: sqlite3.Connection) -> tuple[AiClient | None, AiStatus]:
        """The live client (None when offline) and what to tell the student about it."""
        if self._ai_client is not None:  # injected (tests); always treated as live
            return self._ai_client, AiStatus(offline=False, label="AI: live")
        from pcc.core.config import settings

        config, warning = resolve_provider_config(
            get_saved_config(conn),
            env_mode=settings.ai_mode,
            env_api_key=settings.ai_api_key,
            env_model_name=settings.ai_model_name,
            env_timeout_seconds=settings.ai_timeout_seconds,
        )
        client = build_ai_client(config)
        if isinstance(client, MockAiClient):
            if config.provider_type != "mock" and not warning:
                warning = "The configured AI provider could not be set up."
            return None, AiStatus(
                offline=True, label="Offline mode: curated roadmaps and coaching", warning=warning
            )
        return client, AiStatus(offline=False, label=f"AI: {config.provider_type} (live)")

    def _resolve_ai_client(self, conn: sqlite3.Connection) -> AiClient | None:
        return self._resolve_ai(conn)[0]

    def get_ai_status(self) -> AiStatus:
        with closing(self._connect()) as conn:
            return self._resolve_ai(conn)[1]

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

    def last_active_profile(self) -> Profile | None:
        """The most recently active profile: a local single-user app reopens where you left off."""
        profiles = self.list_profiles()
        return profiles[0] if profiles else None

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
            months_by_skill={m.skill_id: m for m in months},
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

    def checkable_semesters(self, career_id: str) -> list[int]:
        """Semesters of this career that already have a reviewed question bank to check against."""
        settings = load_app_settings()
        skills = {s.skill_id: s for s in load_skills()}
        bank = load_question_bank(career_id)
        template = load_roadmap_template(career_id)
        return [
            sem
            for sem in SEMESTERS
            if any(
                is_quiz_assessable(skills[m.skill_id].skill_type)
                and compute_skill_assessability(m.skill_id, bank, settings)
                for m in template.months
                if m.semester == sem
            )
        ]

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
        """Starts a baseline check or a re-check, or resumes the open one.

        Resuming re-selects from the stored seed, so the same questions come back.
        """
        self.sync_state(profile_id)
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
                state = ctx.profile.workflow_state
                if state == WorkflowState.ROADMAP_READY:
                    attempt_type = "baseline"
                elif state in (WorkflowState.WEEKLY_PLAN_ACTIVE, WorkflowState.RETEST_DUE):
                    attempt_type = "retest"
                    if state == WorkflowState.WEEKLY_PLAN_ACTIVE:  # re-checking before the due date
                        assert_transition(state, WorkflowState.RETEST_DUE)
                        state = WorkflowState.RETEST_DUE
                else:
                    raise PccError("A check cannot be started right now.")
                assert_transition(state, WorkflowState.ASSESSMENT_IN_PROGRESS)
                attempt_id = create_attempt(
                    conn,
                    profile_id,
                    attempt_type=attempt_type,
                    scope_description=f"Semester {scope.semester} skills",
                    shuffle_seed=secrets.randbits(31),
                    config_snapshot_json=settings.model_dump_json(),
                    started_at=self._now_iso(),
                )
                set_workflow_state(conn, profile_id, WorkflowState.ASSESSMENT_IN_PROGRESS)
                conn.commit()
                attempt = get_attempt(conn, attempt_id)
                assert attempt is not None
            seen = seen_question_ids_oldest_first(conn, profile_id)
            _, _, questions = self._questions_for(ctx, attempt, seen)
        return AssessmentSession(
            attempt_id=attempt.id,
            attempt_type=attempt.attempt_type,
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
            attempt_type=attempt.attempt_type,
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
                submitted_at=self._now_iso(),
            )
            set_workflow_state(conn, profile_id, WorkflowState.RESULTS_READY)
            if result.weakest.status == "weakest_found" and result.weakest.skill_id:
                plan = self._coach(conn, ctx, result, settings)
                save_active_plan(conn, profile_id, attempt_id, plan)
                assert_transition(WorkflowState.RESULTS_READY, WorkflowState.COACHING_READY)
                set_workflow_state(conn, profile_id, WorkflowState.COACHING_READY)
            self._plan_week(conn, ctx, attempt_id, result, settings)
            conn.commit()
        return result

    # --- weekly loop (M5) ---------------------------------------------------------------------
    def _plan_week(
        self,
        conn: sqlite3.Connection,
        ctx: "_CheckContext",
        attempt_id: int,
        result: EvaluationResult,
        settings: AppSettings,
    ) -> None:
        """Builds and saves this week's plan by rules, then moves to WEEKLY_PLAN_ACTIVE."""
        profile_id = ctx.profile.id
        weakest = result.weakest
        focus_skill_id: str | None = None
        if weakest.status == "no_major_gap":
            focus_skill_id = weakest.next_roadmap_skill_id
        elif weakest.status == "insufficient_evidence":
            focus_skill_id = result.position.skill_id
        month = ctx.months_by_skill.get(focus_skill_id or "")
        focus = (
            RoadmapFocus(
                skill_id=month.skill_id,
                skill_name=ctx.skills_by_id[month.skill_id].name,
                topics=month.topics,
                deliverable=month.deliverable,
            )
            if month
            else None
        )
        tags = {q.question_id: q.concept_tag for q in ctx.bank}
        missed: dict[str, list[str]] = {}
        for review in result.reviews:
            if not review.is_correct:
                bucket = missed.setdefault(review.skill_id, [])
                if tags[review.question_id] not in bucket:
                    bucket.append(tags[review.question_id])

        plan = build_weekly_plan(
            WeeklyPlanContext(
                today=self._today(),
                weakest=weakest,
                coaching_plan=get_active_plan(conn, profile_id)
                if weakest.status == "weakest_found"
                else None,
                skill_scores=result.skill_scores,
                skill_names={sid: s.name for sid, s in ctx.skills_by_id.items()},
                missed_concepts_by_skill=missed,
                roadmap_focus=focus,
                mastery_threshold=settings.mastery_threshold,
            ),
            WeeklyPlanConfig(
                min_tasks=settings.weekly_plan.min_tasks,
                max_tasks=settings.weekly_plan.max_tasks,
                max_total_minutes=settings.weekly_plan.max_total_minutes,
                retest_after_days=settings.retest_after_days,
            ),
        )
        save_weekly_plan(conn, profile_id, attempt_id, plan)
        current = get_profile(conn, profile_id)
        assert current is not None
        assert_transition(current.workflow_state, WorkflowState.WEEKLY_PLAN_ACTIVE)
        set_workflow_state(conn, profile_id, WorkflowState.WEEKLY_PLAN_ACTIVE)

    def sync_state(self, profile_id: int) -> None:
        """Keeps stored state honest: completes a missing weekly plan, flags a due re-check.

        Safe to call on every page load. The first part repairs profiles saved before the
        weekly plan existed (they stopped at RESULTS_READY or COACHING_READY).
        """
        with closing(self._connect()) as conn:
            profile = get_profile(conn, profile_id)
            if profile is None or not profile.career_id:
                return
            if profile.workflow_state in (
                WorkflowState.RESULTS_READY,
                WorkflowState.COACHING_READY,
            ):
                attempt = get_latest_submitted_attempt(conn, profile_id)
                if attempt is not None:
                    ctx = self._check_context(conn, profile_id)
                    settings = AppSettings.model_validate_json(attempt.config_snapshot_json)
                    answers = load_answers(conn, attempt.id)
                    result = self._evaluate(
                        ctx, attempt, answers, settings, self._scope(ctx, settings)
                    )
                    self._plan_week(conn, ctx, attempt.id, result, settings)
                    conn.commit()
                    profile = get_profile(conn, profile_id)
                    assert profile is not None
            if profile.workflow_state == WorkflowState.WEEKLY_PLAN_ACTIVE:
                latest = get_latest_weekly_plan(conn, profile_id)
                if latest is not None and self._today() >= latest[1].retest_due_date:
                    assert_transition(profile.workflow_state, WorkflowState.RETEST_DUE)
                    set_workflow_state(conn, profile_id, WorkflowState.RETEST_DUE)
                    conn.commit()

    def get_weekly_plan(self, profile_id: int) -> WeeklyPlanView | None:
        self.sync_state(profile_id)
        with closing(self._connect()) as conn:
            latest = get_latest_weekly_plan(conn, profile_id)
        if latest is None:
            return None
        plan_id, plan, done = latest
        days_left = max((plan.retest_due_date - self._today()).days, 0)
        return WeeklyPlanView(
            plan_id=plan_id,
            plan=plan,
            done_task_ids=done,
            retest_due=days_left == 0,
            days_until_retest=days_left,
        )

    def set_task_done(self, profile_id: int, plan_id: int, task_id: str, done: bool) -> None:
        with closing(self._connect()) as conn:
            latest = get_latest_weekly_plan(conn, profile_id)
            if latest is None or latest[0] != plan_id:
                raise PccError("That weekly plan is no longer current.")
            if task_id not in {t.task_id for t in latest[1].tasks}:
                raise PccError("Unknown task.")
            ids = set(latest[2])
            if done:
                ids.add(task_id)
            else:
                ids.discard(task_id)
            set_done_task_ids(conn, plan_id, sorted(ids))
            conn.commit()

    def get_progress(self, profile_id: int) -> ProgressView:
        """Every submitted check, re-derived from its own snapshot, plus latest-vs-previous."""
        with closing(self._connect()) as conn:
            records = list_submitted_attempts(conn, profile_id)
            if not records:
                return build_progress([], 60)
            ctx = self._check_context(conn, profile_id)
            summaries = []
            for record in records:
                settings = AppSettings.model_validate_json(record.config_snapshot_json)
                result = self._evaluate(
                    ctx,
                    record,
                    load_answers(conn, record.id),
                    settings,
                    self._scope(ctx, settings),
                )
                summaries.append(
                    AttemptSummary(
                        attempt_id=record.id,
                        attempt_type=record.attempt_type,
                        submitted_at=record.submitted_at or "",
                        overall_score=result.overall_score,
                        level=result.level,
                        skill_scores=result.skill_scores,
                    )
                )
            latest_settings = AppSettings.model_validate_json(records[-1].config_snapshot_json)
        return build_progress(summaries, latest_settings.mastery_threshold)

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

    # --- coaching tutor (P5) ------------------------------------------------------------------
    _STUDENT_LABELS = {
        "explain_differently": "Explain it differently",
        "example": "Show me an example",
    }

    def _tutor_task(
        self, conn: sqlite3.Connection, profile_id: int, task_order: int
    ) -> tuple[CoachingPlan, int, CoachingTask]:
        plan = get_active_plan(conn, profile_id)
        plan_id = get_active_plan_id(conn, profile_id)
        task = next((t for t in plan.tasks if t.order == task_order), None) if plan else None
        if plan is None or plan_id is None or task is None:
            raise PccError("That coaching task was not found.")
        return plan, plan_id, task

    def _missed_for_task(
        self, profile_id: int, skill_id: str, task: CoachingTask
    ) -> list[MissedQuestion]:
        result = self.get_latest_results(profile_id)
        if result is None:
            return []
        with closing(self._connect()) as conn:
            ctx = self._check_context(conn, profile_id)
        tags = {q.question_id: q.concept_tag for q in ctx.bank}
        missed = [
            MissedQuestion(
                question_id=r.question_id,
                concept_tag=tags[r.question_id],
                stem=r.stem,
                selected_option_text=r.selected_option_text,
                correct_option_text=r.correct_option_text,
                explanation=r.explanation,
            )
            for r in result.reviews
            if r.skill_id == skill_id and not r.is_correct
        ]
        about_task = [
            m
            for m in missed
            if m.question_id == task.linked_question_id or m.concept_tag == task.concept_tag
        ]
        return (about_task or missed)[:3]

    def get_tutor_thread(self, profile_id: int, task_order: int) -> list[TutorMessage]:
        with closing(self._connect()) as conn:
            _, plan_id, _ = self._tutor_task(conn, profile_id, task_order)
            return list_messages(conn, plan_id, task_order)

    def ask_tutor(
        self, profile_id: int, task_order: int, kind: TutorKind, text: str = ""
    ) -> TutorReply:
        """One tutor turn on a coaching task. Explains only; scores and plans never change."""
        text = " ".join(text.split())
        if kind == "question" and not text:
            raise PccError("Type your question first.")
        if len(text) > MAX_STUDENT_TEXT:
            raise PccError(f"Keep your question under {MAX_STUDENT_TEXT} characters.")
        with closing(self._connect()) as conn:
            plan, plan_id, task = self._tutor_task(conn, profile_id, task_order)
            history = list_messages(conn, plan_id, task_order)
            if sum(m.role == "student" for m in history) >= MAX_STUDENT_MESSAGES_PER_TASK:
                raise PccError(
                    "You have reached the chat limit for this task. Try the quiz, or move on "
                    "to the next task."
                )
            ctx = self._check_context(conn, profile_id)
            client = self._resolve_ai_client(conn)
        career = next(c for c in load_careers() if c.career_id == ctx.profile.career_id)
        context = TutorContext(
            career_name=career.name,
            skill_name=ctx.skills_by_id[plan.skill_id].name,
            task=task,
            missed=self._missed_for_task(profile_id, plan.skill_id, task),
            history=history,
        )
        reply = tutor_reply(context, kind, text, client)
        source = "ai" if client is not None and not reply.used_fallback else "template"
        with closing(self._connect()) as conn:
            add_message(
                conn,
                profile_id,
                plan_id,
                task_order,
                role="student",
                kind=kind,
                content=text or self._STUDENT_LABELS[kind],
                generation_source="student",
            )
            add_message(
                conn,
                profile_id,
                plan_id,
                task_order,
                role="coach",
                kind=kind,
                content=reply.text,
                generation_source=source,
            )
            conn.commit()
        return reply

    def get_practice_quiz(self, profile_id: int, task_order: int) -> list[PresentedQuestion]:
        """Up to 3 questions on this task's concept, taken only from ones the student has seen.

        Unseen questions are left alone so the re-check stays fresh. Graded by code, not stored.
        """
        with closing(self._connect()) as conn:
            plan, plan_id, task = self._tutor_task(conn, profile_id, task_order)
            ctx = self._check_context(conn, profile_id)
            seen = set(seen_question_ids_oldest_first(conn, profile_id))
        missed_ids = {m.question_id for m in self._missed_for_task(profile_id, plan.skill_id, task)}
        tag = task.concept_tag or next(
            (q.concept_tag for q in ctx.bank if q.question_id == task.linked_question_id), None
        )
        pool = [q for q in ctx.bank if q.skill_id == plan.skill_id and q.question_id in seen]
        pool.sort(
            key=lambda q: (q.question_id not in missed_ids, q.concept_tag != tag, q.question_id)
        )
        return present(pool[:3], ctx.skills_by_id, plan_id * 1000 + task_order)

    def grade_practice_quiz(
        self, profile_id: int, task_order: int, selections: dict[str, str]
    ) -> list[PracticeQuestionResult]:
        quiz = self.get_practice_quiz(profile_id, task_order)
        if not quiz or set(selections) != {q.question_id for q in quiz}:
            raise PccError("Answer every quiz question first.")
        with closing(self._connect()) as conn:
            bank = {q.question_id: q for q in self._check_context(conn, profile_id).bank}
        results = []
        for q in quiz:
            source = bank[q.question_id]
            options = {o.option_id: o.text for o in source.options}
            if selections[q.question_id] not in options:
                raise PccError("Pick one of the listed options.")
            results.append(
                PracticeQuestionResult(
                    question_id=q.question_id,
                    stem=q.stem,
                    selected_option_text=options[selections[q.question_id]],
                    correct_option_text=options[source.correct_option_id],
                    is_correct=selections[q.question_id] == source.correct_option_id,
                    explanation=source.explanation,
                )
            )
        return results

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
    months_by_skill: dict[str, RoadmapMonth]


def get_controller() -> WorkflowController:
    from pcc.core.config import settings

    return WorkflowController(settings.db_path)
