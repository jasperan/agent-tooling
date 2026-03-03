"""
Agent implementations for agent-tooling.

Provides ready-to-use agents that leverage the tool system.
"""

from agent_tooling.agents.ollama import OllamaAgent
from agent_tooling.agents.base import BaseAgent
from agent_tooling.agents.logger import SessionLogger

__all__ = ["BaseAgent", "OllamaAgent", "SessionLogger"]
