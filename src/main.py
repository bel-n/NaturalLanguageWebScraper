from src.fetcher import fetch_page
from src.parser import parse_html
from src.analyzer.feature_extractor import extract_features


def print_tree(node, level: int = 0) -> None:
    indentation = "  " * level

    text = node.text.replace("\n", " ").strip()

    if len(text) > 60:
        text = text[:60] + "..."

    print(
        f"{indentation}{node.tag}"
        + (f" -> {text}" if text else "")
    )

    for child in node.children:
        print_tree(child, level + 1)


def main() -> None:
    url = input("Enter URL: ").strip()

    if not url:
        print("URL cannot be empty.")
        return

    print("\nFetching webpage...")
    html = fetch_page(url)

    print("Parsing webpage...")
    root = parse_html(html)

    print("\nDOM tree:")
    print_tree(root)

    print("\nRoot features:")
    print(extract_features(root))


if __name__ == "__main__":
    main()