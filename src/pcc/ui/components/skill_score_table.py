"""Per-skill scores always shown with correct/answered (Section 10.3)."""

import streamlit as st

from pcc.domain.schemas.assessment_schemas import SkillScore


def render_skill_score_table(
    scores: list[SkillScore], skill_names: dict[str, str], min_answered: int
) -> None:
    st.dataframe(
        [
            {
                "Skill": skill_names.get(s.skill_id, s.skill_id)
                + ("  ⚠ weakest" if s.is_weakest else ""),
                "Correct / answered": f"{s.correct_count}/{s.answered_count}",
                "Score": f"{s.score:.1f}%",
                "Evidence": "enough"
                if s.has_sufficient_evidence
                else f"not enough (need {min_answered}+ answers)",
            }
            for s in scores
        ],
        hide_index=True,
        width="stretch",
    )
