from __future__ import annotations

from dataclasses import dataclass

from checker.allowed_sites import ALLOWED_SITES


@dataclass(frozen=True)
class MonitoredPage:
    url: str
    category: str
    expected_frequency: str


_RAW_PAGES: dict[str, list[str]] = {
    "news": [
        "https://www.bbc.com", "https://www.cnn.com", "https://www.nytimes.com",
        "https://www.theguardian.com", "https://www.reuters.com", "https://apnews.com",
        "https://www.aljazeera.com", "https://www.washingtonpost.com", "https://www.usatoday.com",
        "https://www.nbcnews.com", "https://www.foxnews.com", "https://www.bloomberg.com",
        "https://www.euronews.com", "https://www.politico.com", "https://www.forbes.com",
        "https://www.ft.com", "https://www.cbc.ca/news", "https://www.dw.com",
        "https://www.lemonde.fr", "https://www.elpais.com", "https://www.ansa.it",
        "https://www.rte.ie/news", "https://www.smh.com.au", "https://www.japantimes.co.jp",
        "https://www.straitstimes.com", "https://www.hindustantimes.com", "https://www.ndtv.com",
        "https://www.timesofisrael.com", "https://abcnews.go.com", "https://news.sky.com",
    ],
    "tech_company": [
        "https://www.google.com", "https://www.apple.com", "https://www.microsoft.com",
        "https://www.amazon.com", "https://www.meta.com", "https://www.netflix.com",
        "https://www.spotify.com", "https://www.openai.com", "https://www.github.com",
        "https://www.gitlab.com", "https://www.ibm.com", "https://www.oracle.com",
        "https://www.adobe.com", "https://www.nvidia.com", "https://www.intel.com",
        "https://www.tesla.com", "https://www.salesforce.com", "https://www.paypal.com",
        "https://www.shopify.com", "https://www.airbnb.com", "https://www.uber.com",
        "https://www.linkedin.com", "https://www.dropbox.com", "https://www.cloudflare.com",
        "https://www.digitalocean.com",
    ],
    "docs_developer": [
        "https://docs.python.org", "https://docs.oracle.com/javase", "https://kubernetes.io/docs",
        "https://developer.mozilla.org", "https://docs.docker.com", "https://react.dev",
        "https://angular.io", "https://vuejs.org", "https://pytorch.org/docs",
        "https://www.tensorflow.org", "https://numpy.org/doc", "https://pandas.pydata.org/docs",
        "https://scikit-learn.org", "https://www.r-project.org", "https://go.dev/doc",
        "https://www.rust-lang.org", "https://docs.aws.amazon.com", "https://cloud.google.com/docs",
        "https://learn.microsoft.com", "https://www.php.net/docs.php",
    ],
    "educational_reference": [
        "https://www.wikipedia.org", "https://www.britannica.com", "https://www.khanacademy.org",
        "https://www.coursera.org", "https://www.edx.org", "https://www.udemy.com",
        "https://ocw.mit.edu", "https://plato.stanford.edu", "https://www.nationalgeographic.com",
        "https://www.worldhistory.org", "https://www.sciencedaily.com", "https://www.howstuffworks.com",
        "https://www.investopedia.com", "https://www.mathsisfun.com", "https://www.stackoverflow.com",
        "https://www.famnit.upr.si/sl/", "https://www.upr.si/",
    ],
    "government": [
        "https://www.whitehouse.gov", "https://www.europa.eu", "https://www.un.org",
        "https://www.who.int", "https://www.nasa.gov", "https://www.cdc.gov",
        "https://www.nih.gov", "https://www.data.gov", "https://www.gov.uk",
        "https://www.bundesregierung.de", "https://www.canada.ca", "https://www.australia.gov.au",
        "https://www.japan.go.jp", "https://www.oecd.org", "https://www.imf.org",
    ],
}

_FREQUENCY_BY_CATEGORY = {
    "news": "high",
    "tech_company": "medium",
    "docs_developer": "low_medium",
    "educational_reference": "low",
    "government": "very_low",
}

MONITORED_PAGES: list[MonitoredPage] = [
    MonitoredPage(url=url, category=category, expected_frequency=_FREQUENCY_BY_CATEGORY[category])
    for category, urls in _RAW_PAGES.items()
    for url in urls
]


def allowed_monitored_pages() -> list[MonitoredPage]:
    """
    MONITORED_PAGES filtered to hosts checker/checker_robots.py already
    marked ALLOWED (see checker/allowed_sites.py). Scraping should only
    ever run against this filtered list — some Appendix A hosts (e.g.
    cnn.com, netflix.com) are excluded on purpose because their
    robots.txt disallows generic bots.
    """
    allowed_urls = {url for urls in ALLOWED_SITES.values() for url in urls}
    return [page for page in MONITORED_PAGES if page.url in allowed_urls]