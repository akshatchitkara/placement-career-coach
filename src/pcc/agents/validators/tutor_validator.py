"""Tutor rules. Pure functions.

Reply rules V-TU-01..06 return violations (empty means acceptable). The input screen decides
whether a student's message is sent to the AI at all, and `sanitize_student_text` stops a
message from closing the tag that marks it as the student's words.
"""

import re

MAX_REPLY_CHARS = 1200

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_SCORING = re.compile(
    r"\b(your score|you scored|your level|your result)\b|\d+(\.\d+)?\s?%", re.IGNORECASE
)
_THIRD_PERSON = re.compile(r"\bthe student\b", re.IGNORECASE)

# A reply that quotes or describes its own instructions has leaked them.
_LEAK = re.compile(
    r"student_text|system prompt|developer prompt|my (instructions|rules) (are|say|state)"
    r"|here (are|is) (my|the) (instructions|rules|prompt)",
    re.IGNORECASE,
)
# Deliberately short: a catch for plainly abusive words, not a moderation system.
_PROFANE = re.compile(
    r"\b(fuck\w*|shit\w*|bitch\w*|asshole\w*|bastard\w*|cunt\w*|dick ?head|motherfuck\w*)\b",
    re.IGNORECASE,
)
# Phrases that only appear when someone is trying to steer the tutor, not learn from it.
_INJECTION = re.compile(
    r"(ignore|disregard|forget|override)\s+(all\s+)?(the\s+|your\s+|my\s+)?"
    r"(previous|prior|above|earlier|system|original)\s+(instructions?|rules?|prompts?)"
    r"|(ignore|disregard|forget)\s+(all\s+)?(your|these|those)\s+(instructions?|rules?|prompts?)"
    r"|(ignore|disregard|forget)\s+all\s+(the\s+)?(instructions?|rules?)"
    r"|(system|developer)\s+prompt|(reveal|print|show|repeat)\s+(me\s+)?your\s+"
    r"(instructions?|rules?|prompt)|</?\s*student_text|jailbreak|DAN\s+mode"
    r"|pretend\s+(to\s+be|you\s+are)|you\s+are\s+now\s+(a|an|the|DAN)\b",
    re.IGNORECASE,
)

BLOCKED_INPUT_REPLY = (
    "I can only help with this practice task, so I will not follow that request. Ask me "
    "about the task itself, or try the quiz to test yourself."
)
RESPECT_REPLY = (
    "Let us keep this friendly. I am here to help you learn this task, so ask me anything "
    "about it and I will explain."
)


def validate_tutor_reply(text: str) -> list[str]:
    errors: list[str] = []
    if not text.strip():
        errors.append("V-TU-01: reply is empty")
    elif len(text) > MAX_REPLY_CHARS:
        errors.append(f"V-TU-01: reply is {len(text)} characters, limit is {MAX_REPLY_CHARS}")
    if _URL.search(text):
        errors.append("V-TU-02: reply contains a URL")
    if _SCORING.search(text):
        errors.append("V-TU-03: reply talks about scores or levels")
    if _THIRD_PERSON.search(text):
        errors.append("V-TU-04: reply refers to 'the student' instead of 'you'")
    if _LEAK.search(text):
        errors.append("V-TU-05: reply exposes the tutor's instructions or markup")
    if _PROFANE.search(text):
        errors.append("V-TU-06: reply contains abusive language")
    return errors


def screen_student_text(text: str) -> str | None:
    """A fixed reply when the message should not reach the AI, otherwise None.

    This runs before any AI call, so an attack costs nothing and cannot succeed.
    """
    if _PROFANE.search(text):
        return RESPECT_REPLY
    if _INJECTION.search(text):
        return BLOCKED_INPUT_REPLY
    return None


def sanitize_student_text(text: str) -> str:
    """Angle brackets become look-alike characters, so no student text can form a tag."""
    return text.replace("<", "\u2039").replace(">", "\u203a")
