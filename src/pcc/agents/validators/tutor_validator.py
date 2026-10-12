"""Tutor reply rules V-TU-01..04. Pure; returns violations (empty means acceptable)."""

import re

MAX_REPLY_CHARS = 1200

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_SCORING = re.compile(
    r"\b(your score|you scored|your level|your result)\b|\d+(\.\d+)?\s?%", re.IGNORECASE
)
_THIRD_PERSON = re.compile(r"\bthe student\b", re.IGNORECASE)


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
    return errors
