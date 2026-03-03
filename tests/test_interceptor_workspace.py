"""Tests for workspace-aware ToolingInterceptor."""

import pytest
from agent_tooling.interceptor import ToolingInterceptor
from agent_tooling.workspace.local import LocalWorkspace
import agent_tooling.tools.cognitive.calculator  # noqa: F401 — trigger registration


class TestInterceptorWorkspace:
    def test_default_workspace(self):
        """Interceptor defaults to LocalWorkspace."""
        interceptor = ToolingInterceptor()
        assert isinstance(interceptor.workspace, LocalWorkspace)

    def test_custom_workspace(self):
        """Interceptor accepts custom workspace."""
        ws = LocalWorkspace()
        interceptor = ToolingInterceptor(workspace=ws)
        assert interceptor.workspace is ws

    def test_execute_through_workspace(self):
        """Tool execution goes through workspace."""
        interceptor = ToolingInterceptor()
        result = interceptor.execute("calculate", expression="1 + 1")
        assert result.success
        assert result.data["result"] == 2
