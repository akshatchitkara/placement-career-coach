"""Maps free-text career input to a catalog career (FR-17, T-19). Pure, no AI.

The only free text a student supplies is a career name, so it is length- and
character-limited (blueprint Section 14.10) before any matching happens.
"""

import re
from dataclasses import dataclass
from typing import Literal

from pcc.domain.schemas.career_schemas import Career

MAX_CAREER_TEXT_LENGTH = 60
_ALLOWED = re.compile(r"^[A-Za-z0-9 .,&+/#'\-]+$")


@dataclass(frozen=True)
class CareerResolution:
    status: Literal["matched", "unsupported", "invalid_input"]
    career: Career | None = None
    message: str = ""


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def resolve_career(text: str, careers: list[Career]) -> CareerResolution:
    cleaned = text.strip()
    if not cleaned:
        return CareerResolution("invalid_input", message="Enter a career name.")
    if len(cleaned) > MAX_CAREER_TEXT_LENGTH or not _ALLOWED.match(cleaned):
        return CareerResolution(
            "invalid_input",
            message=(
                f"Use up to {MAX_CAREER_TEXT_LENGTH} characters: letters, digits, spaces "
                "and basic punctuation only."
            ),
        )

    needle = _normalise(cleaned)
    for career in careers:  # exact name/alias first, so "mean" never loses to a substring hit
        if needle in {_normalise(career.name), *map(_normalise, career.aliases)}:
            return CareerResolution("matched", career=career)
    for career in careers:
        if any(re.search(rf"\b{re.escape(_normalise(a))}\b", needle) for a in career.aliases):
            return CareerResolution("matched", career=career)

    supported = ", ".join(c.name for c in careers)
    return CareerResolution(
        "unsupported",
        message=(
            f"'{cleaned}' is not supported yet. This coach currently covers "
            f"Computer Science careers only: {supported}."
        ),
    )
