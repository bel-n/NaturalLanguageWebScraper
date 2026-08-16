from __future__ import annotations

from datetime import date, timedelta

from src.intent import ScrapeIntent

KNOWN_FIELDS = ("title", "price", "author", "date", "tags", "link")
_DATE_CHOICES = {"1": None, "2": "today", "3": "yesterday"}


def build_intent_interactively() -> ScrapeIntent:
    """
    Same end result as parse_intent(text) — a ScrapeIntent — but built
    from a fixed sequence of questions instead of guessing at a free
    sentence. Every question can be left blank to skip it.
    """

    intent = ScrapeIntent()

    intent.target_type = _ask_choice(
        "What kind of thing are you scraping?",
        {"1": "news", "2": "listing", "3": "generic"},
        default="generic",
    )

    keywords_raw = input(
        "Only keep items containing these words (comma-separated, blank for none): "
    ).strip()
    if keywords_raw:
        intent.keywords = [k.strip().lower() for k in keywords_raw.split(",") if k.strip()]

    category = input(
        "Genre/category to navigate to first, if any (e.g. 'humor', blank to skip): "
    ).strip()
    if category:
        intent.category = category.lower()

    location = input("Location to look for, if any (blank to skip): ").strip()
    if location:
        intent.location = location

    date_choice = _ask_choice(
        "Filter by date?",
        {"1": "no filter", "2": "today", "3": "yesterday"},
        default="no filter",
    )
    if date_choice == "today":
        intent.date_filter = date.today()
    elif date_choice == "yesterday":
        intent.date_filter = date.today() - timedelta(days=1)

    limit_raw = input("How many items do you want? (blank for as many as exist): ").strip()
    if limit_raw:
        if not limit_raw.isdigit():
            print(f"  '{limit_raw}' isn't a number — ignoring, no limit set.")
        else:
            intent.limit = int(limit_raw)

    fields_raw = input(
        f"Which fields do you want ({', '.join(KNOWN_FIELDS)}; comma-separated, "
        "blank for everything available): "
    ).strip()
    if fields_raw:
        requested = [f.strip().lower() for f in fields_raw.split(",") if f.strip()]
        unknown = [f for f in requested if f not in KNOWN_FIELDS]
        if unknown:
            print(f"  Not recognized, skipping: {', '.join(unknown)}")
        intent.fields = [f for f in requested if f in KNOWN_FIELDS]

    intent.output_format = _ask_choice(
        "Output format?", {"1": "json", "2": "csv"}, default="json",
    )

    return intent


def _ask_choice(prompt: str, options: dict[str, str], default: str) -> str:
    listing = "  " + "\n  ".join(f"{key}) {label}" for key, label in options.items())
    print(prompt)
    print(listing)
    choice = input(f"> [{default}]: ").strip()
    return options.get(choice, default)
