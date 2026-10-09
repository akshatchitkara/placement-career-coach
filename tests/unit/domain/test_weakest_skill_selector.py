from pcc.domain.scoring.weakest_skill_selector import select_weakest_skill

ROADMAP_ORDER = [
    "linux_fundamentals",
    "shell_scripting",
    "python_for_automation",
    "git_version_control",
]
MASTERY_THRESHOLD = 60


def test_T05_skill_with_one_answered_question_is_not_eligible_as_weakest(skill_score_factory):
    skill_scores = {
        "linux_fundamentals": skill_score_factory(
            "linux_fundamentals", score=0, answered=1, sufficient=False
        ),
        "shell_scripting": skill_score_factory(
            "shell_scripting", score=50, answered=3, sufficient=True
        ),
    }
    outcome = select_weakest_skill(skill_scores, ROADMAP_ORDER, MASTERY_THRESHOLD)
    assert outcome.status == "weakest_found"
    assert outcome.skill_id == "shell_scripting"  # the insufficient-evidence skill is never picked


def test_T06_tied_lowest_skills_break_tie_by_earlier_roadmap_position(skill_score_factory):
    skill_scores = {
        "shell_scripting": skill_score_factory("shell_scripting", score=33.3, sufficient=True),
        "linux_fundamentals": skill_score_factory(
            "linux_fundamentals", score=33.3, sufficient=True
        ),
    }
    outcome = select_weakest_skill(skill_scores, ROADMAP_ORDER, MASTERY_THRESHOLD)
    assert outcome.status == "weakest_found"
    assert outcome.skill_id == "linux_fundamentals"  # earlier in ROADMAP_ORDER than shell_scripting


def test_T07_no_skill_with_sufficient_evidence_returns_insufficient_evidence(skill_score_factory):
    skill_scores = {
        "linux_fundamentals": skill_score_factory(
            "linux_fundamentals", score=0, answered=1, sufficient=False
        ),
    }
    outcome = select_weakest_skill(skill_scores, ROADMAP_ORDER, MASTERY_THRESHOLD)
    assert outcome.status == "insufficient_evidence"
    assert outcome.skill_id is None


def test_T08_weakest_skill_at_or_above_mastery_is_no_major_gap(skill_score_factory):
    skill_scores = {
        "linux_fundamentals": skill_score_factory("linux_fundamentals", score=60, sufficient=True),
        "shell_scripting": skill_score_factory("shell_scripting", score=90, sufficient=True),
    }
    outcome = select_weakest_skill(skill_scores, ROADMAP_ORDER, MASTERY_THRESHOLD)
    assert outcome.status == "no_major_gap"
    assert outcome.next_roadmap_skill_id == "shell_scripting"  # next after linux_fundamentals
