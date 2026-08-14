from __future__ import annotations

from typing import Optional


class DOMNode:
    def __init__(
        self,
        tag: str,
        text: str = "",
        attributes: Optional[dict] = None,
    ):
        self.tag = tag
        self.text = text
        self.attributes = attributes or {}

        self.children: list[DOMNode] = []
        self.parent: Optional[DOMNode] = None

    def add_child(self, child: DOMNode) -> None:
        child.parent = self
        self.children.append(child)

    def __repr__(self) -> str:
        return f"DOMNode(tag={self.tag!r}, text={self.text[:30]!r})"