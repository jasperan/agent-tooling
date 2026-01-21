"""
Agent Tooling: The Tooling Layer of the AI Agent Stack

Transform agent decisions into actions via unified tool abstractions.
Supports both direct Python integration and MCP (Model Context Protocol) servers.
"""

__version__ = "0.1.0"

from agent_tooling.tools.base import BaseTool, ToolResult, ToolError
from agent_tooling.tools.decorator import tool
from agent_tooling.tools.registry import ToolRegistry, TOOL_MAP
from agent_tooling.interceptor import ToolingInterceptor
from agent_tooling.composer import ToolComposer

__all__ = [
    # Version
    "__version__",
    # Core classes
    "BaseTool",
    "ToolResult",
    "ToolError",
    # Decorator
    "tool",
    # Registry
    "ToolRegistry",
    "TOOL_MAP",
    # Interceptor
    "ToolingInterceptor",
    # Composer
    "ToolComposer",
]
