"""Small shared stylesheet. Colours come from .streamlit/config.toml; this adds layout polish."""

import streamlit as st

_CSS = """
<style>
.block-container { padding-top: 2.2rem; max-width: 1100px; }
h1 { letter-spacing: -0.02em; }
.pcc-hero { background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); color: #fff;
  border-radius: 18px; padding: 2rem 2.2rem; margin-bottom: 1.2rem; }
.pcc-hero h1, .pcc-hero h2, .pcc-hero p { color: #fff; margin: 0 0 .4rem 0; }
.pcc-hero p { opacity: .92; font-size: 1.05rem; }
.pcc-steps { display: flex; gap: .5rem; flex-wrap: wrap; margin: .6rem 0 1.2rem 0; }
.pcc-step { flex: 1 1 130px; border-radius: 12px; padding: .7rem .9rem; background: #F3F5FB;
  border: 1px solid #E3E7F2; font-size: .92rem; color: #6B7280; }
.pcc-step b { display: block; font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; }
.pcc-step.done { background: #ECFDF5; border-color: #A7F3D0; color: #065F46; }
.pcc-step.current { background: #EEF2FF; border-color: #4F46E5; color: #3730A3;
  box-shadow: 0 0 0 2px #C7D2FE; }
.pcc-feature { background: #F8F9FD; border: 1px solid #E3E7F2; border-radius: 14px;
  padding: 1rem 1.1rem; height: 100%; }
.pcc-feature h4 { margin: 0 0 .3rem 0; }
.pcc-feature p { margin: 0; color: #4B5563; font-size: .93rem; }
.pcc-bar-row { margin: .55rem 0; }
.pcc-bar-row span { font-weight: 600; }
.pcc-bar-row small { color: #B45309; font-weight: 500; }
.pcc-bar-row em { color: #6B7280; font-size: .85rem; font-style: normal; }
.pcc-bar { position: relative; height: 12px; background: #E8EBF5; border-radius: 8px;
  margin: .25rem 0; }
.pcc-bar i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 8px; }
.pcc-bar i.good { background: #10B981; }
.pcc-bar i.mid { background: #F59E0B; }
.pcc-bar i.low { background: #EF4444; }
.pcc-bar u { position: absolute; top: -3px; bottom: -3px; width: 2px; background: #1F2937; }
[data-testid="stProgressBarTrack"] { background: #D9DEF0; height: 10px; border-radius: 8px; }
[data-testid="stProgressBarTrack"] > div { background: #4F46E5; border-radius: 8px; }
.pcc-bar b { position: absolute; top: -2px; bottom: -2px; width: 3px; background: #9CA3AF;
  border-radius: 2px; }
.pcc-spark { float: right; line-height: 0; margin-top: 2px; }
.pcc-up { color: #047857 !important; font-weight: 600; }
.pcc-down { color: #B91C1C !important; font-weight: 600; }
.pcc-chart { overflow-x: auto; }
[data-testid="stSidebar"] { border-right: 1px solid #E3E7F2; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
