"""Tests for sandbox_required flag on tools."""

import pytest
from agent_tooling import tool, ToolRegistry


class TestSandboxFlag:
    def test_default_no_sandbox(self):
        """Tools default to sandbox_required=False."""
        @tool(name="safe_test_tool_sf", category="test", auto_register=False)
        def safe_tool(x: str) -> str:
            """A safe tool."""
            return x

        assert safe_tool.tool.sandbox_required is False

    def test_sandbox_required_flag(self):
        """Tools can declare sandbox_required=True."""
        @tool(name="dangerous_test_tool_sf", category="test",
              sandbox_required=True, auto_register=False)
        def dangerous_tool(cmd: str) -> str:
            """A dangerous tool that needs sandboxing."""
            return cmd

        assert dangerous_tool.tool.sandbox_required is True

    def test_sandbox_in_definition(self):
        """sandbox_required appears in tool definition."""
        @tool(name="sandbox_def_test_sf", category="test",
              sandbox_required=True, auto_register=False)
        def sandbox_tool(x: str) -> str:
            """Needs sandbox."""
            return x

        defn = sandbox_tool.tool.definition
        assert defn.sandbox_required is True
