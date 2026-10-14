# Defect register

Priorities: **P0** critical (core journey unusable or severe security issue), **P1** an essential assessment requirement is missing or broken, **P2** significant usability, correctness or reliability issue, **P3** minor. IDs starting with Q came from the earlier QA pass on the same day (`test-reports/qa-report.md`); D are from this review.

## Counts

| Priority | Found | Fixed | Unresolved |
|---|---|---|---|
| P0 | 0 | 0 | 0 |
| P1 | 2 | 2 | 0 |
| P2 | 10 | 6 | 4 |
| P3 | 10 | 4 | 6 |
| **Total** | **22** | **12** | **10** |

## Defects

### D-001 (P1, FIXED): The product note (Task 1) was never written

- **Reproduction:** Open `docs/01_PRODUCT_NOTE.md`.
- **Expected:** A 3 to 4 page note or 6 to 8 slides answering the assessment's questions.
- **Actual:** A zero-byte file; half of the assessment had no deliverable.
- **Evidence:** `wc -c` on the file reported 0; README listed it as not written.
- **Root cause:** Milestone M7 was waiting on a question to the owner (document or slides) that was never answered, and was never closed.
- **Affected files:** `docs/01_PRODUCT_NOTE.md`, `docs/01_PRODUCT_NOTE.pdf`, `qa/build_product_note.py`, `docs/assets/`
- **Fix or action:** Wrote a 3-page document from the blueprint and the real app; screenshots and the diagram come from the running app; PDF page count and layout checked. The author must still read it.

### D-002 (P1, FIXED): Industry-ready was unreachable, and the app told students to take a check that did not exist

- **Reproduction:** Take a semester check and answer everything correctly.
- **Expected:** The four levels in the brief, including Industry ready, can all be reached.
- **Actual:** Level capped at Advanced with the note 'take the full-path check'. No full-path check existed, so no one could ever be Industry-ready.
- **Evidence:** Unit test T-03 documented the cap; searching the UI found no full-path control; the DevOps example in the brief (test every roadmap skill) was not reproducible.
- **Root cause:** The blueprint's full-path check (P1) was never built, and the coverage gate needs 100% of core skills.
- **Affected files:** `src/pcc/agents/evaluation_agent.py`, `src/pcc/workflow/workflow_controller.py`, `src/pcc/ui/pages/assessment_page.py`, results and progress pages
- **Fix or action:** Built the full-path check: every quiz skill, two questions each (28 for a career), offered only when every skill has enough questions. About 85 new tests: 56-case scenario sweep, every level reachable across both thresholds, the brief's two DevOps examples, a UI test, and a real-browser journey to Industry-ready.

### D-003 (P2, FIXED): Every roadmap month had the same deliverable sentence

- **Reproduction:** Open Roadmap and expand any month.
- **Expected:** A specific, useful focus, topics and deliverable per month.
- **Actual:** 'Produce a short artifact demonstrating X applied to a realistic task' in 64 of 64 months; capstone and interview months listed 'core concepts' and 'common pitfalls' as topics.
- **Evidence:** A script over the four templates: 1 distinct deliverable pattern in 64 months.
- **Root cause:** Template generated from a pattern, never authored.
- **Affected files:** `data/content/roadmap_templates/*.json`
- **Fix or action:** Rewrote all 64 months (focus, four topics, a distinct deliverable). Guard test fails if a deliverable repeats, a topic list is thin, or filler returns.

### D-004 (P3, FIXED): Two empty prompt files implied features that do not exist

- **Reproduction:** List `src/pcc/ai/prompts/`.
- **Expected:** Only prompts that are used.
- **Actual:** `custom_career_draft_v1.md` and `mistake_explanation_v1.md` were 0 bytes and referenced nowhere.
- **Evidence:** `wc -c`; grep found no references in code or tests.
- **Root cause:** Created from the blueprint's file list and never filled.
- **Affected files:** `src/pcc/ai/prompts/`
- **Fix or action:** Removed.

### D-005 (P3, FIXED): A semester check and a full-path check would have been compared by overall score

- **Reproduction:** Take a semester check, then a full-path check; open Progress.
- **Expected:** No like-for-unlike comparison.
- **Actual:** Found while building D-002, before release: it would have shown '+40 points' between checks that cover different skills.
- **Evidence:** Unit and UI tests written first.
- **Root cause:** Progress compared any two attempts.
- **Affected files:** `src/pcc/domain/progress.py`, `src/pcc/ui/pages/progress_page.py`
- **Fix or action:** The overall change is not shown across scopes; the page says so and compares skill by skill. Tested.

