from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def find_next_link(html: str, base_url: str) -> str | None:
    """
    Look for a 'next page' link using the common conventions, in order
    of reliability:
      1. <a rel="next"> — the semantically correct way to mark it
      2. <li class="next"><a href="...">  — Bootstrap-style pagers (this
         is what books.toscrape.com and a lot of sites built on similar
         templates use)
      3. any <a> whose visible text is literally "next" / "next page" / »
    """

    soup = BeautifulSoup(html, "html.parser")

    candidate = soup.select_one('a[rel="next"]')
    if candidate is None:
        candidate = soup.select_one("li.next a, .pagination .next a")
    if candidate is None:
        for a in soup.find_all("a"):
            text = a.get_text(strip=True).lower()
            if text in ("next", "next page", "»", "next »"):
                candidate = a
                break

    if candidate is not None and candidate.get("href"):
        return urljoin(base_url, candidate["href"])
    return None
