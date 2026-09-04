"""
Step 1: run the REAL extraction pipeline (fetcher -> parser -> group_finder
-> scorer -> extractor), non-interactively, against every ALLOWED site.

main.py is interactive (input() prompts), which makes it unusable for
testing 90 sites unattended — this reuses the same underlying modules
main.py calls, just wired straight through with a fixed query instead
of asking a human at each step.

Run locally:
    python3 batch_test.py                          # every ALLOWED site
    python3 batch_test.py --category news           # one category
    python3 batch_test.py --limit 5                 # first 5 per category
    python3 batch_test.py --query "prices and titles"

Writes batch_test_results.csv with one row per site: whether the fetch
succeeded, how many candidate repeating groups were found, the top
group's score, how many items survived intent filtering, and a sample
extracted item so you can eyeball extraction quality without opening
every site by hand.
"""

from __future__ import annotations

import argparse
import csv
import time
import traceback

from src.fetcher import fetch_page
from src.parser import parse_html
from src.analyzer.group_finder import find_candidate_groups
from src.analyzer.scorer import rank_groups, filter_items, score_group
from src.intent_parser import parse_intent
from src.extractor import extract_fields

from checker.allowed_sites import ALLOWED_SITES

DEFAULT_QUERY = "titles and links"
DELAY_BETWEEN_REQUESTS = 1.5  # be polite


def test_site(url: str, query: str) -> dict:
    result = {
        "url": url,
        "fetch_ok": False,
        "error": None,
        "candidate_groups": 0,
        "best_group_score": None,
        "items_in_best_group": 0,
        "items_after_filter": 0,
        "sample_item": None,
    }

    intent = parse_intent(query)

    try:
        html = fetch_page(url)
        result["fetch_ok"] = True
    except Exception as e:
        result["error"] = f"fetch failed: {e}"
        return result

    try:
        root = parse_html(html)
        groups = find_candidate_groups(root)
        result["candidate_groups"] = len(groups)

        ranked = rank_groups(groups, intent)
        if not ranked:
            result["error"] = "no repeating groups found on this page"
            return result

        best = ranked[0]
        result["best_group_score"] = round(score_group(best, intent), 3)
        result["items_in_best_group"] = len(best)

        filtered = filter_items(best, intent)
        result["items_after_filter"] = len(filtered)

        if filtered:
            result["sample_item"] = str(extract_fields(filtered[0], intent.fields))

    except Exception as e:
        result["error"] = f"pipeline error: {e}"
        # keep the traceback out of the CSV row but print it live so you
        # can see what actually broke while the batch is running
        print(traceback.format_exc(limit=3))

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default=None, choices=list(ALLOWED_SITES.keys()))
    parser.add_argument("--limit", type=int, default=None, help="max sites per category")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="fixed NL query to test with")
    parser.add_argument("--out", default="batch_test_results.csv")
    args = parser.parse_args()

    categories = {args.category: ALLOWED_SITES[args.category]} if args.category else ALLOWED_SITES

    rows = []
    for category, urls in categories.items():
        if args.limit:
            urls = urls[: args.limit]
        print(f"\n=== {category} ===")
        for url in urls:
            r = test_site(url, args.query)
            r["category"] = category
            rows.append(r)

            status = "OK" if r["fetch_ok"] else "FETCH FAIL"
            print(
                f"{url:40s} {status:12s} "
                f"groups={r['candidate_groups']:<4} "
                f"best_score={r['best_group_score']} "
                f"items={r['items_after_filter']:<4} "
                f"{'| ' + r['error'] if r['error'] else ''}"
            )
            time.sleep(DELAY_BETWEEN_REQUESTS)

    if rows:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved {len(rows)} results to {args.out}")


if __name__ == "__main__":
    main()