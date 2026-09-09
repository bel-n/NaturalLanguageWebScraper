from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.fetcher import fetch_page
from src.parser import parse_html
from src.monitor.content_groups import extract_content_groups, CONTENT_TYPES


@dataclass
class Snapshot:
    page_url: str
    category: str
    expected_frequency: str
    content_type: str
    timestamp: str  # ISO 8601, UTC
    items: list[str] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def content_hash(self) -> str:
        joined = "\n".join(self.items)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "page_url": self.page_url,
            "category": self.category,
            "expected_frequency": self.expected_frequency,
            "content_type": self.content_type,
            "timestamp": self.timestamp,
            "items": self.items,
        }

    @staticmethod
    def from_dict(data: dict) -> "Snapshot":
        return Snapshot(
            page_url=data["page_url"],
            category=data["category"],
            expected_frequency=data["expected_frequency"],
            content_type=data["content_type"],
            timestamp=data["timestamp"],
            items=list(data.get("items", [])),
        )


def take_snapshots(page_url: str, category: str, expected_frequency: str) -> list[Snapshot]:
    """Fetches one page, returns one Snapshot per tracked content type,
    all stamped with the same timestamp."""
    html = fetch_page(page_url)
    root = parse_html(html)
    groups = extract_content_groups(root)

    timestamp = datetime.now(timezone.utc).isoformat()

    return [
        Snapshot(
            page_url=page_url,
            category=category,
            expected_frequency=expected_frequency,
            content_type=content_type,
            timestamp=timestamp,
            items=groups.get(content_type, []),
        )
        for content_type in CONTENT_TYPES
    ]