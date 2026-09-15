package tui

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/repo"
	"github.com/jasperan/agent-tooling/gotui/internal/ws"
)

// PlainTools renders the tool list without styling.
//
// Every scripted path goes through these renderers instead of the full-screen
// model: stdout may be a pipe, a file or a cron job, where an alt-screen TUI
// would produce nothing useful.
func PlainTools(list api.ToolList) string {
	var b strings.Builder
	lastCategory := ""
	for _, t := range list.Tools {
		if t.Category != lastCategory {
			if lastCategory != "" {
				b.WriteString("\n")
			}
			b.WriteString(strings.ToUpper(t.Category) + "\n")
			lastCategory = t.Category
		}
		mcp := "-"
		if t.MCPEnabled {
			mcp = "mcp"
		}
		fmt.Fprintf(&b, "  %-24s %-4s %s\n", t.Name, mcp, t.Description)
	}
	fmt.Fprintf(&b, "\n%d tools\n", list.Count)
	return strings.TrimRight(b.String(), "\n")
}

// PlainToolsJSON renders the tool list as JSON, for scripts.
func PlainToolsJSON(list api.ToolList) (string, error) {
	return marshalIndent(list)
}

// PlainTool renders one tool's schema as text.
func PlainTool(tool api.Tool, schema json.RawMessage) string {
	var b strings.Builder
	b.WriteString(tool.Name + "\n")
	b.WriteString("  " + tool.Description + "\n")
	fmt.Fprintf(&b, "  category: %s\n  mcp: %t\n", tool.Category, tool.MCPEnabled)

	b.WriteString("\nparameters:\n")
	if len(tool.Parameters) == 0 {
		b.WriteString("  (none)\n")
	}
	for _, p := range tool.Parameters {
		req := "optional"
		if p.Required {
			req = "required"
		}
		fmt.Fprintf(&b, "  %-18s %-8s %s\n", p.Name, p.Type, req)
		if p.Description != "" {
			b.WriteString("      " + p.Description + "\n")
		}
	}

	if len(schema) > 0 {
		var pretty strings.Builder
		if err := indentJSON(schema, &pretty); err == nil {
			b.WriteString("\nschema:\n" + indentLines(pretty.String(), "  ") + "\n")
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// PlainToolJSON renders one tool as JSON.
func PlainToolJSON(tool api.Tool, schema json.RawMessage) (string, error) {
	payload := map[string]any{
		"name":        tool.Name,
		"description": tool.Description,
		"category":    tool.Category,
		"mcp_enabled": tool.MCPEnabled,
		"parameters":  tool.Parameters,
	}
	if len(schema) > 0 {
		var decoded any
		if err := json.Unmarshal(schema, &decoded); err == nil {
			payload["json_schema"] = decoded
		}
	}
	return marshalIndent(payload)
}

// PlainFrames renders a live run's frames and final data as text.
func PlainFrames(tool string, frames []ws.Frame) string {
	var b strings.Builder
	fmt.Fprintf(&b, "run: %s\n", tool)
	for _, f := range frames {
		switch f.Type {
		case "tool_call":
			fmt.Fprintf(&b, "  -> tool_call %s\n", f.Name)
		case "tool_result":
			if f.Result == nil {
				continue
			}
			if f.Result.Success {
				fmt.Fprintf(&b, "  ok  %.2fms\n", f.Result.ExecutionTimeMS)
			} else {
				fmt.Fprintf(&b, "  fail  %s\n", f.Result.ErrorText())
			}
		case "text":
			fmt.Fprintf(&b, "  %s\n", f.Content)
		case "done":
			b.WriteString("  -- done --\n")
		}
	}

	if result := lastResult(frames); result != nil && result.Success {
		var decoded any
		if err := json.Unmarshal(result.Data, &decoded); err == nil {
			if payload, err := json.MarshalIndent(decoded, "", "  "); err == nil {
				b.WriteString("\ndata:\n" + indentLines(string(payload), "  ") + "\n")
			}
		} else {
			b.WriteString("\ndata:\n  " + string(result.Data) + "\n")
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// PlainFramesJSON renders a run as JSON, so a script can assert on the outcome.
func PlainFramesJSON(tool string, frames []ws.Frame) (string, error) {
	payload := map[string]any{
		"tool":   tool,
		"frames": frames,
	}
	if result := lastResult(frames); result != nil {
		payload["success"] = result.Success
		payload["error"] = result.Error
		payload["execution_time_ms"] = result.ExecutionTimeMS
		var decoded any
		if err := json.Unmarshal(result.Data, &decoded); err == nil {
			payload["data"] = decoded
		} else {
			payload["data"] = string(result.Data)
		}
	}
	return marshalIndent(payload)
}

// PlainSandbox renders the workspace and sandbox facts as text.
func PlainSandbox(info repo.Sandbox) string {
	var b strings.Builder
	fmt.Fprintf(&b, "workspace: %s", info.Workspace)
	if info.Unsandboxed() {
		b.WriteString("  (tools run in-process on the host)")
	}
	b.WriteString("\n")
	fmt.Fprintf(&b, "tools: %d\n", info.ToolCount)
	if len(info.SandboxRequired) == 0 {
		b.WriteString("sandbox_required: none\n")
	} else {
		fmt.Fprintf(&b, "sandbox_required: %s\n", strings.Join(info.SandboxRequired, ", "))
	}
	return strings.TrimRight(b.String(), "\n")
}

// marshalIndent renders any payload as indented JSON.
func marshalIndent(v any) (string, error) {
	payload, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", err
	}
	return string(payload), nil
}

// indentLines prefixes every line, to keep nested JSON readable in plain output.
func indentLines(s, prefix string) string {
	lines := strings.Split(strings.TrimRight(s, "\n"), "\n")
	for i, line := range lines {
		lines[i] = prefix + line
	}
	return strings.Join(lines, "\n")
}
