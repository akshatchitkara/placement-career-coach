# Placement Career Coach (PCC)

A placement-readiness coach for Computer Science students in Semesters 3-6.

**Pick a career → get a Semester 3-6 roadmap → take a short skills check → see your level and where you stand → get a practice plan for your weakest skill → follow a weekly plan → re-check and see what improved.**

It runs fully offline with no API key. An AI provider is optional and only ever *writes advice*; scores, levels and routing are always decided by plain, tested code.

Full product and engineering spec: [`docs/00_PROJECT_BLUEPRINT.md`](docs/00_PROJECT_BLUEPRINT.md). Test and acceptance results: [`docs/03_TEST_REPORT.md`](docs/03_TEST_REPORT.md). Decisions made while building: [`docs/04_DECISION_LOG.md`](docs/04_DECISION_LOG.md).

## Quick start

Requires Python 3.11 or newer.

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python scripts/reset_demo.py          # optional: creates the demo profiles (see below)
streamlit run src/pcc/main.py
```

```bash
# macOS / Linux
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python scripts/reset_demo.py          # optional
streamlit run src/pcc/main.py
```

`make setup`, `make run`, `make db-reset` and the other Makefile targets do the same where `make` is installed. The database is created automatically on first run, so `reset_demo.py` is only needed for the demo profiles.

Open http://localhost:8501. The sidebar shows **Offline mode** when no AI is configured. That is a normal, fully working state.

## Try it in two minutes

After `python scripts/reset_demo.py`, pick a profile on the **Profile** page:

| Profile | State | What to show |
|---|---|---|
| **Asha** | Brand new | Pick **DevOps Engineer**, Semester 3 → **Roadmap** → **Skills Check** (12 questions) → **Results** → **Coaching Plan** → **Weekly Plan** |
| **Ravi** | One baseline check | The blueprint's worked example: 50.0, Intermediate, weakest skill Linux, a coaching plan and a weekly plan |
| **Meera** | Baseline plus an improved re-check | **Progress**: 50.0 → 91.7, Intermediate → Advanced, three skills up and one unchanged, roadmap position moved on to Networking |

Also try typing a non-CS career such as "Doctor" under *My career isn't listed*: you get a clear "not supported yet" message and the list of supported careers.

## What each page does

| Page | Purpose |
|---|---|
| Profile | Sign in with a display name (no password; progress is saved locally) |
| Career & Semester | Pick one of 4 CS careers or type one; builds the validated roadmap |
| Roadmap | Semesters 3-6, four months each, with topics and deliverables |
| Skills Check | 3 questions per skill (1 easy, 1 medium, 1 hard), options shuffled; also hosts the re-check |
| Results | Score, level and its scope, per-skill `correct/answered`, level rules, roadmap position, weakest skill, answer review |
| Coaching Plan | 3-5 tasks for the weakest skill, each tied to a question you missed |
| Weekly Plan | 3-5 tasks, tick-off with progress, and a re-check date |
| Progress | Latest check against the previous one, skill by skill |
| AI Settings | Optional AI provider (see below) |

## How scoring stays fair

- Scoring, levels, the weakest skill and your roadmap position are **pure functions** with no network and no AI. The same answers always give the same result.
- Level cut-offs, question counts and time limits live only in [`data/content/app_settings.json`](data/content/app_settings.json). Each attempt stores a snapshot of that file, so changing a threshold later never alters a past result.
- **Industry-ready** needs an overall score of 85+, every tested skill at 60+, and evidence across the whole career. A single-semester check therefore tops out at Advanced and says why.
- A skill needs at least 2 answered questions to count as evidence; otherwise the app says "not enough evidence yet" instead of inventing a weakest skill.
- Skills that need a hands-on or interview method are shown as "assessed later" and are never scored with a quiz.

## AI (optional)

The app works completely without AI. When a provider is configured, AI may *reword* roadmap months and *draft* coaching plans, and everything it returns is validated before you see it:

- It can never reorder the roadmap's skills, change the weakest skill, add links, or touch a score.
- A reply that is empty, malformed, off-topic or breaks a rule is rejected; after one repair attempt the curated plan is used instead.
- Provider timeouts or errors are retried once, then the curated plan is used.
- No names or personal data are sent; prompts contain only the career, skill and missed-question text.

**Choosing a provider.** Precedence is: a provider saved on the **AI Settings** page → `.env` → offline.

- *In the app:* open **AI Settings**, choose Anthropic, OpenAI, NVIDIA NIM or any OpenAI-compatible endpoint, paste the key, press **Test connection**, then **Save**.
- *In `.env`:* set `PCC_AI_MODE=live` and `PCC_AI_API_KEY=...` (Anthropic). With `live` but no real key, the app stays offline and shows a warning in the sidebar.

The key is stored in plain text in the local SQLite file. That is acceptable for a single-user local prototype and is **not** a pattern to reuse for a shared deployment.

## Content and data

- [`data/content/`](data/content) holds the reviewed content: careers, skills, 16-month roadmap templates for 4 careers, practice templates and the question bank.
- The app validates this content at start-up and refuses to run on broken files, with a message saying what is wrong. Run it yourself with `python scripts/validate_content.py`.
- **Question bank coverage:** only **DevOps Engineer, Semester 3** (4 skills, 24 reviewed questions) can be assessed today. Other semesters and careers have roadmaps but show "assessment coming soon". Adding a bank needs at least 6 approved questions per skill (2 per difficulty); see [`docs/02_QUESTION_AUTHORING_GUIDE.md`](docs/02_QUESTION_AUTHORING_GUIDE.md).
- Learner state (profiles, attempts, plans) is in `data/runtime/pcc.db` (SQLite, git-ignored). `python scripts/reset_demo.py` recreates it. **It deletes the database**, so it refuses to run if real profiles exist unless you pass `--force`.

## Tests and checks

```bash
python -m pytest --cov                     # tests plus coverage on scoring, weekly plan, progress
python -m ruff check src tests scripts     # lint
python -m ruff format --check src tests scripts
python -m mypy src/pcc/domain src/pcc/workflow
python scripts/validate_content.py
```

The suite covers the scoring rules and level boundaries, validators, fallbacks, the whole journey with the AI failing in seven different ways (down, crashing, empty, not JSON, wrong shape, prompt injection, hostile JSON), persistence and restore, and the Streamlit pages (headless).

## Project layout

```text
src/pcc/
  domain/        pure logic: scoring, weekly plan builder, progress, schemas (no I/O)
  content/       loads and validates data/content/
  agents/        roadmap, evaluation and coaching modules, with validators and fallbacks
  ai/            one AI interface, provider adapters, prompts, JSON parsing
  workflow/      the controller that runs the journey, state machine, demo seeding
  persistence/   SQLite access (parameterised queries only)
  ui/            Streamlit pages and components; no scoring, SQL or prompts
data/content/    reviewed content        schema/   database schema
scripts/         init_db, reset_demo, validate_content
tests/           unit, integration and UI tests
docs/            blueprint, test report, decision log, authoring guide
```

## Known limits

- Local, single-user, no login: a profile is just a display name.
- One assessable bank (DevOps Semester 3). The full-path "Industry-ready" check, the Career Finder, custom CS careers and a demo answer simulator are designed but not built.
- Roadmap focus and deliverable text is generic template wording; it passes validation but is placeholder quality.
- A live AI provider has not yet produced accepted output. One real attempt (NVIDIA NIM) answered a small call, but realistic prompts were refused as overloaded or timed out, so the curated roadmap and coaching plan were shown, as designed. The AI paths are otherwise covered with scripted fake clients and failure drills.

## Status

Milestones M0-M6 are complete; see [`docs/03_TEST_REPORT.md`](docs/03_TEST_REPORT.md) for each acceptance item marked Pass, Fail or Not verified, and Blueprint Section 18 for what comes next.

The sidebar's developer-only **M1 Preview** page (content browser and scoring playground) is hidden by default; set `PCC_SHOW_DEV_PAGES=true` to show it.
