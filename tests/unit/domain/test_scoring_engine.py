import pytest

from pcc.domain.schemas.assessment_schemas import Answer
from pcc.domain.schemas.question_schemas import Option, Question
from pcc.domain.scoring.scoring_engine import compute_overall_score, compute_skill_scores


def _question(question_id, skill_id, correct="opt_a"):
    return Question(
        question_id=question_id,
        skill_id=skill_id,
        concept_tag="x",
        difficulty="easy",
        stem="stem",
        options=[Option(option_id=f"opt_{c}", text=c) for c in "abcd"],
        correct_option_id=correct,
        explanation="because",
    )


@pytest.fixture
def devops_sem3_worked_example():
    """Section 10.7's worked example: 12 questions, 4 skills, 3 each."""
    questions = {}
    answers = []
    # linux: 1/3 correct
    for i, selected in enumerate(["opt_a", "opt_b", "opt_b"]):
        qid = f"q_linux_{i}"
        questions[qid] = _question(qid, "linux_fundamentals")
        answers.append(Answer(question_id=qid, selected_option_id=selected))
    # shell: 1/3 correct
    for i, selected in enumerate(["opt_a", "opt_b", "opt_b"]):
        qid = f"q_shell_{i}"
        questions[qid] = _question(qid, "shell_scripting")
        answers.append(Answer(question_id=qid, selected_option_id=selected))
    # python: 2/3 correct
    for i, selected in enumerate(["opt_a", "opt_a", "opt_b"]):
        qid = f"q_python_{i}"
        questions[qid] = _question(qid, "python_for_automation")
        answers.append(Answer(question_id=qid, selected_option_id=selected))
    # git: 2/3 correct
    for i, selected in enumerate(["opt_a", "opt_a", "opt_b"]):
        qid = f"q_git_{i}"
        questions[qid] = _question(qid, "git_version_control")
        answers.append(Answer(question_id=qid, selected_option_id=selected))
    return answers, questions


def test_worked_example_matches_section_10_7(devops_sem3_worked_example):
    answers, questions = devops_sem3_worked_example

    scores = compute_skill_scores(answers, questions, min_answered_for_evidence=2)
    overall = compute_overall_score(answers, questions)

    assert scores["linux_fundamentals"].score == pytest.approx(33.3, abs=0.1)
    assert scores["shell_scripting"].score == pytest.approx(33.3, abs=0.1)
    assert scores["python_for_automation"].score == pytest.approx(66.7, abs=0.1)
    assert scores["git_version_control"].score == pytest.approx(66.7, abs=0.1)
    assert overall == pytest.approx(50.0, abs=0.1)


def test_T01_same_answers_scored_twice_gives_identical_results(devops_sem3_worked_example):
    answers, questions = devops_sem3_worked_example

    scores_first = compute_skill_scores(answers, questions, min_answered_for_evidence=2)
    scores_second = compute_skill_scores(answers, questions, min_answered_for_evidence=2)
    overall_first = compute_overall_score(answers, questions)
    overall_second = compute_overall_score(answers, questions)

    assert scores_first == scores_second
    assert overall_first == overall_second
