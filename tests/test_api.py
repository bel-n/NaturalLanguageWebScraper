import pytest
import requests
from fastapi.testclient import TestClient

from src import service
from src.api import app

client = TestClient(app)

HTML = """<html><body><ul>
<li class="item"><h2>Flood hits town</h2><a href="/a">more</a></li>
<li class="item"><h2>Fire downtown</h2><a href="/b">more</a></li>
<li class="item"><h2>Storm warning</h2><a href="/c">more</a></li>
</ul></body></html>"""


@pytest.fixture(autouse=True)
def fake_download(monkeypatch):
    service._page_cache.clear()
    monkeypatch.setattr(service, "fetch_page", lambda url: HTML)


def _preview():
    response = client.post("/api/preview", json={"url": "http://test/", "intent": {}})
    assert response.status_code == 200
    return response.json()


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}

def test_preview_returns_candidates():
    data = _preview()
    assert data["candidates"]
    assert data["page_url"] == "http://test/"

def test_preview_rejects_a_non_http_address():
    response = client.post("/api/preview", json={"url": "ftp://test/", "intent": {}})
    assert response.status_code == 400

def test_preview_needs_a_description_or_an_intent():
    assert client.post("/api/preview", json={"url": "http://test/"}).status_code == 400

def test_unknown_output_format_is_rejected():
    response = client.post("/api/preview", json={"url": "http://test/", "intent": {"output_format": "xml"}})
    assert response.status_code == 422

def test_download_failure_becomes_502(monkeypatch):
    def boom(url):
        raise requests.ConnectionError("no route")
    monkeypatch.setattr(service, "fetch_page", boom)
    response = client.post("/api/preview", json={"url": "http://test/", "intent": {}})
    assert response.status_code == 502
    assert "no route" not in response.text   # the real reason must not leak

def test_extract_returns_items():
    data = _preview()
    response = client.post("/api/extract", json={
        "page_url": data["page_url"],
        "intent": data["intent"],
        "candidate_index": data["candidates"][0]["index"],
    })
    assert response.status_code == 200
    assert response.json()["count"] == 3

def test_extract_with_a_bad_index_is_400():
    data = _preview()
    response = client.post("/api/extract", json={
        "page_url": data["page_url"], "intent": data["intent"], "candidate_index": 99,
    })
    assert response.status_code == 400

def test_refine_adds_a_keyword():
    response = client.post("/api/refine", json={"intent": {}, "feedback": "only about fire"})
    assert response.status_code == 200

def test_export_csv_download():
    response = client.post("/api/export", json={"items": [{"title": "a"}, {"title": "b"}], "format": "csv"})
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.splitlines() == ["title", "a", "b"]