### Q-01 (P2, FIXED): Dollar signs vanished from content (Streamlit read `$...$` as maths)

- **Reproduction:** Open the MongoDB aggregation question.
- **Expected:** Options show `$group`, `$sum`.
- **Actual:** Options showed 'group by customer with a sum'.
- **Evidence:** Browser comparison of all 318 questions with their source: 1 difference.
- **Root cause:** Markdown maths syntax in labels.
- **Affected files:** `src/pcc/ui/text.py` and six UI files
- **Fix or action:** `safe_md` at every place content is shown. Unit, UI (mutation-checked) and browser tests.

### Q-02 (P2, FIXED): An answer was lost when Next was pressed before the app finished updating

- **Reproduction:** Choose an option and press Next at once.
- **Expected:** The answer is kept.
- **Actual:** '8 of 12 answered' with four questions blank.
- **Evidence:** Browser test and screenshot; a same-step UI test fails without the fix ('0 of 12').
- **Root cause:** The answer was stored only when its question was redrawn.
- **Affected files:** `src/pcc/ui/components/check_wizard.py`
- **Fix or action:** Answer stored in the radio's change callback.

### Q-03 (P2, FIXED): Reloading mid-check lost every answer

- **Reproduction:** Answer questions, reload the page.
- **Expected:** The check resumes with the answers.
- **Actual:** The same questions, all blank.
- **Evidence:** Browser test.
- **Root cause:** Answers lived only in browser session state.
- **Affected files:** `schema/001_initial_schema.sql`, repository, controller, wizard
- **Fix or action:** Draft table, deleted on submission, never used for scoring.

### Q-04 (P2, FIXED): The AI Settings page sent the saved key to the browser and a provider error could echo it

- **Reproduction:** Save a key and reopen AI Settings.
- **Expected:** The key never leaves the server.
- **Actual:** The password box was pre-filled with the stored key.
- **Evidence:** Code review; UI tests.
- **Root cause:** Pre-filled input; raw exception text shown.
- **Affected files:** `src/pcc/ui/pages/ai_settings_page.py`
- **Fix or action:** Box starts empty and keeps the saved key when blank; key redacted from errors.

### Q-05 (P3, FIXED): A display name could become a clickable link

- **Reproduction:** Sign in as `[x](http://evil.example)`.
- **Expected:** Shown as text.
- **Actual:** A link, even after escaping the characters.
- **Evidence:** Browser test and failure screenshot.
- **Root cause:** Streamlit auto-links bare addresses.
- **Affected files:** `src/pcc/ui/text.py`
- **Fix or action:** Escaping plus an invisible character inside address patterns.

### Q-06 (P2, FIXED): Accessibility: contrast, heading order, an unreachable scroll region, identical tab titles

- **Reproduction:** axe-core and Lighthouse on every page.
- **Expected:** No serious findings caused by this project.
- **Actual:** Contrast under 4.5:1 in several places; h1 to h3 jumps; one title for every page.
- **Evidence:** axe-core results in `test-reports/data/`.
- **Root cause:** Streamlit defaults and unstructured headings.
- **Affected files:** `src/pcc/ui/theme.py`, `src/pcc/main.py`, pages
- **Fix or action:** Fixed; a browser test fails on any new critical or serious finding outside the sidebar.

### Q-07 (P3, FIXED): Default page declared a URL that does not exist; four asserts; one unclosed connection

- **Reproduction:** Open `/home`; run Bandit.
- **Expected:** No console error; no `assert` for control flow; connections closed.
- **Actual:** Console error; Bandit low findings; a ResourceWarning.
- **Evidence:** Browser console; Bandit; pytest.
- **Root cause:** Minor.
- **Affected files:** `src/pcc/main.py`, controller, AI settings page
- **Fix or action:** Fixed.

### D-006 (P2, OPEN): Only four computer science careers are supported

- **Reproduction:** Type 'cybersecurity' or 'astronaut'.
- **Expected:** The brief lists Cybersecurity, VLSI and astronaut as example fields.
- **Actual:** A clear 'not supported yet' message and the list of four.
- **Evidence:** Browser test of free-text careers.
- **Root cause:** Scope decision (blueprint 1.3): curated roadmaps and questions need content per career.
- **Affected files:** `data/content/`, `src/pcc/domain/career_resolver.py`
- **Fix or action:** None in code. Adding a career is content work. The note states the decision.

### D-007 (P2, OPEN): Only the quiz assessment method is built

