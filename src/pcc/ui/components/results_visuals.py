"""Results visuals: the level ladder and per-skill score bars (plain HTML, no chart library)."""

import html

import streamlit as st

from pcc.domain.enums import Level
from pcc.domain.schemas.assessment_schemas import SkillScore
from pcc.ui.components.level_badge import LEVEL_LABELS

_ORDER = [Level.BEGINNER, Level.INTERMEDIATE, Level.ADVANCED, Level.INDUSTRY_READY]
_BOUND_KEY = {
    Level.INTERMEDIATE: "intermediate",
    Level.ADVANCED: "advanced",
    Level.INDUSTRY_READY: "industry_ready",
}


def level_ladder(level: Level, score: float, lower_bounds: dict[str, float]) -> None:
    """Four steps with the current one highlighted, and how far to the next level."""
    cells = []
    for step in _ORDER:
        css = (
            "current"
            if step == level
            else "done"
            if _ORDER.index(step) < _ORDER.index(level)
            else ""
        )
        bound = "" if step == Level.BEGINNER else f"from {lower_bounds[_BOUND_KEY[step]]:g}%"
        cells.append(
            f'<div class="pcc-step {css}"><b>{bound or "start"}</b>{LEVEL_LABELS[step]}</div>'
        )
    st.markdown(f'<div class="pcc-steps">{"".join(cells)}</div>', unsafe_allow_html=True)

    if level == Level.INDUSTRY_READY:
        st.caption("You are at the top level.")
        return
    nxt = _ORDER[_ORDER.index(level) + 1]
    gap = lower_bounds[_BOUND_KEY[nxt]] - score
    if gap > 0:
        st.caption(
            f"{gap:.1f} points to reach {LEVEL_LABELS[nxt]} ({lower_bounds[_BOUND_KEY[nxt]]:g}%)."
        )
    else:
        st.caption(
            f"Your score reaches {LEVEL_LABELS[nxt]}, but another rule holds you back. "
            "See the notes above."
        )


def skill_bars(
    scores: list[SkillScore], names: dict[str, str], mastery: float, min_answered: int
) -> None:
    rows = []
    for s in scores:
        name = html.escape(names.get(s.skill_id, s.skill_id))
        if not s.has_sufficient_evidence:
            rows.append(
                f'<div class="pcc-bar-row"><span>{name}</span><div class="pcc-bar"></div>'
                f"<em>Not enough answers yet (need {min_answered}+)</em></div>"
            )
            continue
        tone = "good" if s.score >= mastery else "mid" if s.score >= 50 else "low"
        tag = " · biggest opportunity" if s.is_weakest else ""
        rows.append(
            f'<div class="pcc-bar-row"><span>{name}<small>{html.escape(tag)}</small></span>'
            f'<div class="pcc-bar"><i class="{tone}" style="width:{s.score:.0f}%"></i>'
            f'<u style="left:{mastery:.0f}%"></u></div>'
            f"<em>{s.score:.0f}% · {s.correct_count} of {s.answered_count} right</em></div>"
        )
    st.markdown("".join(rows), unsafe_allow_html=True)
    st.caption(f"The vertical line marks mastery ({mastery:g}%).")
