from src.analyzer.group_finder import find_candidate_groups
from src.analyzer.scorer import filter_items, pick_best_group
from src.extractor import extract_by_selectors, extract_fields
from src.exporter import export
from src.fetcher import fetch_page
from src.intent_parser import parse_intent
from src.parser import parse_html


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
        results, fmt = _run_intent_path(html)

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


def _run_intent_path(html: str) -> tuple[list[dict], str]:
    query = input(
        "\nDescribe what you want "
        "(e.g. 'last 5 news from yesterday mentioning catastrophe, titles only'): "
    ).strip()

    intent = parse_intent(query)
    print(f"\nParsed intent: {intent}")

    root = parse_html(html)
    groups = find_candidate_groups(root)
    print(f"Found {len(groups)} candidate repeating group(s) on the page.")

    best_group = pick_best_group(groups, intent)
    if not best_group:
        return [], intent.output_format

    items = filter_items(best_group, intent)
    results = [extract_fields(item, intent.fields) for item in items]
    return results, intent.output_format


if __name__ == "__main__":
    main()
