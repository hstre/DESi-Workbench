"""ChatGPT/MCP surface for DESi Workbench's epistemic review circle.

Run locally:
    python -m app.mcp_server

Then connect an MCP client to http://localhost:8000/mcp.
"""
from __future__ import annotations

import io
import os
import urllib.parse
import urllib.request
import zipfile
from typing import Any
from xml.etree import ElementTree

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .epistemic_review import EpistemicReviewOrchestrator
from .epistemic_review.schemas import FileRef, StageSubmission, StartReviewInput


INSTRUCTIONS = (
    "Always call start_review before any other review tool. Never skip stages. "
    "Kevin may propose but not confirm. DESi may flag but not determine truth. "
    "The theorist may formulate hypotheses but not verdicts; the falsifier may attack "
    "but not repair; only the adversarial reviewer may recommend accept, revise or reject. "
    "Call finalize_review only after get_next_stage reports complete."
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


def _download(ref: FileRef) -> bytes:
    parsed = urllib.parse.urlparse(str(ref.download_url))
    if parsed.scheme != "https":
        raise ValueError("file download_url must use HTTPS")
    req = urllib.request.Request(
        str(ref.download_url), headers={"User-Agent": "DESi-Workbench/0.2"}
    )
    limit = 10_000_000
    with urllib.request.urlopen(req, timeout=20) as response:  # noqa: S310
        if urllib.parse.urlparse(response.geturl()).scheme != "https":
            raise ValueError("file download redirected to a non-HTTPS URL")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("file exceeds the 10 MB transport limit")
    return data


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    chunks: list[str] = []
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for paragraph in root.iter(ns + "p"):
        text = "".join(node.text or "" for node in paragraph.iter(ns + "t"))
        if text.strip():
            chunks.append(text.strip())
    return "\n\n".join(chunks)


def _pdf_text(data: bytes) -> str:
    try:
        import fitz  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ValueError("PDF support requires the 'files' extra (PyMuPDF)") from exc
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n\n".join(page.get_text("text") for page in doc)


def _file_text(ref: FileRef) -> str:
    data = _download(ref)
    name = (ref.file_name or "").lower()
    mime = (ref.mime_type or "").lower()
    if name.endswith(".docx") or "wordprocessingml" in mime:
        return _docx_text(data)
    if name.endswith(".pdf") or mime == "application/pdf":
        return _pdf_text(data)
    if name.endswith((".txt", ".md", ".markdown")) or mime.startswith("text/") or not mime:
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("text files must be UTF-8") from exc
    raise ValueError(f"unsupported file type: {ref.mime_type or ref.file_name}")


@mcp.tool(
    title="Start epistemic review",
    description=(
        "Start a domain-neutral DESi -> Kevin -> Doktores review. Provide either manuscript "
        "text or a ChatGPT file reference. Returns the DESi audit, Kevin blind spots and stage plan."
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
    manuscript = request.text if request.text is not None else _file_text(request.paper)  # type: ignore[arg-type]
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
        "Submit one completed theorist, falsifier or adversarial-reviewer stage. Results are "
        "schema-validated, reference-checked and appended to the hash chain."
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
        "Consolidate the completed DESi, Kevin and Doktores run into a replay-verifiable JSON "
        "artifact and Markdown report. Does not determine truth or replace peer review."
    ),
    annotations=_BOUNDED_WRITE,
    structured_output=True,
)
def finalize_review(run_id: str) -> dict[str, Any]:
    return _orchestrator.finalize(run_id)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
