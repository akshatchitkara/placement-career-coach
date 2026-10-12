"""Small coloured labels with accessible contrast (Streamlit's own badges fail contrast checks).

A pill is HTML, so it is rendered on a line of its own: mixing it with question or AI text in
one unsafe-HTML block would let angle brackets in that text be read as tags.
"""

import html

import streamlit as st

TONES = ("good", "warn", "bad", "info")


def pill_html(label: str, tone: str) -> str:
    tone = tone if tone in TONES else "info"
    return f'<span class="pcc-pill {tone}">{html.escape(label)}</span>'


def pill(label: str, tone: str) -> None:
    st.markdown(pill_html(label, tone), unsafe_allow_html=True)
