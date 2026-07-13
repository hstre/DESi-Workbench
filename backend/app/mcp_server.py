"""ChatGPT/MCP surface for DESi Workbench's epistemic review circle.

Run locally:
    python -m app.mcp_server

Then open http://localhost:8000/ for the cockpit or connect an MCP client to
http://localhost:8000/mcp.
"""
from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .epistemic_review import EpistemicReviewOrchestrator, adapters
from .epistemic_review.orchestrator import PROTOCOL_VERSION
from .epistemic_review.schemas import (
    STAGE_ORDER,
    FileRef,
    StageSubmission,
    StartReviewInput,
)
from .file_ingest import DOCUMENT_LIMIT, DOWNLOAD_LIMIT, file_ref_to_text
from .ui import register_ui


INSTRUCTIONS = (
    "Always call get_capabilities first and start_review before any stage tool. "
    "Never skip or merge the seven Doktores roles: theorist, literature scout, "
    "falsifier, experimental designer, method reviewer, paper builder, adversarial reviewer. "
    "Kevin may propose but not confirm. DESi may flag but not determine truth. "
    "Each role must obey its packet and exact output schema. Only the adversarial reviewer "
    "may recommend accept, revise or reject. Call finalize_review only after "
    "get_next_stage reports complete."
)

mcp = FastMCP(
    "DESi Epistemic Review",
    instructions=INSTRUCTIONS,
    host=os.getenv("DESI_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("DESI_MCP_PORT", "8000")),
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)
_orchestrator = EpistemicReviewOrchestrator()

_READ_ONLY = ToolAnnotations(readOnlyHint=True)
_BOUNDED_WRITE = ToolAnnotations(
    readOnlyHint=False,
    openWorldHint=False,
    destructiveHint=False,
    idempotentHint=True,
)


@mcp.tool(
    title="Inspect epistemic review capabilities",
    description=(
        "Return protocol version, fixed role order, file support and explicit native/fallback "
        "status for DESi, Kevin and Doktores. Call this before starting a review."
    ),
    annotations=_READ_ONLY,
    structured_output=True,
)
def get_capabilities() -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "roles": list(STAGE_ORDER),
        "role_count": len(STAGE_ORDER),
        "engines": adapters.engine_manifest(),
        "file_support": {
            "formats": ["utf-8-text", "markdown", "docx", "pdf"],
            "download_transport": "https-only",
            "download_limit_bytes": DOWNLOAD_LIMIT,
            "document_limit_bytes": DOCUMENT_LIMIT,
        },
        "interfaces": {
            "browser_cockpit": "/",
            "mcp": "/mcp",
        },
        "scope_verdict": "REVIEW_ASSISTANCE_ONLY",
    }


@mcp.tool(
    title="Start epistemic review",
    description=(
        "Start a domain-neutral DESi -> Kevin -> seven-role Doktores review. Provide either "
        "manuscript text or a ChatGPT file reference. Returns the DESi audit, Kevin blind "
        "spots, engine provenance and fixed stage plan."
    ),
    annotations=_BOUNDED_WRITE,
    meta={"openai/fileParams": ["paper"]},
    structured_output=True,
)
def start_review(
    text: str | None = None,
    paper: FileRef | None = None,
    title: str | None = None,
    modes: tuple[str, ...] = ("audit", "extend", "adversarial"),
    focus: str | None = None,
) -> dict[str, Any]:
    request = StartReviewInput(
        text=text, paper=paper, title=title, modes=modes, focus=focus
    )
    manuscript = (
        request.text
        if request.text is not None
        else file_ref_to_text(request.paper)  # type: ignore[arg-type]
    )
    return _orchestrator.start(request, manuscript)


@mcp.tool(
    title="Get next separated review stage",
    description=(
        "Return the next role packet. The packet contains only the context and actions allowed "
        "for that Doktores role and its exact output schema."
    ),
    annotations=_READ_ONLY,
    structured_output=True,
)
def get_next_stage(run_id: str) -> dict[str, Any]:
    return _orchestrator.next_stage(run_id)


@mcp.tool(
    title="Submit review stage",
    description=(
        "Submit one completed Doktores role stage. Results are schema-validated, "
        "reference-checked and appended to the hash chain."
    ),
    annotations=_BOUNDED_WRITE,
    structured_output=True,
)
def submit_stage(run_id: str, stage_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return _orchestrator.submit(
        StageSubmission(run_id=run_id, stage_id=stage_id, result=result)
    )


@mcp.tool(
    title="Finalize epistemic review",
    description=(
        "Consolidate the completed DESi, Kevin and seven-role Doktores run into a "
        "replay-verifiable JSON artifact and Markdown report. Does not determine truth or "
        "replace peer review."
    ),
    annotations=_BOUNDED_WRITE,
    structured_output=True,
)
def finalize_review(run_id: str) -> dict[str, Any]:
    return _orchestrator.finalize(run_id)


register_ui(mcp, _orchestrator, get_capabilities)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
