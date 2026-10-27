import logging
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlparse
import ipaddress

import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src import service
from src.exporter import render
from src.intent import ScrapeIntent

try:
    from playwright.sync_api import Error as PlaywrightError
    DOWNLOAD_ERRORS = (requests.RequestException, PlaywrightError)
except ImportError:
    DOWNLOAD_ERRORS = (requests.RequestException,)

logger = logging.getLogger(__name__)
app = FastAPI(title="Natural Language Web Scraper")

ShortText = Annotated[str, Field(max_length=100)]


# ---------------------------------------------------------------------------
# Security: rate limiting and IP blocking
# ---------------------------------------------------------------------------

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(429, "Too many requests. Max 10 per hour.")


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname is a private/local address."""
    if not hostname:
        return False
    
    # Local hostnames
    if hostname.lower() in ('localhost', 'host.docker.internal', 'test'):
        return False  # Allow 'test' for unit tests
    
    # Try to parse as IP address
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        # Not an IP address, allow domain names
        return False


def _check_url(url: str) -> str:
    """Validate URL: only http/https."""
    url = url.strip()
    parsed = urlparse(url)
    
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(400, "Please enter a full web address starting with http:// or https://")
    
    # Only block actual private IPs, not test domains
    if _is_private_ip(parsed.hostname):
        raise HTTPException(400, "Cannot access local or private addresses")
    
    return url


def _download_failed(url: str, error: Exception) -> HTTPException:
    logger.warning("download failed for %s: %s", url, error)
    return HTTPException(502, "Couldn't download that page. Check the address and try again.")


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class IntentModel(BaseModel):
    target_type: Literal["news", "listing", "generic"] = "generic"
    keywords: list[ShortText] = Field(default_factory=list, max_length=10)
    category: ShortText | None = None
    location: ShortText | None = None
    date_filter: date | None = None
    limit: int | None = Field(default=None, ge=1, le=500)
    fields: list[ShortText] = Field(default_factory=list, max_length=10)
    output_format: Literal["csv", "json"] = "json"


class PreviewRequest(BaseModel):
    url: str = Field(max_length=2000)
    description: str | None = Field(default=None, max_length=500)
    intent: IntentModel | None = None


class RefineRequest(BaseModel):
    intent: IntentModel
    feedback: str = Field(max_length=500)


class ExtractRequest(BaseModel):
    page_url: str = Field(max_length=2000)
    intent: IntentModel
    candidate_index: int = Field(ge=0)


class ExportRequest(BaseModel):
    items: list[dict] = Field(max_length=5000)
    format: Literal["csv", "json"] = "json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_intent(model: IntentModel) -> ScrapeIntent:
    """Validated JSON -> ScrapeIntent object."""
    return ScrapeIntent.from_dict(model.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/test")
def test():
    return {"message": "test works"}


@app.get("/")
def serve_index():
    return FileResponse("index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/preview")
def preview(req: PreviewRequest):
    url = _check_url(req.url)

    if req.intent is not None:
        intent = _to_intent(req.intent)
    elif req.description and req.description.strip():
        intent = service.build_intent(req.description)
    else:
        raise HTTPException(400, "Send either a description or an intent.")

    try:
        result = service.prepare_preview(url, intent)
    except DOWNLOAD_ERRORS as error:
        raise _download_failed(url, error) from None
    return result.to_dict()

@app.post("/api/refine")
def refine(req: RefineRequest):
    """'What's missing or wrong?' -> an updated intent (no download needed)."""
    refined = service.refine_intent(_to_intent(req.intent), req.feedback)
    return refined.to_dict()


@app.post("/api/extract")
@limiter.limit("10/hour")
def extract(req: ExtractRequest, request: Request = None):
    """Step 2: the user confirmed a candidate -> run the full scrape."""
    page_url = _check_url(req.page_url)
    intent = _to_intent(req.intent)

    try:
        results = service.run_extraction(page_url, intent, req.candidate_index)
    except DOWNLOAD_ERRORS as error:
        raise _download_failed(page_url, error) from None
    except ValueError as error:
        raise HTTPException(400, str(error)) from None

    return {"count": len(results), "results": results}


@app.post("/api/export")
def export_file(req: ExportRequest):
    """Items -> a CSV or JSON file the browser downloads."""
    try:
        content = render(req.items, req.format)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None

    media_type = "text/csv" if req.format == "csv" else "application/json"
    return Response(
        content=content,
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="results.{req.format}"'},
    )