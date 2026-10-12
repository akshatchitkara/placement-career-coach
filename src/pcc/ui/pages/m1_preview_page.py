"""Developer preview of the M1 content + scoring core. Replaced by the real pages in M2+."""

import streamlit as st

from pcc.content.content_loader import (
    compute_skill_assessability,
    load_app_settings,
    load_careers,
    load_question_bank,
    load_roadmap_template,
    load_skills_for_career,
)
from pcc.domain.enums import SkillType
from pcc.domain.schemas.assessment_schemas import Answer
from pcc.domain.scoring.coverage_calculator import compute_coverage_ratio
from pcc.domain.scoring.level_classifier import classify_level
from pcc.domain.scoring.roadmap_position_locator import locate_position
from pcc.domain.scoring.scoring_engine import compute_overall_score, compute_skill_scores
from pcc.domain.scoring.weakest_skill_selector import select_weakest_skill


def _quiz(career_id: str, semester: int) -> None:
    settings = load_app_settings()
    roadmap = load_roadmap_template(career_id)
    questions = load_question_bank(career_id)
    skills = {s.skill_id: s for s in load_skills_for_career(career_id)}
    order = roadmap.skill_ids_in_order()
    scope = [
        m.skill_id
        for m in roadmap.months
        if m.semester == semester
        and skills[m.skill_id].skill_type == SkillType.CONCEPTUAL
        and compute_skill_assessability(m.skill_id, questions, settings)
    ]
    if not scope:
        st.warning("Assessment coming soon: no assessable question bank for this semester.")
        return

    picked = []
    for skill_id in scope:
        for difficulty, count in settings.difficulty_mix_per_skill.items():
            picked += [
                q for q in questions if q.skill_id == skill_id and q.difficulty == difficulty
            ][:count]
    by_id = {q.question_id: q for q in questions}

    with st.form(f"quiz_{career_id}_{semester}"):
        choices: dict[str, str | None] = {}
        for q in picked:
            st.markdown(f"**{skills[q.skill_id].name}** · _{q.difficulty}_")
            labels = {o.option_id: o.text for o in q.options}
            choices[q.question_id] = st.radio(
                q.stem,
                list(labels),
                format_func=labels.get,
                index=None,
                key=f"q_{q.question_id}",
            )
        submitted = st.form_submit_button("Submit answers")
    if not submitted:
        return

    answers = [Answer(question_id=k, selected_option_id=v) for k, v in choices.items() if v]
    if not answers:
        st.error("Answer at least one question.")
        return

    scores = compute_skill_scores(answers, by_id, settings.min_answered_for_evidence)
    core_ids = [s for s, sk in skills.items() if sk.skill_type == SkillType.CONCEPTUAL]
    coverage = compute_coverage_ratio(scores, core_ids)
    overall = compute_overall_score(answers, by_id)
    level, notes = classify_level(
        overall,
        scores,
        coverage,
        settings.level_lower_bounds,
        settings.industry_ready_min_skill_score,
    )
    weakest = select_weakest_skill(scores, order, settings.mastery_threshold)
    position = locate_position(order, set(scope), scores, settings.mastery_threshold)

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall score", f"{overall:.0f}%")
    c2.metric("Level", level.value.replace("_", " ").title())
    c3.metric("Coverage of career", f"{coverage:.0%}")
    for n in notes:
        st.info(n)
    st.header("Per-skill scores")
    st.dataframe(
        [
            {
                "skill": skills[s.skill_id].name,
                "correct": f"{s.correct_count}/{s.answered_count}",
                "score %": round(s.score, 1),
                "enough evidence": s.has_sufficient_evidence,
            }
            for s in scores.values()
        ],
        hide_index=True,
    )
    if weakest.status == "weakest_found" and weakest.skill_id:
        st.error(f"Weakest skill: {skills[weakest.skill_id].name}")
    elif weakest.status == "no_major_gap":
        nxt = weakest.next_roadmap_skill_id
        st.success(f"No major gap. Next on roadmap: {skills[nxt].name if nxt else 'none'}")
    else:
        st.warning("Insufficient evidence to name a weakest skill.")
    where = skills[position.skill_id].name if position.skill_id else ""
    st.write(f"**Roadmap position:** {position.label.replace('_', ' ')} {where}")
    with st.expander("Answer review"):
        for a in answers:
            q = by_id[a.question_id]
            ok = a.selected_option_id == q.correct_option_id
            st.write(f"{'✅' if ok else '❌'} {q.stem} — {q.explanation}")


def render() -> None:
    st.title("M1 Preview: content & scoring")
    careers = {c.career_id: c for c in load_careers()}
    career_id = st.selectbox("Career", list(careers), format_func=lambda c: careers[c].name)
    st.caption(f"Tier {careers[career_id].tier} · {careers[career_id].description}")

    t_content, t_road, t_bank, t_quiz = st.tabs(
        ["Skills", "Roadmap", "Question bank", "Live skills check"]
    )
    skills = load_skills_for_career(career_id)
    with t_content:
        st.dataframe(
            [
                {"skill": s.name, "type": s.skill_type.value, "careers": ", ".join(s.career_ids)}
                for s in skills
            ],
            hide_index=True,
        )
    with t_road:
        names = {s.skill_id: s.name for s in skills}
        months = sorted(
            load_roadmap_template(career_id).months, key=lambda m: (m.semester, m.month_index)
        )
        for m in months:
            with st.expander(f"Sem {m.semester} · Month {m.month_index} · {names[m.skill_id]}"):
                st.write(m.focus)
                st.write("\n".join(f"- {t}" for t in m.topics))
                st.caption(f"Deliverable: {m.deliverable}")
    with t_bank:
        settings = load_app_settings()
        qs = load_question_bank(career_id)
        st.write(f"{len(qs)} questions authored.")
        st.dataframe(
            [
                {
                    "skill": s.name,
                    "questions": sum(q.skill_id == s.skill_id for q in qs),
                    "assessable": compute_skill_assessability(s.skill_id, qs, settings),
                }
                for s in skills
            ],
            hide_index=True,
        )
    with t_quiz:
        semester = st.selectbox("Semester", [3, 4, 5, 6])
        _quiz(career_id, semester)
