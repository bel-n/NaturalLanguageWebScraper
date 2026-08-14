from __future__ import annotations

from datetime import date

from dateutil import parser as date_parser

from src.dom_node import DOMNode


def collect_text(node: DOMNode) -> str:


    parts = [node.text] if node.text else []
    for child in node.children:
        child_text = collect_text(child)
        if child_text:
            parts.append(child_text)
    return " ".join(parts)


def date_in_text(text: str, target: date) -> bool:

    if not text.strip():
        return False

    if _try_parse(text) == target:
        return True

    words = text.split()
    for window in (3, 2):
        for i in range(len(words) - window + 1):
            candidate = " ".join(words[i:i + window])
            if _try_parse(candidate) == target:
                return True

    return False


def _try_parse(candidate: str) -> date | None:
    try:
        parsed = date_parser.parse(candidate, fuzzy=True, default=_UNLIKELY_DEFAULT)
    except (ValueError, OverflowError):
        return None


    if parsed.year == _UNLIKELY_DEFAULT.year and str(_UNLIKELY_DEFAULT.year) not in candidate:
        return None

    return parsed.date()


from datetime import datetime 

_UNLIKELY_DEFAULT = datetime(1587, 1, 1)


def looks_like_headline(node: DOMNode) -> bool:
    if node.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return True
    if node.tag == "a" and node.text:
        return True
    classes = " ".join(node.attributes.get("class", [])).lower()
    return "title" in classes or "headline" in classes
