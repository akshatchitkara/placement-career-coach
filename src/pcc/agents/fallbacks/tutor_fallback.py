"""Tutor fallback: a deterministic answer built from the curated explanation of a missed question.

Always passes V-TU-01..04 by construction, so the chat works with no AI at all.
"""

from pcc.domain.schemas.tutor_schemas import TutorContext, TutorKind


def template_reply(context: TutorContext, kind: TutorKind) -> str:
    task = context.task
    first = context.missed[0] if context.missed else None
    parts: list[str] = []
    if kind == "explain_differently" and first is not None:
        parts.append(
            f'Look at it from another angle. In the question "{first.stem}", '
            f'the right answer is "{first.correct_option_text}".'
        )
        parts.append(first.explanation)
    elif kind == "example":
        parts.append(f"Here is a hands-on way to see it: {task.action}")
    elif first is not None:
        parts.append(f"Here is what your practice material says about this: {first.explanation}")
    else:
        parts.append(task.misconception or f"This task is about {task.title.lower()}.")
    parts.append(f"You will know it worked when: {task.success_check}")
    parts.append("Try the quiz on this task to test yourself.")
    return " ".join(p.strip() for p in parts if p.strip())
