from bs4 import BeautifulSoup
from dom_node import DomNode

def parse_html(html: str) -> DomNode:
  soup = BeautifulSoup(html, "html.parser")
  return _convert_elemnt(soup.html)

def _convert_elemnt(element) -> DomNode:
    node = DomNode(
        tag=element.name,
        text=_get_direct_text(element),
        attributes=element.attrs
    )
    
    for child in element.children:

       if not getattr(child, "name", None):
          continue
       child_node = _convert_elemnt(child)
       child_node.parent = node
       node.children.append(child_node)

    return node

def _get_direct_text(element) -> str:
    return "".join(
       text.strip()
       for text in element.findall(
          string=True,
          recursive=False
       )
       if text.strip
    ) 
    
    