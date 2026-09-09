from __future__ import annotations

from src.dom_node import DOMNode
from src.dom_utils import collect_text

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
PARAGRAPH_TAGS = ("p",)
LINK_TAGS = ("a",)

CONTENT_TYPES = ("headings", "paragraphs", "links")


def extract_content_groups(root: DOMNode) -> dict[str, list[str]]:

    groups: dict[str, list[str]] = {ctype: [] for ctype in CONTENT_TYPES}
    _walk(root, groups)
    return groups


def _walk(node: DOMNode, groups: dict[str, list[str]]) -> None:
    if node.tag in HEADING_TAGS:
        text = _normalize(collect_text(node))
        if text:
            groups["headings"].append(text)
    elif node.tag in PARAGRAPH_TAGS:
        text = _normalize(collect_text(node))
        if text:
            groups["paragraphs"].append(text)
    elif node.tag in LINK_TAGS:
        label = _normalize(collect_text(node))
        href = node.attributes.get("href", "")
        if label or href:
            groups["links"].append(f"{label}|{href}")

    for child in node.children:
        _walk(child, groups)


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()