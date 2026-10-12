"""Layout at three screen sizes and accessibility (axe-core) on every page of a signed-in student.

axe-core is read from PCC_AXE_PATH or node_modules/axe-core/axe.min.js (npm install axe-core).
The accessibility check ignores four findings that come from Streamlit's own sidebar markup and
that also appear in a minimal Streamlit app with none of this project's code: aria-allowed-attr
on the sidebar element, and region, list and listitem inside the sidebar navigation.
"""

import json
import os
from pathlib import Path

import pytest
from tests.e2e.helpers import (
    answer_check,
    build_roadmap,
    nav,
    settle,
    sign_in,
    start_check,
)

ROOT = Path(__file__).resolve().parents[2]
SIZES = {
    "mobile": {"width": 390, "height": 844},
    "tablet": {"width": 820, "height": 1180},
    "desktop": {"width": 1440, "height": 900},
}
PAGES = [
    "Home",
    "Profile",
    "Career & Semester",
    "Roadmap",
    "Skills Check",
    "Results",
    "Coaching Plan",
    "Weekly Plan",
    "Progress",
    "AI Settings",
]
FRAMEWORK_RULES = {"aria-allowed-attr", "region", "list", "listitem"}
WORKED = {
    "linux_fundamentals": 1,
    "shell_scripting": 1,
    "python_for_automation": 2,
    "git_version_control": 2,
}

AXE_JS = """
async (frameworkRules) => {
  const r = await axe.run(document, { resultTypes: ['violations'] });
  const inSidebar = (target) => {
    const el = document.querySelector(target.join(' '));
    const side = '[data-testid="stSidebar"]';
    return !!el && (el.matches(side) || !!el.closest(side));
  };
  return r.violations.map(v => ({
    id: v.id, impact: v.impact, help: v.help,
    nodes: v.nodes.filter(n => !(frameworkRules.includes(v.id) && inSidebar(n.target)))
                  .map(n => ({ target: n.target.join(' '), html: n.html.slice(0, 120) })),
  })).filter(v => v.nodes.length > 0);
}
"""


def _axe_source() -> str:
    candidates = [
        os.environ.get("PCC_AXE_PATH", ""),
        str(ROOT / "node_modules/axe-core/axe.min.js"),
    ]
    for path in candidates:
        if path and Path(path).exists():
            return Path(path).read_text("utf-8")
    pytest.skip("axe-core not found: npm install axe-core, or set PCC_AXE_PATH")


def _audit(page, label: str, size: str, axe: str, record: list, problems: list) -> None:
    settle(page, 1500)
    overflow = page.evaluate(
        "() => { const d = document.documentElement; "
        "const m = document.querySelector('[data-testid=stMain]'); "
        "return Math.max(d.scrollWidth - d.clientWidth, m ? m.scrollWidth - m.clientWidth : 0); }"
    )
    if overflow > 1:
        problems.append(f"{label} at {size}: the page scrolls sideways by {overflow}px")
    page.add_script_tag(content=axe)
    violations = page.evaluate(AXE_JS, sorted(FRAMEWORK_RULES))
    record.append({"page": label, "size": size, "violations": violations})
    for v in violations:
        if v["impact"] in ("critical", "serious"):
            problems.append(
                f"{label} at {size}: {v['impact']} {v['id']} on {v['nodes'][0]['target']}"
            )


def test_no_sideways_scrolling_and_no_serious_accessibility_violations(page):
    axe = _axe_source()
    record: list[dict] = []
    problems: list[str] = []
    sign_in(page, "Audit student")
    build_roadmap(page, "devops_engineer")

    page.set_viewport_size(SIZES["desktop"])
    start_check(page)  # audits the question screen too
    for size, viewport in SIZES.items():
        page.set_viewport_size(viewport)
        _audit(page, "Skills Check (question)", size, axe, record, problems)
    page.set_viewport_size(SIZES["desktop"])
    answer_check(page, "devops_engineer", WORKED)

    for name in PAGES:  # navigate at desktop width (a phone collapses the sidebar), then resize
        page.set_viewport_size(SIZES["desktop"])
        nav(page, name)
        for size, viewport in SIZES.items():
            page.set_viewport_size(viewport)
            _audit(page, name, size, axe, record, problems)

    report_dir = os.environ.get("PCC_REPORT_DIR")
    if report_dir:
        Path(report_dir).mkdir(parents=True, exist_ok=True)
        (Path(report_dir) / "a11y-e2e.json").write_text(json.dumps(record, indent=1), "utf-8")
    assert not problems, "\n".join(problems)
