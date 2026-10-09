# Acceptance Test Report

Each milestone's acceptance items are recorded here as **Pass**, **Fail**, or **Not verified** (blueprint Section 17.4, 24.10).

## M0 — Foundation

### Full re-verification pass (2026-10-09, second session)

| Item | Result | Notes |
|---|---|---|
| `make lint` (`ruff check`, `ruff format --check`, `mypy domain/ workflow/`) | **Pass** | Clean across `src/`, `tests/`, `scripts/` |
| `make test` (`pytest --cov`) | **Pass** | 1/1 passed: `test_init_schema_is_idempotent` (schema uses `CREATE TABLE/INDEX IF NOT EXISTS`, confirmed safe to re-run) |
| `make db-init`, run twice | **Pass** | Idempotent, no error on second run |
| `make validate-content` | **Pass** | No-op stub (no content yet, by design -- content lands in M1) |
| `make db-reset` | **Pass** | Deletes and recreates the DB file cleanly |
| Every page route serves and every page's `render()` executes without exception | **Pass** | Verified two ways: (1) full headless `streamlit run`, curled all 9 `url_path` routes -> HTTP 200, no server traceback; (2) `AppTest` driving each page's `render()` directly -- the first attempt gave a false pass because pointing `AppTest.from_file` at a page module never calls `render()` (nothing executes); fixed by wrapping each page in a one-line script that imports and calls `render()`, which now genuinely exercises the code |
| AI Settings page: mock / openai / nvidia / custom / anthropic selectable, fields show correctly per provider | **Pass** | `AppTest` interaction script: selectbox + text_input counts verified per provider (mock=0 fields, others=3) |
| AI Settings page: Test Connection against a real endpoint with a fake key | **Pass** | OpenAI and Anthropic both returned a clean `401 Unauthorized` surfaced as `st.error(...)` -- confirms requests are correctly formed and reach the real API, and that failures never crash the page |
| AI Settings page: Test Connection against an unreachable custom URL | **Pass** | Connection-refused surfaced as `st.error(...)`, no crash |
| AI Settings page: Save + reload persists the active provider | **Pass** | Saved `openai`, reloaded a fresh page instance, selectbox pre-selected `openai` |
| NVIDIA default base URL prefill | **Pass** | `https://integrate.api.nvidia.com/v1` |

