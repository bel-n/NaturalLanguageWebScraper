from __future__ import annotations

from src.dom_node import DOMNode
from src.dom_utils import collect_text, date_in_text, looks_like_headline
from src.intent import ScrapeIntent
from src.nav_detection import has_price_pattern, is_in_navigation


def _scored_groups(groups: list[list[DOMNode]], intent: ScrapeIntent) -> list[tuple[float, list[DOMNode]]]:
    scored = [(score_group(group, intent), group) for group in groups]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


def rank_groups(groups: list[list[DOMNode]], intent: ScrapeIntent) -> list[list[DOMNode]]:
    """
    All candidate groups, best-scoring first. This is what the preview
    loop walks through when the user says the first guess was wrong —
    same ranking pick_best_group uses, just not stopping at #1.
    """

    return [group for _, group in _scored_groups(groups, intent)]


def pick_best_group(groups: list[list[DOMNode]], intent: ScrapeIntent) -> list[DOMNode] | None:
    scored = _scored_groups(groups, intent)
    if not scored:
        return None
    best_score, best_group = scored[0]
    if best_score > 0 or not (intent.keywords or intent.date_filter):
        return best_group
    return _best_nonzero(scored)


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

    # A sidebar/menu list is structurally identical to a content list
    # (both are repeating <a>/<li> groups) — nothing above tells them
    # apart, so we penalize anything that lives inside nav-shaped markup.
    sample = group[: min(len(group), 5)]
    nav_penalty = -1.5 if any(is_in_navigation(item) for item in sample) else 0.0

    # If the user wants a price, a group whose items actually contain
    # currency-like text is almost certainly the right one.
    price_bonus = 0.0
    if "price" in intent.fields and any(has_price_pattern(collect_text(i)) for i in sample):
        price_bonus = 0.3

    # Content vs. a list of link labels ("Top Ten tags", a nav menu) —
    # actual content (a quote, an article, a product card) tends to
    # carry far more text per item than a bare list of short labels.
    # This is what stops a same-sized tag cloud from outscoring the
    # real list just because it happens to have more/equal items.
    avg_text_len = sum(len(collect_text(item)) for item in sample) / len(sample)
    richness_bonus = min(avg_text_len / 150, 1.0) * 0.4

    return avg + size_bonus + nav_penalty + price_bonus + richness_bonus


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
    """
    Applies keyword/date filtering only. Deliberately does NOT apply
    intent.limit — with pagination, "last 5" has to be enforced once
    across ALL pages combined, not 5-per-page. See main.py.
    """

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

    return items
