from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from app.mcp_server import get_capabilities, mcp  # noqa: E402


@pytest.mark.anyio
async def test_mcp_exposes_five_bounded_tools():
    tools = await mcp.list_tools()
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name) == {
        "get_capabilities",
        "start_review",
        "get_next_stage",
        "submit_stage",
        "finalize_review",
    }
    for name in ("get_capabilities", "get_next_stage"):
        assert by_name[name].annotations.readOnlyHint is True
    for name in ("start_review", "submit_stage", "finalize_review"):
        ann = by_name[name].annotations
        assert ann.readOnlyHint is False
        assert ann.openWorldHint is False
        assert ann.destructiveHint is False
    assert by_name["start_review"].meta["openai/fileParams"] == ["paper"]


def test_capabilities_disclose_protocol_and_execution_modes():
    capabilities = get_capabilities()
    assert capabilities["protocol_version"] == "epistemic-review-v1"
    assert capabilities["role_count"] == 7
    assert capabilities["roles"][0] == "theorist"
    assert capabilities["roles"][-1] == "adversarial_reviewer"
    assert capabilities["engines"]["desi"]["execution"] == "native-claim-audit"
    assert capabilities["engines"]["doktores"]["native_run_invoked"] is False
    assert capabilities["scope_verdict"] == "REVIEW_ASSISTANCE_ONLY"
