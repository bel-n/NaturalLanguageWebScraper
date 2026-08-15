from __future__ import annotations

from datetime import date

from dateutil import parser as date_parser

from src.dom_node import DOMNode


def collect_text(node: DOMNode) -> str:
    """
    Full text of a node's subtree.

    DOMNode.text only holds text directly under a node (see parser.py) —
    for anything above single-tag granularity (a whole news item, a whole
    listing card) you need the joined text of every descendant, which is
    what scoring and keyword/date matching need to work against.
    """

    parts = [node.text] if node.text else []
    for child in node.children:
        child_text = collect_text(child)
        if child_text:
            parts.append(child_text)
    return " ".join(parts)


def date_in_text(text: str, target: date) -> bool:
    """
    True if any date-like substring in `text` resolves to `target`.

    Tries dateutil's fuzzy parsing on the whole string first (cheap, catches
    most "Published Aug 13, 2026" / "13/08/2026" cases), then falls back to
    scanning individual tokens/short windows so a date buried in a longer
    sentence doesn't get lost.
    """

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

    # dateutil fills in missing fields (e.g. missing year) using `default`.
    # If the parsed year matches our deliberately-unlikely default, the
    # string almost certainly wasn't a real date — reject it instead of
    # silently matching on a false positive.
    if parsed.year == _UNLIKELY_DEFAULT.year and str(_UNLIKELY_DEFAULT.year) not in candidate:
        return None

    return parsed.date()


from datetime import datetime  # noqa: E402  (kept near its only use)

_UNLIKELY_DEFAULT = datetime(1587, 1, 1)


def looks_like_headline(node: DOMNode) -> bool:
    if node.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return True
    classes = " ".join(node.attributes.get("class", [])).lower()
    if "title" in classes or "headline" in classes:
        return True
    # An <a> only counts as a headline when it's actually acting as one
    # (nested directly inside a heading tag, e.g. <h3><a>Book title</a></h3>).
    # Treating EVERY <a> as headline-worthy was too loose — on a page
    # where an item's only links are things like tag chips ("humor",
    # "life"), that rule picked a random tag as the "title" instead of
    # recognizing there's no real headline in this item at all.
    if node.tag == "a" and node.parent is not None and node.parent.tag in (
        "h1", "h2", "h3", "h4", "h5", "h6",
    ):
        return True
    return False
