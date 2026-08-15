from __future__ import annotations

import re

from src.dom_node import DOMNode

_CURRENCY_RE = re.compile(r"[£$€]\s?\d|\d+[.,]\d{2}\s?[£$€]?")
_NAV_MARKERS = ("nav", "menu", "sidebar", "breadcrumb", "footer")


def has_price_pattern(text: str) -> bool:
    return bool(_CURRENCY_RE.search(text))


def is_in_navigation(node: DOMNode) -> bool:
    """
    True if this node lives inside something nav-shaped — a <nav>,
    <header>, <footer>, or a container whose class names it as a menu
    or sidebar. Sidebars are structurally identical to content lists
    (both are repeating <a>/<li> groups), so scoring can't tell them
    apart from shape alone — this is what breaks the tie.
    """

    current = node.parent
    while current is not None:
        if current.tag in ("nav", "header", "footer"):
            return True
        classes = " ".join(current.attributes.get("class", [])).lower()
        if any(marker in classes for marker in _NAV_MARKERS):
            return True
        current = current.parent
    return False
