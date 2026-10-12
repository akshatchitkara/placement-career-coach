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

After editing code, restart the server. The file watcher is switched off in `.streamlit/config.toml` (see the decision log, A72), so edits are not hot-reloaded.

## Try it in two minutes

After `python scripts/reset_demo.py`, pick a profile on the **Profile** page (or just press **Get started** on Home and make your own):

| Profile | State | What to show |
|---|---|---|
| **Asha** | Brand new | Pick a career, Semester 3 → **Roadmap** → **Skills Check** (12 questions, one at a time) → **Results** → **Coaching Plan** → **Weekly Plan** |
| **Ravi** | One baseline check | The blueprint's worked example: 50.0, Intermediate, weakest skill Linux, a coaching plan and a weekly plan |
| **Meera** | Baseline plus an improved re-check | **Progress**: 50.0 → 91.7, Intermediate → Advanced, three skills up and one unchanged, roadmap position moved on to Networking |

All four careers (DevOps, MEAN, Java, AI) can complete a check in any of Semesters 3 to 6. Also try typing a non-CS career such as "Doctor" under *My career isn't listed*: you get a clear "not supported yet" message and the list of supported careers.

## What each page does

| Page | Purpose |
|---|---|
| Home | Where you are in the journey (five-step tracker), your one next step, latest score, re-check countdown and, after two checks, your trend. New visitors see what the app does |
| Career & Semester | Pick one of 4 CS careers or type one; shows which semesters have a skills check; builds the validated roadmap |
| Roadmap | Semesters 3-6, four months each, with topics and deliverables |
| Skills Check | One question at a time with progress, Back/Next and an unanswered list before submit; 3 questions per skill (1 easy, 1 medium, 1 hard), options shuffled; also hosts the re-check and the **full-path check** (every roadmap skill, 2 questions each, 28 for a career; the only way to reach Industry-ready) |
| Results | Score and level with a four-step ladder and the gap to the next level, a "biggest opportunity" skill, per-skill bars with the mastery line, full numbers, roadmap position, answer review |
| Coaching Plan | 3-5 tasks for the weakest skill, each tied to a question you missed. Each task has a **coach**: explain it differently, show an example, ask your own question, or take a short practice quiz |
| Weekly Plan | The week laid out over seven days plus a re-check day, task links, a time-budget picker, progress and a calendar (.ics) download |
| Progress | Score trend across checks, skill-by-skill change with a tick for the previous check, whether last week's effort showed up in the score, and a ready-to-send mentor message for any skill under 40% |
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
- **Question bank coverage:** all four careers have questions for **Semesters 3 to 6**: every one of the 14 quiz skills has 6 questions (2 easy, 2 medium, 2 hard), which is 24 per full semester and 12 in Semester 6 (84 per career). Capstone and interview skills are not quizzed and show as "assessed later". Adding or extending a bank needs at least 6 approved questions per skill; see the [authoring guide](docs/02_QUESTION_AUTHORING_GUIDE.md).
- **Review status:** about 300 questions across the four banks (everything for MEAN, Java and AI except the shared Git questions, and Semesters 4-6 for DevOps) are labelled `ai_drafted` and have **not been reviewed by a person**. The 24 DevOps Semester 3 questions (and the Git questions copied from them) are labelled `ai_drafted_human_reviewed`, but that label was set during the first build and the repository holds no record of who reviewed them, so treat it as unconfirmed. Review them, then keep or change the label.
- Learner state (profiles, attempts, plans, coach chats) is in `data/runtime/pcc.db` (SQLite, git-ignored). `python scripts/reset_demo.py` recreates it. **It deletes the database**, so it refuses to run if real profiles exist unless you pass `--force`.

## Tests and checks

```bash
python -m pytest --cov                     # tests plus coverage on scoring, weekly plan, progress
python -m ruff check src tests scripts     # lint
python -m ruff format --check src tests scripts
python -m mypy src/pcc/domain src/pcc/workflow
python scripts/validate_content.py
```

The suite (about 400 tests) covers the scoring rules and level boundaries, validators, fallbacks, the whole journey for every career with the AI failing in seven different ways (down, crashing, empty, not JSON, wrong shape, prompt injection, hostile JSON), the coach (limits, fallbacks, quiz), the weekly schedule and calendar export, persistence and restore, and the Streamlit pages (headless). A separate suite of 34 real-browser tests (Playwright with Edge or Chrome) is in `tests/e2e`; it is skipped unless you ask for it:

```bash
pip install -r requirements-e2e.txt
npm install axe-core                      # only for the accessibility test
PCC_E2E=1 python -m pytest tests/e2e      # about 10 minutes
```

