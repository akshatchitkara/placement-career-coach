# Acceptance Test Report

Each milestone's acceptance items are recorded here as **Pass**, **Fail**, or **Not verified** (blueprint Section 17.4, 24.10).

## M0 — Foundation

### Full re-verification pass (2026-10-09, second session)

| Item | Result | Notes |
| --- | --- | --- |
| `make lint` (`ruff check`, `ruff format --check`, `mypy domain/ workflow/`) | **Pass** | Clean across `src/`, `tests/`, `scripts/` |
| `make test` (`pytest --cov`) | **Pass** | 1/1 passed: `test_init_schema_is_idempotent` (schema uses `CREATE TABLE/INDEX IF NOT EXISTS`, confirmed safe to re-run) |
| `make db-init`, run twice | **Pass** | Idempotent, no error on second run |
| `make validate-content` | **Pass** | No-op stub (no content yet, by design -- content lands in M1) |
| `make db-reset` | **Pass** | Deletes and recreates the DB file cleanly |
| Every page route serves and every page's `render()` executes without exception | **Pass** | Verified two ways: (1) full headless `streamlit run`, curled all 9 `url_path` routes -&gt; HTTP 200, no server traceback; (2) `AppTest` driving each page's `render()` directly -- the first attempt gave a false pass because pointing `AppTest.from_file` at a page module never calls `render()` (nothing executes); fixed by wrapping each page in a one-line script that imports and calls `render()`, which now genuinely exercises the code |
| AI Settings page: mock / openai / nvidia / custom / anthropic selectable, fields show correctly per provider | **Pass** | `AppTest` interaction script: selectbox + text_input counts verified per provider (mock=0 fields, others=3) |
| AI Settings page: Test Connection against a real endpoint with a fake key | **Pass** | OpenAI and Anthropic both returned a clean `401 Unauthorized` surfaced as `st.error(...)` -- confirms requests are correctly formed and reach the real API, and that failures never crash the page |
| AI Settings page: Test Connection against an unreachable custom URL | **Pass** | Connection-refused surfaced as `st.error(...)`, no crash |
| AI Settings page: Save + reload persists the active provider | **Pass** | Saved `openai`, reloaded a fresh page instance, selectbox pre-selected `openai` |
| NVIDIA default base URL prefill | **Pass** | `https://integrate.api.nvidia.com/v1` |

