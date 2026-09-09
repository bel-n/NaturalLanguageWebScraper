from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime

from src.monitor.diff import build_change_history
from src.monitor.snapshot import Snapshot


@dataclass(frozen=True)
class ContentGroupFeatures:
    page_url: str
    category: str
    expected_frequency: str
    content_type: str
    observation_start: str
    observation_end: str
    num_snapshots: int
    number_of_changes: int
    average_size_of_change: float
    variance_of_changes: float
    change_frequency: float  # changes per day over the observed window

    def to_row(self) -> dict:
        return {
            "page_url": self.page_url,
            "category": self.category,
            "expected_frequency": self.expected_frequency,
            "content_type": self.content_type,
            "observation_start": self.observation_start,
            "observation_end": self.observation_end,
            "num_snapshots": self.num_snapshots,
            "number_of_changes": self.number_of_changes,
            "average_size_of_change": round(self.average_size_of_change, 4),
            "variance_of_changes": round(self.variance_of_changes, 4),
            "change_frequency": round(self.change_frequency, 6),
        }


def build_features(snapshots: list[Snapshot]) -> "ContentGroupFeatures | None":
    """
    Turns one content group's full snapshot history into the four
    features the modeling phase needs. Returns None if there's not
    enough history yet (need >=2 snapshots to observe a single change).
    """
    if len(snapshots) < 2:
        return None

    history = build_change_history(snapshots)
    real_changes = [event for event in history if event.change_count > 0]

    sizes = [event.change_size for event in real_changes]
    average_size = statistics.mean(sizes) if sizes else 0.0
    variance = statistics.variance(sizes) if len(sizes) > 1 else 0.0

    start = datetime.fromisoformat(snapshots[0].timestamp)
    end = datetime.fromisoformat(snapshots[-1].timestamp)
    observed_days = max((end - start).total_seconds() / 86400, 1e-9)
    change_frequency = len(real_changes) / observed_days

    first = snapshots[0]
    return ContentGroupFeatures(
        page_url=first.page_url,
        category=first.category,
        expected_frequency=first.expected_frequency,
        content_type=first.content_type,
        observation_start=snapshots[0].timestamp,
        observation_end=snapshots[-1].timestamp,
        num_snapshots=len(snapshots),
        number_of_changes=len(real_changes),
        average_size_of_change=average_size,
        variance_of_changes=variance,
        change_frequency=change_frequency,
    )