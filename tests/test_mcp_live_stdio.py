"""
Tests against pass_mcp.mcp_server: a live stdio JSON-RPC round trip (simulating
Claude Desktop / an MCP client), plus in-process tool-registry conformance and
usage checks run directly against the FastMCP instance.
"""
import sys
import subprocess
import json
from typing import Any, Dict

import httpx
import pytest
from pass_mcp.mcp_server import mcp

@pytest.mark.asyncio
async def test_mcp_stdio_server_communication():
    """Launches pass-mcp via subprocess and verifies JSON-RPC initialize & list_tools responses."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "pass_mcp.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # 1. Send MCP Initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    proc.stdin.write(json.dumps(init_request) + "\n")
    proc.stdin.flush()

    line = proc.stdout.readline()
    assert line, "MCP server closed output stream unexpectedly"
    res = json.loads(line)
    assert res.get("id") == 1
    assert "result" in res
    assert res["result"]["serverInfo"]["name"] == "pass-mcp"

    # 2. Send tools/list request
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }

    proc.stdin.write(json.dumps(list_tools_request) + "\n")
    proc.stdin.flush()

    line = proc.stdout.readline()
    res = json.loads(line)
    assert res.get("id") == 2
    tools = res["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    assert "request_pass" in tool_names
    assert "check_mandate_status" in tool_names
    assert "poll_escalation" in tool_names
    assert "issue_mandate" in tool_names
    assert "get_holder_passes" in tool_names
    assert "lookup_pass" in tool_names
    assert "respond_to_escalation" in tool_names
    assert "revoke_mandate" in tool_names

    # Terminate server process cleanly
    proc.terminate()
    proc.wait(timeout=2)


# ---------------------------------------------------------------------------
# Tool-registry acceptance (in-process, no subprocess needed)
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "issue_mandate",
    "request_pass",
    "get_holder_passes",
    "lookup_pass",
    "check_mandate_status",
    "poll_escalation",
    "respond_to_escalation",
    "revoke_mandate",
}

@pytest.mark.asyncio
async def test_full_mandate_lifecycle_is_exposed():
    """The server must expose the complete mandate lifecycle, not just issue/enforce."""
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - tool_names
    assert not missing, f"pass-mcp is missing lifecycle tools: {missing}"

@pytest.mark.asyncio
async def test_every_tool_declares_a_description():
    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description and tool.description.strip(), (
            f"tool '{tool.name}' has no description; MCP clients rely on this "
            "to decide when to call it"
        )

@pytest.mark.asyncio
async def test_every_tool_accepts_an_optional_api_key_override():
    """Every tool must be able to act on behalf of a caller-supplied business,
    not just the server's own default WALLETKIT_API_KEY."""
    tools = await mcp.list_tools()
    for tool in tools:
        props = tool.inputSchema.get("properties", {})
        required = tool.inputSchema.get("required", [])
        assert "api_key" in props, f"tool '{tool.name}' cannot accept a per-caller api_key"
        assert "api_key" not in required, (
            f"tool '{tool.name}' must not force every caller to supply api_key "
            "(the server's own default must remain a valid fallback)"
        )

@pytest.mark.asyncio
async def test_required_parameters_match_tool_purpose():
    tools = {t.name: t for t in await mcp.list_tools()}
    assert set(tools["issue_mandate"].inputSchema["required"]) == {
        "principal_id", "agent_id", "authorization_details",
    }
    assert set(tools["request_pass"].inputSchema["required"]) == {
        "mandate_token", "pass_class",
    }
    assert set(tools["revoke_mandate"].inputSchema["required"]) == {"jti"}
    assert set(tools["respond_to_escalation"].inputSchema["required"]) == {
        "auth_req_id", "approved",
    }


# ---------------------------------------------------------------------------
# Usage: tool calls behave correctly end-to-end (server -> client -> HTTP)
# ---------------------------------------------------------------------------

def _content_to_dict(result: Any) -> Dict[str, Any]:
    """FastMCP's call_tool returns (content_blocks, structured_result) tuples
    in recent SDK versions, or a bare content-block sequence in older ones.
    Either way, the tool itself always returns a JSON string; unwrap down to it."""
    if isinstance(result, dict):
        return result
    if isinstance(result, tuple):
        _content, structured = result
        raw = structured.get("result", structured) if isinstance(structured, dict) else structured
        return json.loads(raw) if isinstance(raw, str) else raw
    block = result[0] if isinstance(result, list) else result
    text = getattr(block, "text", block)
    return json.loads(text)

@pytest.mark.asyncio
async def test_request_pass_round_trip_returns_allow(recording_transport):
    result = await mcp.call_tool(
        "request_pass",
        {"mandate_token": "tok", "pass_class": "loyalty", "api_key": "wk_caller_key"},
    )
    payload = _content_to_dict(result)
    assert payload["decision"] == "ALLOW"

@pytest.mark.asyncio
async def test_missing_required_argument_is_rejected(recording_transport):
    with pytest.raises(Exception):
        await mcp.call_tool("lookup_pass", {})
    # And no HTTP call should have been attempted for an invalid call.
    assert len(recording_transport.requests) == 0

@pytest.mark.asyncio
async def test_revoke_mandate_tool_hits_revoke_endpoint(recording_transport):
    result = await mcp.call_tool("revoke_mandate", {"jti": "mnd_1", "reason": "test"})
    _content_to_dict(result)  # must not raise / must be valid JSON
    assert any(r.url.path.endswith("/mandates/revoke") for r in recording_transport.requests)

@pytest.mark.asyncio
async def test_respond_to_escalation_tool_hits_respond_endpoint(recording_transport):
    result = await mcp.call_tool(
        "respond_to_escalation",
        {"auth_req_id": "auth_1", "approved": True},
    )
    _content_to_dict(result)
    assert any(
        r.url.path.endswith("/escalations/auth_1/respond") for r in recording_transport.requests
    )

@pytest.mark.asyncio
async def test_upstream_error_is_surfaced_not_raised(monkeypatch):
    """Tool functions must catch client errors and return them as content,
    never let an unhandled exception cross the MCP boundary."""
    from tests.conftest import RecordingTransport

    def _failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = RecordingTransport(_failing_handler)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda *a, **kw: real_async_client(*a, **{**kw, "transport": transport}),
    )

    result = await mcp.call_tool("lookup_pass", {"pass_id": "p1"})
    payload = _content_to_dict(result)
    assert "error" in payload

@pytest.mark.asyncio
async def test_mcp_tool_call_forwards_caller_supplied_key_to_http_layer(recording_transport):
    """End-to-end: an api_key passed into an MCP tool call must reach the
    outbound HTTP request, not just the Python client method."""
    await mcp.call_tool(
        "check_mandate_status",
        {"mandate_token": "tok", "api_key": "wk_from_mcp_caller"},
    )
    assert recording_transport.requests, "no HTTP request was made"
    assert recording_transport.requests[-1].headers["x-api-key"] == "wk_from_mcp_caller"
