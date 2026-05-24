"""Guarantees: no live calls by default, and no secret leakage."""
from __future__ import annotations

import socket

from app.config import settings
from app.review_pipeline import run_review

SENTINEL = "sk-WORKBENCH-CANARY-DO-NOT-EMIT-0xDEADBEEF"


def test_no_network_during_pipeline(sample, monkeypatch):
    # The offline pipeline must not open any socket. We test the pipeline
    # directly (not via TestClient, whose asyncio loop uses socketpair).
    def deny(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("network access attempted during offline review")

    monkeypatch.setattr(socket, "socket", deny)
    monkeypatch.setattr(socket, "create_connection", deny)

    review = run_review(None, sample, settings)
    assert review.verdict == "REVIEW_ASSISTANCE_ONLY"
    assert review.replay.offline_mode is True


def test_live_mode_rejected_by_default(client, sample):
    r = client.post("/api/review", json={"text": sample, "mode": "live"})
    assert r.status_code == 400


def test_api_key_never_leaks(client, sample, monkeypatch):
    monkeypatch.setenv(settings.api_key_env, SENTINEL)

    review = client.post("/api/review", json={"text": sample}).json()
    rid = review["review_id"]
    report = client.get(f"/api/review/{rid}/report.md").text
    config = client.get("/config").text

    assert SENTINEL not in str(review)
    assert SENTINEL not in report
    assert SENTINEL not in config
    # presence is reported as a flag, never the value
    assert client.get("/config").json()["api_key_present"] is True
