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
Not started.

## M2 — Roadmap flow
Not started.

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
