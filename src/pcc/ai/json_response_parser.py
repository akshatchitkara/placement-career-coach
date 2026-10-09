"""Turns raw model text into a JSON object. Never trusts the shape -- callers validate it."""

import json
import re
from typing import Any

from pcc.core.exceptions import AiOutputInvalidError

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_object(raw: str) -> dict[str, Any]:
    text = _FENCE.sub("", raw.strip())
    if not text.startswith("{"):  # tolerate a short preamble before the object
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise AiOutputInvalidError("response contains no JSON object")
        text = text[start : end + 1]
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AiOutputInvalidError(f"response is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise AiOutputInvalidError("response JSON is not an object")
    return value
