"""Tests for workspace abstraction."""

import pytest
from agent_tooling.workspace.base import Workspace, CommandResult
from agent_tooling.workspace.local import LocalWorkspace
from agent_tooling.tools.base import ToolResult


class TestLocalWorkspace:
    """Tests for LocalWorkspace — in-process execution."""

    def test_instantiation(self):
        ws = LocalWorkspace()
        assert ws.workspace_type == "local"

    def test_execute_tool(self):
        """Tool execution returns ToolResult."""
        from agent_tooling.tools.cognitive.calculator import calculate
        tool = calculate.tool  # FunctionTool underlying the decorator

        ws = LocalWorkspace()
        result = ws.execute_tool(tool, expression="2 + 2")
        assert isinstance(result, ToolResult)
        assert result.success
        assert result.data["result"] == 4

    def test_run_command(self):
        """Shell command execution."""
        ws = LocalWorkspace()
        result = ws.run_command("echo hello")
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_run_command_failure(self):
        ws = LocalWorkspace()
        result = ws.run_command("false")  # exits 1
        assert result.exit_code != 0

    def test_read_file(self, tmp_path):
        ws = LocalWorkspace()
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        content = ws.read_file(str(f))
        assert content == "hello world"

    def test_write_file(self, tmp_path):
        ws = LocalWorkspace()
        f = tmp_path / "output.txt"
        ws.write_file(str(f), "written by workspace")
        assert f.read_text() == "written by workspace"

    def test_read_file_not_found(self):
        ws = LocalWorkspace()
        with pytest.raises(FileNotFoundError):
            ws.read_file("/nonexistent/path/file.txt")
