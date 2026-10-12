"""Evaluation Agent (blueprint Section 9.3): select, present, grade by code. No AI involved.

Everything here is a pure function of its inputs, so an attempt can be re-derived from
its stored seed, answers and config snapshot (T-01, T-20).
"""

import random

from pcc.content.content_loader import AppSettings
from pcc.core.constants import SEMESTERS
from pcc.domain.enums import Difficulty
from pcc.domain.schemas.assessment_schemas import (
    Answer,
    EvaluationResult,
    PresentedQuestion,
    QuestionReview,
    SkillScore,
)
from pcc.domain.schemas.question_schemas import Option, Question
from pcc.domain.schemas.roadmap_schemas import Skill
from pcc.domain.scoring.coverage_calculator import compute_coverage_ratio
from pcc.domain.scoring.level_classifier import classify_level
from pcc.domain.scoring.roadmap_position_locator import locate_position
from pcc.domain.scoring.scoring_engine import compute_overall_score, compute_skill_scores
from pcc.domain.scoring.weakest_skill_selector import select_weakest_skill

_DIFFICULTY_ORDER = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
_FULL_PATH_ORDER = [Difficulty.EASY, Difficulty.HARD, Difficulty.MEDIUM]


def full_path_mix(per_skill: int) -> dict[str, int]:
    """Difficulty mix when every skill gets only a few questions: easy and hard first.

    Two questions per skill (the configured default) are one easy and one hard, which spans the
    range, and still meet the two-answers-per-skill evidence rule.
    """
    return {d.value: 1 for d in _FULL_PATH_ORDER[: max(per_skill, 0)]}


def select_questions(
    scope_skill_ids: list[str],
    bank: list[Question],
    settings: AppSettings,
    seen_question_ids: list[str],
    seed: int,
    *,
    full_path: bool = False,
) -> list[Question]:
    """Fixed difficulty mix per skill; unseen first, then least recently seen.

    `seen_question_ids` is ordered oldest -> newest last-seen. Grouped by skill (roadmap
    order), easy -> hard, so a given seed always yields the same list.
    """
    last_seen = {qid: i for i, qid in enumerate(seen_question_ids)}
    rng = random.Random(seed)
    picked: list[Question] = []
    mix = (
        full_path_mix(settings.full_path_questions_per_skill)
        if full_path
        else settings.difficulty_mix_per_skill
    )
    for skill_id in scope_skill_ids:
        for difficulty in _DIFFICULTY_ORDER:
            need = mix.get(difficulty.value, 0)
            pool = [q for q in bank if q.skill_id == skill_id and q.difficulty == difficulty]
            pool.sort(key=lambda q: q.question_id)  # stable base order before seeded choice
            unseen = [q for q in pool if q.question_id not in last_seen]
            rng.shuffle(unseen)
            seen = sorted(
                (q for q in pool if q.question_id in last_seen),
                key=lambda q: last_seen[q.question_id],
            )
            picked += (unseen + seen)[:need]
    return picked


def shuffled_option_order(question: Question, seed: int) -> list[str]:
    """Seeded per question, so a review screen can reproduce what the student saw."""
    ids = [o.option_id for o in question.options]
    random.Random(f"{seed}:{question.question_id}").shuffle(ids)
    return ids


def present(
    questions: list[Question], skills_by_id: dict[str, Skill], seed: int
) -> list[PresentedQuestion]:
    presented = []
    for q in questions:
        by_id = {o.option_id: o for o in q.options}
        options: list[Option] = [by_id[oid] for oid in shuffled_option_order(q, seed)]
        presented.append(
            PresentedQuestion(
                question_id=q.question_id,
                skill_id=q.skill_id,
                skill_name=skills_by_id[q.skill_id].name,
                difficulty=q.difficulty,
                stem=q.stem,
                options=options,
            )
        )
    return presented


def evaluate(
    *,
    attempt_id: int,
    attempt_type: str,
    scope_description: str,
    answers: list[Answer],
    questions_by_id: dict[str, Question],
    scope_skill_ids: list[str],
    core_skill_ids: list[str],
    roadmap_order: list[str],
    current_semester: int,
    semester_skill_ids: dict[int, list[str]],
    settings: AppSettings,
) -> EvaluationResult:
    """Scores an attempt using the config snapshot taken when it started."""
    if current_semester not in SEMESTERS:
        raise ValueError("current_semester must be 3..6")
    scores = compute_skill_scores(answers, questions_by_id, settings.min_answered_for_evidence)
    overall = compute_overall_score(answers, questions_by_id)
    coverage = compute_coverage_ratio(scores, core_skill_ids)
    level, notes = classify_level(
        overall,
        scores,
        coverage,
        settings.level_lower_bounds,
        settings.industry_ready_min_skill_score,
    )
    weakest = select_weakest_skill(scores, roadmap_order, settings.mastery_threshold)

    # "Where do I stand?" looks from the student's current semester onward (Section 10.6).
    first_current = semester_skill_ids[current_semester][0]
    order_from_here = roadmap_order[roadmap_order.index(first_current) :]
    position = locate_position(
        order_from_here, set(scope_skill_ids), scores, settings.mastery_threshold
    )

    if weakest.status == "no_major_gap":
        # The selector only knows the weakest skill, so its "next" can point at a skill that
        # was just mastered. The position is the first skill still to do, which is what to offer.
        weakest = weakest.model_copy(update={"next_roadmap_skill_id": position.skill_id})

    ordered_scores: list[SkillScore] = []
    for skill_id in roadmap_order:
        if skill_id in scores:
            score = scores[skill_id]
            if weakest.status == "weakest_found" and weakest.skill_id == skill_id:
                score = score.model_copy(update={"is_weakest": True})
            ordered_scores.append(score)

    reviews = []
    for answer in answers:
        q = questions_by_id[answer.question_id]
        text = {o.option_id: o.text for o in q.options}
        reviews.append(
            QuestionReview(
                question_id=q.question_id,
                skill_id=q.skill_id,
                stem=q.stem,
                selected_option_text=text[answer.selected_option_id],
                correct_option_text=text[q.correct_option_id],
                is_correct=answer.selected_option_id == q.correct_option_id,
                explanation=q.explanation,
            )
        )

    return EvaluationResult(
        attempt_id=attempt_id,
        attempt_type=attempt_type,
        scope_description=scope_description,
        overall_score=overall,
        level=level,
        level_notes=notes,
        coverage_ratio=coverage,
        skill_scores=ordered_scores,
        weakest=weakest,
        position=position,
        reviews=reviews,
        level_lower_bounds=settings.level_lower_bounds,
        mastery_threshold=settings.mastery_threshold,
        min_answered_for_evidence=settings.min_answered_for_evidence,
    )
