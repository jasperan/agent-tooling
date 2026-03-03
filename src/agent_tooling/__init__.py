"""
Agent Tooling: The Tooling Layer of the AI Agent Stack

Transform agent decisions into actions via unified tool abstractions.
Supports multiple LLM providers, sandboxed execution, and interop with
pi-dev and OpenHands agent harnesses.
"""

__version__ = "0.2.0"

from agent_tooling.tools.base import BaseTool, ToolResult, ToolError
from agent_tooling.tools.decorator import tool
from agent_tooling.tools.registry import ToolRegistry, TOOL_MAP
from agent_tooling.interceptor import ToolingInterceptor
from agent_tooling.composer import ToolComposer
from agent_tooling.workspace.base import Workspace, CommandResult
from agent_tooling.workspace.local import LocalWorkspace

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
    # Workspace
    "Workspace",
    "CommandResult",
    "LocalWorkspace",
]

# Conditionally export optional components
try:
    from agent_tooling.workspace.docker import DockerWorkspace
    __all__.append("DockerWorkspace")
except ImportError:
    pass

try:
    from agent_tooling.agents.base import BaseAgent
    __all__.append("BaseAgent")
except ImportError:
    pass
