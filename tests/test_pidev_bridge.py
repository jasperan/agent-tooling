"""Tests for Pi-dev MCP/RPC bridge."""

import pytest
import sys
from agent_tooling.bridges.pidev import PiDevBridge

# Import a tool module to trigger auto-registration in the ToolRegistry
from agent_tooling.tools.cognitive.calculator import calculate  # noqa: F401


class TestPiDevBridge:
    def test_instantiation(self):
        bridge = PiDevBridge()
        assert bridge is not None

    def test_serve_tools_returns_mcp_config(self):
        """serve_tools returns MCP server config dict."""
        bridge = PiDevBridge()
        config = bridge.get_mcp_config()
        assert "command" in config
        assert "name" in config
        assert config["name"] == "agent-tooling"

    def test_mcp_config_has_description(self):
        """MCP config includes a description field."""
        bridge = PiDevBridge()
        config = bridge.get_mcp_config()
        assert "description" in config
        assert isinstance(config["description"], str)

    def test_mcp_config_command_is_list(self):
        """MCP config command is a list of strings."""
        bridge = PiDevBridge()
        config = bridge.get_mcp_config()
        assert isinstance(config["command"], list)
        assert all(isinstance(c, str) for c in config["command"])

    def test_tool_list_for_pidev(self):
        """Can generate tool list in pi-dev compatible format."""
        bridge = PiDevBridge()
        tools = bridge.list_tools_for_pidev()
        assert isinstance(tools, list)
        assert len(tools) > 0
        for t in tools:
            assert "name" in t
            assert "description" in t

    def test_tool_list_includes_category(self):
        """Pi-dev tool list includes category for each tool."""
        bridge = PiDevBridge()
        tools = bridge.list_tools_for_pidev()
        for t in tools:
            assert "category" in t

    def test_tool_list_includes_parameters(self):
        """Pi-dev tool list includes parameters for each tool."""
        bridge = PiDevBridge()
        tools = bridge.list_tools_for_pidev()
        for t in tools:
            assert "parameters" in t
            assert isinstance(t["parameters"], list)

    def test_consume_pidev_tools_returns_empty_on_failure(self):
        """consume_pidev_tools returns empty list when RPC command fails."""
        bridge = PiDevBridge()
        # Use a command that will definitely not exist
        result = bridge.consume_pidev_tools(rpc_command=["nonexistent_command_xyz"])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_close_without_process(self):
        """close() works fine when no RPC process is running."""
        bridge = PiDevBridge()
        bridge.close()  # Should not raise


class TestRpcToolRegistration:
    def test_imported_rpc_tool_forwards_arguments(self):
        """Imported pi-dev tools expose inputSchema params and pass args through."""
        import json
        from agent_tooling.tools.registry import ToolRegistry

        class FakeStdin:
            def __init__(self):
                self.written = []

            def write(self, data):
                self.written.append(data)

            def flush(self):
                pass

        class FakeStdout:
            def readline(self):
                return json.dumps({"id": 1, "result": {"ok": True}}) + "\n"

        class FakeProc:
            stdin = FakeStdin()
            stdout = FakeStdout()

            def poll(self):
                return None

        bridge = PiDevBridge()
        bridge._rpc_process = FakeProc()
        bridge._register_rpc_tool({
            "name": "echo_probe",
            "description": "probe",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "t"}},
                "required": ["text"],
            },
        })
        t = ToolRegistry.get("pidev_echo_probe")
        assert [p.name for p in t.get_parameters()] == ["text"]
        result = t.run(text="hi")
        assert result.success
        sent = json.loads(FakeProc.stdin.written[0])
        assert sent["params"]["arguments"] == {"text": "hi"}
        bridge._rpc_process = None
