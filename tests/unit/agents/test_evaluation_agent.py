from collections import Counter

import pytest

from pcc.agents.evaluation_agent import present, select_questions, shuffled_option_order
from pcc.content.content_loader import load_app_settings, load_question_bank, load_skills

SEM3 = ["linux_fundamentals", "shell_scripting", "python_for_automation", "git_version_control"]


@pytest.fixture(scope="module")
def bank():
    return load_question_bank("devops_engineer")


@pytest.fixture(scope="module")
def settings():
    return load_app_settings()


def test_selection_is_three_per_skill_with_1_1_1_mix(bank, settings):
    picked = select_questions(SEM3, bank, settings, [], seed=1)
    assert len(picked) == 12
    for skill_id in SEM3:
        mix = Counter(q.difficulty.value for q in picked if q.skill_id == skill_id)
        assert mix == {"easy": 1, "medium": 1, "hard": 1}
    assert [q.skill_id for q in picked] == [s for s in SEM3 for _ in range(3)]


def test_same_seed_same_questions_different_seed_can_differ(bank, settings):
    a = select_questions(SEM3, bank, settings, [], seed=7)
    assert a == select_questions(SEM3, bank, settings, [], seed=7)
    others = {
        tuple(q.question_id for q in select_questions(SEM3, bank, settings, [], s))
        for s in range(10)
    }
    assert len(others) > 1


def test_t17_unseen_questions_come_first(bank, settings):
    first = select_questions(SEM3, bank, settings, [], seed=3)
    seen = [q.question_id for q in first]
    second = select_questions(SEM3, bank, settings, seen, seed=4)
    assert not {q.question_id for q in second} & set(seen)  # bank has 2 per difficulty
    assert len({q.question_id for q in second}) == 12


def test_t17_when_pool_runs_out_least_recently_seen_is_reused(bank, settings):
    everything = [q.question_id for q in bank]  # ordered oldest -> newest
    picked = select_questions(["linux_fundamentals"], bank, settings, everything, seed=5)
    for q in picked:
        same = [x for x in bank if x.skill_id == q.skill_id and x.difficulty == q.difficulty]
        oldest = min(same, key=lambda x: everything.index(x.question_id))
        assert q.question_id == oldest.question_id


def test_option_shuffle_is_reproducible_and_a_permutation(bank):
    q = bank[0]
    order = shuffled_option_order(q, seed=42)
    assert order == shuffled_option_order(q, seed=42)
    assert sorted(order) == sorted(o.option_id for o in q.options)


def test_option_shuffle_removes_fixed_answer_position(bank):
    positions = {
        shuffled_option_order(bank[0], seed=s).index(bank[0].correct_option_id) for s in range(40)
    }
    assert len(positions) > 1


def test_presented_questions_never_expose_the_answer_key(bank):
    skills = {s.skill_id: s for s in load_skills()}
    presented = present(bank[:3], skills, seed=1)
    assert "correct_option_id" not in presented[0].model_dump()
    assert presented[0].skill_name == skills[bank[0].skill_id].name
