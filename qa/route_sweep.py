"""Visits every route at three screen sizes and records what a user or a tester would notice.

For each page and size: console errors, uncaught page errors, failed or 4xx/5xx requests,
horizontal overflow, axe-core accessibility violations, and a screenshot.

Usage (needs Playwright, Edge or Chrome, and axe-core from npm):
    python qa/route_sweep.py <label> <app url> <axe.min.js> <out dir>
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROUTES = [
    "",
    "home",
    "profile",
    "career",
    "roadmap",
    "assessment",
    "results",
    "coaching",
    "weekly-plan",
    "progress",
    "ai-settings",
    "m1-preview",  # hidden unless PCC_SHOW_DEV_PAGES is set: expected to show no page
    "does-not-exist",
]
VIEWPORTS = {
    "mobile": {"width": 390, "height": 844},
    "tablet": {"width": 820, "height": 1180},
    "desktop": {"width": 1440, "height": 900},
}
IGNORED_REQUESTS = ("favicon", "_stcore/health", "_stcore/host-config")


def launch(p):
    try:
        return p.chromium.launch(channel="msedge", headless=True)
    except Exception:
        return p.chromium.launch(channel="chrome", headless=True)


def main(label: str, base: str, axe_path: str, out_dir: str) -> int:
    out = Path(out_dir)
    (out / "screenshots").mkdir(parents=True, exist_ok=True)
    axe_source = Path(axe_path).read_text("utf-8")
    results = []
    with sync_playwright() as p:
        browser = launch(p)
        for size, viewport in VIEWPORTS.items():
            context = browser.new_context(viewport=viewport)
            for route in ROUTES:
                page = context.new_page()
                console, page_errors, bad_requests = [], [], []
                page.on(
                    "console",
                    lambda m, c=console: c.append(m.text) if m.type == "error" else None,
                )
                page.on("pageerror", lambda e, c=page_errors: c.append(str(e)))
                page.on(
                    "requestfailed",
                    lambda r, c=bad_requests: c.append(f"FAILED {r.url} {r.failure}"),
                )
                page.on(
                    "response",
                    lambda r, c=bad_requests: (
                        c.append(f"{r.status} {r.url}")
                        if r.status >= 400 and not any(i in r.url for i in IGNORED_REQUESTS)
                        else None
                    ),
                )
                url = f"{base}/{route}".rstrip("/") if route else base
                page.goto(url, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector("[data-testid=stApp]", timeout=20000)
                except Exception:
                    pass
                page.wait_for_timeout(3500)
                overflow = page.evaluate(
                    "() => { const d = document.documentElement; "
                    "const main = document.querySelector('[data-testid=stMain]'); "
                    "return { page: d.scrollWidth - d.clientWidth, "
                    "main: main ? main.scrollWidth - main.clientWidth : 0 }; }"
                )
                page.add_script_tag(content=axe_source)
                axe = page.evaluate(
                    "async () => { const r = await axe.run(document, "
                    "{ resultTypes: ['violations'] }); "
                    "return r.violations.map(v => ({ id: v.id, impact: v.impact, "
                    "help: v.help, nodes: v.nodes.length, "
                    "target: v.nodes[0] ? v.nodes[0].target.join(' ') : '' })); }"
                )
                body = page.inner_text("body")
                shot = out / "screenshots" / f"{label}_{size}_{route or 'root'}.png"
                page.screenshot(path=str(shot), full_page=True)
                results.append(
                    {
                        "state": label,
                        "size": size,
                        "route": route or "(root)",
                        "title": page.title(),
                        "console_errors": console,
                        "page_errors": page_errors,
                        "bad_requests": bad_requests,
                        "overflow_px": overflow,
                        "axe_violations": axe,
                        "shows_error_text": any(
                            t in body for t in ("Traceback", "Something went wrong", "Exception")
                        ),
                        "body_preview": " ".join(body.split())[:160],
                        "screenshot": str(shot.relative_to(out)),
                    }
                )
                page.close()
            context.close()
        browser.close()
    (out / f"route-sweep-{label}.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False), "utf-8"
    )
    print(f"{label}: {len(results)} page views recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
