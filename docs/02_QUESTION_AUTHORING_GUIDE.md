# Question Authoring Guide

How to add or review questions for the skills check. Rules in the field table and the size rules are enforced by `python scripts/validate_content.py` (also run when the app starts) or by a test. The checklist under "Writing good questions" is **by hand**, except the length rule in item 3.

## Where questions live

- One file per career: `data/content/question_bank/<career_id>.json`, a JSON array of questions.
- `career_id` is one of `devops_engineer`, `mean_stack_developer`, `java_backend_developer`, `ai_developer`.
- A skill's questions go in the file of the career it belongs to. A skill shared by several careers (for example `git_version_control`) needs its questions copied into each career's file.

## One question

```json
{
  "question_id": "q_linux_fundamentals_001",
  "skill_id": "linux_fundamentals",
  "concept_tag": "file_permissions",
  "difficulty": "easy",
  "stem": "A file has permission mode 644 (rw-r--r--). What can users in the file's group do?",
  "options": [
    { "option_id": "opt_a", "text": "Read only" },
    { "option_id": "opt_b", "text": "Read and write" },
    { "option_id": "opt_c", "text": "Read, write, and execute" },
    { "option_id": "opt_d", "text": "Nothing" }
  ],
  "correct_option_id": "opt_a",
  "explanation": "644 breaks down as owner=rw(6), group=r(4), others=r(4). The group digit 4 grants read only.",
  "review_status": "approved",
  "source": "ai_drafted",
  "reviewed_on": ""
}
```

| Field | Rule |
|---|---|
| `question_id` | Unique within the file. Convention: `q_<skill_id>_<nnn>` |
| `skill_id` | Must be a skill of this career in `skills.json` |
| `concept_tag` | Must be one of that skill's `concept_tags`. Enforced indirectly: the skill needs a practice template for every tag its questions use, and a template's tag must belong to the skill |
| `difficulty` | `easy`, `medium` or `hard` |
| `stem`, `explanation` | No URLs (enforced) |
| `options` | Exactly 4, unique `option_id`s |
| `correct_option_id` | Must be one of the options. That exactly one option is correct is **by hand** (see below) |
| `review_status` | `approved` for anything the app may show |
| `source` | `ai_drafted` until a person has read and checked it, then `ai_drafted_human_reviewed`. Free text; the app does not read it, but the label must be true |
| `reviewed_on` | Empty until reviewed, then the date |

The app shuffles the options on every attempt, so the position of the correct option in the file does not matter. Do not rely on it, and do not read anything into it.

## How many questions a skill needs

A skill is only assessed when its bank has at least:

- **6 questions** in total (`min_bank_questions_per_skill`), and
- **2 questions per difficulty** (twice the 1-easy, 1-medium, 1-hard mix a check uses), so a re-check can pick questions the student has not seen.

So **2 easy + 2 medium + 2 hard = 6** per skill. A semester has 4 skills, so **24 questions** make a semester assessable (Semester 6 has only 2 quiz skills, so 12). A skill below the minimum is shown as "assessment coming soon" instead of failing.

Skills of type `build` (capstone) and `communication` (interview preparation) are never quiz-assessed, so they need no questions.

Each skill also needs **a practice template for every concept tag its questions use** (`practice_templates` in `skills.json`), so the coaching plan always has real material. A template needs a title, an action, a success check, a resource hint (a topic or search phrase, **never a URL**) and `estimated_minutes`.

## Writing good questions

Test one idea per question. For every question, check:

1. **One defensible answer.** Read each wrong option as if you were arguing for it. One draft here had a distractor (`orders RIGHT JOIN customers ON 1=0`) that also solved the problem, which made two correct answers. Run any code or commands you put in options.
2. **Wrong answers that are plausible**, ideally the mistake a real student makes. Do not use jokes or obviously absurd options.
3. **No giveaway by length or wording.** The right answer must not be the longest or most carefully qualified option. A test rejects a question whose right answer is at least twice as long as every wrong one and 15 or more characters longer. Aim for options of similar length and similar tone, and avoid "always" and "never" in wrong options only.
4. **No giveaway between questions.** One question's stem should not reveal another's answer.
5. **Difficulty means something.** Easy: recall a fact or a command. Medium: apply it to a small situation. Hard: reason about a trap, an edge case or an ordering (for example event-loop order, partial dependencies in a table, Bayes with a rare condition).
6. **Scenario over trivia** where you can: "your deploy fails with ..." beats "what does flag X do". Aim for about a third of questions to be scenarios.
7. **An explanation that teaches.** Say why the right answer is right and, where useful, why the tempting wrong one fails. Students see this on the review screen, and the coach reuses it when the AI is offline.
8. **Facts checked** against current documentation. Numbers in worked examples should be recomputed by hand or in code.

## Process

1. Draft the questions (by hand, or with an AI assistant). This repository does not generate drafts itself: `scripts/generate_question_drafts.py` is only a placeholder.
2. Save them with `"source": "ai_drafted"` and an empty `reviewed_on`.
3. Add the missing practice templates in `skills.json`.
4. Run `python scripts/validate_content.py`, then `python -m pytest`. Tests check bank sizes, the difficulty split, duplicate options, and the length rule above.
5. **A person reviews each question** against the checklist above. Change `source` to `ai_drafted_human_reviewed` and set `reviewed_on` only for questions that person has actually read. A review by the same assistant that drafted the questions is not a human review.
6. Restart the app. Content is validated once at start-up.

## Current state

| Career | Semester 3 bank | Review |
|---|---|---|
| DevOps Engineer | 24 questions (4 skills) | Labelled `ai_drafted_human_reviewed` during the first build, with `reviewed_on` set to a date after the commit that added them; no record of who reviewed them. **Unconfirmed** |
| MEAN Stack, AI | 24 questions each: 18 new plus 6 Git questions shared with DevOps | The 18 are `ai_drafted`; the 6 Git questions keep the unconfirmed DevOps label |
| Java Backend | 24 questions (4 skills) | All 24 are `ai_drafted` |
| Semesters 4-6, all careers | None | Not written |

In all, 60 questions are `ai_drafted` and not yet reviewed by a person. An assistant-only check of those 60 found and fixed one question with two correct answers, and lengthened the wrong options in about 20 questions where the right answer stood out by length. See the test report for the record.
