# Placement Career Coach (PCC)

A placement-readiness coach for CS students (Sem 3-6): pick a career, get a Sem 3-6 roadmap, take a short skills check, see your level and weakest skill, get a coaching plan, follow a weekly loop, re-check and see progress.

Full product + engineering spec: [`docs/00_PROJECT_BLUEPRINT.md`](docs/00_PROJECT_BLUEPRINT.md). Execution plan and milestone log: see `docs/03_TEST_REPORT.md` and `docs/04_DECISION_LOG.md`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
make setup
cp .env.example .env           # defaults to PCC_AI_MODE=mock -- no key needed
make db-init
make run
```

## AI provider

The blueprint ships with a `.env`-based Anthropic/mock switch. This build extends that: open the **AI Settings** page in the running app to pick a provider (Anthropic, OpenAI, NVIDIA NIM, or any other OpenAI-compatible endpoint), paste a base URL + API key, and hit **Test connection**. Settings are stored locally in SQLite (`ai_provider_settings` table) and take precedence over `.env`. This is a local, single-user app -- the key is stored in plaintext in the local DB file, which is fine for this prototype but is **not** a pattern to reuse for a multi-user deployment.

Mock mode (no key) is a first-class feature: the entire student journey works offline and deterministically.

## Status

Milestone M0 (Foundation) complete. See `docs/03_TEST_REPORT.md` for acceptance results and `docs/00_PROJECT_BLUEPRINT.md` Section 18 for the full milestone plan.
