from bs4 import BeautifulSoup, NavigableString, Tag

from src.dom_node import DOMNode


def parse_html(html: str) -> DOMNode:
    """
    Parse raw HTML and convert it into our own DOMNode tree.

    The returned root is always a DOMNode. For a normal webpage,
    its first meaningful child will usually be the <html> element.
    """

    soup = BeautifulSoup(html, "html.parser")

    root = DOMNode(tag="document")

    for child in soup.children:
        if isinstance(child, Tag):
            root.add_child(_convert_element(child))

    return root


def _convert_element(element: Tag) -> DOMNode:
    """
    Convert one BeautifulSoup Tag into a DOMNode and recursively
    convert all of its element children.
    """

    node = DOMNode(
        tag=element.name or "unknown",
        text=_get_direct_text(element),
        attributes=dict(element.attrs),
    )

    for child in element.children:
        if isinstance(child, Tag):
            node.add_child(_convert_element(child))

    return node


def _get_direct_text(element: Tag) -> str:
    """
    Return only text directly belonging to this element.

    Text inside nested child elements is not included.
    """

    parts: list[str] = []

    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()

            if text:
                parts.append(text)

    return " ".join(parts)