"""
Test script simulating Claude Desktop / MCP client stdio connection to pass_mcp.mcp_server.
"""
import sys
import subprocess
import json
import pytest

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

    # Terminate server process cleanly
    proc.terminate()
    proc.wait(timeout=2)
