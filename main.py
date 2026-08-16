from src.analyzer.group_finder import find_candidate_groups, find_group_by_signature, group_signature
from src.analyzer.scorer import filter_items, rank_groups
from src.extractor import extract_by_selectors, extract_fields
from src.exporter import export
from src.fetcher import fetch_page
from src.intent import ScrapeIntent
from src.intent_builder import KNOWN_FIELDS, build_intent_interactively
from src.intent_parser import parse_intent
from src.navigator import find_category_link
from src.paginator import find_next_link
from src.parser import parse_html

MAX_PAGES = 20  # safety cap so a bad "next" match can't crawl forever
PREVIEW_SIZE = 3


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
    intent = _build_intent()
    print(f"\nStarting with: {intent}")

    while True:
        page_html, page_url = _navigate_to_category(html, url, intent)

        root = parse_html(page_html)
        groups = find_candidate_groups(root)
        ranked = rank_groups(groups, intent)

        if not ranked:
            print("No repeating content found on this page.")
            return [], intent.output_format

        confirmed = _preview_and_confirm(ranked, intent)
        if confirmed is not None:
            break

        print("\nNone of the candidates looked right.")
        if input("Adjust your answers and try again? (y/n): ").strip().lower() != "y":
            return [], intent.output_format
        intent = _adjust_intent(intent)

    all_items = filter_items(confirmed, intent)
    all_items = _follow_pagination(page_html, page_url, confirmed, intent, all_items)

    if intent.limit:
        all_items = all_items[: intent.limit]

    results = [extract_fields(item, intent.fields) for item in all_items]
    return results, intent.output_format


def _build_intent() -> ScrapeIntent:
    mode = input(
        "\nHow do you want to describe what you want?\n"
        "  1) type a sentence\n"
        "  2) answer guided questions\n"
        "> [1]: "
    ).strip()

    if mode == "2":
        return build_intent_interactively()

    query = input(
        "\nDescribe what you want "
        "(e.g. 'last 5 news from yesterday mentioning catastrophe, titles only'): "
    ).strip()
    return parse_intent(query)


def _navigate_to_category(html: str, url: str, intent: ScrapeIntent) -> tuple[str, str]:
    if not intent.category:
        return html, url

    target_url = find_category_link(html, url, intent.category)
    if not target_url:
        print(
            f"Couldn't find a '{intent.category}' link on this page — "
            "scraping the page as given instead."
        )
        return html, url

    print(f"Found a '{intent.category}' section — visiting {target_url}")
    return fetch_page(target_url), target_url


def _preview_and_confirm(ranked: list, intent: ScrapeIntent):
    """
    Walks the ranked candidate groups, showing a small preview of each
    and asking the user to confirm, before anything gets exported.
    Returns the confirmed group, or None if the user rejected all of them.
    """

    for i, candidate in enumerate(ranked, start=1):
        preview_items = filter_items(candidate, intent)[:PREVIEW_SIZE]
        if not preview_items:
            continue  # this candidate has nothing matching the filters — skip silently

        print(f"\nCandidate {i}/{len(ranked)} — preview of {min(PREVIEW_SIZE, len(preview_items))} item(s):")
        for item in preview_items:
            print(" ", extract_fields(item, intent.fields))

        if input("Does this look right? (y/n): ").strip().lower() == "y":
            return candidate

    return None


def _follow_pagination(
    start_html: str, start_url: str, confirmed_group: list, intent: ScrapeIntent, all_items: list,
) -> list:
    if intent.limit is not None and len(all_items) >= intent.limit:
        return all_items

    signature = group_signature(confirmed_group)
    current_html, current_url = start_html, start_url

    for _ in range(2, MAX_PAGES + 1):
        next_url = find_next_link(current_html, current_url)
        if not next_url:
            break

        print(f"{len(all_items)} matching so far — fetching next page...")
        current_html = fetch_page(next_url)
        current_url = next_url

        root = parse_html(current_html)
        groups = find_candidate_groups(root)
        # Prefer the exact same list the user confirmed; only re-guess if
        # this page's markup genuinely doesn't have that shape anymore.
        match = find_group_by_signature(groups, signature)
        if match:
            all_items.extend(filter_items(match, intent))

        if intent.limit is not None and len(all_items) >= intent.limit:
            break

    return all_items


def _adjust_intent(intent: ScrapeIntent) -> ScrapeIntent:
    options = {
        "1": "keywords", "2": "category", "3": "location", "4": "date filter",
        "5": "limit", "6": "fields", "7": "output format", "8": "content type",
    }
    print("What would you like to change?")
    for key, label in options.items():
        print(f"  {key}) {label}")
    choice = input("> ").strip()

    if choice == "1":
        raw = input("New keywords (comma-separated, blank for none): ").strip()
        intent.keywords = [k.strip().lower() for k in raw.split(",") if k.strip()]
    elif choice == "2":
        raw = input("New category (blank to clear): ").strip()
        intent.category = raw.lower() or None
    elif choice == "3":
        raw = input("New location (blank to clear): ").strip()
        intent.location = raw or None
    elif choice == "4":
        from datetime import date, timedelta
        raw = input("Date filter — 1) none 2) today 3) yesterday: ").strip()
        intent.date_filter = {"2": date.today(), "3": date.today() - timedelta(days=1)}.get(raw)
    elif choice == "5":
        raw = input("New limit (blank for none): ").strip()
        intent.limit = int(raw) if raw.isdigit() else None
    elif choice == "6":
        raw = input(f"New fields ({', '.join(KNOWN_FIELDS)}; blank for all): ").strip()
        intent.fields = [f.strip().lower() for f in raw.split(",") if f.strip() in KNOWN_FIELDS]
    elif choice == "7":
        raw = input("Output format (csv/json): ").strip().lower()
        if raw in ("csv", "json"):
            intent.output_format = raw
    elif choice == "8":
        raw = input("Content type (news/listing/generic): ").strip().lower()
        if raw in ("news", "listing", "generic"):
            intent.target_type = raw
    else:
        print("  Not recognized — nothing changed.")

    return intent


if __name__ == "__main__":
    main()
