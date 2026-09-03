"""
Robots.txt checker for the Web Content Stability Analysis project.
Checks each site's robots.txt for:
  1. Whether generic bots (User-agent: *) are technically allowed to crawl
  2. Warning keywords in comments that may indicate an explicit anti-scraping /
     anti-AI-training policy even when the technical rules look permissive
     (see the Seattle Times example we found — this catches that case)

Run locally: `python check_robots.py`
Requires only the standard library.
"""

import urllib.robotparser as urobot
import urllib.request
import time

SITES = {
    "News (high change)": [
        "https://www.bbc.com",
        "https://www.cnn.com",
        "https://www.nytimes.com",
        "https://www.theguardian.com",
        "https://www.reuters.com",
        "https://apnews.com",
        "https://www.aljazeera.com",
        "https://www.washingtonpost.com",
        "https://www.usatoday.com",
        "https://www.nbcnews.com",
        "https://www.foxnews.com",
        "https://www.bloomberg.com",
        "https://www.euronews.com",
        "https://www.politico.com",
        "https://www.forbes.com",
        "https://www.ft.com",
        "https://www.cbc.ca",
        "https://www.dw.com",
        "https://www.lemonde.fr",
        "https://www.elpais.com",
        "https://www.ansa.it",
        "https://www.rte.ie",
        "https://www.smh.com.au",
        "https://www.japantimes.co.jp",
        "https://www.straitstimes.com",
        "https://www.hindustantimes.com",
        "https://www.ndtv.com",
        "https://www.timesofisrael.com",
        "https://abcnews.go.com",
        "https://news.sky.com",
    ],
    "Tech/company (medium change)": [
        "https://www.google.com",
        "https://www.apple.com",
        "https://www.microsoft.com",
        "https://www.amazon.com",
        "https://www.meta.com",
        "https://www.netflix.com",
        "https://www.spotify.com",
        "https://www.openai.com",
        "https://www.github.com",
        "https://www.gitlab.com",
        "https://www.ibm.com",
        "https://www.oracle.com",
        "https://www.adobe.com",
        "https://www.nvidia.com",
        "https://www.intel.com",
        "https://www.tesla.com",
        "https://www.salesforce.com",
        "https://www.paypal.com",
        "https://www.shopify.com",
        "https://www.airbnb.com",
        "https://www.uber.com",
        "https://www.linkedin.com",
        "https://www.dropbox.com",
        "https://www.cloudflare.com",
        "https://www.digitalocean.com",
    ],
    "Docs/developer (low-medium change)": [
        "https://docs.python.org",
        "https://docs.oracle.com",
        "https://kubernetes.io",
        "https://developer.mozilla.org",
        "https://docs.docker.com",
        "https://react.dev",
        "https://angular.io",
        "https://vuejs.org",
        "https://pytorch.org",
        "https://www.tensorflow.org",
        "https://numpy.org",
        "https://pandas.pydata.org",
        "https://scikit-learn.org",
        "https://www.r-project.org",
        "https://go.dev",
        "https://www.rust-lang.org",
        "https://docs.aws.amazon.com",
        "https://cloud.google.com",
        "https://learn.microsoft.com",
        "https://www.php.net",
    ],
    "Educational/reference (low change)": [
        "https://www.wikipedia.org",
        "https://www.britannica.com",
        "https://www.khanacademy.org",
        "https://www.coursera.org",
        "https://www.edx.org",
        "https://www.udemy.com",
        "https://ocw.mit.edu",
        "https://plato.stanford.edu",
        "https://www.nationalgeographic.com",
        "https://www.worldhistory.org",
        "https://www.sciencedaily.com",
        "https://www.howstuffworks.com",
        "https://www.investopedia.com",
        "https://www.mathsisfun.com",
        "https://www.stackoverflow.com",
        "https://www.famnit.upr.si",
        "https://www.upr.si",
    ],
    "Government/institutional (very low change)": [
        "https://www.whitehouse.gov",
        "https://www.europa.eu",
        "https://www.un.org",
        "https://www.who.int",
        "https://www.nasa.gov",
        "https://www.cdc.gov",
        "https://www.nih.gov",
        "https://www.data.gov",
        "https://www.gov.uk",
        "https://www.bundesregierung.de",
        "https://www.canada.ca",
        "https://www.australia.gov.au",
        "https://www.japan.go.jp",
        "https://www.oecd.org",
        "https://www.imf.org",
    ],
}

WARNING_WORDS = [
    "scrape", "scraping", "data min", "machine learning",
    "artificial intelligence", " ai ", "llm", "written permission",
    "prohibited", "training data", "large language model",
]


def check_site(url: str) -> str:
    robots_url = url.rstrip("/") + "/robots.txt"
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": "thesis-research-checker/1.0"})
        raw = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"ERROR fetching robots.txt ({e})"

    rp = urobot.RobotFileParser()
    rp.parse(raw.splitlines())
    allowed = rp.can_fetch("*", url.rstrip("/") + "/")

    flags = [w for w in WARNING_WORDS if w.lower() in raw.lower()]
    status = "ALLOWED" if allowed else "BLOCKED (Disallow: / for User-agent: *)"
    if flags:
        status += f"  |  \u26a0 WARNING: comment mentions {flags} \u2014 read manually before using"
    return status


def main():
    for category, sites in SITES.items():
        print(f"\n=== {category} ===")
        for site in sites:
            result = check_site(site)
            print(f"{site:45s} {result}")
            time.sleep(1)  # be polite between requests


if __name__ == "__main__":
    main()