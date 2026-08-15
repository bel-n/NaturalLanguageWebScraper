from src.analyzer.group_finder import find_candidate_groups
from src.analyzer.scorer import filter_items, pick_best_group
from src.extractor import extract_by_selectors, extract_fields
from src.exporter import export
from src.fetcher import fetch_page
from src.intent_parser import parse_intent
from src.navigator import find_category_link
from src.paginator import find_next_link
from src.parser import parse_html

MAX_PAGES = 20  # safety cap so a bad "next" match can't crawl forever


def main() -> None:
    url = input("Enter URL: ").strip()
    if not url:
        print("URL cannot be empty.")
        return

    print("\nFetching webpage...")
    html = fetch_page(url)

    knows_selectors = input(
        "\nDo you know the CSS selectors for what you need? (y/n): "
    ).strip().lower()

    if knows_selectors == "y":
        results, fmt = _run_selector_path(html)
    else:
        results, fmt = _run_intent_path(html, url)

    if not results:
        print("\nNo matching items found.")
        return

    out_path = export(results, fmt, f"output.{fmt}")
    print(f"\nExtracted {len(results)} item(s) -> {out_path}")


def _run_selector_path(html: str) -> tuple[list[dict], str]:
    print(
        "\nEnter field:selector pairs, one per line "
        "(e.g. 'title:.article h2'). Blank line to finish."
    )
    selector_map: dict[str, str] = {}
    while True:
        line = input("> ").strip()
        if not line:
            break
        if ":" not in line:
            print("  format is field:selector — try again.")
            continue
        field, _, selector = line.partition(":")
        selector_map[field.strip()] = selector.strip()

    fmt = input("Output format (csv/json) [json]: ").strip().lower() or "json"
    results = extract_by_selectors(html, selector_map)
    return results, fmt


def _run_intent_path(html: str, url: str) -> tuple[list[dict], str]:
    query = input(
        "\nDescribe what you want "
        "(e.g. 'last 5 news from yesterday mentioning catastrophe, titles only'): "
    ).strip()

    intent = parse_intent(query)
    print(f"\nParsed intent: {intent}")

    if intent.category:
        target_url = find_category_link(html, url, intent.category)
        if target_url:
            print(f"Found a '{intent.category}' section — visiting {target_url}")
            url = target_url
            html = fetch_page(url)
        else:
            print(
                f"Couldn't find a '{intent.category}' link on this page — "
                "scraping the page as given instead."
            )

    all_items = []
    current_html, current_url = html, url

    for page_num in range(1, MAX_PAGES + 1):
        root = parse_html(current_html)
        groups = find_candidate_groups(root)
        best_group = pick_best_group(groups, intent)

        if best_group:
            all_items.extend(filter_items(best_group, intent))

        have_enough = intent.limit is not None and len(all_items) >= intent.limit
        if have_enough:
            break

        next_url = find_next_link(current_html, current_url)
        if not next_url:
            break

        print(f"Page {page_num} done ({len(all_items)} matching so far) — "
              f"fetching next page...")
        current_html = fetch_page(next_url)
        current_url = next_url

    if intent.limit:
        all_items = all_items[: intent.limit]

    results = [extract_fields(item, intent.fields) for item in all_items]
    return results, intent.output_format


if __name__ == "__main__":
    main()
