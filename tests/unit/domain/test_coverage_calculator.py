from pcc.domain.scoring.coverage_calculator import compute_coverage_ratio


def test_full_coverage_when_every_core_skill_has_evidence(skill_score_factory):
    skill_scores = {
        "a": skill_score_factory("a", score=50, sufficient=True),
        "b": skill_score_factory("b", score=80, sufficient=True),
    }
    assert compute_coverage_ratio(skill_scores, ["a", "b"]) == 1.0


def test_partial_coverage_when_only_some_core_skills_have_evidence(skill_score_factory):
    skill_scores = {"a": skill_score_factory("a", score=50, sufficient=True)}
    # Section 10.4: a single-semester attempt only covers a slice of the full
    # career's core skills, which is why it caps at Advanced (T-03).
    assert compute_coverage_ratio(skill_scores, ["a", "b", "c", "d"]) == 0.25


def test_zero_coverage_when_no_core_skills_have_evidence():
    assert compute_coverage_ratio({}, ["a", "b"]) == 0.0


def test_insufficient_evidence_skill_does_not_count_toward_coverage(skill_score_factory):
    skill_scores = {"a": skill_score_factory("a", score=0, answered=1, sufficient=False)}
    assert compute_coverage_ratio(skill_scores, ["a", "b"]) == 0.0
