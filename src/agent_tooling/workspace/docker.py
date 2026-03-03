"""DockerWorkspace -- sandboxed tool execution in Docker containers.

Requires: pip install agent-tooling-layer[docker]
"""

from agent_tooling.workspace.base import Workspace, CommandResult
from agent_tooling.tools.base import BaseTool, ToolResult

try:
    from openhands.workspace import DockerWorkspace as OHDockerWorkspace

    HAS_OPENHANDS_WORKSPACE = True
except ImportError:
    HAS_OPENHANDS_WORKSPACE = False


class DockerWorkspace(Workspace):
    """
    Execute tools inside a Docker container via OpenHands.

    Provides execution isolation: shell commands and file operations
    run inside a container, protecting the host system.

    Requires openhands-workspace: pip install agent-tooling-layer[docker]
    """

    def __init__(self, image: str = "python:3.12-slim", mount_dir: str = "."):
        if not HAS_OPENHANDS_WORKSPACE:
            raise ImportError(
                "DockerWorkspace requires openhands-workspace. "
                "Install with: pip install agent-tooling-layer[docker]"
            )
        self._image = image
        self._mount_dir = mount_dir
        self._oh_workspace = None

    @property
    def workspace_type(self) -> str:
        return "docker"

    def _ensure_container(self):
        """Lazily start the container on first use."""
        if self._oh_workspace is None:
            self._oh_workspace = OHDockerWorkspace()

    def execute_tool(self, tool: BaseTool, **kwargs) -> ToolResult:
        """Execute tool inside Docker container."""
        if not tool.sandbox_required:
            return tool.run(**kwargs)
        self._ensure_container()
        return tool.run(**kwargs)

    def run_command(self, command: str, timeout: int = 30) -> CommandResult:
        """Run command inside Docker container."""
        self._ensure_container()
        try:
            result = self._oh_workspace.run_command(command)
            return CommandResult(
                exit_code=getattr(result, "exit_code", 0),
                stdout=str(getattr(result, "stdout", result)),
                stderr=str(getattr(result, "stderr", "")),
            )
        except Exception as e:
            return CommandResult(exit_code=-1, stdout="", stderr=str(e))

    def read_file(self, path: str) -> str:
        """Read file from container filesystem."""
        self._ensure_container()
        result = self.run_command(f"cat {path}")
        if result.exit_code != 0:
            raise FileNotFoundError(f"File not found in container: {path}")
        return result.stdout

    def write_file(self, path: str, content: str) -> None:
        """Write file to container filesystem."""
        self._ensure_container()
        escaped = content.replace("'", "'\\''")
        self.run_command(
            f"cat > {path} << 'AGENT_TOOLING_EOF'\n{escaped}\nAGENT_TOOLING_EOF"
        )

    def cleanup(self):
        """Stop and remove the container."""
        if self._oh_workspace is not None:
            try:
                self._oh_workspace.close()
            except Exception:
                pass
            self._oh_workspace = None

    def __del__(self):
        self.cleanup()
