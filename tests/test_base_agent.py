"""Tests for BaseAgent with multi-provider support."""

import pytest
from unittest.mock import patch
from agent_tooling.agents.base import BaseAgent
from agent_tooling.workspace.local import LocalWorkspace

# Import tool modules to trigger auto-registration in the ToolRegistry
import agent_tooling.tools.cognitive.calculator  # noqa: F401


class TestBaseAgentInit:
    def test_default_model(self):
        """BaseAgent defaults to ollama/qwen3-coder."""
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent()
            assert agent.model == "ollama/qwen3-coder"

    def test_custom_model(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent(model="anthropic/claude-sonnet-4-20250514")
            assert agent.model == "anthropic/claude-sonnet-4-20250514"

    def test_default_workspace(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent()
            assert isinstance(agent.workspace, LocalWorkspace)

    def test_custom_workspace(self):
        ws = LocalWorkspace()
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent(workspace=ws)
            assert agent.workspace is ws

    def test_tools_from_registry(self):
        """When no tools specified, loads from ToolRegistry."""
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent()
            assert len(agent.tools) > 0

    def test_provider_property(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent(model="anthropic/claude-sonnet-4-20250514")
            assert agent.provider == "anthropic"
            assert agent.model_name == "claude-sonnet-4-20250514"

    def test_ollama_provider(self):
        with patch("agent_tooling.agents.base.HAS_OPENHANDS_SDK", False):
            agent = BaseAgent(model="ollama/qwen3-coder")
            assert agent.provider == "ollama"
            assert agent.model_name == "qwen3-coder"
