from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from app.mcp_server import mcp  # noqa: E402


@pytest.mark.anyio
async def test_mcp_exposes_four_bounded_tools():
    tools = await mcp.list_tools()
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name) == {
        "start_review", "get_next_stage", "submit_stage", "finalize_review"
    }
    assert by_name["get_next_stage"].annotations.readOnlyHint is True
    for name in ("start_review", "submit_stage", "finalize_review"):
        ann = by_name[name].annotations
        assert ann.readOnlyHint is False
        assert ann.openWorldHint is False
        assert ann.destructiveHint is False
    assert by_name["start_review"].meta["openai/fileParams"] == ["paper"]
