# QA report

Placement Career Coach, 12 October 2026. Tested on Windows 11 with Python 3.14.3, Streamlit 1.65, Microsoft Edge (browser tests) and Google Chrome (Lighthouse). Everything below was run for real; the evidence is in this folder.

## Result

| Area | Result |
|---|---|
| Automated tests (unit, integration, headless UI) | **395 passed**, 0 failed, 0 warnings. Plus 34 browser tests that run on request |
| Browser tests (real Edge, `PCC_E2E=1`) | **34 passed**, 0 failed |
| Route sweep: 13 routes x 3 sizes x signed out and in | **78 of 78 page views ok** (definition in `functional-tests.md`) |
| Question display: all 318 questions compared with their source text in a browser | **0 differences** (1 before the fix) |
| Lint, formatting, types (domain and workflow, strict), content validation | Clean |
| Dependency audit | No known vulnerabilities |
| Accessibility (axe-core) | No critical or serious findings except 4 that come from Streamlit's own sidebar |
| Lighthouse | Performance 38 to 59, accessibility 83 to 87, best practices 96 to 100, SEO 82. The shortfalls are Streamlit's (see below) |

**Verdict:** the app works end to end for all four careers in all four semesters, and the defects found by this pass are fixed and covered by tests. What remains is framework behaviour that this project cannot change, and the open items under "Unresolved". This is a local single-user prototype; read the limits before relying on the numbers.

## What was tested

Discovery: a Streamlit app with ten pages (Home, Profile, Career & Semester, Roadmap, Skills Check, Results, Coaching Plan, Weekly Plan, Progress, AI Settings), one hidden developer page, one role (a student identified by a display name, no login), a local SQLite database and an optional AI provider. There is no HTTP API, so there are no API tests; backend behaviour was checked through the workflow controller and by reading the database after browser actions.

| Layer | What was done |
|---|---|
| Browser journeys | Four full journeys (one per career, in Semesters 3, 4, 5 and 6) from sign-in to results, coaching, weekly plan and progress, each checked against the database rows. A weak-result journey, and a baseline plus re-check |
| Behaviour | Question counter, Back keeps the answer, unanswered list, reload mid-check, a stale second tab after a submission elsewhere, coach chat with a prompt-injection attempt, the 300-character limit, the practice quiz, ticking tasks, the time budget, the calendar download |
| Input | Blank, over-long, Unicode, HTML and SQL display names; free-text careers: unsupported, empty, SQL, script, alias; changing career after a roadmap |
| Layout and accessibility | Every page at 390, 820 and 1440 px: sideways scroll, axe-core violations, screenshots |
| Content display | Every question stem and option compared with its source text as drawn by the real widgets |
| Performance | Lighthouse on all ten pages, mobile and desktop |
| Security | Bandit, pip-audit, secret scan, injection tests, review of the AI Settings page |

## Defects found and fixed

| # | Severity | Defect | How it was found | Fix and regression test |
|---|---|---|---|---|
| 1 | High | **Dollar signs vanished from content.** Streamlit reads a pair of `$` as maths, so the MongoDB question showed "match on customer followed by skip" and "group by customer with a sum of the amount" with the operator names stripped. The same renderer is used for coaching text and weekly tasks, and two practice templates contain `$` | Comparing all 318 questions with their source in a browser | `safe_md` at every place content is shown (6 files). Unit tests; a deterministic UI test (mutation-checked); the browser comparison. My first patch missed the skills-check widget itself; the test sampled a random check and passed by luck, which is why the UI test now builds its own question |
| 2 | High | **An answer was lost when the student chose an option and pressed Next before the app finished its first update.** Both changes arrived together, the page moved on, and the earlier question was never drawn again. The student would find it "unanswered" at the end | Browser test clicking at machine speed; the screenshot showed "8 of 12 answered" with questions 2, 5, 6 and 10 missing | The answer is stored in the radio's own change callback, which runs before the page moves. Regression test (mutation-checked: without the fix it shows "0 of 12 answered") |
| 3 | Medium | **Reloading the page in the middle of a check lost every answer** (the check resumed with the same questions but blank) | Browser test written to describe the expected behaviour | New `assessment_drafts` table; the check restores the answers and resumes at the first unanswered question; the draft is deleted on submission and can never change what is graded. 6 integration tests, a UI test, a browser test |
| 4 | Medium | **The AI Settings page sent the saved API key back to the browser, and a provider error could echo it** | Code review | See `security-and-accessibility.md` S1, S2 |
| 5 | Low | **A display name could become a clickable link** (escaping was not enough: Streamlit auto-links bare addresses) | Browser test; the failure screenshot showed the link | Escaping plus an invisible character inside address patterns. Tested in a browser |
| 6 | Medium | **Accessibility:** contrast failures on captions, step labels, badges, success banners and metric changes; heading levels skipping; an unreachable scroll region | axe-core and Lighthouse | See `security-and-accessibility.md` A1 to A3 |
| 7 | Medium | **Every page had the same browser-tab title** | Route sweep | One title per page |
| 8 | Low | The default page declared a URL (`/home`) that does not exist, which logged a console error | Browser console check | The Home page is served at `/` |
| 9 | Low | Four `assert` statements for type narrowing; an unclosed database connection on one page | Bandit; a `ResourceWarning` | Explicit errors; `closing(...)` |

