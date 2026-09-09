from src.monitor.snapshot import take_snapshots

snapshots = take_snapshots(
    "https://example.com",
    "test",
    "low"
)

print("Number of snapshots:", len(snapshots))

for snapshot in snapshots:
    print("\nTYPE:", snapshot.content_type)
    print("ITEMS:", snapshot.items)
    print("HASH:", snapshot.content_hash)