from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field, replace

from src.analyzer.group_finder import find_candidate_groups
from src.analyzer.scorer import filter_items, rank_groups
from src.dom_preview import PreviewMatch, find_matches_by_content_type
from src.extractor import extract_by_selectors, extract_fields
from src.fetcher import fetch_page
from src.intent import ScrapeIntent
from src.intent_parser import parse_intent
from src.navigator import find_category_link
from src.paginator import find_next_link
from src.parser import parse_html


MAX_PAGES = 20
PREVIEW_SIZE = 3
CACHE_SECONDS = 300
CACHE_MAX_PAGES = 50 


# ---------------------------------------------------------------------------
# Result shapes: what the service hands back to the CLI or the web page
# ---------------------------------------------------------------------------

@dataclass
class CandidatePreview:
    index: int
    items: list[dict]

@dataclass
class PreviewResult:
    intent: ScrapeIntent
    page_url: str
    dom_matches: dict[str, list[PreviewMatch]]
    candidates: list[CandidatePreview]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["intent"] = self.intent.to_dict()  
        return data


# ---------------------------------------------------------------------------
# Page cache: a page we just downloaded is reused for a few minutes
# ---------------------------------------------------------------------------

_page_cache: dict[str, tuple[float, str]] = {}


def _fetch_cached(url: str) -> str:
    now = time.time()
    hit = _page_cache.get(url)
    if hit is not None and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    
    html = fetch_page(url)

    if len(_page_cache) >= CACHE_MAX_PAGES:
        oldest = min(_page_cache, key=lambda u: _page_cache[u][0])
        del _page_cache[oldest]
    _page_cache[url] = (now, html)
    return html


def load_page(url: str) -> str:
    """Download a page and remember it. The CLI calls this right after the URL
    is typed, so a bad URL fails early, and the later steps reuse the cached copy."""
    return _fetch_cached(url)


# ---------------------------------------------------------------------------
# Step 1: understand the request and show a preview
# ---------------------------------------------------------------------------

def build_intent(description: str) -> ScrapeIntent:
    """Turn the user's plain sentence into a ScrapeIntent."""
    return parse_intent(description)


def _get_page(url: str, intent: ScrapeIntent, notes: list[str]) -> tuple[str, str]:
    """
    Download the page. If the user asked for a category (like 'humor'),
    follow the link to that section. Returns (html, url_we_ended_up_on).
    """
    html = _fetch_cached(url)
    if not intent.category:
        return html, url

    target_url = find_category_link(html, url, intent.category)
    if not target_url:
        notes.append(
            f"Couldn't find a '{intent.category}' link on this page, "
            "so the page was scraped as given."
        )
        return html, url

    notes.append(f"Found a '{intent.category}' section and visited {target_url}")
    return _fetch_cached(target_url), target_url


def prepare_preview(url: str, intent: ScrapeIntent) -> PreviewResult:
    """
    Everything that happens before the user says "yes, that's right":
    download, parse, show what's on the page, and guess which list they mean.
    """
    notes: list[str] = []
    page_html, page_url = _get_page(url, intent, notes)
    root = parse_html(page_html)

    # The "we found 5 headings and 4 links" part
    dom_matches = find_matches_by_content_type(root, intent)

    # The "which repeating list do you mean?" part, best guess first
    ranked = rank_groups(find_candidate_groups(root), intent)

    candidates = []
    for index, group in enumerate(ranked):
        sample = filter_items(group, intent)[:PREVIEW_SIZE]
        if not sample:
            continue
        candidates.append(
            CandidatePreview(index, [extract_fields(item, intent.fields) for item in sample])
        )

    if not candidates:
        notes.append("No list of items on this page matched the request.")

    return PreviewResult(intent, page_url, dom_matches, candidates, notes)


# ---------------------------------------------------------------------------
# Step 2: the user said "that's wrong", so update the intent
# ---------------------------------------------------------------------------

def refine_intent(intent: ScrapeIntent, feedback: str) -> ScrapeIntent:
    """
    Merge what the user said into the existing intent.
    Returns a new intent and leaves the old one untouched.
    """
    feedback = feedback.strip()
    if not feedback:
        return intent

    parsed = parse_intent(feedback)
    merged = replace(intent, keywords=list(intent.keywords), fields=list(intent.fields))

    for kw in parsed.keywords:
        if kw not in merged.keywords:
            merged.keywords.append(kw)
    for f in parsed.fields:
        if f not in merged.fields:
            merged.fields.append(f)
    if parsed.category:
        merged.category = parsed.category
    if parsed.location:
        merged.location = parsed.location
    if parsed.date_filter:
        merged.date_filter = parsed.date_filter
    if parsed.limit is not None:
        merged.limit = parsed.limit
    if parsed.target_type != "generic":
        merged.target_type = parsed.target_type
    if "csv" in feedback.lower() or "json" in feedback.lower():
        merged.output_format = parsed.output_format

    return merged


# ---------------------------------------------------------------------------
# Step 3: the user confirmed a candidate, so run the full scrape
# ---------------------------------------------------------------------------

def run_extraction(page_url: str, intent: ScrapeIntent, candidate_index: int) -> list[dict]:
    """
    page_url        : PreviewResult.page_url (the category was already followed)
    intent          : must be the SAME intent the preview used
    candidate_index : CandidatePreview.index of the list the user confirmed
    """
    page_html = _fetch_cached(page_url)
    root = parse_html(page_html)
    ranked = rank_groups(find_candidate_groups(root), intent)

    if not 0 <= candidate_index < len(ranked):
        raise ValueError(f"No candidate list with index {candidate_index}.")
    confirmed = ranked[candidate_index]

    items = filter_items(confirmed, intent)
    items = _follow_pagination(page_html, page_url, confirmed, intent, items)

    # The limit ("last 5") is applied once, across all pages together.
    if intent.limit:
        items = items[: intent.limit]

    return [extract_fields(item, intent.fields) for item in items]


def _follow_pagination(
    start_html: str,
    start_url: str,
    confirmed_group: list,
    intent: ScrapeIntent,
    all_items: list,
    max_pages: int = MAX_PAGES,
) -> list:
    """Follow pagination links and collect more items."""
    from src.analyzer.group_finder import find_group_by_signature, group_signature

    if intent.limit is not None and len(all_items) >= intent.limit:
        return all_items

    signature = group_signature(confirmed_group)
    current_html, current_url = start_html, start_url

    for _ in range(2, max_pages + 1):
        next_url = find_next_link(current_html, current_url)
        if not next_url:
            break

        current_html = _fetch_cached(next_url)
        current_url = next_url

        groups = find_candidate_groups(parse_html(current_html))
        match = find_group_by_signature(groups, signature)
        if match:
            all_items.extend(filter_items(match, intent))

        if intent.limit is not None and len(all_items) >= intent.limit:
            break

    return all_items




def extract_with_selectors(url: str, selector_map: dict[str, str]) -> list[dict]:
    """Skips all the guessing. The user names the selectors themselves."""
    return extract_by_selectors(_fetch_cached(url), selector_map)