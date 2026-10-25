import logging 
from datetime import date
from typing import Annotated, Literal
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from src import service
from src.exporter import render
from src.intent import ScrapeIntent

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


try:
    from playwright.sync_api import Error as PlaywrightError
    DOWNLOAD_ERRORS = (requests.RequestException, PlaywrightError)
except ImportError: #working on plai mode
    DOWNLOAD_ERRORS = (requests.RequestException,)


logger = logging.getLogger(__name__)
app = FastAPI(title="Natural Language Web Scraper")

@app.get("/")
def serve_index():
    return FileResponse("index.html")

ShortText = Annotated[str, Field(max_length=100)]

#every data type that doesnt fit will be rejected automatically with 422

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
    description: str  | None = Field(default=None, max_length=500)
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
    format: Literal["csv", "json"] ="json"


#helperss

def _to_intent(model: IntentModel) -> ScrapeIntent:
    return ScrapeIntent.from_dict(model.model_dump(mode="json"))


def _check_url(url: str) -> str:
 #blocking private and local addresses is the next step (safety), and this function is where it goes.

    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(400, "Please enter a full web address starting with http:// or https://")
    return url


def _download_failed(url: str, error: Exception) -> HTTPException:
    # The real reason goes to the log, not to the user. Error messages can
    # reveal things about the server's network that a stranger shouldn't see.
    logger.warning("download failed for %s: %s", url, error)
    return HTTPException(502, "Couldn't download that page. Check the address and try again.")



#endpoints - not async because the scraping code is blocking so fastapi will run each call in its worker thread

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
    refined = service.refine_intent(_to_intent(req.intent), req.feedback)
    return refined.to_dict()



#once the user confirms a candiadte we run the scrape
@app.post("/api/extract")
def extract(req: ExtractRequest):
    page_url = _check_url(req.page_url)   # it comes from the browser, so check it too
    intent = _to_intent(req.intent)

    try:
        results = service.run_extraction(page_url, intent, req.candidate_index)
    except DOWNLOAD_ERRORS as error:      # must come before ValueError (see note below)
        raise _download_failed(page_url, error) from None
    except ValueError as error:           # e.g. "No candidate list with index 7."
        raise HTTPException(400, str(error)) from None

    return {"count": len(results), "results": results}

@app.post("/api/export")
def export_file(req: ExportRequest):
    try:
        content = render(req.items, req.format)
    except ValueError as error:           # e.g. rows with different columns
        raise HTTPException(400, str(error)) from None

    media_type = "text/csv" if req.format == "csv" else "application/json"
    return Response(
        content=content,
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="results.{req.format}"'},
    )





 