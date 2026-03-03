"""LocalWorkspace — in-process tool execution (default)."""

import subprocess
from agent_tooling.workspace.base import Workspace, CommandResult
from agent_tooling.tools.base import BaseTool, ToolResult


class LocalWorkspace(Workspace):
    """
    Execute tools in the current process.

    This is the default workspace and matches agent-tooling's original
    behavior exactly — no containers, no isolation, no extra dependencies.
    """

    @property
    def workspace_type(self) -> str:
        return "local"

    def execute_tool(self, tool: BaseTool, **kwargs) -> ToolResult:
        """Execute tool directly in-process."""
        return tool.run(**kwargs)

    def run_command(self, command: str, timeout: int = 30) -> CommandResult:
        """Run shell command in current environment."""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return CommandResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
            )

    def read_file(self, path: str) -> str:
        """Read file from local filesystem."""
        with open(path, "r") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        """Write file to local filesystem."""
        with open(path, "w") as f:
            f.write(content)
