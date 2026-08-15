from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def find_category_link(html: str, base_url: str, category: str) -> str | None:
    """
    Look for an <a> whose visible text names the requested category
    (e.g. "Humor") and return the absolute URL it points to.

    Tries an exact match first ("Humor" == "humor"), then falls back to
    a whole-word match ("Humor Books" contains "humor" as a word) so we
    don't misfire on partial substrings like "art" inside "Martial Arts".
    """

    soup = BeautifulSoup(html, "html.parser")
    target = category.strip().lower()

    candidates = [
        (a.get_text(strip=True), a.get("href"))
        for a in soup.find_all("a")
        if a.get("href") and a.get_text(strip=True)
    ]

    for text, href in candidates:
        if text.strip().lower() == target:
            return urljoin(base_url, href)

    for text, href in candidates:
        if target in text.lower().split():
            return urljoin(base_url, href)

    return None
