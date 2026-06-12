"""
Ollama Agent - backward-compatible wrapper around BaseAgent.

Uses Ollama as the LLM provider. This is a thin wrapper that preserves
the original OllamaAgent API while delegating to BaseAgent's multi-provider
infrastructure.
"""

import os
from typing import List, Optional

from rich.console import Console

from agent_tooling.tools.base import BaseTool
from agent_tooling.agents.base import BaseAgent
from agent_tooling.agents.logger import SessionLogger
from agent_tooling.workspace.base import Workspace


# Default configuration (backward compat)
DEFAULT_MODEL = "qwen3-coder"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAgent(BaseAgent):
    """
    Agent that uses Ollama for LLM inference.

    This is a backward-compatible wrapper around BaseAgent that defaults
    to the Ollama provider. All functionality is inherited from BaseAgent.

    Example:
        agent = OllamaAgent()
        response = agent.chat("Create a file called hello.py with a greeting")
        print(response)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        logger: Optional[SessionLogger] = None,
        console: Optional[Console] = None,
        verbose: bool = True,
        workspace: Optional[Workspace] = None,
    ):
        # Resolve model name — prefix with ollama/ for BaseAgent
        resolved_model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        if "/" not in resolved_model:
            resolved_model = f"ollama/{resolved_model}"

        # Resolve base URL, passing it through explicitly instead of mutating os.environ
        resolved_base_url = base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)

        super().__init__(
            model=resolved_model,
            workspace=workspace,
            tools=tools,
            system_prompt=system_prompt,
            logger=logger,
            console=console,
            verbose=verbose,
            base_url=resolved_base_url,
        )

        # Expose base_url for backward compat
        self.base_url = resolved_base_url