- **Reproduction:** Look at capstone and interview preparation in Semester 6.
- **Expected:** Voice, written and assignment methods exist.
- **Actual:** Shown as 'assessed later', never scored with a quiz.
- **Evidence:** Unit test T-21.
- **Root cause:** Planned for later (note section 5).
- **Affected files:** `src/pcc/domain/enums.py`
- **Fix or action:** None. The selection rule exists and is explained in the note.

### D-008 (P2, OPEN): About 300 questions are unreviewed drafts, and the DevOps 'human reviewed' label is unconfirmed

- **Reproduction:** Inspect `source` and `reviewed_on` in the question banks.
- **Expected:** Questions reviewed by a person before levels are trusted.
- **Actual:** `ai_drafted` with no review date for about 300; the DevOps label has no record of a reviewer.
- **Evidence:** `docs/02_QUESTION_AUTHORING_GUIDE.md` (current state); assistant-only checks found and fixed a question with two correct answers and an answer-length cue.
- **Root cause:** Content was written by the assistant.
- **Affected files:** `data/content/question_bank/*.json`
- **Fix or action:** A person must review them. The note and README say so.

### D-009 (P2, OPEN): Sidebar accessibility findings: one critical, two serious

- **Reproduction:** axe-core on any page.
- **Expected:** No critical or serious findings.
- **Actual:** aria-allowed-attr on the sidebar; list and listitem on the navigation.
- **Evidence:** Reproduced on a minimal Streamlit app; list and listitem appear only with grouped navigation.
- **Root cause:** Streamlit's own markup.
- **Affected files:** `src/pcc/main.py` (navigation sections)
- **Fix or action:** Owner's choice: keep the grouped sidebar, or use a flat list to remove two of the three.

### D-010 (P3, OPEN): Lighthouse performance 38 to 59, layout shift up to 0.5

- **Reproduction:** Lighthouse on any page.
- **Expected:** Better scores.
- **Actual:** Streamlit's bundle and progressive rendering dominate.
- **Evidence:** `test-reports/lighthouse/summary.md`; removing this project's layout CSS changed little.
- **Root cause:** Framework.
- **Affected files:** n/a
- **Fix or action:** Accept for a local tool.

### D-011 (P3, OPEN): Roadmaps are curated per career, not generated per student

- **Reproduction:** Compare roadmaps of two students on one career.
- **Expected:** Personalised.
- **Actual:** Identical; an AI may only reword months.
- **Evidence:** Roadmap agent and validator code.
- **Root cause:** Design choice for reliability (the AI cannot change skill order).
- **Affected files:** `src/pcc/agents/roadmap_agent.py`
- **Fix or action:** None. Disclosed in the README and the note.

### D-012 (P3, OPEN): Console 404s when a page is opened by its URL

- **Reproduction:** Open `/profile` directly.
- **Expected:** A clean console.
- **Actual:** 404 on `/profile/_stcore/health`.
- **Evidence:** Reproduced on a minimal Streamlit app.
- **Root cause:** Framework.
- **Affected files:** n/a
- **Fix or action:** Accept; the browser tests ignore only these two URLs.

### D-013 (P3, OPEN): Python 3.14 on Windows: the server crashed twice in the file-watcher threads

- **Reproduction:** Long browser test runs.
- **Expected:** A stable server.
- **Actual:** `Fatal Python error: _PySemaphore_Wakeup`.
- **Evidence:** Server logs; no crash in any full browser run after the change.
- **Root cause:** Interpreter-level fault in the watcher.
- **Affected files:** `.streamlit/config.toml`
- **Fix or action:** File watcher turned off. Python 3.12 or 3.13 is untested.

### D-014 (P3, OPEN): Live AI output was verified only for the DevOps journey, and not after the latest changes

- **Reproduction:** n/a
- **Expected:** Live check for each career.
- **Actual:** Offline and scripted-fake coverage for the rest.
- **Evidence:** Earlier session records.
- **Root cause:** Cost and no key used in this review.
- **Affected files:** AI paths
- **Fix or action:** Run one live journey per career before a demo with an AI.

### D-015 (P3, OPEN): One class, WorkflowController, holds almost every use case

- **Reproduction:** Open `src/pcc/workflow/workflow_controller.py`.
- **Expected:** Use cases split by concern (check, coaching, tutor, weekly plan, progress).
- **Actual:** About 1,100 lines and 51 methods in one class (module quizzes, the wish list and game state were added on 2026-10-14).
- **Evidence:** `wc -l` and a method count; the file is the most changed in this project.
- **Root cause:** It grew one feature at a time; each addition was small and well tested.
- **Affected files:** `src/pcc/workflow/workflow_controller.py`
- **Fix or action:** None needed for delivery. Split by use case before adding another large feature.
