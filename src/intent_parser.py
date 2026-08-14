from __future__ import annotations

import re
from datetime import date, timedelta

from src.intent import ScrapeIntent

# Add to this as you meet new phrasings — every rule is independent,
# so growing coverage never risks breaking an existing one.
_LISTING_HINTS = (
    "cafeteria", "restaurant", "dentist", "shop", "store",
    "hotel", "clinic", "pharmacy", "bar", "cafe",
)
_NEWS_HINTS = ("news", "article", "headline", "post")


def parse_intent(text: str) -> ScrapeIntent:
    intent = ScrapeIntent()
    lower = text.lower()

    _apply_limit(lower, intent)
    _apply_date(lower, intent)
    _apply_keywords(lower, intent)
    _apply_location(text, intent)
    _apply_fields(lower, intent)
    _apply_format(lower, intent)
    _apply_target_type(lower, intent)

    return intent


def _apply_limit(lower: str, intent: ScrapeIntent) -> None:
    if m := re.search(r"\b(?:last|first|top)\s+(\d+)\b", lower):
        intent.limit = int(m.group(1))


def _apply_date(lower: str, intent: ScrapeIntent) -> None:
    if "yesterday" in lower:
        intent.date_filter = date.today() - timedelta(days=1)
    elif "today" in lower:
        intent.date_filter = date.today()
    else:
        # Explicit dates ("March 3rd", "2026-08-10") are handled lazily by
        # dom_utils.date_in_text against dateutil, so we don't duplicate
        # date-parsing logic here — this function only handles relative words.
        pass


def _apply_keywords(lower: str, intent: ScrapeIntent) -> None:
    # "mentioning the word X" / "mentioning X" / "containing X" / "about X"
    pattern = r"(?:mentioning|containing|about)(?: the word)?\s+['\"]?([a-z0-9\-]+)['\"]?"
    for m in re.finditer(pattern, lower):
        keyword = m.group(1)
        if keyword not in intent.keywords:
            intent.keywords.append(keyword)


_LOCATION_STOPWORDS = {"csv", "json", "format", "and", "with"}


def _apply_location(original_text: str, intent: ScrapeIntent) -> None:
    # "in town A" / "in Koper" — take the phrase after a bare "in", up to
    # punctuation or a clause boundary (and/with/csv/json). Deliberately
    # conservative: only fires on " in ", and every match is tried in turn
    # so "...in csv format" doesn't shadow an earlier real "...in town A".
    for m in re.finditer(
        r"\bin\s+([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z0-9]+)?)"
        r"(?=[,.]|\s+and\b|\s+with\b|\s+I\b|\s+we\b|$)",
        original_text,
    ):
        location = m.group(1).strip()
        if location.lower() not in _LOCATION_STOPWORDS:
            intent.location = location
            return


def _apply_fields(lower: str, intent: ScrapeIntent) -> None:
    field_map = {
        "title": ("title", "titles", "headline", "headlines"),
        "price": ("price", "prices", "cost"),
        "address": ("address", "addresses", "location"),
        "link": ("link", "links", "url", "urls"),
        "date": ("date", "dates", "published"),
    }
    for field_name, triggers in field_map.items():
        if any(re.search(rf"\b{t}\b", lower) for t in triggers):
            intent.fields.append(field_name)


def _apply_format(lower: str, intent: ScrapeIntent) -> None:
    if "csv" in lower:
        intent.output_format = "csv"
    elif "json" in lower:
        intent.output_format = "json"


def _apply_target_type(lower: str, intent: ScrapeIntent) -> None:
    if any(hint in lower for hint in _NEWS_HINTS):
        intent.target_type = "news"
    elif any(hint in lower for hint in _LISTING_HINTS):
        intent.target_type = "listing"
