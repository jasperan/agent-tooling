package repo

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/jasperan/agent-tooling/gotui/internal/proc"
)

// Providers returns the provider catalogue exactly as the project's own CLI
// prints it.
//
// The CLI renders a Rich table with no JSON form, so the text is passed through
// verbatim rather than parsed or re-derived: a hardcoded list here would go
// stale the moment the CLI changed.
func Providers(ctx context.Context) (string, error) {
	root, err := FindRoot("")
	if err != nil {
		return "", err
	}
	argv := append(Python(root), "-m", CLIModule, "--providers")
	res := proc.Run(ctx, root, nil, time.Minute, argv...)
	if res.TimedOut {
		return "", fmt.Errorf("`%s --providers` timed out", CLIModule)
	}
	if res.Err != nil {
		// The CLI prints "Error: ..." on stdout in some paths, so prefer any
		// captured text over the bare exit status.
		if text := strings.TrimSpace(res.Combined()); text != "" {
			return stripANSI(text), nil
		}
		return "", fmt.Errorf("run `%s --providers`: %w", CLIModule, res.Err)
	}
	return stripANSI(res.Combined()), nil
}

// Sandbox describes where tools actually execute and which of them ask for
// isolation.
//
// The server never exposes this: /tools omits sandbox_required, and the server
// builds its interceptor with the default workspace, so the answer has to come
// from the project's own objects. This is reported as fact only when the
// project's own code produced it; otherwise callers get an error and must not
// guess.
type Sandbox struct {
	// Workspace is the interceptor's workspace type: local, docker or remote.
	Workspace string `json:"workspace"`
	// ToolCount is how many tools the registry holds.
	ToolCount int `json:"tool_count"`
	// SandboxRequired lists tools that declare sandbox_required.
	SandboxRequired []string `json:"sandbox_required"`
}

// Unsandboxed reports whether the default workspace runs tools in-process.
func (s Sandbox) Unsandboxed() bool { return s.Workspace == "local" }

// sandboxProbe asks the project's own registry and interceptor. It reads only
// public API (ToolRegistry.get_all, Workspace.workspace_type) and never mutates
// anything.
const sandboxProbe = `
import json
from agent_tooling.interceptor import ToolingInterceptor
from agent_tooling.tools.registry import ToolRegistry
try:
    from agent_tooling.tools import developer, data, cognitive, media  # noqa: F401
except ImportError:
    pass
interceptor = ToolingInterceptor()
tools = ToolRegistry.get_all()
required = sorted(
    name for name, tool in tools.items()
    if getattr(tool, "sandbox_required", False)
)
print(json.dumps({
    "workspace": interceptor.workspace.workspace_type,
    "tool_count": len(tools),
    "sandbox_required": required,
}))
`

// SandboxStatus runs the probe above against the checkout.
func SandboxStatus(ctx context.Context) (Sandbox, error) {
	root, err := FindRoot("")
	if err != nil {
		return Sandbox{}, err
	}
	argv := append(Python(root), "-c", sandboxProbe)
	res := proc.Run(ctx, root, nil, time.Minute, argv...)
	if res.TimedOut {
		return Sandbox{}, fmt.Errorf("sandbox probe timed out")
	}
	if res.Err != nil {
		return Sandbox{}, fmt.Errorf("run sandbox probe: %w", res.Err)
	}

	// The probe prints exactly one JSON line; anything the interpreter emits
	// before it (warnings) is skipped rather than parsed.
	for _, line := range strings.Split(res.Stdout, "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "{") {
			continue
		}
		var out Sandbox
		if err := json.Unmarshal([]byte(line), &out); err != nil {
			return Sandbox{}, fmt.Errorf("decode sandbox probe: %w", err)
		}
		return out, nil
	}
	return Sandbox{}, fmt.Errorf("sandbox probe produced no JSON: %s", strings.TrimSpace(res.Combined()))
}

// stripANSI removes SGR colour sequences so Rich-formatted output can be shown
// as plain text. Box-drawing characters are kept: they are the table.
func stripANSI(s string) string {
	var b strings.Builder
	esc := false
	for _, r := range s {
		switch {
		case esc:
			if r == 'm' {
				esc = false
			}
		case r == 0x1b:
			esc = true
		default:
			b.WriteRune(r)
		}
	}
	return strings.TrimRight(b.String(), "\n")
}
