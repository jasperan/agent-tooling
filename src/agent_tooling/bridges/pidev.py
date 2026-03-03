"""
Pi-dev Bridge — bidirectional integration with pi-dev coding agent.

Pi-dev connects to agent-tooling via MCP protocol (already supported).
This module provides:
1. MCP server config generation for pi-dev to discover agent-tooling tools
2. RPC client to consume pi-dev's tools into agent-tooling's registry
3. Helper methods for pi-dev compatible tool formats

Pi-dev integration is protocol-only — no TypeScript dependencies needed.
"""

import json
import subprocess
import sys
from typing import Any, Dict, List, Optional

from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.tools.base import ToolResult


class PiDevBridge:
    """
    Bidirectional bridge between agent-tooling and pi-dev.

    Serving direction (agent-tooling -> pi-dev):
        Pi-dev discovers agent-tooling tools via MCP protocol.
        Use get_mcp_config() to get the config for pi-dev's MCP settings.

    Consuming direction (pi-dev -> agent-tooling):
        Connect to pi-dev's RPC endpoint to import its tools
        (read/write/edit/bash + any extensions) into ToolRegistry.
    """

    def __init__(self, rpc_endpoint: Optional[str] = None):
        self._rpc_endpoint = rpc_endpoint
        self._rpc_process = None

    def get_mcp_config(self) -> Dict[str, Any]:
        """
        Get MCP server config for pi-dev to discover agent-tooling tools.

        Returns:
            Dict with command and args for starting the MCP server.
        """
        return {
            "command": [sys.executable, "-m", "agent_tooling.cli", "--mcp"],
            "name": "agent-tooling",
            "description": "Agent Tooling - unified tool abstractions for AI agents",
        }

    def list_tools_for_pidev(self) -> List[Dict[str, Any]]:
        """
        List all tools in a format compatible with pi-dev's tool display.

        Returns:
            List of tool dicts with name, description, and parameters.
        """
        tools = ToolRegistry.list_tools()
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "category": t.get("category", "general"),
                "parameters": t.get("parameters", []),
            }
            for t in tools
        ]

    def consume_pidev_tools(self, rpc_command: Optional[List[str]] = None) -> List[str]:
        """
        Connect to pi-dev RPC and import its tools into agent-tooling.

        Args:
            rpc_command: Command to start pi-dev in RPC mode.
                         Default: ["npx", "pi", "--mode", "rpc"]

        Returns:
            List of imported tool names.
        """
        if rpc_command is None:
            rpc_command = ["npx", "pi", "--mode", "rpc"]

        imported = []
        try:
            self._rpc_process = subprocess.Popen(
                rpc_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            request = json.dumps({"method": "tools/list", "id": 1}) + "\n"
            self._rpc_process.stdin.write(request)
            self._rpc_process.stdin.flush()

            response_line = self._rpc_process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                tools = response.get("result", {}).get("tools", [])

                for tool_info in tools:
                    self._register_rpc_tool(tool_info)
                    imported.append(tool_info["name"])

        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

        return imported

    def _register_rpc_tool(self, tool_info: Dict[str, Any]) -> None:
        """Wrap a pi-dev RPC tool as an agent-tooling tool."""
        from agent_tooling.tools.decorator import create_tool

        tool_name = f"pidev_{tool_info['name']}"
        description = tool_info.get("description", f"Pi-dev tool: {tool_info['name']}")

        def rpc_executor(**kwargs) -> Dict[str, Any]:
            if self._rpc_process is None or self._rpc_process.poll() is not None:
                return {"error": "Pi-dev RPC process not running"}

            request = json.dumps({
                "method": "tools/call",
                "id": 2,
                "params": {
                    "name": tool_info["name"],
                    "arguments": kwargs,
                },
            }) + "\n"

            self._rpc_process.stdin.write(request)
            self._rpc_process.stdin.flush()

            response_line = self._rpc_process.stdout.readline()
            if response_line:
                return json.loads(response_line).get("result", {})
            return {"error": "No response from pi-dev"}

        create_tool(
            rpc_executor,
            name=tool_name,
            description=description,
            category="pidev",
            mcp_enabled=True,
        )

    def close(self):
        """Clean up RPC process."""
        if self._rpc_process and self._rpc_process.poll() is None:
            self._rpc_process.terminate()
            try:
                self._rpc_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._rpc_process.kill()

    def __del__(self):
        self.close()
