"""Builds test-reports/functional-tests.md from pytest JUnit XML files.

Usage: python qa/make_functional_report.py <out.md> <junit.xml> [<junit.xml> ...]
Every test is listed with its result; nothing is summarised away or rewritten.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

AREAS = {
    "test_routes_and_inputs": "Routes, hidden pages and hostile or invalid input (browser)",
    "test_journeys": "Whole student journeys, checked against the database (browser)",
    "test_behaviours": "Skills check, coach and weekly plan behaviour (browser)",
    "test_responsive_and_a11y": "Responsive layout and accessibility (browser)",
    "test_question_rendering": "Every question displayed exactly as written (browser)",
}


def collect(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        root = ET.parse(path).getroot()
        for case in root.iter("testcase"):
            status = "pass"
            note = ""
            for child in case:
                if child.tag in ("failure", "error"):
                    status = "FAIL"
                    note = (child.get("message") or "").splitlines()[0][:160]
                elif child.tag == "skipped":
                    status = "skipped"
                    note = (child.get("message") or "")[:120]
            module = case.get("classname", "").rsplit(".", 1)[-1]
            rows.append(
                {
                    "module": module,
                    "name": case.get("name", ""),
                    "status": status,
                    "seconds": float(case.get("time", 0)),
                    "note": note,
                }
            )
    return rows


def main(out: str, junit_files: list[str]) -> None:
    rows = collect(junit_files)
    counts = {s: sum(r["status"] == s for r in rows) for s in ("pass", "FAIL", "skipped")}
    lines = [
        "# Functional test results",
        "",
        f"{len(rows)} browser tests: **{counts['pass']} passed**, **{counts['FAIL']} failed**, "
        f"{counts['skipped']} skipped. Generated from pytest JUnit XML; each row is one test.",
        "",
    ]
    by_module: dict[str, list[dict]] = {}
    for row in rows:
        by_module.setdefault(row["module"], []).append(row)
    for module, items in by_module.items():
        lines += [
            f"## {AREAS.get(module, module)}",
            "",
            "| Test | Result | Seconds | Note |",
            "|---|---|---|---|",
        ]
        for r in items:
            lines.append(f"| `{r['name']}` | {r['status']} | {r['seconds']:.1f} | {r['note']} |")
        lines.append("")
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}: {counts}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
