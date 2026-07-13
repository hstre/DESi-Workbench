from __future__ import annotations

import base64

import pytest
from starlette.testclient import TestClient

pytest.importorskip("mcp")

from mcp.server.fastmcp import FastMCP  # noqa: E402

from app.epistemic_review.orchestrator import EpistemicReviewOrchestrator  # noqa: E402
from app.epistemic_review.state import RunStore  # noqa: E402
from app.ui import register_ui  # noqa: E402


PAPER = """# UI fixture

The mechanism holds generically.
At r = 1 the boundary condition changes and the symmetry is enhanced.
"""


def _client(tmp_path):
    mcp = FastMCP(
        "UI test",
        host="127.0.0.1",
        port=8000,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )
    orchestrator = EpistemicReviewOrchestrator(RunStore(tmp_path / "ui.sqlite3"))
    register_ui(
        mcp,
        orchestrator,
        lambda: {
            "protocol_version": "epistemic-review-v1",
            "roles": ["theorist"],
            "engines": {},
            "scope_verdict": "REVIEW_ASSISTANCE_ONLY",
        },
    )
    return TestClient(mcp.streamable_http_app())


def test_cockpit_assets_are_served(tmp_path):
    with _client(tmp_path) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Epistemic Review Cockpit" in page.text
        assert "/ui/app.js" in page.text

        script = client.get("/ui/app.js")
        assert script.status_code == 200
        assert "startReview" in script.text

        styles = client.get("/ui/styles.css")
        assert styles.status_code == 200
        assert ".stage-list" in styles.text


def test_cockpit_starts_text_run_and_opens_first_role(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/ui/api/start",
            json={"title": "UI fixture", "text": PAPER, "focus": "boundary"},
        )
        assert response.status_code == 200
        run = response.json()
        assert run["run_id"].startswith("ER_")
        assert len(run["stages"]) == 7

        summary = client.get(f"/ui/api/run/{run['run_id']}")
        assert summary.status_code == 200
        assert summary.json()["title"] == "UI fixture"

        next_stage = client.post(f"/ui/api/run/{run['run_id']}/next", json={})
        assert next_stage.status_code == 200
        assert next_stage.json()["role"] == "theorist"
        assert "output_schema" in next_stage.json()["packet"]


def test_cockpit_accepts_base64_text_file(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/ui/api/start",
            json={
                "title": "Uploaded fixture",
                "file": {
                    "name": "paper.md",
                    "type": "text/markdown",
                    "data_base64": base64.b64encode(PAPER.encode("utf-8")).decode("ascii"),
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Uploaded fixture"


def test_cockpit_rejects_unsupported_file(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            "/ui/api/start",
            json={
                "file": {
                    "name": "paper.exe",
                    "type": "application/octet-stream",
                    "data_base64": base64.b64encode(b"not a paper").decode("ascii"),
                }
            },
        )
        assert response.status_code == 400
        assert "unsupported file type" in response.json()["detail"]
