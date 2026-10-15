import requests

from src import service
from src.dom_preview import format_preview
from src.exporter import export
from src.intent import ScrapeIntent
from src.intent_builder import KNOWN_FIELDS, build_intent_interactively


def main() -> None:
    url = input("Enter URL: ").strip()
    if not url:
        print("URL cannot be empty.")
        return

    print("\nFetching webpage...")
    try:
        service.load_page(url)
    except requests.RequestException as error:
        print(f"Couldn't download that page: {error}")
        return

    knows_selectors = input(
        "\nDo you know the CSS selectors for what you need? (y/n): "
    ).strip().lower()

    if knows_selectors == "y":
        results, fmt = _run_selector_path(url)
    else:
        results, fmt = _run_intent_path(url)

    if not results:
        print("\nNo matching items found.")
        return

    out_path = export(results, fmt, f"output.{fmt}")
    print(f"\nExtracted {len(results)} item(s) -> {out_path}")


def _run_selector_path(url: str) -> tuple[list[dict], str]:
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

    try:
        results = service.extract_with_selectors(url, selector_map)
    except ValueError as error:   # the selectors matched different numbers of items
        print(f"\n{error}")
        return [], fmt
    return results, fmt


def _run_intent_path(url: str) -> tuple[list[dict], str]:
    intent = _build_intent()
    print(f"\nStarting with: {intent}")

    while True:
        preview = service.prepare_preview(url, intent)

        for note in preview.notes:
            print(note)

        print()
        print(format_preview(preview.dom_matches))
        print()

        if input("Does this look like what you need? (y/n):").strip().lower() != "y":
            feedback = input(
                "\nWhat's missing or wrong? Describe it in a sentence (blank to give up): "
            ).strip()
            if not feedback:
                return [], intent.output_format
            intent = service.refine_intent(intent, feedback)
            continue  # preview again with the refined intent

        chosen = _choose_candidate(preview)
        if chosen is not None:
            break

        print("\nNone of the candidates looked right.")
        if input("Adjust your answers and try again? (y/n): ").strip().lower() != "y":
            return [], intent.output_format
        intent = _adjust_intent(intent)

    results = service.run_extraction(preview.page_url, intent, chosen.index)
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
    return service.build_intent(query)


def _choose_candidate(preview: service.PreviewResult):
    """Show each candidate list in turn until the user says one looks right."""
    total = len(preview.candidates)
    for position, candidate in enumerate(preview.candidates, start=1):
        print(f"\nCandidate {position}/{total} — preview of {len(candidate.items)} item(s):")
        for item in candidate.items:
            print(" ", item)

        if input("Does this look right? (y/n): ").strip().lower() == "y":
            return candidate

    return None


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