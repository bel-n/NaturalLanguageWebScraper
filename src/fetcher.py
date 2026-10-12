import requests
from bs4 import BeautifulSoup

USER_AGENT = "NaturalLanguageWebScraper/1.0"
MIN_TEXT_LENGTH = 500  # if less visible than this it probs need js


def fetch_page(url: str, mode: str = "auto") -> str:
    """
    mode:
      "plain"  - requests only (fast, light)
      "render" - real browser, runs JavaScript
      "auto"   - try plain first, fall back to the browser if the page looks empty
    """
    if mode == "render":
        return _fetch_rendered(url)

    html = _fetch_plain(url)
    if mode == "auto" and _looks_empty(html):
        return _fetch_rendered(url)
    return html


def _fetch_plain(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()
    return response.text


def _looks_empty(html: str) -> bool:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return len(text) < MIN_TEXT_LENGTH


def _fetch_rendered(url: str) -> str:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, wait_until="load", timeout=20000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except PlaywrightTimeout:
                pass  # some sites never go idle; take what is on screen
            return page.content()
        finally:
            browser.close()