"""Compares every question as displayed in a real browser with its source text.

Usage (needs Playwright and Edge or Chrome; no project dependencies):
    python qa/check_question_rendering.py <app url> <output json>

Streamlit renders radio labels as Markdown, so characters such as $, *, _ and < can be
swallowed or restyled. Backticks are expected to disappear (they mark code) and are ignored.
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "data" / "content"


def norm(text: str) -> str:
    return " ".join(text.split())


def expected_questions() -> list[dict]:
    careers = json.loads((CONTENT / "careers.json").read_text("utf-8"))
    seen, out = set(), []
    for career in careers:
        bank = json.loads(
            (CONTENT / "question_bank" / f"{career['career_id']}.json").read_text("utf-8")
        )
        for q in bank:
            if q["question_id"] not in seen:
                seen.add(q["question_id"])
                out.append(q)
    return out


def compare_rendering(page, url: str) -> tuple[int, int, list[dict]]:
    """Opens the harness page and returns (questions, rendered radios, mismatches)."""
    questions = expected_questions()
    mismatches = []
    page.goto(url)
    page.wait_for_selector("[data-testid=stRadio]", timeout=60000)
    page.wait_for_timeout(8000)
    groups = page.locator("[data-testid=stRadio]")
    count = groups.count()
    for i in range(min(count, len(questions))):
        q = questions[i]
        group = groups.nth(i)
        stem = norm(group.locator("[data-testid=stWidgetLabel]").first.inner_text())
        shown = [norm(t) for t in group.locator("[data-testid=stRadioOption]").all_inner_texts()]
        want_stem = norm(q["stem"].replace("`", ""))
        want = [norm(o["text"].replace("`", "")) for o in q["options"]]
        problems = []
        if stem != want_stem:
            problems.append({"field": "stem", "source": want_stem, "shown": stem})
        for j, (w, s) in enumerate(zip(want, shown, strict=False)):
            if w != s:
                problems.append({"field": f"option {j + 1}", "source": w, "shown": s})
        if len(shown) != len(want):
            problems.append({"field": "option count", "source": len(want), "shown": len(shown)})
        if problems:
            mismatches.append({"question_id": q["question_id"], "problems": problems})
    return len(questions), count, mismatches


def main(url: str, out_path: str) -> int:
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        total, rendered, mismatches = compare_rendering(page, url)
        browser.close()
    if rendered != total:
        print(f"WARNING: page shows {rendered} radios, expected {total}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(
            {"questions": total, "rendered": rendered, "mismatches": mismatches},
            indent=2,
            ensure_ascii=False,
        ),
        "utf-8",
    )
    print(f"{total} questions, {len(mismatches)} with a rendering difference")
    for m in mismatches[:40]:
        first = [(p["field"], str(p["source"])[:50], str(p["shown"])[:50]) for p in m["problems"]]
        print(" ", m["question_id"], first[:2])
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
