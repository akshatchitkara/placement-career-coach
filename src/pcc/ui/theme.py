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
  border: 1px solid #E3E7F2; font-size: .92rem; color: #4B5563; }
.pcc-step b { display: block; font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; }
.pcc-step.done { background: #ECFDF5; border-color: #A7F3D0; color: #065F46; }
.pcc-step.current { background: #EEF2FF; border-color: #4F46E5; color: #3730A3;
  box-shadow: 0 0 0 2px #C7D2FE; }
.pcc-features { display: grid; gap: .8rem; margin-bottom: .4rem;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
.pcc-feature { background: #F8F9FD; border: 1px solid #E3E7F2; border-radius: 14px;
  padding: 1rem 1.1rem; height: 100%; }
.pcc-feature h2 { margin: 0 0 .3rem 0; font-size: 1.1rem; font-weight: 600; }
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
[data-testid="stHeading"] h2 { font-size: 1.55rem; font-weight: 600; letter-spacing: -0.01em; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
  color: #565C66 !important; opacity: 1 !important; }
.pcc-pill { display: inline-block; padding: .08rem .65rem; border-radius: 999px; font-size: .78rem;
  font-weight: 600; line-height: 1.55; }
.pcc-pill.good { background: #DCFCE7; color: #14532D; }
.pcc-pill.warn { background: #FEF3C7; color: #78350F; }
.pcc-pill.bad { background: #FEE2E2; color: #7F1D1D; }
.pcc-pill.info { background: #E0E7FF; color: #312E81; }
[data-testid="stAlertContainer"] p, [data-testid="stAlertContainer"] li {
  color: #1F2937 !important; }
[data-testid="stMetricDelta"] { color: #4B5563 !important; }
[data-testid="stMetricDelta"]:has([data-testid="stMetricDeltaIcon-Up"]) {
  color: #0F6B2A !important; }
[data-testid="stMetricDelta"]:has([data-testid="stMetricDeltaIcon-Down"]) {
  color: #B91C1C !important; }
[data-testid="stSidebar"] { border-right: 1px solid #E3E7F2; }
[data-testid="stHeaderActionElements"] { display: none !important; }
.pcc-grow-step { margin-left: 0 !important; list-style: none; }

.pcc-career-card { background: #F8F9FD; border: 1px solid #E3E7F2; border-radius: 16px;
  padding: 1.1rem 1.3rem; margin: .6rem 0 1.2rem 0; }
.pcc-card-title { margin: 0 0 .3rem 0; font-size: 1.25rem; font-weight: 700; color: #1F2937; }
.pcc-card-label { margin: .9rem 0 .3rem 0; font-size: .8rem; font-weight: 700;
  letter-spacing: .06em; text-transform: uppercase; color: #3730A3; }
.pcc-career-card p, .pcc-career-card li { color: #1F2937; font-size: .95rem; }
.pcc-career-card ul { margin: 0; padding-left: 1.2rem; }
.pcc-career-card ol.pcc-grow { margin: 0 !important; padding: 0 !important;
  padding-inline-start: 0 !important; margin-inline-start: 0 !important; }
.pcc-grow { display: flex; flex-wrap: wrap; gap: .5rem; list-style: none; padding: 0; margin: 0; }
.pcc-grow-step { flex: 1 1 150px; background: #fff; border: 1px solid #C7D2FE; border-radius: 12px;
  padding: .55rem .7rem; font-size: .88rem; font-weight: 600; color: #312E81; }
.pcc-grow-step span { display: inline-block; width: 1.4rem; height: 1.4rem; line-height: 1.4rem;
  text-align: center; border-radius: 50%; background: #4F46E5; color: #fff; margin-right: .45rem;
  font-size: .78rem; }
.pcc-game { background: linear-gradient(135deg, #312E81 0%, #5B21B6 100%); color: #fff;
  border-radius: 16px; padding: .9rem 1.2rem; margin: .4rem 0 1rem 0; }
.pcc-game-top { display: flex; justify-content: space-between; align-items: baseline; }
.pcc-game-top b { font-size: 1.25rem; color: #fff; }
.pcc-game-top span { font-weight: 700; color: #FDE68A; }
.pcc-xpbar { height: 10px; background: rgba(255,255,255,.28); border-radius: 8px; margin: .5rem 0;
  overflow: hidden; }
.pcc-xpbar i { display: block; height: 100%; background: #FBBF24; border-radius: 8px; }
.pcc-game small { color: #E0E7FF; }
.pcc-road { display: flex; list-style: none; padding: 0; margin: .6rem 0 1rem 0; }
.pcc-node { flex: 1 1 0; position: relative; text-align: center; padding: 0 .3rem; }
.pcc-node::before { content: ""; position: absolute; top: 22px; left: -50%; width: 100%;
  height: 6px;
  background: repeating-linear-gradient(90deg, #C7CCE0 0 12px, transparent 12px 20px);
  border-radius: 4px; z-index: 0; }
.pcc-node:first-child::before { display: none; }
.pcc-node.done::before { background: #10B981; }
.pcc-dot { position: relative; z-index: 1; display: inline-flex; align-items: center;
  justify-content: center; width: 46px; height: 46px; border-radius: 50%; font-weight: 700;
  font-size: 1.1rem; background: #E8EBF5; color: #374151; border: 3px solid #C7CCE0; }
.pcc-node.done .pcc-dot { background: #059669; border-color: #047857; color: #fff; }
.pcc-node.current .pcc-dot { background: #4F46E5; border-color: #312E81; color: #fff;
  animation: pcc-pulse 1.8s ease-in-out infinite; }
.pcc-node-text { display: block; margin-top: .35rem; font-size: .85rem; line-height: 1.25; }
.pcc-node-text small { display: block; color: #565C66; }
.pcc-node-text b { color: #1F2937; }
@keyframes pcc-pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(79,70,229,.45); }
  50% { box-shadow: 0 0 0 10px rgba(79,70,229,0); } }
@media (prefers-reduced-motion: reduce) { .pcc-node.current .pcc-dot { animation: none; } }
.pcc-badges { display: grid; gap: .6rem;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  list-style: none; padding: 0; margin: .4rem 0 1rem 0; }
.pcc-badges { margin: 0 !important; padding: 0 !important;
  padding-inline-start: 0 !important; margin-inline-start: 0 !important; }
[data-testid="stHorizontalBlock"]:has(.pcc-feature) { align-items: stretch; }
[data-testid="stColumn"]:has(.pcc-feature) > div, [data-testid="stColumn"]:has(.pcc-feature)
  [data-testid="stMarkdownContainer"] { height: 100%; }
.pcc-feature { height: 100%; box-sizing: border-box; }
.pcc-badge { border-radius: 14px; padding: .7rem .9rem; border: 1px solid #E3E7F2; }
.pcc-badge b { display: block; }
.pcc-badge small { display: block; color: #4B5563; margin: .15rem 0 .35rem 0; }
.pcc-badge.on { background: #FFFBEB; border-color: #FCD34D; }
.pcc-badge.off { background: #F3F4F6; }
.pcc-badge.off b { color: #4B5563; }
.pcc-badge-state { font-size: .75rem; font-weight: 700; color: #78350F; }
.pcc-badge.off .pcc-badge-state { color: #4B5563; }
@media (max-width: 640px) {
  .block-container { padding: 1.2rem .9rem 3rem .9rem; }
  .pcc-hero { padding: 1.3rem 1.1rem; }
  .pcc-features { grid-template-columns: 1fr 1fr; gap: .6rem; }
  .pcc-feature { padding: .7rem .8rem; }
  .pcc-feature h2 { font-size: 1rem; }
  .pcc-feature p { font-size: .85rem; }
  .pcc-road { flex-direction: column; margin-left: .2rem; }
  .pcc-node { display: flex; align-items: flex-start; text-align: left; gap: .8rem;
    padding: 0 0 1.1rem 0; }
  .pcc-node::before { top: 46px; left: 20px; width: 6px; height: calc(100% - 46px);
    background: repeating-linear-gradient(180deg, #C7CCE0 0 10px, transparent 10px 16px); }
  .pcc-node:first-child::before { display: block; }
  .pcc-node:last-child::before { display: none; }
  .pcc-node.done::before { background: #10B981; }
  .pcc-node-text { margin-top: .2rem; }
  .pcc-grow-step { flex: 1 1 100%; }
  .stButton > button { min-height: 44px; }
  .stButton { display: flex; justify-content: flex-start; }
  [data-testid="stRadio"] label { min-height: 44px; }
  .pcc-game-top b { font-size: 1.1rem; }
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
    flex-wrap: nowrap !important; gap: .5rem !important; }
  [data-testid="stColumn"]:has([data-testid="stMetric"]) {
    min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }
  [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
  [data-testid="stMetricLabel"] { font-size: .8rem !important; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
