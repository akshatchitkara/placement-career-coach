"""Seeds the three demo profiles (blueprint Section 11.3) through the real controller.

Going through the controller (not raw SQL) means the demo data is exactly what a student
would have produced: same scoring, plans and state. The clock is moved back so the
attempts carry plausible dates.
"""

from datetime import date, timedelta

from pcc.content.content_loader import load_question_bank
from pcc.domain.schemas.assessment_schemas import AssessmentSession
from pcc.domain.schemas.question_schemas import Question
from pcc.workflow.workflow_controller import WorkflowController

DEMO_NAMES = ("Asha", "Ravi", "Meera")
_CAREER = "devops_engineer"
_SEMESTER = 3
_SKILLS = ("linux_fundamentals", "shell_scripting", "python_for_automation", "git_version_control")

# Section 10.7 worked example: Linux and Shell 1/3, Python and Git 2/3 -> 50.0, Intermediate.
RAVI_BASELINE = dict(zip(_SKILLS, (1, 1, 2, 2), strict=True))
MEERA_BASELINE = RAVI_BASELINE
MEERA_RECHECK = dict(zip(_SKILLS, (3, 3, 3, 2), strict=True))


class _Clock:
    def __init__(self, today: date) -> None:
        self.today = today

    def __call__(self) -> date:
        return self.today


def _answers(
    session: AssessmentSession, correct_per_skill: dict[str, int], bank: dict[str, Question]
) -> dict[str, str | None]:
    """Picks the first N questions of each skill correctly and the rest wrongly."""
    seen: dict[str, int] = {}
    selections: dict[str, str | None] = {}
    for question in session.questions:
        n = seen.get(question.skill_id, 0)
        seen[question.skill_id] = n + 1
        right = bank[question.question_id].correct_option_id
        want_correct = n < correct_per_skill[question.skill_id]
        selections[question.question_id] = next(
            o.option_id for o in question.options if (o.option_id == right) == want_correct
        )
    return selections


def _take_check(controller: WorkflowController, profile_id: int, correct: dict[str, int]) -> None:
    bank = {q.question_id: q for q in load_question_bank(_CAREER)}
    session = controller.start_assessment(profile_id)
    controller.submit_assessment(profile_id, session.attempt_id, _answers(session, correct, bank))


def _pass_modules(controller: WorkflowController, profile_id: int, count: int) -> None:
    """Passes the first `count` modules through the real quiz, so the road shows progress."""
    bank = {q.question_id: q for q in load_question_bank(_CAREER)}
    roadmap = controller.get_roadmap(profile_id)
    assert roadmap is not None
    for skill_id in roadmap.skill_ids_in_order()[:count]:
        quiz = controller.get_module_quiz(profile_id, skill_id)
        picks = {q.question_id: bank[q.question_id].correct_option_id for q in quiz}
        controller.grade_module_quiz(profile_id, skill_id, picks)


def seed_demo_profiles(db_path: str, today: date) -> None:
    """Creates Asha (new), Ravi (one baseline) and Meera (baseline then improved re-check)."""
    clock = _Clock(today)
    controller = WorkflowController(db_path, today=clock)

    controller.open_profile("Asha")  # nothing else: the demo starts from "pick a career"

    ravi = controller.open_profile("Ravi")
    controller.select_career(ravi.id, career_id=_CAREER, custom_text="", semester=_SEMESTER)
    clock.today = today - timedelta(days=1)
    _take_check(controller, ravi.id, RAVI_BASELINE)

    clock.today = today - timedelta(days=10)
    meera = controller.open_profile("Meera")
    controller.select_career(meera.id, career_id=_CAREER, custom_text="", semester=_SEMESTER)
    _take_check(controller, meera.id, MEERA_BASELINE)
    clock.today = today - timedelta(days=3)
    _take_check(controller, meera.id, MEERA_RECHECK)

    clock.today = today
    _pass_modules(controller, ravi.id, 1)
    _pass_modules(controller, meera.id, 3)
    controller.sync_state(ravi.id)
    controller.sync_state(meera.id)
