from __future__ import annotations

from src.dom_node import DOMNode
from src.dom_utils import collect_text, date_in_text, looks_like_headline
from src.intent import ScrapeIntent


def pick_best_group(groups: list[list[DOMNode]], intent: ScrapeIntent) -> list[DOMNode] | None:
    if not groups:
        return None
    scored = [(score_group(group, intent), group) for group in groups]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best_group = scored[0]
    return best_group if best_score > 0 or not (intent.keywords or intent.date_filter) else _best_nonzero(scored)


def _best_nonzero(scored: list[tuple[float, list[DOMNode]]]) -> list[DOMNode] | None:
    for score, group in scored:
        if score > 0:
            return group
    return None


def score_group(group: list[DOMNode], intent: ScrapeIntent) -> float:
    """
    Average per-item relevance, scaled slightly by group size so a
    convincing 20-item list beats a lucky 2-item match.
    """

    if not group:
        return 0.0

    per_item_scores = [_score_item(item, intent) for item in group]
    avg = sum(per_item_scores) / len(per_item_scores)
    size_bonus = min(len(group), 10) / 10 * 0.2
    return avg + size_bonus


def _score_item(node: DOMNode, intent: ScrapeIntent) -> float:
    text = collect_text(node).lower()
    score = 0.0

    for keyword in intent.keywords:
        if keyword in text:
            score += 1.0

    if intent.location and intent.location.lower() in text:
        score += 0.5  # soft signal — never excludes, only boosts

    if intent.date_filter and date_in_text(text, intent.date_filter):
        score += 1.0

    if intent.target_type == "news" and any(looks_like_headline(c) for c in _flatten(node)):
        score += 0.3

    return score


def _flatten(node: DOMNode):
    yield node
    for child in node.children:
        yield from _flatten(child)


def filter_items(group: list[DOMNode], intent: ScrapeIntent) -> list[DOMNode]:
    items = group

    if intent.keywords:
        items = [
            item for item in items
            if all(kw in collect_text(item).lower() for kw in intent.keywords)
        ]

    if intent.date_filter:
        items = [
            item for item in items
            if date_in_text(collect_text(item).lower(), intent.date_filter)
        ]

    if intent.limit:
        items = items[: intent.limit]

    return items
