"""DESi Workbench backend - FastAPI app.

Makes the DESi governance library visible via a small HTTP API. It does
not modify or re-implement the DESi core. Offline by default; no live LLM
calls without both gates explicitly opened (and the MVP makes none).
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from . import PIPELINE_VERSION, VERDICT, __version__, desi_adapter, review_pipeline, storage
from .config import settings
from .models import Graph, ReviewRequest, ReviewResponse

app = FastAPI(
    title="DESi Workbench",
    version=__version__,
    description="Epistemic-audit assistant that makes DESi visible. Not a peer reviewer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok" if desi_adapter.governance_intact() else "degraded",
        "verdict": VERDICT,
        "pipeline_version": PIPELINE_VERSION,
        "desi": desi_adapter.governance_health(),
    }


@app.get("/config")
def config() -> dict:
    # public_dict contains NO secret - only the env-var name and a flag.
    out = settings.public_dict()
    out["pipeline_version"] = PIPELINE_VERSION
    out["verdict"] = VERDICT
    return out


@app.post("/api/review", response_model=ReviewResponse)
def create_review(req: ReviewRequest) -> ReviewResponse:
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="'text' must not be empty")
    if req.mode != "offline" and not settings.live_calls_enabled:
        raise HTTPException(
            status_code=400,
            detail="live mode is disabled (offline_mode/allow_live_llm_calls)",
        )
    if not desi_adapter.governance_intact():
        raise HTTPException(
            status_code=503,
            detail="DESi protected-core identity check failed; refusing to emit a review",
        )
    # Opt-in, online: build a real OpenAI-compatible llm_call only when BOTH
    # gates are open and a key is present. Offline default -> None (no network).
    spl_llm_call = None
    if settings.live_calls_enabled:
        api_key = os.environ.get(settings.api_key_env)
        if api_key:
            spl_llm_call = desi_adapter.build_llm_call(
                api_key, settings.llm_base_url, settings.llm_model
            )
    review = review_pipeline.run_review(
        req.title, req.text, settings, spl_llm_call=spl_llm_call
    )
    storage.save_review(review, req.text)
    return review


@app.get("/api/review/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str) -> ReviewResponse:
    review = storage.load_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return review


@app.get("/api/review/{review_id}/report.md", response_class=PlainTextResponse)
def get_report(review_id: str) -> PlainTextResponse:
    report = storage.load_report(review_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return PlainTextResponse(report, media_type="text/markdown; charset=utf-8")


@app.get("/api/review/{review_id}/graph", response_model=Graph)
def get_graph(review_id: str) -> Graph:
    review = storage.load_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return review.graph
