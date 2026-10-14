import pytest

from pcc.domain.gamification import (
    RANKS,
    Activity,
    compute_xp,
    game_state,
    rank_for,
    semesters_completed,
)


def test_xp_is_the_sum_of_recorded_effort():
    a = Activity(modules_passed=2, checks_completed=1, tasks_done=3, improved=True)
    assert compute_xp(a) == 2 * 50 + 100 + 3 * 10 + 50
    assert compute_xp(Activity()) == 0


@pytest.mark.parametrize(
    ("xp", "rank"),
    [(0, "Rookie"), (99, "Rookie"), (100, "Explorer"), (299, "Explorer"), (300, "Builder"),
     (600, "Pro"), (899, "Pro"), (900, "Industry-ready"), (5000, "Industry-ready")],
)  # fmt: skip
def test_rank_boundaries(xp, rank):
    assert rank_for(xp)[0] == rank


def test_progress_inside_a_rank_band_and_at_the_top():
    name, nxt, need, progress = rank_for(150)
    assert (name, nxt, need) == ("Explorer", "Builder", 150) and progress == pytest.approx(0.25)
    assert rank_for(900) == ("Industry-ready", None, 0, 1.0)
    assert [n for n, _ in RANKS][0] == "Rookie"


def test_semesters_completed_needs_all_four_modules():
    assert semesters_completed({3: 4, 4: 3, 5: 0, 6: 0}) == 1
    assert semesters_completed({3: 4, 4: 4, 5: 4, 6: 4}) == 4
    assert semesters_completed({}) == 0


def test_badges_are_earned_only_by_the_matching_activity():
    none = game_state(Activity())
    assert none.earned_badges == [] and none.rank == "Rookie"
    state = game_state(
        Activity(modules_passed=4, semesters_completed=1, checks_completed=2, improved=True,
                 tasks_done=10, full_path_done=True)
    )  # fmt: skip
    assert {b.key for b in state.earned_badges} == {
        "first_module", "first_check", "semester", "improver", "full_path", "doer"
    }  # fmt: skip
    only_check = game_state(Activity(checks_completed=1))
    assert [b.key for b in only_check.earned_badges] == ["first_check"]