The QA report, with every finding and what could not be tested, is in [`test-reports/qa-report.md`](test-reports/qa-report.md).

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
tests/           unit, integration and UI tests; tests/e2e holds the browser tests
qa/              QA tools: route sweep, question-rendering check, report builder
test-reports/    results of the last QA pass
docs/            blueprint, test report, decision log, authoring guide
```

## Known limits

- Local, single-user, no login: a profile is just a display name.
- The Career Finder, custom CS careers, any career outside the four, the written, assignment and voice assessments, and a demo answer simulator are designed but not built. A student who types another career (for example cybersecurity or VLSI) is told it is not supported yet.
- Most questions are unreviewed drafts written by an assistant (see above). A student's level is only as trustworthy as the questions behind it.
- Roadmap focus and deliverable text is generic template wording; it passes validation but is placeholder quality.
- Coaching covers the single weakest skill. The plan cannot be regenerated, because the weekly plan is built from it.
- Coach replies and AI plans take several seconds on a live model; there is a spinner but no streaming.
- Lighthouse performance is 38 to 59 and accessibility 83 to 87. The shortfalls are Streamlit's own front end and sidebar markup, not this app's content; `test-reports/lighthouse/summary.md` has the detail.
- On Python 3.14 and Windows the Streamlit server crashed twice in its file-watcher threads during long test runs. The watcher is now off; Python 3.12 or 3.13 has not been tried.
- Live AI has been verified with **Anthropic** (`claude-haiku-5-5`) for the DevOps journey only: roadmap, coaching plan and coach replies were accepted by the validators and read well. A first attempt with NVIDIA NIM was refused as overloaded, so the curated plans were shown as designed. Other providers, models and careers are untested live; the AI paths are otherwise covered with scripted fake clients and failure drills.
- Roadmaps are curated per career, not generated for each student; the AI can only reword them. Personalisation comes from the assessment, the coaching plan and the weekly plan.

## Free hosted demo (Streamlit Community Cloud)

For showing the app to a team without running it locally:

1. Push the repository to GitHub (`.env`, `*.db` and `data/runtime/` are git-ignored, so no key or personal data goes up).
2. At [share.streamlit.io](https://share.streamlit.io) choose **Create app**, pick the repository and branch, and set the main file to `src/pcc/main.py` (Python 3.12).
3. Under **Advanced settings > Secrets** paste:

   ```toml
   PCC_AI_MODE = "offline"
   PCC_DEMO_MODE = "true"
   ```

To use live AI on the hosted copy with Groq (or any OpenAI-compatible provider), replace the secrets with the block below. Models are tried left to right, so the later ones are fallbacks if the first is rate-limited or retired. Keep the key in Secrets only, never in the repository.

```toml
PCC_AI_MODE = "live"
PCC_AI_PROVIDER = "custom_openai_compatible"
PCC_AI_BASE_URL = "https://api.groq.com/openai/v1"
PCC_AI_API_KEY = "your-groq-key"
PCC_AI_MODEL_NAME = "openai/gpt-oss-20b, openai/gpt-oss-120b, qwen/qwen3.8-27b"
PCC_DEMO_MODE = "true"
```

`PCC_AI_PROVIDER` can also be `anthropic` (the default), `openai` or `nvidia`.

`PCC_DEMO_MODE=true` recreates the three demo profiles (Asha, Ravi, Meera) whenever the database is empty and hides the AI Settings page. Limits of the free tier: the disk is not kept, so anything entered during the demo disappears when the app restarts or wakes from sleep; the app sleeps after a period of no visits; and there is no login, so anyone with the link can use it.

## Product note and delivery review

The product note (Task 1 of the assessment) is [`docs/01_PRODUCT_NOTE.md`](docs/01_PRODUCT_NOTE.md), with a 3-page PDF copy, [`docs/01_PRODUCT_NOTE.pdf`](docs/01_PRODUCT_NOTE.pdf). Rebuild the PDF with `python qa/build_product_note.py`. The pre-delivery review, with a requirement-by-requirement compliance matrix, is in [`delivery-review/`](delivery-review/delivery-readiness.md).

## Status

Milestones M0-M6 are complete, followed by a product-polish pass (all careers working at Semester 3, a Home page and navigation, a one-question-at-a-time check, a redesigned Results page, a coach with a practice quiz, a day-by-day weekly plan, and a progress dashboard). See [`docs/03_TEST_REPORT.md`](docs/03_TEST_REPORT.md) for each acceptance item marked Pass, Fail or Not verified, and Blueprint Section 18 for what comes next (M7 is the product note).

The sidebar's developer-only **M1 Preview** page (content browser and scoring playground) is hidden by default; set `PCC_SHOW_DEV_PAGES=true` to show it.
