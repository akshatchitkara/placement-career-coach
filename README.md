# Placement Career Coach (PCC)

A placement-readiness coach for Computer Science students in Semesters 3-6.

**Pick a career → get a Semester 3-6 roadmap → take a short skills check → see your level and where you stand → get a practice plan for your weakest skill and a coach to ask → follow a day-by-day weekly plan → re-check and see what improved.**

It runs fully offline with no API key. An AI provider is optional and only ever *writes advice*; scores, levels and routing are always decided by plain, tested code.

Full product and engineering spec: [`docs/00_PROJECT_BLUEPRINT.md`](docs/00_PROJECT_BLUEPRINT.md) (its Appendix D lists what changed after it was written). Test and acceptance results: [`docs/03_TEST_REPORT.md`](docs/03_TEST_REPORT.md). Decisions made while building: [`docs/04_DECISION_LOG.md`](docs/04_DECISION_LOG.md). How to add questions: [`docs/02_QUESTION_AUTHORING_GUIDE.md`](docs/02_QUESTION_AUTHORING_GUIDE.md).

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

`make setup`, `make run`, `make db-reset` and the other Makefile targets do the same where `make` is installed. The database is created automatically on first run (and new tables are added to an existing database on the next start), so `reset_demo.py` is only needed for the demo profiles.

Open http://localhost:8501. The sidebar shows **Offline mode** when no AI is configured. That is a normal, fully working state.

After editing code, restart the server: Streamlit does not always reload edited page modules.

## Try it in two minutes

After `python scripts/reset_demo.py`, pick a profile on the **Profile** page (or just press **Get started** on Home and make your own):

| Profile | State | What to show |
|---|---|---|
| **Asha** | Brand new | Pick a career, Semester 3 → **Roadmap** → **Skills Check** (12 questions, one at a time) → **Results** → **Coaching Plan** → **Weekly Plan** |
| **Ravi** | One baseline check | The blueprint's worked example: 50.0, Intermediate, weakest skill Linux, a coaching plan and a weekly plan |
| **Meera** | Baseline plus an improved re-check | **Progress**: 50.0 → 91.7, Intermediate → Advanced, three skills up and one unchanged, roadmap position moved on to Networking |

All four careers (DevOps, MEAN, Java, AI) can complete a Semester 3 check. Also try typing a non-CS career such as "Doctor" under *My career isn't listed*: you get a clear "not supported yet" message and the list of supported careers.

## What each page does

| Page | Purpose |
|---|---|
| Home | Where you are in the journey (five-step tracker), your one next step, latest score and re-check countdown. New visitors see what the app does |
| Career & Semester | Pick one of 4 CS careers or type one; shows which semesters have a skills check; builds the validated roadmap |
| Roadmap | Semesters 3-6, four months each, with topics and deliverables |
| Skills Check | One question at a time with progress, Back/Next and an unanswered list before submit; 3 questions per skill (1 easy, 1 medium, 1 hard), options shuffled; also hosts the re-check |
| Results | Score and level with a four-step ladder and the gap to the next level, a "biggest opportunity" skill, per-skill bars with the mastery line, full numbers, roadmap position, answer review |
| Coaching Plan | 3-5 tasks for the weakest skill, each tied to a question you missed. Each task has a **coach**: explain it differently, show an example, ask your own question, or take a short practice quiz |
| Weekly Plan | The week laid out over seven days plus a re-check day, task links, a time-budget picker, progress and a calendar (.ics) download |
| Progress | Latest check against the previous one, skill by skill |
| Profile / AI Settings | Sign in with a display name (no password); optional AI provider |

## How scoring stays fair

- Scoring, levels, the weakest skill and your roadmap position are **pure functions** with no network and no AI. The same answers always give the same result.
- Level cut-offs, question counts and time limits live only in [`data/content/app_settings.json`](data/content/app_settings.json). Each attempt stores a snapshot of that file, so changing a threshold later never alters a past result.
- **Industry-ready** needs an overall score of 85+, every tested skill at 60+, and evidence across the whole career. A single-semester check therefore tops out at Advanced and says why.
- A skill needs at least 2 answered questions to count as evidence; otherwise the app says "not enough evidence yet" instead of inventing a weakest skill.
- Skills that need a hands-on or interview method are shown as "assessed later" and are never scored with a quiz.
- The coach's practice quiz re-asks questions you have already seen, is graded by code, and is never stored as a check, so it cannot change a score or use up the unseen questions your re-check needs.

## AI (optional)

The app works completely without AI. When a provider is configured, AI may *reword* roadmap months, *draft* coaching plans and *answer coach questions*, and everything it returns is validated before you see it:

- It can never reorder the roadmap's skills, change the weakest skill, add links, or touch a score.
- A reply that is empty, malformed, off-topic or breaks a rule is rejected. Plans get one repair attempt, then the curated plan is used. Coach replies that mention scores or levels, contain links, or talk about "the student" are replaced by a built-in answer taken from the question's explanation.
- Your own words to the coach are passed to the model as quoted data, limited to 300 characters, with at most 12 messages per task.
- Provider timeouts or errors are retried once, then the curated plan or built-in answer is used.
- No names or personal data are sent; prompts contain only the career, skill, task and missed-question text.

