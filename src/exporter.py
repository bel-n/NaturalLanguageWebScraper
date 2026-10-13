from __future__ import annotations

import csv
import io
import json
from pathlib import Path


def render(items: list[dict], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(items, indent=2, ensure_ascii=False)
    if fmt == "csv":
        if not items:
            return ""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(items[0].keys()))
        writer.writeheader()
        writer.writerows(items)
        return buffer.getvalue()
    raise ValueError(f"Unknown export format: {fmt!r}")

def export(items: list[dict], fmt: str, path: str | Path) -> Path:
    path = Path(path)

    path.write_text(render(items, fmt), encoding="utf-8", newlines="")
    return path



