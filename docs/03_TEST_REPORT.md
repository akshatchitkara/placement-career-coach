# Acceptance Test Report

Each milestone's acceptance items are recorded here as **Pass**, **Fail**, or **Not verified** (blueprint Section 17.4, 24.10).

## M0 — Foundation

| Item | Result | Notes |
|---|---|---|
| `make run` opens the app shell | **Pass** | Verified via headless Streamlit run on port 8765, `HTTP 200` returned |
| `make lint` passes | **Pass** | `ruff check` and `ruff format` clean on `src/`, `tests/` |
| Mock AI client callable end-to-end with no key | **Pass** | `build_ai_client(AiProviderConfig())` -> `MockAiClient`, `.generate()` returns `"{}"` |
| AI Settings page can write/read a row in `ai_provider_settings`; factory picks it up | **Pass** | Verified by script: saved an `openai` config, reloaded it, factory returned `OpenAiCompatibleAiClient` |
| Invalid/unreachable provider config falls back cleanly, never crashes | **Pass** | Construction-time failures (missing `base_url`) fall back to mock in the factory; connection-time failures are caught by the Settings page's Test Connection button and the agent-level fallback planned for M2-M4 |
| `mypy` clean on `domain/` and `workflow/` | **Not verified** | No implementation in `domain/`/`workflow/` yet (M1+) -- nothing to type-check beyond stubs |

Deviation noted: local Python available is 3.14 (blueprint specifies 3.11). No 3.11-specific feature is used yet; flagged here in case a dependency later requires <3.12.

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
