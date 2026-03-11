# Agent Tooling: The Tooling Layer

[![PyPI](https://img.shields.io/pypi/v/agent-tooling-layer?style=for-the-badge)](https://pypi.org/project/agent-tooling-layer/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/agent-tooling-layer?style=for-the-badge)](https://pypi.org/project/agent-tooling-layer/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)](https://www.python.org/)
![Status](https://img.shields.io/badge/status-experimental-orange?style=for-the-badge)

[![OpenHands](https://img.shields.io/badge/powered_by-OpenHands-purple?style=for-the-badge)](https://github.com/OpenHands/OpenHands)
[![Pi-dev](https://img.shields.io/badge/bridge-Pi--dev-ff6b35?style=for-the-badge)](https://buildwithpi.ai/)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=for-the-badge)

Transform agent decisions into actions. Unified tool abstractions with **multi-provider LLM support** via [OpenHands](https://github.com/OpenHands/OpenHands), **sandboxed Docker execution**, and **bidirectional interop** with [pi-dev](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) coding agent.

> **"Any LLM provider. Any execution environment. Any agent harness."**

---

## Why Agent Tooling?

Most tool-calling frameworks lock you into one LLM provider and run everything on the host. Agent Tooling breaks both constraints:

| Problem | Agent Tooling Solution |
|---------|----------------------|
| Locked into one LLM provider | **Multi-provider agent** powered by OpenHands — Ollama, Anthropic, OpenAI, Google, Mistral, Groq |
| Tools run unsandboxed on host | **Workspace abstraction** — Local, Docker, or Remote execution environments |
| No interop between agent systems | **Pi-dev bridge** — bidirectional MCP/RPC protocol exchange |
| Rigid tool definitions | **`@tool` decorator** — one definition, auto-generates OpenAI + MCP schemas |

---

## Quick Start

<!-- one-command-install -->
> **One-command install** — clone, configure, and run in a single step:
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/jasperan/agent-tooling/main/install.sh | bash
> ```
>
> <details><summary>Advanced options</summary>
>
> Override install location:
> ```bash
> PROJECT_DIR=/opt/myapp curl -fsSL https://raw.githubusercontent.com/jasperan/agent-tooling/main/install.sh | bash
> ```
>
> Or install manually:
> ```bash
> git clone https://github.com/jasperan/agent-tooling.git
> cd agent-tooling
> # See below for setup instructions
> ```
> </details>


```bash
# Core package
pip install agent-tooling-layer

# With OpenHands multi-provider support
pip install "agent-tooling-layer[openhands]"

# With Docker sandboxing
pip install "agent-tooling-layer[docker]"

# Everything
pip install "agent-tooling-layer[all]"

# Or use uv
uv add agent-tooling-layer
uv add "agent-tooling-layer[openhands]"
uv add "agent-tooling-layer[all]"
```

### Installation with uv

```bash
# Clone and sync
git clone https://github.com/jasperan/agent-tooling.git
cd agent-tooling
uv sync

# Or with extras
uv sync --extra openhands
uv sync --extra docker
uv sync --all-extras
```

## Development

```bash
# Sync dependencies
uv sync

# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run ty check .

# Add a new dependency
uv add <package>

# Add a dev dependency
uv add --dev <package>

# Add with extras
uv add --extra openhands <package>
```

```bash
# Chat with any LLM provider
agent-tooling --chat --model ollama/qwen3-coder
agent-tooling --chat --model anthropic/claude-sonnet-4-20250514
agent-tooling --chat --model openai/gpt-4o

# Chat with Docker sandboxing
agent-tooling --chat --workspace docker

# Connect to pi-dev coding agent
agent-tooling --bridge pidev

# List supported providers
agent-tooling --providers
```

---

## OpenHands Integration

[OpenHands](https://github.com/OpenHands/OpenHands) is an open platform for AI software developers. Agent Tooling embeds its SDK to provide:

### Multi-Provider LLM Support

Use any LLM provider with a single `provider/model` syntax:

```python
from agent_tooling.agents.base import BaseAgent

# Local Ollama (default, no API key needed)
agent = BaseAgent(model="ollama/qwen3-coder")

# Anthropic Claude
agent = BaseAgent(model="anthropic/claude-sonnet-4-20250514")

# OpenAI GPT
agent = BaseAgent(model="openai/gpt-4o")

# Google Gemini
agent = BaseAgent(model="google/gemini-pro")

# Mistral
agent = BaseAgent(model="mistral/mistral-large-latest")

# Groq (fast inference)
agent = BaseAgent(model="groq/llama-3.3-70b-versatile")

# Interactive chat session
agent.run_interactive()
```

When OpenHands SDK is installed, all providers are available through its provider-agnostic `LLM` class. Without it, Ollama and Anthropic still work via the built-in Anthropic SDK fallback.

```
$ agent-tooling --providers

┌──────────────┬────────────────────────────┬──────────────────┐
│ Provider     │ Description                │ Env Variable     │
├──────────────┼────────────────────────────┼──────────────────┤
│ ollama/*     │ Local Ollama models        │ OLLAMA_BASE_URL  │
│ anthropic/*  │ Anthropic API (Claude)     │ ANTHROPIC_API_KEY │
│ openai/*     │ OpenAI API (GPT)           │ OPENAI_API_KEY   │
│ google/*     │ Google AI (Gemini)         │ GOOGLE_API_KEY   │
│ mistral/*    │ Mistral AI                 │ MISTRAL_API_KEY  │
│ groq/*       │ Groq (fast inference)      │ GROQ_API_KEY     │
└──────────────┴────────────────────────────┴──────────────────┘
```

### Sandboxed Execution via Docker

Tools marked with `sandbox_required=True` run inside Docker containers, protecting the host system:

```python
from agent_tooling import tool
from agent_tooling.workspace.docker import DockerWorkspace
from agent_tooling.agents.base import BaseAgent

# Define a tool that requires sandboxing
@tool(name="run_untrusted", category="developer", sandbox_required=True)
def run_untrusted(code: str) -> str:
    """Execute untrusted code in a sandbox."""
    exec(code)
    return "executed"

# Create agent with Docker workspace
agent = BaseAgent(
    model="ollama/qwen3-coder",
    workspace=DockerWorkspace(image="python:3.12-slim"),
)
agent.run_interactive()
```

The workspace abstraction provides three execution environments:

| Workspace | Use Case | Isolation |
|-----------|----------|-----------|
| `LocalWorkspace` | Development, trusted tools | None (in-process) |
| `DockerWorkspace` | Untrusted code, production | Full container isolation |
| `RemoteWorkspace` | Distributed execution | Network-isolated via HTTP |

```python
from agent_tooling.workspace.local import LocalWorkspace
from agent_tooling.workspace.docker import DockerWorkspace
from agent_tooling.workspace.remote import RemoteWorkspace

# Default: tools run in-process (same as before)
ws = LocalWorkspace()

# Docker: tools run in containers via OpenHands
ws = DockerWorkspace(image="python:3.12-slim")

# Remote: tools run on a remote agent-server
ws = RemoteWorkspace(server_url="http://agent-server:3000")
```

---

## Pi-dev Bridge

[Pi-dev](https://buildwithpi.ai/) is a minimal terminal-based coding agent. Agent Tooling connects to it via **MCP and RPC protocols** — no TypeScript dependencies required.

### Bidirectional Tool Exchange

```python
from agent_tooling.bridges.pidev import PiDevBridge

bridge = PiDevBridge()

# Direction 1: Serve agent-tooling's tools TO pi-dev
# Pi-dev discovers them via MCP protocol
config = bridge.get_mcp_config()
# Returns: {"command": ["python", "-m", "agent_tooling.cli", "--mcp"], ...}
# Add this to pi-dev's MCP settings

# Direction 2: Import pi-dev's tools INTO agent-tooling
# Pi-dev's read/write/edit/bash tools become available in the registry
imported = bridge.consume_pidev_tools()
# Returns: ["pidev_read", "pidev_write", "pidev_edit", "pidev_bash", ...]
```

### CLI Integration

```bash
# Import pi-dev tools into the registry
agent-tooling --bridge pidev

# Then chat using both agent-tooling + pi-dev tools
agent-tooling --chat
```

### How It Works

```
Pi-dev (TypeScript/Node)              Agent-Tooling (Python)
       │                                      │
       │──── MCP protocol (stdio) ───────────>│  Pi-dev discovers tools
       │                                      │
       │<──── RPC (stdin/stdout) ─────────────│  Agent-tooling imports tools
       │                                      │
       ▼                                      ▼
  Pi-dev uses agent-tooling's         Agent-tooling uses pi-dev's
  calculate, web_search, etc.         read, write, edit, bash, etc.
```

---

## Core Features

### `@tool` Decorator

Define tools once, use them everywhere — direct Python, OpenAI function calling, and MCP:

```python
from agent_tooling import tool, ToolError

@tool(name="greet", category="custom", mcp_enabled=True, sandbox_required=False)
def greet(name: str, formal: bool = False) -> str:
    """Generate a greeting message.

    Args:
        name: Name of the person to greet
        formal: Whether to use formal language

    Returns:
        A greeting message
    """
    if formal:
        return f"Good day, {name}. How may I assist you?"
    return f"Hey {name}! What's up?"

# Use directly
result = greet(name="Alice", formal=True)
print(result.data)  # "Good day, Alice. How may I assist you?"

# Get schema for function calling
schema = greet.to_openai_function()

# Get MCP tool format
mcp_schema = greet.to_mcp_tool()
```

### Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **Developer** | `read_file`, `write_file`, `execute_python`, `execute_shell` | File system and code execution |
| **Data** | `query_database`, `call_api`, `fetch_json`, `scrape_webpage` | Database and API access |
| **Cognitive** | `calculate`, `web_search`, `wikipedia_search` | Reasoning support tools |
| **Media** | `pdf_to_markdown`, `analyze_image`, `summarize_pdf` | File processing |
| **Pi-dev** | `pidev_read`, `pidev_write`, `pidev_edit`, `pidev_bash` | Imported via bridge |

### Tool Composition

Build complex workflows from atomic tools:

```python
from agent_tooling import ToolComposer, ToolStep

# Research Assistant: search -> summarize -> save
research = ToolComposer.sequential(
    name="research_assistant",
    description="Search, summarize, and save results",
    tools=[
        ToolStep("web_search", output_key="results"),
        ToolStep("summarize", input_mapping={"text": "results"}),
        ToolStep("write_file", input_mapping={"content": "summary"}),
    ]
)
```

### Tool Registry

Tools are automatically registered and discoverable:

```python
from agent_tooling import ToolRegistry

# List all tools (including pi-dev imports)
for tool in ToolRegistry.list_tools():
    print(f"{tool['name']}: {tool['description']}")

# Get a specific tool
tool = ToolRegistry.get("calculate")
result = tool.run(expression="1 + 1")

# Get schemas for function calling
schemas = ToolRegistry.to_openai_functions()
```

---

## Server Interfaces

### HTTP Server + WebSocket

```bash
# Start HTTP server on port 8082
agent-tooling-server --port 8082
```

REST API:

```bash
# List tools
curl http://localhost:8082/tools

# Execute a tool
curl -X POST http://localhost:8082/execute \
  -H "Content-Type: application/json" \
  -d '{"name": "calculate", "parameters": {"expression": "2 + 2"}}'

# Get OpenAI function schemas
curl http://localhost:8082/schemas/openai
```

WebSocket for real-time agent sessions:

```javascript
const ws = new WebSocket("ws://localhost:8082/ws");

// Send a message
ws.send(JSON.stringify({type: "message", content: "Hello"}));

// Execute a tool via WebSocket
ws.send(JSON.stringify({
    type: "message",
    tool_name: "calculate",
    parameters: {expression: "2 + 2"}
}));

// Receive results
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // {type: "tool_result", name: "calculate", result: {success: true, data: ...}}
};
```

### MCP Server

Expose tools to any MCP-compatible client (Claude, pi-dev, etc.):

```bash
agent-tooling --mcp
```

---

## CLI Reference

```bash
# Interactive menu
agent-tooling

# Chat with agent
agent-tooling --chat                                    # Default: ollama/qwen3-coder
agent-tooling --chat --model anthropic/claude-sonnet-4-20250514  # Any provider
agent-tooling --chat --workspace docker                 # Sandboxed execution

# Tool management
agent-tooling --list                    # List all tools
agent-tooling --schemas                 # Show JSON schemas
agent-tooling --arena                   # Compare tools side by side

# Integrations
agent-tooling --bridge pidev            # Import pi-dev tools
agent-tooling --providers               # Show supported LLM providers
agent-tooling --mcp                     # Start MCP server

# Demo mode
agent-tooling --demo                    # Safe tools only
agent-tooling --demo --demo-network     # Include network tools
agent-tooling --demo --demo-ollama      # Include Ollama tools
agent-tooling --demo --demo-all         # Run everything
agent-tooling --demo-json               # Output as JSON
```

---

## Architecture

```
                    Pi-dev (TS/Node)
                         │
                    MCP / RPC
                         │
┌────────────────────────┼────────────────────────┐
│              Agent-Tooling (Python)              │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ Tools Layer                               │   │
│  │ @tool decorator → ToolRegistry → schemas  │   │
│  └──────────────────────────────────────────┘   │
│                      │                           │
│  ┌──────────────────────────────────────────┐   │
│  │ Workspace Layer                           │   │
│  │ LocalWorkspace │ DockerWorkspace │ Remote  │   │
│  └──────────────────────────────────────────┘   │
│                      │                           │
│  ┌──────────────────────────────────────────┐   │
│  │ Agent Layer                               │   │
│  │ BaseAgent (OpenHands LLM) → OllamaAgent   │   │
│  │ Multi-provider: Anthropic/OpenAI/Google/…  │   │
│  └──────────────────────────────────────────┘   │
│                      │                           │
│  ┌──────────────────────────────────────────┐   │
│  │ Server Layer                              │   │
│  │ REST API + WebSocket + MCP stdio          │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
                         │
                    SDK / Protocol
                         │
                  OpenHands (Python)
```

### Module Map

```
src/agent_tooling/
├── tools/                     # Tool definitions & registry
│   ├── base.py               # BaseTool, ToolResult, ToolDefinition
│   ├── decorator.py          # @tool decorator (sandbox_required flag)
│   ├── registry.py           # Global ToolRegistry singleton
│   └── <categories>/         # developer, cognitive, data, media
├── agents/
│   ├── base.py               # BaseAgent — multi-provider via OpenHands
│   └── ollama.py             # OllamaAgent — thin BaseAgent wrapper
├── workspace/                 # Execution environments
│   ├── base.py               # Abstract Workspace + CommandResult
│   ├── local.py              # LocalWorkspace (in-process, default)
│   ├── docker.py             # DockerWorkspace (container isolation)
│   └── remote.py             # RemoteWorkspace (HTTP to agent-server)
├── bridges/
│   └── pidev.py              # Pi-dev MCP/RPC bidirectional bridge
├── mcp/
│   ├── server.py             # MCP stdio server
│   └── client.py             # MCP client for external servers
├── server.py                  # FastAPI REST + WebSocket server
├── interceptor.py            # Workspace-aware tool execution router
├── composer.py               # Tool composition (sequential, parallel, pipeline)
├── cli.py                    # CLI with --model, --workspace, --bridge
└── visualization/            # Arena, dashboard, traces
```

---

## Installation Options

```bash
# Core only (tools, registry, local workspace)
pip install agent-tooling-layer

# Multi-provider LLM support via OpenHands
pip install "agent-tooling-layer[openhands]"

# Docker sandboxed execution
pip install "agent-tooling-layer[docker]"

# Pi-dev bridge (protocol-only, no extra deps)
pip install "agent-tooling-layer[pidev]"

# MCP server
pip install "agent-tooling-layer[mcp]"

# HTTP server
pip install "agent-tooling-layer[server]"

# PDF/media processing
pip install "agent-tooling-layer[media]"

# Everything
pip install "agent-tooling-layer[all]"

# Or use uv for any of the above
uv add agent-tooling-layer
uv add "agent-tooling-layer[all]"
```

---

## Adding Custom Tools

```python
from agent_tooling import tool, ToolError

@tool(name="my_tool", category="custom", mcp_enabled=True, sandbox_required=False)
def my_tool(param1: str, param2: int = 0) -> dict:
    """Description of what this tool does.

    Args:
        param1: First parameter description
        param2: Second parameter with default

    Returns:
        Dictionary with results
    """
    try:
        return {"result": f"Processed {param1} with {param2}"}
    except Exception as e:
        raise ToolError(str(e), tool_name="my_tool")
```

The tool is immediately available in the registry, MCP server, HTTP API, and any agent session.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Provider not available | Install OpenHands SDK: `pip install agent-tooling-layer[openhands]` |
| Docker workspace fails | Install Docker extras: `pip install agent-tooling-layer[docker]` |
| Pi-dev bridge imports nothing | Start pi-dev in RPC mode: `npx pi --mode rpc` |
| Tool not found | Ensure the tool module is imported before use |
| MCP connection failed | Check that the server is running in stdio mode |

---

## Related Projects

- [OpenHands](https://github.com/OpenHands/OpenHands) — Open platform for AI software developers
- [Pi-dev](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) — Minimal terminal coding agent
- [Agent Stack Whitepaper](https://github.com/jasperan/agent-stack-whitepaper) — Conceptual architecture
- [agent-reasoning](https://github.com/jasperan/agent-reasoning) — The Reasoning Layer

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-jasperan-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jasperan)&nbsp;
[![LinkedIn](https://img.shields.io/badge/LinkedIn-jasperan-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jasperan/)

</div>
