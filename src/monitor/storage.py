from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from src.monitor.snapshot import Snapshot

DATA_DIR = Path("data/snapshots")


def _slug_for(page_url: str) -> str:
    host = urlparse(page_url).netloc or page_url
    return host.replace(":", "_").replace("/", "_")


def _path_for(page_url: str, content_type: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{_slug_for(page_url)}__{content_type}.jsonl"


def append_snapshot(snapshot: Snapshot) -> None:
    """Append-only on purpose — the full timestamped history is the raw
    material the feature calculations run over, so nothing gets
    overwritten or rolled up here."""
    path = _path_for(snapshot.page_url, snapshot.content_type)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")


def load_snapshots(page_url: str, content_type: str) -> list[Snapshot]:
    path = _path_for(page_url, content_type)
    if not path.exists():
        return []

    snapshots = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                snapshots.append(Snapshot.from_dict(json.loads(line)))

    snapshots.sort(key=lambda s: s.timestamp)
    return snapshots