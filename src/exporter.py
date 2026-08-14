from __future__ import annotations

import csv
import json
from pathlib import Path


def export(items: list[dict], fmt: str, path: str | Path) -> Path:
    path = Path(path)

    if fmt == "csv":
        _export_csv(items, path)
    elif fmt == "json":
        _export_json(items, path)
    else:
        raise ValueError(f"Unknown export format: {fmt!r}")

    return path


def _export_csv(items: list[dict], path: Path) -> None:
    if not items:
        path.write_text("")
        return

    fieldnames = list(items[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)


def _export_json(items: list[dict], path: Path) -> None:
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
