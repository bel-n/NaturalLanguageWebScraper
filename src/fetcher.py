import requests

def fetch_page(url: str)-> str:
    response = requests.get(
        url,
        headers={
            "User-Agent": "NaturalLanguageWebScraper/1.0 "
        },
        timeout=10
    )

    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.text