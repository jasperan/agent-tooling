"""
MCP (Model Context Protocol) integration for agent-tooling.

This module provides:
- Automatic MCP server generation from registered tools
- MCP client for connecting to external MCP servers
- Protocol implementations for tool communication
"""

from agent_tooling.mcp.server import MCPServer, create_mcp_server
from agent_tooling.mcp.client import MCPClient

__all__ = [
    "MCPServer",
    "create_mcp_server",
    "MCPClient",
]
