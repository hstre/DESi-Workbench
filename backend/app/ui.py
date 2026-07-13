"""Browser cockpit mounted on the same Starlette app as the MCP endpoint."""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Callable

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from .epistemic_review.orchestrator import EpistemicReviewOrchestrator
from .epistemic_review.schemas import StageSubmission, StartReviewInput
from .file_ingest import base64_file_to_text, ensure_document_limit


CapabilityProvider = Callable[[], dict[str, Any]]


def _asset(name: str) -> str:
    return files("app").joinpath("static", name).read_text(encoding="utf-8")


def _error(exc: Exception) -> JSONResponse:
    if isinstance(exc, KeyError):
        status = 404
    elif isinstance(exc, (ValueError, ValidationError, json.JSONDecodeError)):
        status = 400
    else:
        status = 500
    message = str(exc)
    if isinstance(exc, KeyError) and exc.args:
        message = str(exc.args[0])
    return JSONResponse(
        {"error": type(exc).__name__, "detail": message},
        status_code=status,
    )


async def _json(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise ValueError("request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def register_ui(
    mcp: Any,
    orchestrator: EpistemicReviewOrchestrator,
    capabilities: CapabilityProvider,
) -> None:
    """Register the cockpit and its bounded JSON API on a ``FastMCP`` server."""

    @mcp.custom_route("/", methods=["GET"], include_in_schema=False)
    async def ui_index(_: Request) -> Response:
        return HTMLResponse(_asset("index.html"))

    @mcp.custom_route("/ui/app.js", methods=["GET"], include_in_schema=False)
    async def ui_javascript(_: Request) -> Response:
        return Response(_asset("app.js"), media_type="application/javascript; charset=utf-8")

    @mcp.custom_route("/ui/styles.css", methods=["GET"], include_in_schema=False)
    async def ui_styles(_: Request) -> Response:
        return Response(_asset("styles.css"), media_type="text/css; charset=utf-8")

    @mcp.custom_route("/ui/api/capabilities", methods=["GET"], include_in_schema=False)
    async def ui_capabilities(_: Request) -> Response:
        try:
            return JSONResponse(capabilities())
        except Exception as exc:  # pragma: no cover - defensive deployment boundary
            return _error(exc)

    @mcp.custom_route("/ui/api/start", methods=["POST"], include_in_schema=False)
    async def ui_start(request: Request) -> Response:
        try:
            payload = await _json(request)
            file_payload = payload.get("file")
            text = payload.get("text")
            if file_payload:
                if text and str(text).strip():
                    raise ValueError("provide either text or file, not both")
                if not isinstance(file_payload, dict):
                    raise ValueError("file must be an object")
                text = base64_file_to_text(
                    str(file_payload.get("data_base64", "")),
                    file_name=str(file_payload.get("name", "")),
                    mime_type=str(file_payload.get("type", "")),
                )
            if not isinstance(text, str) or not text.strip():
                raise ValueError("provide manuscript text or a supported file")
            ensure_document_limit(text)
            modes = payload.get("modes") or ["audit", "extend", "adversarial"]
            review_request = StartReviewInput(
                title=payload.get("title"),
                text=text,
                modes=tuple(modes),
                focus=payload.get("focus"),
            )
            return JSONResponse(orchestrator.start(review_request, text))
        except Exception as exc:
            return _error(exc)

    @mcp.custom_route(
        "/ui/api/run/{run_id}", methods=["GET"], include_in_schema=False
    )
    async def ui_run_summary(request: Request) -> Response:
        try:
            return JSONResponse(orchestrator.summary(request.path_params["run_id"]))
        except Exception as exc:
            return _error(exc)

    @mcp.custom_route(
        "/ui/api/run/{run_id}/next", methods=["POST"], include_in_schema=False
    )
    async def ui_next_stage(request: Request) -> Response:
        try:
            return JSONResponse(orchestrator.next_stage(request.path_params["run_id"]))
        except Exception as exc:
            return _error(exc)

    @mcp.custom_route(
        "/ui/api/run/{run_id}/stage/{stage_id}",
        methods=["POST"],
        include_in_schema=False,
    )
    async def ui_submit_stage(request: Request) -> Response:
        try:
            payload = await _json(request)
            result = payload.get("result", payload)
            if not isinstance(result, dict):
                raise ValueError("stage result must be a JSON object")
            submission = StageSubmission(
                run_id=request.path_params["run_id"],
                stage_id=request.path_params["stage_id"],
                result=result,
            )
            return JSONResponse(orchestrator.submit(submission))
        except Exception as exc:
            return _error(exc)

    @mcp.custom_route(
        "/ui/api/run/{run_id}/finalize", methods=["POST"], include_in_schema=False
    )
    async def ui_finalize(request: Request) -> Response:
        try:
            return JSONResponse(orchestrator.finalize(request.path_params["run_id"]))
        except Exception as exc:
            return _error(exc)
