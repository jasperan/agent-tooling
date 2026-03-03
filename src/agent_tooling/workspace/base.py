"""Abstract base class for workspaces."""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from agent_tooling.tools.base import BaseTool, ToolResult


class CommandResult(BaseModel):
    """Result from running a shell command in a workspace."""
    exit_code: int = Field(description="Process exit code")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")


class Workspace(ABC):
    """
    Abstract workspace defining where tools execute.

    Workspaces provide execution isolation. The default LocalWorkspace
    runs tools in-process (identical to agent-tooling's original behavior).
    DockerWorkspace and RemoteWorkspace provide sandboxed execution via
    OpenHands' workspace infrastructure.
    """

    @property
    @abstractmethod
    def workspace_type(self) -> str:
        """Return workspace type identifier (local, docker, remote)."""
        ...

    @abstractmethod
    def execute_tool(self, tool: BaseTool, **kwargs) -> ToolResult:
        """Execute a tool in this workspace."""
        ...

    @abstractmethod
    def run_command(self, command: str, timeout: int = 30) -> CommandResult:
        """Run a shell command in this workspace."""
        ...

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read a file from this workspace's filesystem."""
        ...

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write a file to this workspace's filesystem."""
        ...
