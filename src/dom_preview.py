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


def format_preview(buckets: dict[str, list["PreviewMatch"]], max_per_type: int = 5) -> str:

    non_empty = {ctype: matches for ctype, matches in buckets.items() if matches}

    if not non_empty:
        return "We didn't find any matches"

    counts = ", ".join(
        f"{len(matches)} {_pluralize(ctype, len(matches))}"
        for ctype, matches in non_empty.items()
    )
    lines = [f"We found {counts}:matching your request.\n"]

    
    for ctype, matches in non_empty.items():
        lines.append(f"{ctype.replace('_', ' ').title()}s:")
        shown = matches[:max_per_type]
        for i, match in enumerate(shown, start=1):
            text = match.text if len(match.text) <= 120 else match.text[:117] + "..."
            if match.content_type == "link" and match.href:
                lines.append(f'  {i}. [{match.path}] "{text}" -> {match.href}')
            else:
                lines.append(f'  {i}. [{match.path}] "{text}"')
        remaining = len(matches) - len(shown)
        if remaining > 0:
            lines.append(f"  ... ({remaining} more not shown)")
        lines.append("")

    return "\n".join(lines).rstrip()

def _pluralize(content_type: str, count: int) -> str:
    label = content_type.replace("_"," ")
    if count == 1:
        return label
    return label + ("es" if label.endswith(("ch", "s")) else "s")

