# src/dom_preview.py
from __future__ import annotations

from dataclasses import dataclass

from src.dom_node import DOMNode
from src.dom_utils import collect_text
from src.intent import ScrapeIntent

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

# tag -> human label, in the order we want them presented
CONTENT_TYPES = {
    "heading": HEADING_TAGS,
    "paragraph": {"p"},
    "link": {"a"},
    "list_item": {"li"},
}


@dataclass
class PreviewMatch:
    content_type: str      # "heading" | "paragraph" | "link" | "list_item"
    text: str               # collected text, cleaned
    path: str                # e.g. "html > body > article > h2"
    href: str = ""           # only set for links


def find_matches_by_content_type(
    root: DOMNode, intent: ScrapeIntent
) -> dict[str, list[PreviewMatch]]:

    tag_to_type = {tag: ctype for ctype, tags in CONTENT_TYPES.items() for tag in tags}
    buckets: dict[str, list[PreviewMatch]] = {ctype: [] for ctype in CONTENT_TYPES}

    def walk(node: DOMNode) -> None:
        ctype = tag_to_type.get(node.tag)
        if ctype is not None:
            text = _clean(collect_text(node))
            if text and _matches_keywords(text, intent):
                buckets[ctype].append(
                    PreviewMatch(
                        content_type=ctype,
                        text=text,
                        path=dom_path(node),
                        href=node.attributes.get("href", "") if node.tag == "a" else "",
                    )
                )
        for child in node.children:
            walk(child)

    walk(root)
    return buckets


def dom_path(node: DOMNode) -> str:
    chain = []
    current: DOMNode | None = node
    while current is not None:
        chain.append(current.tag)
        current = current.parent
    return " > ".join(reversed(chain))


def _matches_keywords(text: str, intent: ScrapeIntent) -> bool:
    if not intent.keywords:
        return True
    lowered = text.lower()
    return all(kw in lowered for kw in intent.keywords)


def _clean(text: str) -> str:
    return " ".join(text.split())