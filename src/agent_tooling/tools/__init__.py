"""
Tool implementations organized by category.

Categories:
- developer: File system, code execution, git, shell
- data: Database, vector search, API, web scraping
- cognitive: Calculator, web search, Wikipedia, knowledge retrieval
- communication: Email, Slack, Discord, webhooks
- media: Image analysis, PDF reading, audio transcription
"""

from agent_tooling.tools.base import BaseTool, ToolResult, ToolError
from agent_tooling.tools.decorator import tool
from agent_tooling.tools.registry import ToolRegistry, TOOL_MAP

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolError",
    "tool",
    "ToolRegistry",
    "TOOL_MAP",
]
