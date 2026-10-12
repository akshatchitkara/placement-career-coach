"""Level display with its scope and the rules that produced it."""

import streamlit as st

from pcc.domain.enums import Level

LEVEL_LABELS = {
    Level.BEGINNER: "Beginner",
    Level.INTERMEDIATE: "Intermediate",
    Level.ADVANCED: "Advanced",
    Level.INDUSTRY_READY: "Industry-ready",
}


def render_level_badge(
    level: Level, scope_description: str, overall_score: float, notes: list[str]
) -> None:
    c1, c2 = st.columns(2)
    c1.metric("Overall score", f"{overall_score:.1f}%")
    c2.metric(f"Level for {scope_description}", LEVEL_LABELS[level])
    for note in notes:
        st.info(note)


def render_level_rules(lower_bounds: dict[str, float]) -> None:
    st.caption(
        "Level rules: "
        f"Industry-ready ≥ {lower_bounds['industry_ready']:g} (plus every skill ≥ 60 and full "
        f"career coverage) · Advanced ≥ {lower_bounds['advanced']:g} · "
        f"Intermediate ≥ {lower_bounds['intermediate']:g} · otherwise Beginner."
    )
