"""Progress visuals as plain inline SVG and HTML (no chart library): score trend and skill rows."""

import html

import streamlit as st

from pcc.domain.enums import Level
from pcc.domain.progress import AttemptSummary
from pcc.ui.components.level_badge import LEVEL_LABELS

_W, _H = 640, 230
_LEFT, _RIGHT, _TOP, _BOTTOM = 64, 128, 22, 44
_INDIGO = "#4F46E5"
_GRID = "#E3E7F2"
_MUTED = "#6B7280"
_SAME_TOLERANCE = 0.05


def _x(index: int, count: int) -> float:
    if count == 1:
        return (_LEFT + _W - _RIGHT) / 2
    return _LEFT + index * (_W - _LEFT - _RIGHT) / (count - 1)


def _y(score: float) -> float:
    return _TOP + (100 - score) * (_H - _TOP - _BOTTOM) / 100


def _check_label(index: int, attempt: AttemptSummary) -> str:
    return "Baseline" if index == 0 else f"Re-check {index}"


def trend_svg(attempts: list[AttemptSummary], lower_bounds: dict[str, float]) -> str:
    """Overall score across checks, with the level cut-offs drawn as guide lines."""
    guides = [
        ("intermediate", lower_bounds["intermediate"]),
        ("advanced", lower_bounds["advanced"]),
        ("industry_ready", lower_bounds["industry_ready"]),
    ]
    parts = [
        f'<svg viewBox="0 0 {_W} {_H}" width="100%" style="min-width:520px" role="img" '
        f'aria-label="Overall score for each check: '
        + html.escape(
            ", ".join(
                f"{_check_label(i, a)} {a.overall_score:.0f}%" for i, a in enumerate(attempts)
            )
        )
        + '" xmlns="http://www.w3.org/2000/svg">'
    ]
    for name, bound in guides:
        y = _y(bound)
        label = html.escape(f"{LEVEL_LABELS[Level(name)]} {bound:g}%")
        parts.append(
            f'<line x1="{_LEFT}" x2="{_W - _RIGHT + 4}" y1="{y:.1f}" y2="{y:.1f}" '
            f'stroke="{_GRID}" stroke-dasharray="4 4"/>'
            f'<text x="{_W - _RIGHT + 8}" y="{y + 4:.1f}" text-anchor="start" font-size="11" '
            f'fill="{_MUTED}">{label}</text>'
        )
    count = len(attempts)
    points = [(_x(i, count), _y(a.overall_score)) for i, a in enumerate(attempts)]
    if count > 1:
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        parts.append(
            f'<polyline points="{line}" fill="none" stroke="{_INDIGO}" stroke-width="3" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
    for i, (attempt, (x, y)) in enumerate(zip(attempts, points, strict=True)):
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#fff" stroke="{_INDIGO}" '
            'stroke-width="3"/>'
            f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-size="13" '
            f'font-weight="600" fill="#1F2937">{attempt.overall_score:.0f}%</text>'
            f'<text x="{x:.1f}" y="{_H - 22}" text-anchor="middle" font-size="12" '
            f'fill="#374151">{html.escape(_check_label(i, attempt))}</text>'
            f'<text x="{x:.1f}" y="{_H - 8}" text-anchor="middle" font-size="11" '
            f'fill="{_MUTED}">{html.escape(attempt.submitted_at[:10])}</text>'
        )
    for tick in (0, 50, 100):
        parts.append(
            f'<text x="{_LEFT - 30}" y="{_y(tick) + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="{_MUTED}">{tick}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def sparkline_svg(values: list[float | None], width: int = 84, height: int = 26) -> str:
    """A tiny trend for one skill. Checks where the skill had too little evidence are skipped."""
    known = [(i, v) for i, v in enumerate(values) if v is not None]
    if not known:
        return ""
    last = len(values) - 1 or 1

    def px(i: int) -> float:
        return 4 + i * (width - 8) / last

    def py(v: float) -> float:
        return 4 + (100 - v) * (height - 8) / 100

    coords = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in known)
    end_i, end_v = known[-1]
    line = (
        f'<polyline points="{coords}" fill="none" stroke="{_INDIGO}" stroke-width="2"/>'
        if len(known) > 1
        else ""
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'aria-hidden="true" xmlns="http://www.w3.org/2000/svg">{line}'
        f'<circle cx="{px(end_i):.1f}" cy="{py(end_v):.1f}" r="3" fill="{_INDIGO}"/></svg>'
    )


def _change(previous: float | None, current: float) -> tuple[str, str]:
    if previous is None:
        return "new", "first time measured"
    diff = current - previous
    if abs(diff) < _SAME_TOLERANCE:
        return "same", "no change"
    return ("up", f"+{diff:.0f} points") if diff > 0 else ("down", f"{diff:.0f} points")


def skill_change_rows(attempts: list[AttemptSummary], names: dict[str, str], mastery: float) -> str:
    """One row per skill: current score bar, a tick where the previous check was, and the change."""
    latest = attempts[-1]
    previous = {s.skill_id: s for s in attempts[-2].skill_scores} if len(attempts) > 1 else {}
    rows = []
    for score in latest.skill_scores:
        name = html.escape(names.get(score.skill_id, score.skill_id))
        if not score.has_sufficient_evidence:
            rows.append(
                f'<div class="pcc-bar-row"><span>{name}</span><div class="pcc-bar"></div>'
                "<em>Not enough answers yet to measure</em></div>"
            )
            continue
        old = previous.get(score.skill_id)
        before = old.score if old is not None and old.has_sufficient_evidence else None
        direction, label = _change(before, score.score)
        tone = "good" if score.score >= mastery else "mid" if score.score >= 50 else "low"
        tick = f'<b style="left:{before:.0f}%"></b>' if before is not None else ""
        spark = ""
        if len(attempts) >= 3:
            history = [
                next(
                    (
                        s.score
                        for s in a.skill_scores
                        if s.skill_id == score.skill_id and s.has_sufficient_evidence
                    ),
                    None,
                )
                for a in attempts
            ]
            spark = f'<span class="pcc-spark">{sparkline_svg(history)}</span>'
        rows.append(
            f'<div class="pcc-bar-row"><span>{name}</span>{spark}'
            f'<div class="pcc-bar"><i class="{tone}" style="width:{score.score:.0f}%"></i>'
            f'{tick}<u style="left:{mastery:.0f}%"></u></div>'
            f'<em class="pcc-{direction}">{score.score:.0f}% · {label}</em></div>'
        )
    return "".join(rows)


def render_trend(attempts: list[AttemptSummary], lower_bounds: dict[str, float]) -> None:
    st.markdown(
        f'<div class="pcc-chart" tabindex="0" role="group" '
        f'aria-label="Score trend chart, scrolls sideways on narrow screens">'
        f"{trend_svg(attempts, lower_bounds)}</div>",
        unsafe_allow_html=True,
    )


def render_skill_changes(
    attempts: list[AttemptSummary], names: dict[str, str], mastery: float
) -> None:
    st.markdown(skill_change_rows(attempts, names, mastery), unsafe_allow_html=True)
    if len(attempts) > 1:
        st.caption(
            f"Grey tick: the previous check. Dark line: the mastery bar ({mastery:g}%). "
            "Small lines show each skill across all your checks."
        )
