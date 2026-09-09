from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from src.monitor.snapshot import Snapshot


@dataclass(frozen=True)
class ChangeEvent:
    """
    One observed change between two consecutive snapshots of the same
    content group.
    change_count: items added, removed, or replaced.
    change_size:  total character delta across those items.
    """
    from_timestamp: str
    to_timestamp: str
    change_count: int
    change_size: int


def diff_snapshots(previous: Snapshot, current: Snapshot) -> ChangeEvent:
    matcher = SequenceMatcher(a=previous.items, b=current.items, autojunk=False)

    change_count = 0
    change_size = 0

    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue

        removed = previous.items[a_start:a_end]
        added = current.items[b_start:b_end]

        change_count += max(len(removed), len(added))
        change_size += sum(len(item) for item in removed)
        change_size += sum(len(item) for item in added)

    return ChangeEvent(
        from_timestamp=previous.timestamp,
        to_timestamp=current.timestamp,
        change_count=change_count,
        change_size=change_size,
    )


def build_change_history(snapshots: list[Snapshot]) -> list[ChangeEvent]:
    """snapshots must already be sorted oldest -> newest (load_snapshots does this)."""
    return [diff_snapshots(snapshots[i - 1], snapshots[i]) for i in range(1, len(snapshots))]