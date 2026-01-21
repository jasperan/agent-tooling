"""
MCP Client - Connect to external MCP servers.

This allows agent-tooling to consume tools from other MCP servers,
enabling interoperability with the broader MCP ecosystem.
"""

from typing import Any, Dict, List, Optional
import subprocess
import json
import asyncio
from dataclasses import dataclass


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""
    command: List[str]  # Command to start the server
    name: str = ""
    env: Optional[Dict[str, str]] = None


class MCPClient:
    """
    Client for connecting to MCP servers.

    Allows agent-tooling to discover and use tools from external
    MCP servers, enabling composition of tools across different systems.

    Example:
        client = MCPClient()
        client.connect(MCPServerConfig(
            command=["npx", "-y", "@modelcontextprotocol/server-filesystem"],
            name="filesystem"
        ))

        tools = client.list_tools()
        result = client.call_tool("read_file", {"path": "/tmp/test.txt"})
    """

    def __init__(self):
        self._servers: Dict[str, subprocess.Popen] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}  # tool_name -> server_name

    def connect(self, config: MCPServerConfig) -> bool:
        """
        Connect to an MCP server.

        Args:
            config: Server configuration

        Returns:
            True if connection successful
        """
        try:
            process = subprocess.Popen(
                config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=config.env,
                text=True,
            )

            server_name = config.name or config.command[0]
            self._servers[server_name] = process

            # Initialize the server
            init_response = self._send_message(server_name, {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "agent-tooling",
                        "version": "0.1.0",
                    },
                },
            })

            if init_response and "result" in init_response:
                # Fetch tools
                tools_response = self._send_message(server_name, {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                })

                if tools_response and "result" in tools_response:
                    for tool in tools_response["result"].get("tools", []):
                        tool_name = f"{server_name}/{tool['name']}"
                        self._tools[tool_name] = {
                            "server": server_name,
                            "definition": tool,
                        }

                return True

            return False

        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            return False

    def disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server."""
        if server_name in self._servers:
            self._servers[server_name].terminate()
            del self._servers[server_name]

            # Remove tools from this server
            self._tools = {
                name: info
                for name, info in self._tools.items()
                if info["server"] != server_name
            }

    def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for name in list(self._servers.keys()):
            self.disconnect(name)

    def _send_message(self, server_name: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a message to an MCP server and get response."""
        if server_name not in self._servers:
            return None

        process = self._servers[server_name]

        try:
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

            response_line = process.stdout.readline()
            if response_line:
                return json.loads(response_line.strip())

        except Exception as e:
            print(f"Error communicating with MCP server: {e}")

        return None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools from all connected servers."""
        return [
            {
                "name": name,
                "server": info["server"],
                **info["definition"],
            }
            for name, info in self._tools.items()
        ]

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        return self._tools.get(tool_name)

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Call a tool on an MCP server.

        Args:
            tool_name: Full tool name (server/tool_name format)
            arguments: Tool arguments

        Returns:
            Tool result or None if failed
        """
        tool_info = self._tools.get(tool_name)
        if not tool_info:
            # Try without server prefix
            for name, info in self._tools.items():
                if name.endswith(f"/{tool_name}"):
                    tool_info = info
                    break

        if not tool_info:
            return None

        server_name = tool_info["server"]
        actual_tool_name = tool_info["definition"]["name"]

        response = self._send_message(server_name, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": actual_tool_name,
                "arguments": arguments,
            },
        })

        if response and "result" in response:
            result = response["result"]
            content = result.get("content", [])
            if content and len(content) > 0:
                text = content[0].get("text", "")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text

        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect_all()
