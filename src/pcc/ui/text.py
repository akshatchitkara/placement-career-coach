"""Display helpers for text that comes from content files, the AI or the student.

Streamlit renders labels, captions and markdown with a Markdown engine that also reads a pair of
dollar signs as maths. Text such as "$group and $sum" then loses its dollar signs and gets
restyled, which silently changes the meaning of a command or a database operator.
"""

import re

_ZERO_WIDTH_SPACE = "​"
_MARKDOWN_SPECIALS = set("\\`*_{}[]()#+-.!|~<>$")
_WEB_SCHEME = re.compile(r"\b(https?|ftp|mailto):", re.IGNORECASE)
_WWW = re.compile(r"\bwww\.", re.IGNORECASE)


def safe_md(text: str) -> str:
    """Escapes dollar signs so the text is shown exactly as written."""
    return text.replace("\\", "\\\\").replace("$", "\\$") if "$" in text else text


def escape_md(text: str) -> str:
    """Shows text the student typed literally, so a name cannot become a link, image or heading.

    Streamlit turns a bare web or e-mail address into a link even when its characters are
    escaped, so an invisible zero-width space is placed inside those patterns to break them.
    """
    text = _WEB_SCHEME.sub(lambda m: m.group(0) + _ZERO_WIDTH_SPACE, text)
    text = _WWW.sub(lambda m: "www" + _ZERO_WIDTH_SPACE + ".", text)
    text = text.replace("@", "@" + _ZERO_WIDTH_SPACE)
    return "".join("\\" + ch if ch in _MARKDOWN_SPECIALS else ch for ch in text)
