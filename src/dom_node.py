class DOMNode:

    def __init__(
            self,
            tag: str,
            text: str = "",
            attributes: dict | None = None
    ):
        self.tag = tag
        self.text = text
        self.attributes = attributes or {}
        self.children: list["DOMNode"] = []
        self.parent: "DOMNode | None" = None