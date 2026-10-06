"""Tests for MCP JSON-RPC message handling."""

from agent_tooling.mcp.server import MCPServer


def test_notification_gets_no_response():
    server = MCPServer()
    assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_request_with_id_still_answered():
    server = MCPServer()
    resp = server.handle_message({"jsonrpc": "2.0", "id": 7, "method": "tools/list", "params": None})
    assert resp["id"] == 7
    assert "tools" in resp["result"]


def test_unknown_method_with_id_errors():
    resp = MCPServer().handle_message({"jsonrpc": "2.0", "id": 1, "method": "nope"})
    assert resp["error"]["code"] == -32601
