from src.parser import parse_html

def test_parse_simple_html():
    html = """
    <html>
        <body>
            <article class="news">
                <h2>Earthquake hits Italy</h2>
                <p>Something happened yesterday.</p>
            </article>
        </body>
    </html>
    """

    root = parse_html(html)

    assert root.tag == "document"
    html_elem = root.children[0]
    assert html_elem.tag == "html"
    
    # rest of the test, if any, should now start from html_elem instead of root