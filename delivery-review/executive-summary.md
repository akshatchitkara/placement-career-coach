# Executive summary: pre-delivery review

Placement Career Coach, reviewed 12 October 2026. Source of truth: the original assessment, `PM Assignment1.docx`. Implementation reference: `docs/00_PROJECT_BLUEPRINT.md`. Everything stated here as verified was executed in this review; items I could only read are marked as inspection.

## Verdict in brief

The prototype now meets every mandatory requirement of the assessment (22 of 22 verified), and the core journey works end to end for all four careers. **It was not deliverable when this review began:** half of the assessment had no deliverable, and one of the four required levels could not be reached. Both are fixed. What remains is real but does not block delivery: narrow career coverage (a stated scope decision), a quiz-only assessment, about 300 questions no person has reviewed, and accessibility and performance limits that come from Streamlit.

Compliance with the assessment, using equal weights (an internal estimate, not an official score): **86.7%** (26 of 30), up from about 43% at the start of the review. See `assessment-compliance.md`.

## What the review found at the start

1. **Task 1, the product note, did not exist.** `docs/01_PRODUCT_NOTE.md` was zero bytes. That is nine of the assessment's questions unanswered and one of its two tasks undelivered.
2. **Industry-ready could not be reached.** The assessment names four levels. The rules require evidence for 100% of a career's skills, only a "full-path check" can supply that, and it had never been built. A student who answered every question correctly was told to "take the full-path check", which did not exist.
3. **The roadmap, the first thing a student sees, was filler.** All 64 months had the same deliverable sentence, and two stages listed "core concepts" and "common pitfalls" as topics.
4. **The assessment's own DevOps example could not be reproduced:** it tests the student on every roadmap skill, but the product only tested one semester.

## What was done

| Area | Result |
|---|---|
| Product note | Written as a 3-page document with a diagram and screenshots from the running app (`docs/01_PRODUCT_NOTE.md` and `.pdf`). It answers each question in the assessment. The author must read it and confirm it says what they mean |
| Full-path check | Built: every quiz skill on the roadmap, two questions each (28 for a career). All four levels are now reachable, proved on both sides of both thresholds, for all four careers, and in a real browser. The assessment's two DevOps examples (basics only is Beginner; containers but weak on Terraform is Intermediate) are reproduced by tests |
| Consistency of the stages | A sweep over all four careers and all 14 skills each (56 cases) makes each skill the weakest in turn and checks that the weakest skill, the roadmap position, the coaching plan and its links to missed questions, and the weekly plan all agree. All 56 pass |
| Roadmaps | All 64 months rewritten with a specific focus, four topics and a distinct deliverable, with a guard test |
| Cross-scope progress | Found while building the full-path check: a semester check and a full-path check would have been compared by overall score. Fixed before it shipped |
| Earlier QA pass, same day | Twelve further defects fixed, including content corruption in one question, lost answers on reload and on a quick click, and a saved API key being sent to the browser (`test-reports/`) |

## Product assessment

**Strengths.** The journey is complete and has no dead ends in anything I exercised: choose, roadmap, check, level, weakest skill, coaching, weekly plan, re-check, progress. Scoring is deterministic and explainable: the level rules have no gaps or overlaps (tested at 0, 39.9, 40, 64.9, 65, 84.9, 85 and 100), every skill shows right over answered, and results can be re-derived from stored answers. The AI only writes advice, is validated, and falls back, so the product works without a key. Nothing I found is faked: the roadmap is honestly labelled curated, scores come from code, and coaching tasks are tied to real missed questions.

**Weaknesses.**
- **Career coverage is narrow by decision.** Four computer science careers. The assessment's examples include Cybersecurity, VLSI and an astronaut; typing those gets a clear "not supported yet". The note defends this choice, but a literal reader of the assessment may mark it down.
- **Only the quiz method exists.** The method-selection rule is in code and explained, but written, assignment and voice assessments are "later".
- **Personalisation is in the assessment, not the plan.** Two students on the same career see the same roadmap.
- **Trust in the levels depends on the questions**, about 300 of which are drafts no person has reviewed.

## Engineering assessment

**Architecture and maintainability (inspection plus tooling).** A clear layering: pure domain logic (scoring, levels, weekly plan, progress) with no I/O; agents with validators and fallbacks; one AI interface with swappable providers; a workflow controller; repositories with parameterised queries; thin UI pages that hold no scoring or SQL. About 6,000 lines of application code and 5,800 of tests. The weak spot is `WorkflowController`: 1,000 lines and 45 methods in one class. It is well tested and not a delivery risk, but it should be split before the next large feature.

**Correctness (executed).** 481 unit, integration and headless UI tests and 35 real-browser tests; strict type checking on the domain and workflow packages; lint clean; content validation clean; 98% coverage on the measured scoring, weekly-plan and progress modules (the coverage scope is those modules only, not the UI).

**AI integration (executed with fakes; live for one career earlier).** Output is parsed, validated by named rules, and replaced by a curated fallback on failure. Seven failure modes (provider down, crash, empty, not JSON, wrong shape, prompt injection, hostile JSON) are exercised end to end. A prompt-injection attempt against the coach returned a refusal with no score, level or link. Live provider output was verified for the DevOps journey in earlier sessions only.

**Security (executed).** Parameterised SQL; HTML and SQL typed into names and careers are inert; no secret in tracked files; no known vulnerable dependency; Bandit shows two false positives. Fixed during the earlier QA pass: the saved AI key was being sent to the browser and could appear in an error. Still accepted: the key is stored in plain text in the local database, which is fine for a single-user prototype and not for a hosted one.

**Performance and accessibility (executed).** Lighthouse: performance 38 to 59, accessibility 83 to 87, best practices 96 to 100, SEO 82. The app's own markup passes axe-core apart from findings caused by Streamlit's sidebar; the performance and layout-shift scores are Streamlit's front end. Fine for a local prototype, and a real limit if this were a public product.

**Fake functionality check.** Searched for buttons that do nothing, placeholder screens and hardcoded results. None found. The demo profiles (Asha, Ravi, Meera) are seeded through the same controller code as real use. The roadmap is curated and labelled so. The only hardcoded behaviour that affects a student is deterministic scoring, which the assessment requires.

## Minimum work before submitting

1. Read the product note and confirm it says what you mean (it was written by the assistant).
2. Review at least the DevOps Semester 3 questions, which are the demo path.
3. Decide whether to keep the grouped sidebar (an approved design choice that causes two accessibility findings).
4. Submit both deliverables together; timing is outside the repository.

See `delivery-readiness.md` for the recommendation and `defect-register.md` for every defect.
