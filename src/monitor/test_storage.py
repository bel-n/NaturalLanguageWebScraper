from src.monitor.snapshot import take_snapshots
from src.monitor.storage import append_snapshot, load_snapshots

url = "https://example.com"

snapshots = take_snapshots(url, "test", "low")

for snapshot in snapshots:
    append_snapshot(snapshot)

for content_type in ["headings", "paragraphs", "links"]:
    history = load_snapshots(url, content_type)

    print(content_type, "snapshots:", len(history))