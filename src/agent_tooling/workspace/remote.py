"""RemoteWorkspace -- tool execution on a remote agent-server."""

import httpx
from agent_tooling.workspace.base import Workspace, CommandResult
from agent_tooling.tools.base import BaseTool, ToolResult


class RemoteWorkspace(Workspace):
    """
    Execute tools on a remote OpenHands agent-server.

    Connects via HTTP to an agent-server instance running elsewhere.
    """

    def __init__(self, server_url: str = "http://localhost:3000"):
        self._server_url = server_url.rstrip("/")
        self._client = httpx.Client(base_url=self._server_url, timeout=60.0)

    @property
    def workspace_type(self) -> str:
        return "remote"

    def execute_tool(self, tool: BaseTool, **kwargs) -> ToolResult:
        """Execute tool on remote server."""
        try:
            resp = self._client.post(
                "/tools/execute",
                json={
                    "name": tool.name,
                    "parameters": kwargs,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return ToolResult(
                success=data.get("success", False),
                data=data.get("data"),
                error=data.get("error"),
                tool_name=tool.name,
                execution_time_ms=data.get("execution_time_ms", 0),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Remote execution failed: {e}",
                tool_name=tool.name,
            )

    def run_command(self, command: str, timeout: int = 30) -> CommandResult:
        """Run command on remote server."""
        try:
            resp = self._client.post(
                "/command",
                json={
                    "command": command,
                    "timeout": timeout,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return CommandResult(
                exit_code=data.get("exit_code", -1),
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
            )
        except Exception as e:
            return CommandResult(exit_code=-1, stdout="", stderr=str(e))

    def read_file(self, path: str) -> str:
        """Read file from remote filesystem."""
        resp = self._client.get("/file", params={"path": path})
        resp.raise_for_status()
        return resp.text

    def write_file(self, path: str, content: str) -> None:
        """Write file to remote filesystem."""
        self._client.post("/file", json={"path": path, "content": content})

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __del__(self):
        self.close()
