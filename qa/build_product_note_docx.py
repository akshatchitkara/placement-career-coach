"""Builds docs/01_PRODUCT_NOTE.docx, the Task 1 product note, as a Word document.

Run:  python qa/build_product_note_docx.py
Needs python-docx (pip install python-docx). The note is written to fit 3 to 4 pages.
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "01_PRODUCT_NOTE.docx"
DIAGRAM = ROOT / "docs" / "assets" / "system-overview.png"

INDIGO = RGBColor(0x31, 0x2E, 0x81)
GREY = RGBColor(0x4B, 0x55, 0x63)
HEADER_FILL = "E0E7FF"
BAND_FILL = "F5F7FF"
BORDER = "C7CCE0"


# --- low-level helpers ---------------------------------------------------------------------
def _shade(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def _borders(table) -> None:
    props = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), BORDER)
        borders.append(el)
    props.append(borders)


def _cell_margins(table, top=40, bottom=40, left=80, right=80) -> None:
    props = table._tbl.tblPr
    margins = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    props.append(margins)


def _repeat_header(row) -> None:
    props = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    props.append(el)


def _no_split(row) -> None:
    props = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    props.append(el)


def _runs(paragraph, text: str, size: float | None = None, color: RGBColor | None = None) -> None:
    """Writes text where **double asterisks** make bold."""
    parts = text.split("**")
    for i, part in enumerate(parts):
        if not part:
            continue
        run = paragraph.add_run(part)
        run.bold = i % 2 == 1
        if size:
            run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color


def _page_number(footer_paragraph) -> None:
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_paragraph.add_run("Placement Career Coach · Product note · page ")
    run.font.size = Pt(8)
    run.font.color.rgb = GREY
    page = footer_paragraph.add_run()
    page.font.size = Pt(8)
    page.font.color.rgb = GREY
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        page._r.append(el)


# --- document builders ---------------------------------------------------------------------
def new_document() -> Document:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)  # A4
    section.left_margin = section.right_margin = Inches(0.8)
    section.top_margin, section.bottom_margin = Inches(0.7), Inches(0.7)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08
    for name, size in (("Heading 1", 13), ("Heading 2", 11)):
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = INDIGO
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(3)
        style.paragraph_format.keep_with_next = True
    _page_number(section.footer.paragraphs[0])
    return doc


def para(doc, text: str, *, size: float | None = None, after: float | None = None, color=None):
    p = doc.add_paragraph()
    _runs(p, text, size, color)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def bullet(doc, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.left_indent = Inches(0.22)
    _runs(p, text)


def table(doc, header: list[str], rows: list[list[str]], widths: list[float], size=8.5) -> None:
    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _borders(t)
    _cell_margins(t)
    for i, label in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.width = Inches(widths[i])
        _shade(cell, HEADER_FILL)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(label)
        run.bold = True
        run.font.size = Pt(size)
        run.font.color.rgb = INDIGO
    _repeat_header(t.rows[0])
    for n, values in enumerate(rows):
        row = t.add_row()
        _no_split(row)
        for i, text in enumerate(values):
            cell = row.cells[i]
            cell.width = Inches(widths[i])
            if n % 2 == 1:
                _shade(cell, BAND_FILL)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            _runs(p, text, size)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# --- the note ------------------------------------------------------------------------------
def build() -> Document:
    doc = new_document()

    title = doc.add_paragraph()
    run = title.add_run("Placement Career Coach: Product Note")
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = INDIGO
    title.paragraph_format.space_after = Pt(0)
    para(
        doc,
        "Akshat Chitkara · Product Manager assignment, Task 1 · October 2026 · "
        "a working prototype accompanies this note",
        size=9,
        after=6,
        color=GREY,
    )

    # 1 ----------------------------------------------------------------------------------------
    doc.add_heading("1. The product, the user and the scope decision", level=1)
    para(
        doc,
        "**The problem.** Students in Semesters 3 to 6 sit through theory-heavy lectures and "
        "arrive at placement season with no clear target role, no plan for the skills it needs and "
        "no honest feedback on where they stand. A placement cell cannot coach hundreds of students "
        "one to one. **The user** is an undergraduate Computer Science or IT student in Semesters 3 "
        "to 6 who wants a software or IT job. **The promise:** choose a career, get a Semester 3 to 6 "
        "roadmap, take a short skills check, see your level and your gap, get coached on your weakest "
        "skill, follow a weekly plan, re-check, and see what improved.",
    )
    para(
        doc,
        "**Scope decision, stated plainly.** The brief's examples run from Cloud Ops to an astronaut. "
        "For version one I support four computer science careers: DevOps, MEAN stack, Java backend "
        "and AI developer. Three reasons. First, technical skills have right and wrong answers that "
        "can be measured fairly; an astronaut's skills cannot be scored by a quiz. Second, these "
        "careers have widely agreed skill ladders, so a roadmap can be curated and checked instead of "
        "invented, and an invented roadmap for VLSI that nobody can verify would be worse than none. "
        "Third, depth beats breadth: four careers with questions behind every skill help students more "
        "than forty with none. A student who wants another career can leave a request that tells us "
        "what to add next, and adding a career is a content task (careers, skills, roadmap, questions), "
        "not a rewrite.",
    )
    para(
        doc,
        "**How we would know it works.** Weekly plan completion (tasks done over tasks given); "
        "re-check rate within 10 days of a coaching plan; skill-gap closure (change in the weakest skill "
        "between checks); and level progression per semester.",
    )

    # 2 ----------------------------------------------------------------------------------------
    doc.add_heading("2. The student's journey, and what brings them back every week", level=1)
    table(
        doc,
        ["Stage", "The student thinks", "The product does"],
        [
            [
                "1 Choose",
                "“Which role?”",
                "Four careers, each showing what it is, what you do day to day and how you can grow",
            ],
            [
                "2 Plan",
                "“What do I learn, and when?”",
                "A road of 16 monthly stops across Semesters 3 to 6, each with topics and a deliverable",
            ],
            [
                "3 Baseline",
                "“Where do I stand?”",
                "A 12-question check on this semester's skills: level, per-skill scores, a “you are here” marker",
            ],
            [
                "4 Improve",
                "“What do I fix first?”",
                "A practice plan for the weakest skill; each task is tied to a question they missed, and a coach answers follow-up questions",
            ],
            [
                "5 Weekly",
                "“What do I do this week?”",
                "3 to 5 tasks laid over seven days, at most four hours, ending with a re-check date",
            ],
            [
                "6 Re-check",
                "“Did it work?”",
                "Seven days later: new, unseen questions on the same skills, compared with last time",
            ],
            [
                "7 Ready",
                "“Am I placement-ready?”",
                "A full-path check across every roadmap skill, the only route to the Industry-ready level",
            ],
        ],
        [0.85, 1.75, 4.05],
    )
    para(
        doc,
        "**Why they return each week.** There is always one concrete thing to do, not a reading "
        "list: a weekly plan sized to the hours they have. There is exactly one weakest skill to "
        "fix, so the next step is never unclear. Progress is visible and close: the “you are "
        "here” marker moves along the road as each module quiz is passed, a result says "
        "“6.7 points to Advanced”, and a re-check shows “Linux 33% to 67%”. Small "
        "wins are rewarded with XP, ranks and badges, so effort counts before the score moves. "
        "Reminders and streaks come later, once the product records weekly activity.",
    )

    # 3 ----------------------------------------------------------------------------------------
    doc.add_heading(
        "3. The system: one controller that decides, and agents that each do one job", level=1
    )
    para(
        doc,
        "The product is one controller and five agents. The controller owns the journey and every "
        "decision about what happens next; each agent has a single job and may only compute, draft "
        "or explain. Anything an AI writes is checked by code before a student sees it, and each "
        "agent has a curated fallback, so no AI step can leave a student stuck.",
    )
    doc.add_picture(str(DIAGRAM), width=Inches(6.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.space_after = Pt(4)
    table(
        doc,
        ["Part", "Responsible for", "AI or code"],
        [
            [
                "**Workflow controller** (orchestrator)",
                "Moves the student through the states (roadmap ready, check in progress, results, coaching, "
                "weekly plan, re-check due), decides what happens next, saves progress",
                "Code",
            ],
            [
                "**Roadmap agent**",
                "Supplies the curated 16-month path for the career. AI may reword months, but a validator "
                "rejects any change to skill order, any missing or invented skill and any link; then the "
                "curated path is used",
                "Code, AI wording",
            ],
            [
                "**Evaluation agent**",
                "Picks questions with a fixed difficulty mix, shuffles options, grades, and computes skill "
                "scores, the level, the weakest skill and the position on the roadmap",
                "Code only",
            ],
            [
                "**Coaching agent**",
                "Writes a short plan for the weakest skill. Every task must link to a missed question; a plan "
                "that fails the checks is replaced by a curated one built from the same mistakes",
                "AI writes, code checks",
            ],
            [
                "**Weekly planner**",
                "Builds the week by rules: up to two coaching tasks, then the next roadmap topic, then "
                "revision, always ending with the re-check",
                "Code only",
            ],
            [
                "**Tutor**",
                "Explains one coaching task on request and runs a short practice quiz graded by code. Typed "
                "questions are screened before any AI call, and replies that mention scores, leak "
                "instructions or contain links are rejected",
                "AI explains, code checks",
            ],
        ],
        [1.45, 4.1, 1.1],
    )
    para(
        doc,
        "**Who decides what happens each week, and what is passed.** The controller decides, by "
        "rules and never by AI. After each check: a skill at 60 or more counts as mastered and the "
        "roadmap marker moves on (60 to 79 also gets one revision task); 40 to 59 stays active and "
        "gets a new plan from the new mistakes; below 40 also produces a ready-to-send message "
        "asking a mentor for help. Information moves in one direction through narrow contracts: the "
        "evaluation agent gives the coaching agent only the weakest skill and the questions missed (never "
        "the student's name), the coaching agent gives the planner its tasks, and the planner gives the "
        "controller the week. Every AI step has a validator and a curated fallback, so with no AI at all "
        "the product still works.",
    )
    para(
        doc,
        "**Agents I would add later:** a voice-interview agent and a rubric marker for written and "
        "assignment work, a content-review agent that flags weak questions, and a nudge agent for "
        "reminders. Choosing the assessment method is a rule, not an agent (next section).",
    )

    # 4 ----------------------------------------------------------------------------------------
    doc.add_heading(
        "4. Choosing the assessment method, and keeping scoring consistent and fair", level=1
    )
    table(
        doc,
        ["Skill type", "Method", "Why", "Status"],
        [
            [
                "Knowledge (Linux commands, SQL, HTTP)",
                "Multiple-choice quiz",
                "Objective, fast, repeatable",
                "**Built**",
            ],
            [
                "Reasoning and design",
                "Written answer marked against a rubric",
                "Shows thinking, not recall",
                "Later",
            ],
            [
                "Applied building (Docker, Terraform, APIs)",
                "Hands-on assignment with a checklist",
                "Proves the student can do it",
                "Later",
            ],
            [
                "Communication, interview skills",
                "Voice interview against a rubric",
                "Tests articulation",
                "Later",
            ],
        ],
        [2.0, 2.0, 1.95, 0.7],
    )
    para(
        doc,
        "**The rule.** The method follows the skill's type, decided in code. If a method is not built "
        "yet, the skill is shown as “assessed later” and is never quietly scored with a quiz "
        "instead; the result is labelled a baseline knowledge check, not a hiring verdict.",
    )
    para(
        doc,
        "**Scoring that is the same for everyone.** A question is right or wrong; a skill score is "
        "right over answered; the overall score is total right over total answered, with no hidden "
        "weights. Fairness comes from a fixed test shape: three questions per skill (easy, medium, "
        "hard), shuffled options, at least two answers before a skill counts as evidence, and a "
        "re-check that draws unseen questions first from a bank of at least six per skill. No AI takes "
        "part in grading. Each attempt stores the settings it was scored with, so changing a threshold "
        "later never rewrites an old result. For rubric-based methods the same principle holds: fixed "
        "criteria scored 0 to 4, converted to the same 0 to 100 skill score, with a person sampling "
        "the marks.",
    )
    para(
        doc,
        "**Levels.** Below 40 is Beginner; 40 to 64.9 Intermediate; 65 to 84.9 Advanced; 85 and above "
        "Industry-ready, but only if every tested skill is at least 60 and the check covered every core "
        "skill of the career. A semester check covers a quarter of them, so it caps at Advanced and "
        "says why; the 28-question full-path check is the way to Industry-ready.",
    )
    para(
        doc,
        "**Worked example (DevOps, Semester 3).** Linux 1 of 3, Shell 1 of 3, Python 2 of 3 and Git "
        "2 of 3 give 6 of 12, which is **50.0%, Intermediate**. Linux and Shell tie at 33.3%, and the "
        "earlier skill on the roadmap wins the tie, so Linux is the weakest skill, the student stands at "
        "Semester 3, Month 1, and the plan has three to five Linux tasks tied to the two Linux "
        "questions missed.",
    )

    # 5 ----------------------------------------------------------------------------------------
    doc.add_heading(
        "5. What I would build first, next and later, and what I would leave out", level=1
    )
    table(
        doc,
        ["When", "What", "Why this order"],
        [
            [
                "**First**",
                "Career choice; roadmap; semester check; deterministic scoring and levels; weakest skill; "
                "coaching plan; weekly plan with a re-check date; saved progress",
                "These are the three parts of the brief, and the weekly loop is what makes the product worth "
                "using. Without trustworthy scoring nothing else can be trusted",
            ],
            [
                "**Next**",
                "Re-check and progress view; full-path check for Industry-ready; a coach students can question; "
                "module quizzes with XP, ranks and badges; optional AI wording",
                "Each needs the first set to exist, and each adds retention or trust once the loop works",
            ],
            [
                "**Later**",
                "Written, assignment and voice assessments; a career finder for undecided students; more careers "
                "beyond computer science; a teacher view; reminders and streaks",
                "They need rubrics, reviewed content or an institution to run them",
            ],
            [
                "**Left out**",
                "Logins and roles, proctoring, leaderboards, a job marketplace, AI-written answer keys, "
                "agent frameworks",
                "The brief did not ask for them; proctoring and leaderboards can harm learning; an AI answer key "
                "is unfair when it is wrong; frameworks add risk without proving the idea",
            ],
        ],
        [0.75, 3.35, 2.55],
    )
    para(
        doc,
        "**Where the prototype stands.** Built and tested: four careers, 64 roadmap months, about 320 "
        "questions, the full journey with and without an AI, the full-path check, the coach with its "
        "guardrails, and about 600 automated tests, 38 of them in a real browser. Not built: the three "
        "other assessment methods, the career finder, any career outside computer science, accounts and "
        "reminders.",
    )
    para(
        doc,
        "**Risks I would deal with before a pilot.** The questions were drafted with AI help and have "
        "not been reviewed by a subject expert, and a level is only as trustworthy as its questions, so "
        "that review comes first. Roadmaps are curated, not generated per student, so personalisation "
        "today comes from the assessment and the weekly plan. And a quiz measures knowledge, not the "
        "ability to build, which is why the applied-skill assessments are the next investment.",
    )
    return doc


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    build().save(OUT)
    print(f"wrote {OUT}")
