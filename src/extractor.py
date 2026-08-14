from __future__ import annotations

from bs4 import BeautifulSoup

from src.dom_node import DOMNode
from src.dom_utils import collect_text, looks_like_headline


def extract_by_selectors(html: str, selector_map: dict[str, str]) -> list[dict]:
    """
    Direct path for users who already know the CSS. `selector_map` is
    {field_name: css_selector}. Each selector is expected to match one
    element per "item" — we zip them positionally, so give selectors
    that select consistently-ordered repeating elements
    (e.g. {"title": ".article h2", "date": ".article .date"}).

    Deliberately bypasses the whole DOMNode/intent/heuristic pipeline —
    if the user can name the selector, there's nothing to infer.
    """

    soup = BeautifulSoup(html, "html.parser")

    matches = {field: soup.select(selector) for field, selector in selector_map.items()}
    counts = {len(v) for v in matches.values()}
    if len(counts) > 1:
        raise ValueError(
            "Selectors returned different numbers of matches "
            f"({ {f: len(v) for f, v in matches.items()} }) — "
            "they need to line up one-per-item."
        )

    count = counts.pop() if counts else 0
    return [
        {field: elements[i].get_text(strip=True) for field, elements in matches.items()}
        for i in range(count)
    ]


def extract_fields(item: DOMNode, fields: list[str]) -> dict:
    """
    Heuristic per-field extraction from one item's subtree.

    If the intent didn't name specific fields, return everything we can
    infer (title + full text) rather than guessing wrong narrowly.
    """

    if not fields:
        return {"title": _guess_title(item), "text": collect_text(item)}

    result = {}
    for field_name in fields:
        if field_name == "title":
            result["title"] = _guess_title(item)
        elif field_name == "link":
            result["link"] = _guess_link(item)
        elif field_name == "date":
            result["date"] = _guess_date_text(item)
        else:
            # price / address / anything else without a dedicated guesser
            # yet: fall back to full text so nothing is silently dropped.
            result[field_name] = collect_text(item)
    return result


def _guess_title(item: DOMNode) -> str:
    for node in _flatten(item):
        if looks_like_headline(node) and node.text:
            return node.text
    # Fall back to the longest direct-text node in the subtree.
    candidates = [n.text for n in _flatten(item) if n.text]
    return max(candidates, key=len) if candidates else collect_text(item)


def _guess_link(item: DOMNode) -> str:
    for node in _flatten(item):
        if node.tag == "a" and node.attributes.get("href"):
            return node.attributes["href"]
    return ""


def _guess_date_text(item: DOMNode) -> str:
    for node in _flatten(item):
        classes = " ".join(node.attributes.get("class", [])).lower()
        if "date" in classes or node.tag == "time":
            return node.text or node.attributes.get("datetime", "")
    return ""


def _flatten(node: DOMNode):
    yield node
    for child in node.children:
        yield from _flatten(child)
