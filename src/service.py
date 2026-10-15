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


MAX_PAGES = 20  #so a bad next guess wont crawl forever
PREVIEW_SIZE = 3
CACHE_SECONDS = 300
CACHE_MAX_PAGES = 50 


#part1 what will the service hand back to the web page or cli

@dataclass
class CandidatePreview:
    index: int # position in the ranked list and then needed for run_extractor
    items: list[dict] # as fields the first pulled items

@dataclass
class PreviewResult:
    intent: ScrapeIntent
    page_url: str
    dom_matches: dict[str, list[PreviewMatch]] # what we have found
    candidates: list[CandidatePreview]
    notes: list[str] = field(default_factory=list) # messages that used to be print()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["intent"] = self.intent.to_dict()  
        return data


    #part2: page cache to bridge the gap between the review and the extraction
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


#we have to dwnld the page and remember it for later
def load_page(url:str) -> str:
    return _fetch_cached(url)


    #now we have to understand the intent and show a preview
def build_intent(description: str) -> ScrapeIntent:
    return parse_intent(description)

def _get_page(url: str, intent: ScrapeIntent, notes: list[str]) -> tuple[str, str]:
 
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


def prepare_review(url: str, intent: ScrapeIntent) -> PreviewResult:
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
            continue  # nothing in this list matches the request, so skip it
        candidates.append(
            CandidatePreview(index, [extract_fields(item, intent.fields) for item in sample])
        )

    if not candidates:
        notes.append("No list of items on this page matched the request.")

    return PreviewResult(intent, page_url, dom_matches, candidates, notes)


#case for when the user says that the results are not what they want

def refine_intent(intent: ScrapeIntent, feedback: str) -> ScrapeIntent:
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


#after the user will confirm a candidate we have to do the full scrape

def run_extraction(page_url: str, intent: ScrapeIntent, candidate_index: int) -> list[dict]:

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


#just w/o print

def _follow_pagination(
    start_html: str,
    start_url: str,
    confirmed_group: list,
    intent: ScrapeIntent,
    all_items: list,
    max_pages: int = MAX_PAGES,
) -> list:
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
        # Prefer the exact same list the user confirmed; skip the page if
        # its markup doesn't have that shape any more.
        match = find_group_by_signature(groups, signature)
        if match:
            all_items.extend(filter_items(match, intent))

        if intent.limit is not None and len(all_items) >= intent.limit:
            break

    return all_items


#when the user knows the css selector
def extract_with_selectors(url: str, selector_map: dict[str, str]) -> list[dict]:
    return extract_by_selectors(_fetch_cached(url), selector_map)


