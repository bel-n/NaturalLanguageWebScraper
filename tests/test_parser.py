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

    assert root.tag == "html"

    body = root.children[0]
    assert body.tag == "body"

    article = body.children[0]
    assert article.tag == "article"
    assert article.attributes["class"] == ["news"]

    title = article.children[0]

    assert title.tag == "h2"
    assert title.text == "Earthquake hits Italy"

    assert title.parent is article