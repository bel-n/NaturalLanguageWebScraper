from __future__ import annotations

import csv
import json
from pathlib import Path

from src.monitor.content_groups import CONTENT_TYPES
from src.monitor.feature_builder import build_features
from src.monitor.pages import MONITORED_PAGES, allowed_monitored_pages
from src.monitor.storage import load_snapshots

# Baseline (rule-based) threshold from the proposal's ML section — only
# added here as a convenience reference column; real labeling/modeling
# happens in the ML phase, not in data collection.
UNSTABLE_CHANGE_THRESHOLD = 3


def build_dataset_rows(use_allowed_only: bool = True) -> list[dict]:
    pages = allowed_monitored_pages() if use_allowed_only else MONITORED_PAGES

    rows: list[dict] = []
    for page in pages:
        for content_type in CONTENT_TYPES:
            snapshots = load_snapshots(page.url, content_type)
            features = build_features(snapshots)
            if features is None:
                continue  # not enough history yet for this content group

            row = features.to_row()
            row["baseline_label"] = (
                "unstable" if features.number_of_changes > UNSTABLE_CHANGE_THRESHOLD else "stable"
            )
            rows.append(row)

    return rows


def export_dataset(rows: list[dict], out_path: str | Path = "dataset.csv") -> Path:
    out_path = Path(out_path)
    if out_path.suffix == ".json":
        out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return out_path

    if not rows:
        out_path.write_text("")
        return out_path

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return out_path