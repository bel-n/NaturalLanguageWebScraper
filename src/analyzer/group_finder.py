from __future__ import annotations

from src.dom_node import DOMNode

MIN_GROUP_SIZE = 2  


def find_candidate_groups(root: DOMNode) -> list[list[DOMNode]]:
    """""
    Find every group of sibling nodes that look like a repeating list
    (same tag + same class signature, appearing MIN_GROUP_SIZE+ times
    under the same parent).
    """

    groups: list[list[DOMNode]] = []
    _walk(root, groups)
    return groups


def _walk(node: DOMNode, groups: list[list[DOMNode]]) -> None:
    groups.extend(_group_children_by_signature(node))
    for child in node.children:
        _walk(child, groups)


def _group_children_by_signature(node: DOMNode) -> list[list[DOMNode]]:
    buckets: dict[tuple, list[DOMNode]] = {}
    for child in node.children:
        signature = _signature(child)
        buckets.setdefault(signature, []).append(child)

    return [group for group in buckets.values() if len(group) >= MIN_GROUP_SIZE]


def _signature(node: DOMNode) -> tuple:
    classes = node.attributes.get("class", [])
    return (node.tag, tuple(sorted(classes)))


def group_signature(group: list[DOMNode]) -> tuple:
    """Public signature of an already-picked group, so a later page can
    be matched back to 'the same list' without re-scoring from scratch."""
    return _signature(group[0])


def find_group_by_signature(groups: list[list[DOMNode]], signature: tuple) -> list[DOMNode] | None:
    for group in groups:
        if group_signature(group) == signature:
            return group
    return None
