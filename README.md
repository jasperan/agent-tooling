# Agent Tooling: The Tooling Layer

[![PyPI](https://img.shields.io/pypi/v/agent-tooling-layer?style=for-the-badge)](https://pypi.org/project/agent-tooling-layer/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/agent-tooling-layer?style=for-the-badge)](https://pypi.org/project/agent-tooling-layer/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)](https://www.python.org/)
![Status](https://img.shields.io/badge/status-experimental-orange?style=for-the-badge)
![Ollama](https://img.shields.io/badge/backend-Ollama-black?style=for-the-badge)

<!-- ![GIF demo](https://raw.githubusercontent.com/jasperan/agent-tooling/main/gif/arena_mode.gif) -->

## Vision & Purpose

The **Tooling Layer** is the action engine of the AI Agent Stack. It translates agent decisions into real-world effects by providing a unified interface for tools that interact with databases, APIs, file systems, and external services.

This repository implements the concepts from the [Agent Stack Whitepaper](https://github.com/jasperan/agent-stack-whitepaper), specifically the Tooling section which covers:

- **Tool Definitions**: Name, description, input/output schemas
- **Function Calling**: Structured JSON tool invocations
- **Tool Composition**: Building complex tools from atomic ones
- **MCP Integration**: Model Context Protocol for tool sharing

> **"From decisions to actions - unified tool abstractions for AI agents."**

---

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install agent-tooling-layer

# With MCP server support:
pip install "agent-tooling-layer[mcp]"

# With HTTP server support:
pip install "agent-tooling-layer[server]"

# Everything:
pip install "agent-tooling-layer[all]"
```

### From Source

```bash
git clone https://github.com/jasperan/agent-tooling.git
cd agent-tooling
pip install -e .
```

---

## 📓 Notebooks

Interactive Jupyter notebooks demonstrating tool capabilities:

| Name | Description | Link |
| ---- | ----------- | ---- |
| agent_tooling_demo | Comprehensive demo of all tool categories with arena mode | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=for-the-badge)](notebooks/agent_tooling_demo.ipynb) |

---

## 🚀 Features

### ✅ Unified Tool Abstraction

- **`@tool` Decorator**: Define tools with automatic schema generation
- **Direct + MCP**: Same tool works both ways
- **Type-Safe**: Pydantic validation for inputs/outputs
- **Auto-Documentation**: Schemas generated from docstrings

### 🛠️ Tool Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **Developer** | `read_file`, `write_file`, `execute_python`, `execute_shell` | File system and code execution |
| **Data** | `query_database`, `call_api`, `fetch_json`, `scrape_webpage` | Database and API access |
| **Cognitive** | `calculate`, `web_search`, `wikipedia_search` | Reasoning support tools |
| **Communication** | `send_email`, `slack_notify`, `webhook` | Notifications (coming soon) |
| **Media** | `analyze_image`, `read_pdf`, `transcribe` | File processing (coming soon) |

### 🔗 Tool Composition

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

---

## 💻 Usage

### 1. Interactive CLI

```bash
# Launch interactive menu
agent-tooling

# List all tools
agent-tooling --list

# Arena mode: compare tools
agent-tooling --arena

# Start MCP server
agent-tooling --mcp
```

**Interactive Experience:**
```text
╭────────────────────────────────────────────╮
│ AGENT TOOLING CLI                          │
│ The Tooling Layer of the AI Agent Stack    │
╰────────────────────────────────────────────╯

? Select an action:
  List Tools
  Run Tool
  Arena: Compare Tools
  Dashboard
  MCP Server
  Exit
```

### 2. Python API

```python
from agent_tooling import tool, ToolRegistry

# Define a custom tool
@tool(name="greet", category="custom", mcp_enabled=True)
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
```

### 3. Using Built-in Tools

```python
from agent_tooling.tools.developer import read_file, execute_python
from agent_tooling.tools.cognitive import calculate, web_search

# Read a file
result = read_file(path="README.md")
print(result.data[:100])

# Execute Python code
result = execute_python(code="result = sum(range(100))")
print(result.data)  # {'return_value': 4950, ...}

# Calculate
result = calculate(expression="sqrt(144) + pi")
print(result.data)  # {'result': 15.14159...}

# Search the web
results = web_search(query="Python MCP protocol")
for r in results.data:
    print(f"- {r['title']}: {r['url']}")
```

### 4. MCP Server Mode

Expose your tools to any MCP-compatible client (Claude, etc.):

```bash
# Start MCP server
agent-tooling --mcp

# Or from Python
from agent_tooling.mcp import create_mcp_server
server = create_mcp_server(name="my-tools")
server.run_stdio()
```

### 5. HTTP Server Mode

```bash
# Start HTTP server on port 8082
agent-tooling-server --port 8082
```

Then use the REST API:

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

---

## 🧠 Architecture

### The `@tool` Decorator

The decorator extracts everything needed from your function:

```python
@tool(name="my_tool", category="custom", mcp_enabled=True)
def my_tool(required_param: str, optional_param: int = 10) -> dict:
    """Short description for the tool.

    Args:
        required_param: Description of this parameter
        optional_param: Description with default value

    Returns:
        What the tool returns
    """
    return {"result": f"{required_param}: {optional_param}"}
```

Automatically generates:
- JSON Schema for validation
- OpenAI function calling format
- MCP tool format
- Parameter validation

### Tool Result

All tools return a `ToolResult`:

```python
ToolResult(
    success=True,           # Did it work?
    data={"key": "value"},  # The result data
    error=None,             # Error message if failed
    tool_name="my_tool",    # Which tool produced this
    execution_time_ms=12.5, # How long it took
    metadata={},            # Additional info
)
```

### Registry

Tools are automatically registered:

```python
from agent_tooling import ToolRegistry

# List all tools
for tool in ToolRegistry.list_tools():
    print(f"{tool['name']}: {tool['description']}")

# Get a specific tool
tool = ToolRegistry.get("calculate")
result = tool.run(expression="1 + 1")

# Get schemas for function calling
schemas = ToolRegistry.to_openai_functions()
```

---

## 📊 Visual Modes

### Arena Mode

Compare multiple tools on the same task:

```python
from agent_tooling.visualization import ToolArena

arena = ToolArena()
arena.compare(
    tools=["web_search", "wikipedia_search"],
    query="machine learning"
)
```

### Dashboard

Real-time monitoring of tool activity:

```python
from agent_tooling.visualization import ToolDashboard

dashboard = ToolDashboard()
dashboard.start()  # Live terminal UI
```

### Traces

Step-by-step execution visualization:

```python
from agent_tooling.visualization import ToolTracer

tracer = ToolTracer()
with tracer.trace("my_workflow") as trace:
    trace.add_step("fetch_data", "input", {"url": "..."})
    trace.add_step("process", "process", {"items": 100})
    trace.add_step("save", "output", {"path": "result.json"})
```

---

## 📚 Appendix A: Adding Custom Tools

1. Create a new file in `src/agent_tooling/tools/your_category/`:

```python
from agent_tooling import tool, ToolError

@tool(name="my_custom_tool", category="your_category", mcp_enabled=True)
def my_custom_tool(param1: str, param2: int = 0) -> dict:
    """Description of what this tool does.

    Args:
        param1: First parameter description
        param2: Second parameter with default

    Returns:
        Dictionary with results
    """
    try:
        # Your implementation
        return {"result": f"Processed {param1} with {param2}"}
    except Exception as e:
        raise ToolError(str(e), tool_name="my_custom_tool")
```

2. Import it in the category's `__init__.py`
3. The tool is now available everywhere!

---

## 🔧 Appendix B: Troubleshooting

- **Tool not found**: Ensure the tool module is imported before use
- **MCP connection failed**: Check that the server is running in stdio mode
- **Timeout errors**: Increase timeout parameter for slow operations
- **Permission denied**: Check file/network access permissions

---

## 🧪 Appendix C: Tool Samples (Demo Mode)

Run `agent-tooling --demo` to execute all safe samples interactively. Use flags to include more:

```bash
agent-tooling --demo                  # Safe tools only
agent-tooling --demo --demo-network   # Include network-dependent tools
agent-tooling --demo --demo-ollama    # Include Ollama-dependent tools
agent-tooling --demo --demo-all       # Run everything
agent-tooling --demo-json             # Output results as JSON
```

Below are sample inputs and outputs for each tool category.

### Cognitive Tools

#### `calculate` — Evaluate mathematical expressions

| Sample | Input | Output |
|--------|-------|--------|
| Basic arithmetic | `{"expression": "2 + 2"}` | `{"result": 4, "type": "int"}` |
| Scientific | `{"expression": "sqrt(144) + pow(2, 3)"}` | `{"result": 20.0, "type": "float"}` |
| Trigonometry | `{"expression": "sin(pi / 2)"}` | `{"result": 1.0, "type": "float"}` |

#### `web_search` — Search the web (requires network)

| Sample | Input |
|--------|-------|
| Tech search | `{"query": "Python MCP protocol", "num_results": 3}` |

#### `wikipedia_search` — Wikipedia lookup (requires network)

| Sample | Input |
|--------|-------|
| Science lookup | `{"query": "Large language model", "sentences": 3}` |

### Data Tools

#### `query_database` — Execute SQL queries

| Sample | Input | Output |
|--------|-------|--------|
| Mock SELECT | `{"sql": "SELECT * FROM users LIMIT 5"}` | `{"rows": [{"id": 1, "name": "Example Row 1"}, {"id": 2, "name": "Example Row 2"}], "row_count": 2}` |

#### `call_api` — HTTP API requests (requires network)

| Sample | Input |
|--------|-------|
| Get IP | `{"url": "https://httpbin.org/ip", "method": "GET"}` |

#### `fetch_json` — Fetch JSON data (requires network)

| Sample | Input |
|--------|-------|
| Fetch UUID | `{"url": "https://httpbin.org/uuid"}` |

### Developer Tools

#### `read_file` — Read file contents

| Sample | Input | Output (truncated) |
|--------|-------|--------|
| Read self | `{"path": "src/agent_tooling/tools/developer/filesystem.py"}` | `"""File System Tools - Read, write, and navigate...` |

#### `file_exists` — Check if a path exists

| Sample | Input | Output |
|--------|-------|--------|
| Check README | `{"path": "README.md"}` | `{"exists": true, "is_file": true, "is_dir": false}` |

#### `execute_python` — Execute Python code

| Sample | Input | Output |
|--------|-------|--------|
| Sum range | `{"code": "result = sum(range(1, 101))"}` | `{"return_value": 5050}` |
| List comprehension | `{"code": "result = [x**2 for x in range(10)]"}` | `{"return_value": [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]}` |

#### `get_file_info` — File metadata

| Sample | Input | Output (key fields) |
|--------|-------|--------|
| Info self | `{"path": "src/.../filesystem.py"}` | `{"name": "filesystem.py", "is_file": true, "size_bytes": 18721, "extension": ".py"}` |

#### `search_files` — Search for patterns in files

| Sample | Input | Output |
|--------|-------|--------|
| Search imports | `{"pattern": "from agent_tooling", "include_glob": "*.py", "max_results": 5}` | `[{"file": "tests/test_tools.py", "line": 4, "content": "from agent_tooling import ..."}]` |

### Media Tools

#### `analyze_image` — Vision analysis via Ollama llava (requires Ollama)

| Sample | Input |
|--------|-------|
| Describe URL | `{"source": "https://example.com/photo.png"}` |

#### `pdf_to_markdown` — Convert PDF to markdown

| Sample | Input | Output |
|--------|-------|--------|
| Convert sample | `{"path": "sample.pdf"}` | `"# Agent Tooling - Sample Document\n\n## Introduction\n\nThis is a sample PDF..."` |

#### `summarize_pdf` — Summarize PDF via Ollama (requires Ollama)

| Sample | Input |
|--------|-------|
| Summarize sample | `{"path": "sample.pdf", "max_pages": 1}` |

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## Related Projects

- [agent-reasoning](https://github.com/jasperan/agent-reasoning) - The Reasoning Layer
- [agent-application](https://github.com/jasperan/agent-application) - The Application Layer (coming soon)
- [agent-infrastructure](https://github.com/jasperan/agent-infrastructure) - The Infrastructure Layer (coming soon)

---

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-jasperan-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jasperan)&nbsp;
[![LinkedIn](https://img.shields.io/badge/LinkedIn-jasperan-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jasperan/)

</div>
