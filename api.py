"""
FastAPI wrapper around the intake agent pipeline.

Exposes the same run_intake() pipeline used by run_demo.py / app.py as a REST API,
so any frontend (this project's static page, or something else entirely) can call it
over HTTP instead of importing Python directly. Also serves the static frontend so the
whole thing runs as one process for the demo.
"""

from pathlib import Path

import markdown
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import run_intake
from test_requests import SAMPLE_REQUESTS

app = FastAPI(title="Enterprise Intake Agent API")

STATIC_DIR = Path(__file__).parent / "static"
PROJECT_DIR = Path(__file__).parent

DOCS = {
    "design": "design_doc.md",
    "reliability": "reliability_findings.md",
    "ai-usage": "ai_usage_notes.md",
}


class IntakeRequest(BaseModel):
    raw_request: str = Field(..., min_length=1, max_length=8000)


@app.get("/api/samples")
def get_samples() -> dict:
    return SAMPLE_REQUESTS


@app.post("/api/intake")
def intake(payload: IntakeRequest) -> dict:
    raw = payload.raw_request.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="raw_request must not be empty")
    try:
        result = run_intake(raw)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent pipeline failed: {e}")
    return result.to_dict()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/docs/{doc_name}")
def get_doc(doc_name: str) -> dict:
    if doc_name not in DOCS:
        raise HTTPException(status_code=404, detail=f"Unknown doc '{doc_name}'")
    path = PROJECT_DIR / DOCS[doc_name]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{DOCS[doc_name]} not found")
    html = markdown.markdown(path.read_text(), extensions=["tables", "fenced_code"])
    return {"html": html}


# Serve the static frontend last so it doesn't shadow the /api/* routes above.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
