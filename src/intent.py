from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class ScrapeIntent:
    """
    Structured representation of what the user asked for, in plain language.

    Nothing downstream (group scoring, item filtering, field extraction,
    export) should ever touch the user's raw sentence again once this
    object exists — it's the single source of truth for "what do we want".
    """

    target_type: str = "generic"          # "news", "listing", "generic"
    keywords: list[str] = field(default_factory=list)   # must appear in item text
    category: Optional[str] = None        # "humor" — a genre/category to navigate to, not filter by
    location: Optional[str] = None        # "town A" — soft signal, boosts scoring, never excludes
    date_filter: Optional[date] = None    # resolved from "yesterday" / "today" / explicit date
    limit: Optional[int] = None           # "last 5"
    fields: list[str] = field(default_factory=list)      # ["title"] or [] = everything
    output_format: str = "json"           # "csv" | "json"

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        parts = [f"target_type={self.target_type!r}"]
        if self.keywords:
            parts.append(f"keywords={self.keywords!r}")
        if self.category:
            parts.append(f"category={self.category!r}")
        if self.location:
            parts.append(f"location={self.location!r}")
        if self.date_filter:
            parts.append(f"date_filter={self.date_filter.isoformat()}")
        if self.limit is not None:
            parts.append(f"limit={self.limit}")
        if self.fields:
            parts.append(f"fields={self.fields!r}")
        parts.append(f"output_format={self.output_format!r}")
        return f"ScrapeIntent({', '.join(parts)})"
