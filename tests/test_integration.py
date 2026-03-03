"""Integration tests for the full OpenHands + Pi-dev integration."""

import pytest
from unittest.mock import patch

# Import tool modules to trigger auto-registration in the ToolRegistry
import agent_tooling.tools.cognitive.calculator  # noqa: F401


class TestFullStack:
    """Verify all components work together."""

    def test_tool_through_workspace_through_interceptor(self):
        """Tool -> Workspace -> Interceptor flow works end-to-end."""
        from agent_tooling.interceptor import ToolingInterceptor
        from agent_tooling.workspace.local import LocalWorkspace

        ws = LocalWorkspace()
        interceptor = ToolingInterceptor(workspace=ws)
        result = interceptor.execute("calculate", expression="10 * 5")
        assert result.success
        assert result.data["result"] == 50

    def test_base_agent_with_workspace(self):
        """BaseAgent initializes with workspace."""
        from agent_tooling.agents.base import BaseAgent
        from agent_tooling.workspace.local import LocalWorkspace

        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            ws = LocalWorkspace()
            agent = BaseAgent(workspace=ws)
            assert agent.workspace is ws
            assert len(agent.tools) > 0

    def test_ollama_agent_backward_compat(self):
        """OllamaAgent works exactly as before."""
        from agent_tooling.agents.ollama import OllamaAgent
        from agent_tooling.agents.base import BaseAgent

        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = OllamaAgent()
            assert isinstance(agent, BaseAgent)
            assert agent.provider == "ollama"
            assert len(agent.tools) > 0

    def test_pidev_bridge_mcp_config(self):
        """Pi-dev bridge generates valid MCP config."""
        from agent_tooling.bridges.pidev import PiDevBridge

        bridge = PiDevBridge()
        config = bridge.get_mcp_config()
        assert "command" in config
        assert "name" in config

    def test_imports_all(self):
        """All public exports are importable."""
        from agent_tooling import (
            BaseTool,
            ToolResult,
            ToolError,
            tool,
            ToolRegistry,
            TOOL_MAP,
            ToolingInterceptor,
            ToolComposer,
            Workspace,
            CommandResult,
            LocalWorkspace,
        )

        assert all(
            x is not None
            for x in [
                BaseTool,
                ToolResult,
                ToolError,
                tool,
                ToolRegistry,
                TOOL_MAP,
                ToolingInterceptor,
                ToolComposer,
                Workspace,
                CommandResult,
                LocalWorkspace,
            ]
        )