**Bug found and fixed during this pass:** `anthropic_ai_client.py` passed `temperature=` to `Messages.create()`, which crashed with `TypeError: unexpected keyword argument 'temperature'` on the installed `anthropic==1.13.0` SDK. Confirmed via `inspect.signature` and a full source grep that this SDK version no longer accepts `temperature` on that call at all (not a version pin issue -- genuinely removed). Fixed by dropping the argument from the API call while keeping it on the `AiClient.generate()` interface (so callers stay provider-agnostic; it's a documented no-op for Anthropic). Re-verified: a fake key now reaches the real API and gets a clean `401` instead of crashing.

**Scaffolding gap found and fixed:** `scripts/validate_content.py`, `reset_demo.py`, and `generate_question_drafts.py` were listed in Section 12 and referenced by the Makefile but were never created in the first M0 pass. Added as no-op/partial stubs so `make validate-content` and `make db-reset` don't fail before M1.

| Earlier items (first pass) | Result | Notes |
| --- | --- | --- |
| `make run` opens the app shell | **Pass** | Headless Streamlit run, `HTTP 200` |
| Mock AI client callable end-to-end with no key | **Pass** | `build_ai_client(AiProviderConfig())` -&gt; `MockAiClient`, `.generate()` returns `"{}"` |
| AI Settings page can write/read a row in `ai_provider_settings`; factory picks it up | **Pass** | Saved an `openai` config, reloaded it, factory returned `OpenAiCompatibleAiClient` |

Deviations noted: local Python available is 3.14 (blueprint specifies 3.11) -- no 3.11-only feature is in use. All interactive verification used an isolated `PCC_DB_PATH` so test runs don't mutate the real demo database; the real `data/runtime/pcc.db` was reset via `make db-reset` after manual testing left it in a non-default state.

## M1 — Content and scoring core

| Item | Result | Notes |
| --- | --- | --- |
| Content validator passes against authored content | **Pass** | `scripts/validate_content.py` -&gt; "Content validation passed: 4 careers, 58 skills." |
| Skill maps + roadmap templates for all 4 careers | **Pass** | Generated programmatically from the blueprint's Section 2.3 tables (avoids hand-transcription errors across 64 month entries); 16 months each, validated against V-RM-01/02/03/05/07 equivalents |
| DevOps Sem 3 question bank (24 approved questions) | **Pass** | 4 skills x 6 questions, exactly 2/2/2 easy/medium/hard per skill, hand-authored for technical accuracy; `compute_skill_assessability` confirms all 4 skills assessable |
| Tier B careers (MEAN/Java/AI) have roadmaps but no question bank yet | **Pass** | By design (Section 2.1) -- `load_question_bank` returns `[]` gracefully, no skill in those careers reports assessable |
| `domain/scoring/*` pure functions | **Pass** | scoring_engine, level_classifier, weakest_skill_selector, coverage_calculator, roadmap_position_locator -- 96% line coverage (exceeds the 90% bar in Section 6) |
| Level boundary tests (Section 17.2: 0/39.9/40/64.9/65/84.9/85/100) | **Pass** | All 8 boundaries correct |
| T-01 same answers scored twice -&gt; identical | **Pass** |  |
| T-02 Industry-ready downgraded when one sufficient skill &lt; gate | **Pass** | Note names the failing skill |
| T-03 Industry-ready downgraded when coverage &lt; 100% | **Pass** | Note recommends the full-path check |
| T-04 full-path, 100% coverage, all skills &gt;= 60, overall &gt;= 85 -&gt; Industry-ready | **Pass** |  |
| T-05 skill with 1 answered question not eligible as weakest | **Pass** |  |
| T-06 tied lowest skills -&gt; earlier roadmap position wins | **Pass** |  |
| T-07 no skill with sufficient evidence -&gt; no weakest skill invented | **Pass** |  |
| T-08 weakest skill &gt;= mastery threshold -&gt; "no major gap", next skill offered | **Pass** |  |
| T-20 config snapshot: old attempt unaffected by later threshold changes | **Pass** | Proven by construction -- every scoring function takes config as a parameter, never reads global mutable state |
| T-21 unbuilt skill_type (build/communication) -&gt; "assessed later", not scored | **Pass** | `is_quiz_assessable` only true for `conceptual` |
| T-22 skill with fewer than 6 approved questions -&gt; not assessable | **Pass** | Also verified the 2/2/2-per-difficulty requirement independently of raw count |
| Worked example (Section 10.7) reproduced exactly | **Pass** | Linux/Shell 33.3%, Python/Git 66.7%, overall 50.0 |
| Full test suite + lint + mypy + app smoke test | **Pass** | 43/43 tests, `ruff check`/`format` clean, `mypy` clean on `domain/`, headless `streamlit run` still HTTP 200 with M1 content loaded |

**Design decision made during this pass:** `Skill.career_id` (singular) was changed to `Skill.career_ids: list[str]` before any content was authored. The blueprint's own skill maps (Section 2.3) reuse `git_version_control` across DevOps/MEAN/AI, `system_design_basics` across MEAN/Java, and `interview_preparation` across all four careers -- a single-career field would have forced duplicate skill_ids (rejected by the uniqueness rule) or duplicate skill definitions. Logged as decision A22.

**Scaffolding gap found and fixed:** `tests/conftest.py` was listed in Section 12 but never created in M0; added now with the shared `skill_score_factory` fixture.

`make` **is not installed in this dev shell** (git-bash on Windows) -- all Makefile-wrapped commands were verified by running their underlying command directly (`ruff`, `mypy`, `pytest`, `python scripts/validate_content.py`), not via the `make` binary itself.

## M2 — Roadmap flow

| Item | Result | Notes |
| --- | --- | --- |
| Career picker (4 careers + typed career) and semester select | **Pass** | `career_selection_page`; headless UI test drives it |
| Roadmap agent: AI rewords, never reorders; one repair attempt; template fallback | **Pass** | `agents/roadmap_agent.py`; mock mode skips AI and uses the template directly |
| Roadmap validator V-RM-01..08 | **Pass** | V-RM-06 enforced through V-RM-04 (fixed sequence = template, which respects prerequisites) |
| SQLite profile + roadmap persistence | **Pass** | `profile_repository`, `roadmap_repository`; one active roadmap per profile |
| Roadmap page shows Sem 3-6 and 16 months for DevOps | **Pass** | 16 expanders, 4 semester headings, current semester expanded |
| T-09 missing semester/month rejected, template used | **Pass** | validator unit tests + agent fallback test |
| T-10 AI reorders skills -&gt; rejected (V-RM-04), template used | **Pass** |  |
| T-14 / V-RM-08 URL in AI text rejected | **Pass** | roadmap part only; coaching part lands in M4 |
| T-15 AI disabled/unavailable -&gt; DevOps flow completes with template | **Pass** | integration test with an unavailable AI client |
| T-16 empty/malformed AI response -&gt; no crash, fallback (roadmap part) | **Pass** | `""`, `{}`, non-JSON, wrong shape, array |
| T-18 close and reopen: profile + roadmap restored (weekly plan/results part is M3+) | **Pass** (partial) | new controller on same DB file |
| T-19 non-CS career -&gt; "not supported yet" + supported list, no roadmap | **Pass** | Doctor, Chartered Accountant, Pilot, Chef; invalid characters/length rejected |
| Full suite + lint + mypy + app smoke | **Pass** | 89 tests, ruff clean, mypy clean on `domain/` + `workflow/`, headless full-app render has no exceptions |
| Live AI provider personalising a roadmap | **Not verified** | no API key available; only scripted fake clients were exercised |
| Profile, career picker and roadmap pages in a real browser | **Pass** | see "Real-browser verification (M2-M4)" below |

**Fixes while integrating:** mypy now follows imports from `workflow/` into `ai/` and `content/`; typed `parse_json_object`, `_read_json` and the OpenAI client return so `mypy` stays clean.

## M3 — Assessment flow

| Item | Result | Notes |
| --- | --- | --- |
| Question selection: 3 per skill, fixed 1/1/1 difficulty mix, 12 for DevOps Sem 3 | **Pass** | `select_questions`; seeded, so the same seed gives the same list |
| Unseen-first, then least-recently-seen reuse | **Pass** | unit-tested; the full re-test flow is M5 (T-17 not fully closed until then) |
| Seeded option shuffle, reproducible for review | **Pass** | order saved per response in `displayed_order_json`; answer position varies across seeds |
| Answer key never sent to the UI | **Pass** | `PresentedQuestion` has no `correct_option_id` |
| Assessment page: start, resume, all questions required (FR-05) | **Pass** | resuming re-derives the same questions from the stored seed; unanswered or partial submit rejected, nothing saved |
| Submit grades by code, saves attempt, responses, skill scores | **Pass** | 1 attempt row, 12 responses, 4 skill scores, 1 weakest; config snapshot stored |
| Results page: score, level + scope, per-skill `correct/answered`, level rules, coverage | **Pass** | FR-06 |
| Roadmap position and weakest skill on results (FR-07, FR-08) | **Pass** | position looks from the student's current semester onward |
| Section 10.7 worked example through the real controller | **Pass** | 50.0, Intermediate, Linux weakest on tie, position Linux, coverage 4/14 |
| T-03 perfect single-semester check caps at Advanced with a full-path note | **Pass** |  |
| T-08 no major gap, next skill offered | **Pass** | position -&gt; Networking Fundamentals |
| T-18 results restored by a new controller on the same DB (partial: coaching/weekly plan are M4/M5) | **Pass** (partial) | identical result object, which also shows T-01 |
| T-20 changed thresholds do not alter a past attempt | **Pass** | results are re-derived from the attempt's own snapshot |
| T-21 build/communication skills "assessed later", not scored | **Pass** | Sem 6 DevOps: capstone, interview prep |
| T-22 thin bank -&gt; "coming soon" | **Pass** | Java/MEAN/AI and DevOps Sem 4-6 show it; the check can't be started |
| Full suite + lint + mypy + app smoke | **Pass** | 115 tests, ruff clean, mypy clean on `domain/` + `workflow/`, scoring coverage 96%, full-app headless render has no exceptions |
| Looked at in a real browser | **Pass** | see "Real-browser verification (M2-M4)" below; also found and fixed the Start-button bug |

**Known limits:** only the DevOps Semester 3 bank exists, so DevOps Sem 4-6 and the other careers can't be assessed yet. The full-path check and re-test flow are later milestones.

## M4 — Coaching flow

| Item | Result | Notes |
| --- | --- | --- |
| Coaching agent: AI drafts, validate, one repair attempt, template fallback | **Pass** | `agents/coaching_agent.py`; mock mode skips the AI call and uses the template directly |
| Coaching validator V-CO-01..06 | **Pass** | task count, link to a missed question or concept, skill matches the computed weakest, time limit from config, success check, no URLs |
| Template fallback is always valid | **Pass** | property-tested for 1, 2 and 3 misses with same/different concepts; 3-5 tasks, within the time limit |
| Curated practice templates for the 12 concepts the DevOps Sem 3 bank tests | **Pass** | `skills.json`; content validator now fails if a tested concept has no template or a template holds a URL |
| Plan built after submit only when a weakest skill exists | **Pass** | state goes `RESULTS_READY` -&gt; `COACHING_READY`; with "no major gap" no plan is made and state stays `RESULTS_READY` (M5 routes it to the weekly plan) |
| Coaching page: diagnosis, per-task "what went wrong / do this / done when", linked question | **Pass** | FR-09; source label says curated or AI-drafted |
| Plan saved and restored on reopen; older plans superseded | **Pass** | `coaching_plans` |
| T-12 plan for a different skill than the computed weakest is rejected | **Pass** | AI cannot change the weakest skill |
| T-13 task with no link to a missed question or concept is rejected | **Pass** |  |
| T-14 URL from AI rejected (coaching + roadmap) | **Pass** | every text field checked |
| T-15 AI off/unavailable: DevOps flow completes with templates | **Pass** | through check, results and coaching |
| T-16 empty/malformed AI response: no crash, fallback, nothing unvalidated shown | **Pass** | `""`, `{}`, non-JSON, wrong shape, `[]` |
| AI cannot influence scores | **Pass** | a model replying `{"overall_score": 100}` leaves score, level and weakest unchanged |
| Prompts hold no student identity | **Pass** | asserted on the prompt text |
| Full suite + lint + mypy + app smoke | **Pass** | 159 tests, ruff clean, mypy clean on `domain/` + `workflow/`, scoring coverage 96%, content validation passes |
| A live AI provider writing a coaching plan | **Not verified** | no API key available; only scripted fake AI clients were used |
| Looked at in a real browser | **Pass** | see "Real-browser verification (M2-M4)" below |

**Test change:** the M3 worked-example test now expects `COACHING_READY` after submit, since a weakest skill now triggers a plan.

## Real-browser verification (M2-M4)

Driven in Microsoft Edge with Playwright (headless, 1280x900) against a second copy of the app on port 8502 with a throwaway database, so no real data was touched. The script lives outside the repo (it needs Playwright and Edge). Final run: **23 checks, all passed, no uncaught browser errors.**

| Step | Result | What was observed |
| --- | --- | --- |
| Sidebar lists all pages | **Pass** | Profile, Career & Semester, Roadmap, Skills Check, Results, Coaching Plan, Weekly Plan, Progress, AI Settings, M1 Preview |
| Profile: enter a name and start | **Pass** | "Signed in as ..." shown |
| Career: "Doctor" typed under "My career isn't listed" | **Pass** | "not supported yet" message; no roadmap created (T-19) |
| Career: DevOps Engineer, Semester 3 | **Pass** | "Roadmap ready" |
| Roadmap page | **Pass** | Semesters 3-6 present, 16 month entries, Semester 3 marked "you are in this semester" |
| Skills Check: scope and start | **Pass** | "Assessed now" lists 4 skills; 12 questions shown; Start button hidden once the check runs |
| Skills Check: submit with nothing answered | **Pass** | refused with "Answer every question" (FR-05) |
| Skills Check: submit 1 correct per skill | **Pass** | accepted |
| Results page | **Pass** | 33.3%, Beginner, "Level for Semester 3 skills", level rules and 29% coverage, per-skill `correct/answered` (1/3 each), Linux flagged weakest, "You are here: Linux Fundamentals" |
| Coaching page | **Pass** | Focus skill Linux Fundamentals, 5 tasks (about 110 min), each with what went wrong, what to do, how to know it is done, and the linked question; no URLs on the page |
| Reload the browser, reopen the profile | **Pass** | coaching plan and results still present (T-18, partial: weekly plan is M5) |

**UI bugs found only in the browser (both fixed, commit** `5502587`**):**

1. The "Start skills check" button stayed on screen above the questions after the check started. Fixed by redrawing in the in-progress state.
2. Roadmap and profile pages showed "Devops Engineer" (title-cased id). They now show the catalog name, "DevOps Engineer". This second fix was covered by the unit/UI suite but the browser journey was not re-run after it.

**Operational finding:** Streamlit did not reliably pick up edits to page modules while a server was running (the first retest still showed the old button). Restart the server after code changes.

**Content note (not a defect):** roadmap `focus` and `deliverable` text is generic template wording ("Foundations: ", "Produce a short artifact demonstrating ... applied to a realistic task"). It passes validation but is placeholder-quality.

**Not covered in the browser:** the AI Settings page and live provider calls, Tier B careers (Java/MEAN/AI) "coming soon" state, Semesters 4-6, and the M1 Preview page.

## M5 — Weekly loop

| Item | Result | Notes |
|---|---|---|
| Weekly plan builder: pure rules, 3-5 tasks, within the time limit | **Pass** | `domain/weekly_plan_builder.py`, 100% line coverage; Section 10.7 example reproduced (2 coaching + Shell revision + Python light revision + re-check) |
| Rules from Section 4.5: max 2 coaching tasks, next roadmap topic when no gap, revision for skills < 80, closing re-check | **Pass** | lowest-priority tasks are dropped first when over the time limit; re-check is always kept; short weeks are padded to the minimum |
| Re-check date = plan date + `retest_after_days` | **Pass** | read from config; shown on the plan and the Skills Check page |
| Weekly plan created with the check and saved | **Pass** | state ends at `WEEKLY_PLAN_ACTIVE`; profiles saved before M5 (stuck at `RESULTS_READY`/`COACHING_READY`) get their plan on next load |
| Weekly plan page: tasks, completion checks, tick-off with progress, re-check banner | **Pass** | ticks persist in `tasks_done_json` and survive a browser reload |
| Re-check prompt: "due" banner when the date arrives, early re-check allowed | **Pass** | clock injected in tests; due after exactly 7 days (not at 6) |
| **T-17** re-test uses unseen questions first, no duplicates within a test | **Pass** | baseline then re-check share no questions; a third check reuses the least recently seen; browser run confirmed 12 unseen |
| **T-18** close and reopen: profile, roadmap, last results, coaching plan and weekly plan restored | **Pass** | full restore incl. ticked tasks (closes the partial items from M3/M4) |
| Progress page: latest vs previous, per-skill before/after, level change, history | **Pass** | FR-13; mentor prompt below 40%, flag after two drops in a row (Section 4.4); "N skills still below the mastery bar" close target |
| Re-check results labelled as such; older weekly plan can no longer be edited | **Pass** | |
| Full suite + lint + mypy + content validation | **Pass** | 203 tests, ruff clean, mypy clean on `domain/` + `workflow/`, coverage: scoring 96%, weekly builder 100%, progress 100% |
| Real browser (Edge): baseline -> weekly plan -> tick -> reload -> early re-check -> progress | **Pass** | 25 checks in the M5 run, no uncaught browser errors; screenshots reviewed |
| Live AI provider | **Not verified** | no API key; weekly plan and progress use no AI by design |

**Bugs found while building M5 (fixed):**
1. *Wrong "next skill" when nothing is weak.* The weakest-skill selector breaks ties toward the earliest skill, so with everything mastered it offered the skill after Linux (Shell Scripting, already mastered) as "next". Found by the new weekly-plan test; the Results page showed the same wrong text. Fixed in the evaluation agent: "next" is now the roadmap position (first skill still to do). Regression test added.
2. *Weekly plan padding.* With nothing specific to do, the builder padded one task and landed at 2 (< minimum of 3). Found by a unit test; now pads as many tasks as needed.
3. *Coverage config.* The weekly plan builder was listed by file path, so coverage reported it as "never imported". It is now measured by module name.

**Flow change:** after a check the profile now ends at `WEEKLY_PLAN_ACTIVE` (the coaching plan and weekly plan are both built at submit, as in the blueprint's sequence diagram). `COACHING_READY` is now a transient state. M3/M4 tests that asserted the old end state were updated.

**Not covered in the browser:** the "re-check is due" banner (needs 7 days to pass; covered with an injected clock in integration tests), Tier B careers, Semesters 4-6.

## M6 — Reliability and polish

Not started.

## M7 — Product note

Not started.