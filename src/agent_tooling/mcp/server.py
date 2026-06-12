"""
MCP Server - Auto-generate MCP servers from registered tools.

This module transforms @tool decorated functions into a fully compliant
MCP server that can be consumed by any MCP client (Claude, etc.).
"""

from typing import Any, Dict, List, Optional
import json
import asyncio
from dataclasses import dataclass

from agent_tooling import __version__
from agent_tooling.tools.registry import ToolRegistry
from agent_tooling.tools.base import BaseTool


@dataclass
class MCPToolCall:
    """Represents an incoming MCP tool call."""
    name: str
    arguments: Dict[str, Any]
    call_id: str = ""


@dataclass
class MCPToolResponse:
    """Response to an MCP tool call."""
    call_id: str
    content: Any
    is_error: bool = False


class MCPServer:
    """
    MCP Server that exposes registered tools.

    This server implements the Model Context Protocol, allowing
    AI assistants like Claude to discover and use your tools.

    Example:
        server = MCPServer(name="my-tools")
        server.start()  # Starts stdio server

        # Or get the tools list for manual integration:
        tools = server.list_tools()
    """

    def __init__(
        self,
        name: str = "agent-tooling",
        version: str = __version__,
        description: str = "Tools from agent-tooling",
        tools: Optional[List[str]] = None,
    ):
        """
        Initialize the MCP server.

        Args:
            name: Server name
            version: Server version
            description: Server description
            tools: List of tool names to expose (None = all MCP-enabled tools)
        """
        self.name = name
        self.version = version
        self.description = description
        self._tool_filter = tools
        self._running = False

    @property
    def tools(self) -> List[BaseTool]:
        """Get the tools this server exposes."""
        if self._tool_filter:
            return [
                ToolRegistry.get(name)
                for name in self._tool_filter
                if ToolRegistry.get(name) is not None
            ]
        return ToolRegistry.get_mcp_tools()

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all tools in MCP format.

        Returns:
            List of tool definitions in MCP schema format
        """
        return [tool.to_mcp_tool() for tool in self.tools]

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": {
                "tools": True,
                "resources": False,
                "prompts": False,
            },
        }

    async def handle_tool_call(self, call: MCPToolCall) -> MCPToolResponse:
        """
        Handle an incoming tool call.

        Args:
            call: The tool call to handle

        Returns:
            MCPToolResponse with the result
        """
        tool = ToolRegistry.get(call.name)

        if tool is None:
            return MCPToolResponse(
                call_id=call.call_id,
                content={"error": f"Tool not found: {call.name}"},
                is_error=True,
            )

        try:
            result = tool.run(**call.arguments)

            if result.success:
                return MCPToolResponse(
                    call_id=call.call_id,
                    content=result.data,
                    is_error=False,
                )
            else:
                return MCPToolResponse(
                    call_id=call.call_id,
                    content={"error": result.error},
                    is_error=True,
                )

        except Exception as e:
            return MCPToolResponse(
                call_id=call.call_id,
                content={"error": str(e)},
                is_error=True,
            )

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming MCP message (synchronous).

        Args:
            message: The MCP JSON-RPC message

        Returns:
            The response message
        """
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": self.get_server_info(),
                    "capabilities": {"tools": {}},
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": self.list_tools()},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            call = MCPToolCall(name=tool_name, arguments=arguments, call_id=str(msg_id))
            response = asyncio.run(self.handle_tool_call(call))

            if response.is_error:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(response.content)}],
                        "isError": True,
                    },
                }
            else:
                content = response.content
                if not isinstance(content, str):
                    content = json.dumps(content, default=str)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": content}],
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    def run_stdio(self) -> None:
        """
        Run the server in stdio mode.

        This is the standard way to run an MCP server, communicating
        via stdin/stdout with JSON-RPC messages.
        """
        import sys

        self._running = True

        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                message = json.loads(line.strip())
                response = self.handle_message(message)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

    def stop(self) -> None:
        """Stop the server."""
        self._running = False


def create_mcp_server(
    name: str = "agent-tooling",
    tools: Optional[List[str]] = None,
) -> MCPServer:
    """
    Create an MCP server for the specified tools.

    Args:
        name: Server name
        tools: List of tool names (None = all MCP-enabled tools)

    Returns:
        Configured MCPServer instance
    """
    return MCPServer(name=name, tools=tools)


# CLI entry point for running the MCP server
def main():
    """Run the MCP server from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Tooling MCP Server")
    parser.add_argument("--name", default="agent-tooling", help="Server name")
    parser.add_argument("--tools", nargs="*", help="Specific tools to expose")
    args = parser.parse_args()

    server = create_mcp_server(name=args.name, tools=args.tools)
    server.run_stdio()


if __name__ == "__main__":
    main()
