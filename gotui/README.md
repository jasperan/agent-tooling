# agent-tooling-tui

A Go terminal front-end for `agent-tooling`, built on
[Bubble Tea v2](https://github.com/charmbracelet/bubbletea) with
[huh](https://github.com/charmbracelet/huh) forms.

It is an **additional** delivery surface, not a replacement, and it implements no
tool logic. Everything it shows comes from the project's own components:

| What | Source |
|---|---|
| Tool catalogue, schemas, execution | this project's HTTP server (`agent_tooling.server`) |
| Provider catalogue | this project's CLI (`agent_tooling.cli --providers`) |
| Execution workspace, `sandbox_required` flags | this project's `ToolRegistry` / `ToolingInterceptor` |
| Live run transcript | this project's session channel, falling back to the HTTP execute route |

A Go user and a Python user therefore get identical results.

## Build

```bash
cd gotui && go build ./cmd/agent-tooling-tui
```

Requires Go 1.25+.

## Run

```bash
# Full-screen UI, against a server you started
agent-tooling-server                     # in another shell
./agent-tooling-tui

# Or let the TUI start the server itself
./agent-tooling-tui --start-service
./agent-tooling-tui --start-service --port 9000
```

### Screens

| Screen | Keys |
|---|---|
| **Tools** — grouped by category, `space` expands parameters | `/` filter · `x` run · `enter` schema |
| **Schema** — parameters and the generated OpenAI schema | scroll |
| **Run** — live transcript, result and timing | scroll |
| **Providers** — the project's provider catalogue, verbatim | scroll |
| **Sandbox** — execution workspace and sandbox flags | `r` re-probe |

`tab` / `shift+tab` move between screens, `esc` returns to Tools or cancels an open
form, `q` quits, `?` shows full help.

### Scripted use

No terminal is needed, and each action exits non-zero on failure so it can be used
in a script or CI:

```bash
agent-tooling-tui --list [--json]
agent-tooling-tui --schema read_file [--format openai|mcp|json] [--json]
agent-tooling-tui --run read_file --params '{"path":"README.md"}' [--json]
agent-tooling-tui --providers
agent-tooling-tui --sandbox [--json]
agent-tooling-tui --health
```

`--run` exits 1 when the tool itself fails, with the server's own error message.

### Accessibility

`ACCESSIBLE=1` selects plain prompts and uncoloured output rather than the
full-screen UI. Note that huh v2.0.3 only consults `WithAccessible` inside
`Form.RunWithContext`, so an *embedded* form does not change under that flag; the
plain renderers are the real accessible path and are what this binary uses.

## Design notes

- **The live channel is optional.** The project declares `uvicorn>=0.23.0` rather
  than `uvicorn[standard]`, so without `websockets` or `wsproto` installed the
  server logs *"No supported WebSocket library detected"* and refuses `/ws`. The
  TUI falls back to `POST /tools/{name}/execute` and says so in the transcript,
  instead of implying the run was streamed. Install `uvicorn[standard]` to get the
  live channel.
- **The sandbox screen never guesses.** If the probe against the project's own
  Python fails, the screen reports the failure rather than inventing a workspace.
- **Terminals from 0 to 120 columns** render without panicking and without
  overflowing; the chrome clamps instead of trusting the reported width.
- **Only key presses are acted on.** Bubble Tea v2 also delivers key releases, and
  acting on both would make every binding fire twice.
- Colours come from the workspace design tokens
  (`docs/tui-design-tokens.md`), enforced by `scripts/tui-shot/check_palette.py`.

## Tests

```bash
cd gotui
gofmt -l .                       # must print nothing
go build ./...
go vet ./...
go test -timeout=60s ./...
go test -race -count=1 ./...
```

The suite is hermetic: no server, no Python, no network. Every seam is an
interface, so fakes stand in for the HTTP server, the session channel and the
project's Python.