**Bug found and fixed during this pass:** `anthropic_ai_client.py` passed `temperature=` to `Messages.create()`, which crashed with `TypeError: unexpected keyword argument 'temperature'` on the installed `anthropic==1.13.0` SDK. Confirmed via `inspect.signature` and a full source grep that this SDK version no longer accepts `temperature` on that call at all (not a version pin issue -- genuinely removed). Fixed by dropping the argument from the API call while keeping it on the `AiClient.generate()` interface (so callers stay provider-agnostic; it's a documented no-op for Anthropic). Re-verified: a fake key now reaches the real API and gets a clean `401` instead of crashing.

**Scaffolding gap found and fixed:** `scripts/validate_content.py`, `reset_demo.py`, and `generate_question_drafts.py` were listed in Section 12 and referenced by the Makefile but were never created in the first M0 pass. Added as no-op/partial stubs so `make validate-content` and `make db-reset` don't fail before M1.

| Earlier items (first pass) | Result | Notes |
|---|---|---|
| `make run` opens the app shell | **Pass** | Headless Streamlit run, `HTTP 200` |
| Mock AI client callable end-to-end with no key | **Pass** | `build_ai_client(AiProviderConfig())` -> `MockAiClient`, `.generate()` returns `"{}"` |
| AI Settings page can write/read a row in `ai_provider_settings`; factory picks it up | **Pass** | Saved an `openai` config, reloaded it, factory returned `OpenAiCompatibleAiClient` |

Deviations noted: local Python available is 3.14 (blueprint specifies 3.11) -- no 3.11-only feature is in use. All interactive verification used an isolated `PCC_DB_PATH` so test runs don't mutate the real demo database; the real `data/runtime/pcc.db` was reset via `make db-reset` after manual testing left it in a non-default state.

## M1 — Content and scoring core

| Item | Result | Notes |
|---|---|---|
| Content validator passes against authored content | **Pass** | `scripts/validate_content.py` -> "Content validation passed: 4 careers, 58 skills." |
| Skill maps + roadmap templates for all 4 careers | **Pass** | Generated programmatically from the blueprint's Section 2.3 tables (avoids hand-transcription errors across 64 month entries); 16 months each, validated against V-RM-01/02/03/05/07 equivalents |
| DevOps Sem 3 question bank (24 approved questions) | **Pass** | 4 skills x 6 questions, exactly 2/2/2 easy/medium/hard per skill, hand-authored for technical accuracy; `compute_skill_assessability` confirms all 4 skills assessable |
| Tier B careers (MEAN/Java/AI) have roadmaps but no question bank yet | **Pass** | By design (Section 2.1) -- `load_question_bank` returns `[]` gracefully, no skill in those careers reports assessable |
| `domain/scoring/*` pure functions | **Pass** | scoring_engine, level_classifier, weakest_skill_selector, coverage_calculator, roadmap_position_locator -- 96% line coverage (exceeds the 90% bar in Section 6) |
| Level boundary tests (Section 17.2: 0/39.9/40/64.9/65/84.9/85/100) | **Pass** | All 8 boundaries correct |
| T-01 same answers scored twice -> identical | **Pass** | |
| T-02 Industry-ready downgraded when one sufficient skill < gate | **Pass** | Note names the failing skill |
| T-03 Industry-ready downgraded when coverage < 100% | **Pass** | Note recommends the full-path check |
| T-04 full-path, 100% coverage, all skills >= 60, overall >= 85 -> Industry-ready | **Pass** | |
| T-05 skill with 1 answered question not eligible as weakest | **Pass** | |
| T-06 tied lowest skills -> earlier roadmap position wins | **Pass** | |
| T-07 no skill with sufficient evidence -> no weakest skill invented | **Pass** | |
| T-08 weakest skill >= mastery threshold -> "no major gap", next skill offered | **Pass** | |
| T-20 config snapshot: old attempt unaffected by later threshold changes | **Pass** | Proven by construction -- every scoring function takes config as a parameter, never reads global mutable state |
| T-21 unbuilt skill_type (build/communication) -> "assessed later", not scored | **Pass** | `is_quiz_assessable` only true for `conceptual` |
| T-22 skill with fewer than 6 approved questions -> not assessable | **Pass** | Also verified the 2/2/2-per-difficulty requirement independently of raw count |
| Worked example (Section 10.7) reproduced exactly | **Pass** | Linux/Shell 33.3%, Python/Git 66.7%, overall 50.0 |
| Full test suite + lint + mypy + app smoke test | **Pass** | 43/43 tests, `ruff check`/`format` clean, `mypy` clean on `domain/`, headless `streamlit run` still HTTP 200 with M1 content loaded |

**Design decision made during this pass:** `Skill.career_id` (singular) was changed to `Skill.career_ids: list[str]` before any content was authored. The blueprint's own skill maps (Section 2.3) reuse `git_version_control` across DevOps/MEAN/AI, `system_design_basics` across MEAN/Java, and `interview_preparation` across all four careers -- a single-career field would have forced duplicate skill_ids (rejected by the uniqueness rule) or duplicate skill definitions. Logged as decision A22.

**Scaffolding gap found and fixed:** `tests/conftest.py` was listed in Section 12 but never created in M0; added now with the shared `skill_score_factory` fixture.

**`make` is not installed in this dev shell** (git-bash on Windows) -- all Makefile-wrapped commands were verified by running their underlying command directly (`ruff`, `mypy`, `pytest`, `python scripts/validate_content.py`), not via the `make` binary itself.

## M2 — Roadmap flow

| Item | Result | Notes |
|---|---|---|
| Career picker (4 careers + typed career) and semester select | **Pass** | `career_selection_page`; headless UI test drives it |
| Roadmap agent: AI rewords, never reorders; one repair attempt; template fallback | **Pass** | `agents/roadmap_agent.py`; mock mode skips AI and uses the template directly |
| Roadmap validator V-RM-01..08 | **Pass** | V-RM-06 enforced through V-RM-04 (fixed sequence = template, which respects prerequisites) |
| SQLite profile + roadmap persistence | **Pass** | `profile_repository`, `roadmap_repository`; one active roadmap per profile |
| Roadmap page shows Sem 3-6 and 16 months for DevOps | **Pass** | 16 expanders, 4 semester headings, current semester expanded |
| T-09 missing semester/month rejected, template used | **Pass** | validator unit tests + agent fallback test |
| T-10 AI reorders skills -> rejected (V-RM-04), template used | **Pass** | |
| T-14 / V-RM-08 URL in AI text rejected | **Pass** | roadmap part only; coaching part lands in M4 |
| T-15 AI disabled/unavailable -> DevOps flow completes with template | **Pass** | integration test with an unavailable AI client |
| T-16 empty/malformed AI response -> no crash, fallback (roadmap part) | **Pass** | `""`, `{}`, non-JSON, wrong shape, array |
| T-18 close and reopen: profile + roadmap restored (weekly plan/results part is M3+) | **Pass** (partial) | new controller on same DB file |
| T-19 non-CS career -> "not supported yet" + supported list, no roadmap | **Pass** | Doctor, Chartered Accountant, Pilot, Chef; invalid characters/length rejected |
| Full suite + lint + mypy + app smoke | **Pass** | 89 tests, ruff clean, mypy clean on `domain/` + `workflow/`, headless full-app render has no exceptions |
| Live AI provider personalising a roadmap | **Not verified** | no API key available; only scripted fake clients were exercised |

**Fixes while integrating:** mypy now follows imports from `workflow/` into `ai/` and `content/`; typed `parse_json_object`, `_read_json` and the OpenAI client return so `mypy` stays clean.

## M3 — Assessment flow
Not started.

## M4 — Coaching flow
Not started.

## M5 — Weekly loop
Not started.

## M6 — Reliability and polish
Not started.

## M7 — Product note
Not started.
