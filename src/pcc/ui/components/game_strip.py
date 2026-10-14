"""The student's rank, XP and badges. Display only: the numbers come from the domain rules."""

import html

import streamlit as st

from pcc.domain.gamification import GameState


def render_game_strip(state: GameState) -> None:
    if state.next_rank:
        hint = f"{state.xp_to_next} XP to {html.escape(state.next_rank)}"
    else:
        hint = "Top rank reached"
    earned = len(state.earned_badges)
    st.markdown(
        '<div class="pcc-game">'
        f'<div class="pcc-game-top"><b>{html.escape(state.rank)}</b>'
        f"<span>{state.xp} XP</span></div>"
        f'<div class="pcc-xpbar" role="progressbar" aria-label="Progress to the next rank" '
        f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{round(state.rank_progress * 100)}">'
        f'<i style="width:{state.rank_progress * 100:.0f}%"></i></div>'
        f"<small>{hint} · {earned} of {len(state.badges)} badges</small></div>",
        unsafe_allow_html=True,
    )


def render_badge_shelf(state: GameState) -> None:
    chips = "".join(
        f'<li class="pcc-badge {"on" if b.earned else "off"}" title="{html.escape(b.description)}">'
        f"<b>{html.escape(b.name)}</b>"
        f"<small>{html.escape(b.description)}</small>"
        f'<span class="pcc-badge-state">{"Earned" if b.earned else "Locked"}</span></li>'
        for b in state.badges
    )
    st.markdown(f'<ul class="pcc-badges">{chips}</ul>', unsafe_allow_html=True)
