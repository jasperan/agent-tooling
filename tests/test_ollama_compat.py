"""Tests for OllamaAgent backward compatibility after refactor."""

import pytest
from unittest.mock import patch
from agent_tooling.agents.ollama import OllamaAgent
from agent_tooling.agents.base import BaseAgent
from agent_tooling.workspace.local import LocalWorkspace

# Import tool modules to trigger auto-registration in the ToolRegistry
import agent_tooling.tools.cognitive.calculator  # noqa: F401


class TestOllamaAgentCompat:
    def test_is_base_agent_subclass(self):
        """OllamaAgent is now a BaseAgent subclass."""
        assert issubclass(OllamaAgent, BaseAgent)

    def test_default_model(self):
        """Default model is qwen3-coder via Ollama."""
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = OllamaAgent()
            assert agent.provider == "ollama"
            assert agent.model_name == "qwen3-coder"

    def test_custom_model(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = OllamaAgent(model="llama3.1")
            assert agent.model_name == "llama3.1"
            assert agent.provider == "ollama"

    def test_has_workspace(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = OllamaAgent()
            assert isinstance(agent.workspace, LocalWorkspace)

    def test_has_chat_method(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = OllamaAgent()
            assert hasattr(agent, "chat")
            assert hasattr(agent, "run_interactive")
            assert hasattr(agent, "clear_history")
