from src.dom_node import DOMNode

def extract_features(node: DOMNode) -> dict:
    classes = node.attributes.get("class",[])
    element_id = node.attributes.get("id")

    return {
        "tag": node.tag,
        "text": node.text,
        "text_length": len(node.text),
         "classes": classes,
         "id": element_id,
         "depth": get_depth(node),
         "number_of_children": len(node.children),
         "number_of_siblings": get_number_of_siblings(node),
    }

def get_depth(node: DOMNode) -> int:
    depth = 0
    current = node.parent

    while current is not None:
        depth += 1
        current = current.parent
    return depth

def get_number_of_siblings(node: DOMNode) -> int:

    if node.parent is None:
        return 0

    return max(0,len(node.parent.children) -1)