Earlier in this session (before the formal QA pass): the answer-length cue in the new questions (70% of right answers were the longest option; now 36%) and one question with two correct answers.

## Unresolved

| # | Severity | Issue | Why | Recommendation |
|---|---|---|---|---|
| U1 | Serious (accessibility) | Two sidebar list findings and one critical ARIA attribute finding on every page | Streamlit's own markup; the list findings appear only because navigation is grouped into sections | Your decision: keep the grouped sidebar, or switch to a flat list of ten links to remove two of the three |
| U2 | Medium (performance) | Lighthouse performance 38 to 59; layout shift up to 0.5; mobile LCP about 14 to 18 s under simulated throttling | Streamlit's front-end bundle and progressive rendering. Removing this project's layout CSS did not change it (Progress stayed at 0.49) | Accept for a local tool. A different front end would be needed to change it |
| U3 | Low | Console 404s when a page is opened by its URL (`/profile/_stcore/health`) | Reproduced in a minimal Streamlit app with none of this project's code | Accept. The browser tests ignore only these two URLs |
| U4 | Low | A button click that arrives while an earlier update is still running is dropped by Streamlit | Reproduced in a harness; unaffected by the fix for defect 2. The server-side work for one update is about 9 ms, so a person is very unlikely to hit it | The test helper now waits for the app to be idle |
| U5 | Medium (reliability) | On Python 3.14 and Windows the server process crashed twice in Streamlit's file-watcher threads | An interpreter-level fault | Mitigated by turning the file watcher off. Using Python 3.12 or 3.13 is untested here |
| U6 | High (content) | About 300 questions are `ai_drafted` and have not been reviewed by a person; the DevOps "human reviewed" label is unconfirmed | Not something a test can settle | A person must review them before the levels can be trusted |

## Tests that could not be run, and why

| Not run | Reason |
|---|---|
| Firefox and Safari (WebKit) | Not installed here. Only Chromium-family browsers (Edge, Chrome) were used |
| Real phones and touch input | No devices. A 390 px emulated viewport was used |
| Screen reader and keyboard-only walkthrough | Needs a person and assistive software; axe-core finds only part of the problems |
| Live AI provider in this pass | No key was used and it costs money. The AI paths are tested with scripted fake clients and seven failure drills, and an earlier session verified live Anthropic output; the new tutor chat was verified live then too. Not repeated after the later changes |
| Authentication, roles, multi-user isolation across hosts | The app has none by design |
| API tests | There is no HTTP API |
| Load, stress and soak tests; SQLite under many users | Out of scope for a single-user prototype |
| Linux and macOS | Windows only |
| An upgrade of a long-lived real database to the new tables | The app adds missing tables when it starts and this worked on test databases and during earlier restarts of your server; I did not inspect your real database |
| Visual regression comparison | Screenshots were captured and the key ones inspected by eye, not compared automatically |

## Fixes to the test process itself

Three of the browser-test failures were mistakes in my tests, not in the app, and are worth knowing about because they would mislead anyone reading the history: filling a box with `fill()` skips the browser's length limit; a "double submit from a second tab" cannot exist once the first tab submits (the second tab correctly moves on); and clicking the instant new content appears loses the click while Streamlit is still updating. The helpers now type like a person and wait for the app to be idle. No assertion was weakened to get a pass: two vacuous assertions I wrote in a first draft were removed before the first run.

## Evidence in this folder

| Path | Contents |
|---|---|
| `functional-tests.md` | Every browser test and the route-sweep matrix |
| `security-and-accessibility.md` | Findings, tools, what was not tested |
| `lighthouse/` | HTML reports for Home, Skills Check, Results and Progress (mobile and desktop) and `summary.md` for all ten pages |
| `screenshots/` (`data/screenshots/`) | 78 page screenshots from the route sweep; failure screenshots are written to `screenshots/failures/` when a browser test fails |
| `data/` | Route-sweep and accessibility results as JSON |
| `logs/` | pytest with coverage, ruff, mypy, bandit, pip-audit, the final browser-test JUnit file |

## How to repeat this

```bash
python -m pytest --cov                       # 395 tests, no browser needed
pip install -r requirements-e2e.txt          # Playwright
npm install axe-core                         # for the accessibility test
PCC_E2E=1 python -m pytest tests/e2e         # 34 browser tests (about 10 minutes, needs Edge or Chrome)
python qa/route_sweep.py <label> <url> <axe.min.js> <out dir>
```
