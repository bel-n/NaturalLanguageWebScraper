from src.fetcher import fetch_page
from src.parser import parse_html
from src.monitor.content_groups import extract_content_groups

url = "https://example.com"

html = fetch_page(url)
root = parse_html(html)

groups = extract_content_groups(root)

print("HEADINGS:")
print(groups["headings"])

print("\nPARAGRAPHS:")
print(groups["paragraphs"])

print("\nLINKS:")
print(groups["links"])