**Choosing a provider.** Precedence is: a provider saved on the **AI Settings** page → `.env` → offline.

- *In the app:* open **AI Settings**, choose Anthropic, OpenAI, NVIDIA NIM or any OpenAI-compatible endpoint, paste the key, press **Test connection**, then **Save**.
- *In `.env`:* set `PCC_AI_MODE=live` and `PCC_AI_API_KEY=...` (Anthropic). With `live` but no real key, the app stays offline and shows a warning in the sidebar.

The key is stored in plain text in the local SQLite file. That is acceptable for a single-user local prototype and is **not** a pattern to reuse for a shared deployment.

## Content and data

- [`data/content/`](data/content) holds the content: careers, skills, 16-month roadmap templates for 4 careers, practice templates and the question banks.
- The app validates this content at start-up and refuses to run on broken files, with a message saying what is wrong. Run it yourself with `python scripts/validate_content.py`.
- **Question bank coverage:** all four careers have a **Semester 3** bank (4 assessable skills, 24 questions each). Semesters 4-6 have roadmaps but show "assessment coming soon" and name the semesters that do have a check. Adding a bank needs at least 6 approved questions per skill (2 per difficulty); see the [authoring guide](docs/02_QUESTION_AUTHORING_GUIDE.md).
- **Review status:** the 60 MEAN, Java and AI questions written after the first prototype are labelled `ai_drafted` and have **not been reviewed by a person**. The DevOps questions (and the Git questions copied from them) are labelled `ai_drafted_human_reviewed`, but that label was set during the first build and the repository holds no record of who reviewed them, so treat it as unconfirmed. Review them, then keep or change the label.
- Learner state (profiles, attempts, plans, coach chats) is in `data/runtime/pcc.db` (SQLite, git-ignored). `python scripts/reset_demo.py` recreates it. **It deletes the database**, so it refuses to run if real profiles exist unless you pass `--force`.

## Tests and checks

```bash
python -m pytest --cov                     # tests plus coverage on scoring, weekly plan, progress
python -m ruff check src tests scripts     # lint
python -m ruff format --check src tests scripts
python -m mypy src/pcc/domain src/pcc/workflow
python scripts/validate_content.py
```

The suite (about 340 tests) covers the scoring rules and level boundaries, validators, fallbacks, the whole journey for every career with the AI failing in seven different ways (down, crashing, empty, not JSON, wrong shape, prompt injection, hostile JSON), the coach (limits, fallbacks, quiz), the weekly schedule and calendar export, persistence and restore, and the Streamlit pages (headless). Real-browser checks (Edge, via Playwright) are recorded in the test report; their scripts are not part of the repository.

## Project layout

```text
src/pcc/
  domain/        pure logic: scoring, weekly plan builder, week schedule, calendar export, progress, schemas (no I/O)
  content/       loads and validates data/content/
  agents/        roadmap, evaluation, coaching and tutor modules, with validators and fallbacks
  ai/            one AI interface, provider adapters, prompts, JSON parsing
  workflow/      the controller that runs the journey, state machine, demo seeding
  persistence/   SQLite access (parameterised queries only)
  ui/            Streamlit pages and components; no scoring, SQL or prompts
.streamlit/      theme
data/content/    content                 schema/   database schema
scripts/         init_db, reset_demo, validate_content
tests/           unit, integration and UI tests
docs/            blueprint, test report, decision log, authoring guide
```

## Known limits

- Local, single-user, no login: a profile is just a display name.
- Only Semester 3 has questions, for each of the four careers. Semesters 4-6, the full-path "Industry-ready" check, the Career Finder, custom CS careers and a demo answer simulator are designed but not built.
- The 60 newer questions are unreviewed drafts (see above).
- Roadmap focus and deliverable text is generic template wording; it passes validation but is placeholder quality.
- Coaching covers the single weakest skill. The plan cannot be regenerated, because the weekly plan is built from it.
- Coach replies and AI plans take several seconds on a live model; there is a spinner but no streaming.
- Live AI has been verified with **Anthropic** (`claude-haiku-5-5`) for the DevOps journey only: roadmap, coaching plan and coach replies were accepted by the validators and read well. A first attempt with NVIDIA NIM was refused as overloaded, so the curated plans were shown as designed. Other providers, models and careers are untested live; the AI paths are otherwise covered with scripted fake clients and failure drills.
- The product note ([`docs/01_PRODUCT_NOTE.md`](docs/01_PRODUCT_NOTE.md)) is not written yet.

## Status

Milestones M0-M6 are complete, followed by a product-polish pass (all careers working at Semester 3, a Home page and navigation, a one-question-at-a-time check, a redesigned Results page, a coach with a practice quiz, and a day-by-day weekly plan). See [`docs/03_TEST_REPORT.md`](docs/03_TEST_REPORT.md) for each acceptance item marked Pass, Fail or Not verified, and Blueprint Section 18 for what comes next (M7 is the product note).

The sidebar's developer-only **M1 Preview** page (content browser and scoring playground) is hidden by default; set `PCC_SHOW_DEV_PAGES=true` to show it.
