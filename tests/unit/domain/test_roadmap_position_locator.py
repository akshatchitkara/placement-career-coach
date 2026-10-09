from pcc.domain.scoring.roadmap_position_locator import locate_position

FULL_ORDER = ["a", "b", "c", "d", "e", "f"]
MASTERY_THRESHOLD = 60


def test_position_is_first_unmastered_skill_in_tested_scope(skill_score_factory):
    skill_scores = {
        "a": skill_score_factory("a", score=80, sufficient=True),
        "b": skill_score_factory("b", score=40, sufficient=True),  # below mastery
        "c": skill_score_factory("c", score=90, sufficient=True),
    }
    position = locate_position(FULL_ORDER, {"a", "b", "c"}, skill_scores, MASTERY_THRESHOLD)
    assert position.label == "in_progress"
    assert position.skill_id == "b"


def test_position_is_first_skill_missing_evidence(skill_score_factory):
    skill_scores = {"a": skill_score_factory("a", score=80, sufficient=True)}
    position = locate_position(FULL_ORDER, {"a", "b"}, skill_scores, MASTERY_THRESHOLD)
    assert position.label == "in_progress"
    assert position.skill_id == "b"  # "b" was in scope but never answered


def test_advances_to_next_semester_when_scope_fully_mastered(skill_score_factory):
    skill_scores = {
        "a": skill_score_factory("a", score=90, sufficient=True),
        "b": skill_score_factory("b", score=70, sufficient=True),
    }
    position = locate_position(FULL_ORDER, {"a", "b"}, skill_scores, MASTERY_THRESHOLD)
    assert position.label == "advance_to_next_semester"
    assert position.skill_id == "c"


def test_roadmap_complete_when_every_skill_is_mastered(skill_score_factory):
    skill_scores = {sid: skill_score_factory(sid, score=90, sufficient=True) for sid in FULL_ORDER}
    position = locate_position(FULL_ORDER, set(FULL_ORDER), skill_scores, MASTERY_THRESHOLD)
    assert position.label == "roadmap_complete"
    assert position.skill_id is None
