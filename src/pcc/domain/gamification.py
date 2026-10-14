"""XP, ranks and badges. Pure rules, derived from what the student has actually done.

Nothing here is stored: the same inputs always give the same XP and badges, so the numbers
can never drift from the real data. Games never touch scoring or levels; they only reward
effort that is already recorded (module quizzes passed, checks taken, weekly tasks ticked).
"""

from pydantic import BaseModel

XP_MODULE_PASSED = 50
XP_CHECK_COMPLETED = 100
XP_TASK_DONE = 10
XP_IMPROVEMENT = 50

MODULE_QUIZ_QUESTIONS = 3
MODULE_QUIZ_PASS = 2  # of 3

# (rank name, XP needed). Ascending; the first is the starting rank.
RANKS: tuple[tuple[str, int], ...] = (
    ("Rookie", 0),
    ("Explorer", 100),
    ("Builder", 300),
    ("Pro", 600),
    ("Industry-ready", 900),
)

_MONTHS_PER_SEMESTER = 4


class Activity(BaseModel):
    """Everything XP and badges are computed from."""

    modules_passed: int = 0
    semesters_completed: int = 0  # semesters whose modules have all been passed
    checks_completed: int = 0
    tasks_done: int = 0
    improved: bool = False  # a later check of the same scope scored higher
    full_path_done: bool = False


class Badge(BaseModel):
    key: str
    name: str
    description: str
    earned: bool


class GameState(BaseModel):
    xp: int
    rank: str
    next_rank: str | None
    xp_to_next: int  # 0 at the top rank
    rank_progress: float  # 0..1 within the current rank band
    badges: list[Badge]

    @property
    def earned_badges(self) -> list[Badge]:
        return [b for b in self.badges if b.earned]


def compute_xp(activity: Activity) -> int:
    return (
        activity.modules_passed * XP_MODULE_PASSED
        + activity.checks_completed * XP_CHECK_COMPLETED
        + activity.tasks_done * XP_TASK_DONE
        + (XP_IMPROVEMENT if activity.improved else 0)
    )


def rank_for(xp: int) -> tuple[str, str | None, int, float]:
    """(rank, next rank or None, XP still needed, progress within the band)."""
    index = max(i for i, (_, need) in enumerate(RANKS) if xp >= need)
    name, floor = RANKS[index]
    if index == len(RANKS) - 1:
        return name, None, 0, 1.0
    next_name, ceiling = RANKS[index + 1]
    return name, next_name, ceiling - xp, (xp - floor) / (ceiling - floor)


def semesters_completed(passed_by_semester: dict[int, int]) -> int:
    """How many semesters have every one of their modules passed."""
    return sum(1 for n in passed_by_semester.values() if n >= _MONTHS_PER_SEMESTER)


def _badges(a: Activity) -> list[Badge]:
    return [
        Badge(
            key="first_module",
            name="First step",
            description="Pass your first module quiz.",
            earned=a.modules_passed >= 1,
        ),
        Badge(
            key="first_check",
            name="Know your level",
            description="Complete a skills check.",
            earned=a.checks_completed >= 1,
        ),
        Badge(
            key="semester",
            name="Semester cleared",
            description="Pass every module of a semester.",
            earned=a.semesters_completed >= 1,
        ),
        Badge(
            key="improver",
            name="Improver",
            description="Score higher on a re-check than before.",
            earned=a.improved,
        ),
        Badge(
            key="full_path",
            name="Whole road",
            description="Complete the full-path check.",
            earned=a.full_path_done,
        ),
        Badge(
            key="doer",
            name="Doer",
            description="Tick off 10 weekly-plan tasks.",
            earned=a.tasks_done >= 10,
        ),
    ]


def game_state(activity: Activity) -> GameState:
    xp = compute_xp(activity)
    rank, next_rank, to_next, progress = rank_for(xp)
    return GameState(
        xp=xp,
        rank=rank,
        next_rank=next_rank,
        xp_to_next=to_next,
        rank_progress=progress,
        badges=_badges(activity),
    )
