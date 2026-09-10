
import time

from src.monitor.pages import allowed_monitored_pages
from src.monitor.snapshot import take_snapshots
from src.monitor.storage import append_snapshot

POLITE_DELAY_SECONDS = 2


def main() -> None:
    pages = allowed_monitored_pages()
    print(f"Snapshotting {len(pages)} allowed pages...")

    for i, page in enumerate(pages, start=1):
        try:
            snapshots = take_snapshots(page.url, page.category, page.expected_frequency)
        except Exception as exc:
            print(f"[{i}/{len(pages)}] FAILED {page.url}: {exc}")
            continue

        for snapshot in snapshots:
            append_snapshot(snapshot)

        total_items = sum(s.item_count for s in snapshots)
        print(f"[{i}/{len(pages)}] OK {page.url} ({total_items} items / {len(snapshots)} groups)")
        time.sleep(POLITE_DELAY_SECONDS)


if __name__ == "__main__":
    main()