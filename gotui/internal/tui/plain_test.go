package tui

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/repo"
	"github.com/jasperan/agent-tooling/gotui/internal/ws"
)

// TestPlainToolsGroupsByCategory keeps the scripted output readable.
func TestPlainToolsGroupsByCategory(t *testing.T) {
	out := PlainTools(sampleToolList())

	for _, want := range []string{"DEVELOPER", "COGNITIVE", "DATA", "read_file", "calculate", "fetch_json", "3 tools"} {
		if !strings.Contains(out, want) {
			t.Errorf("plain tools output is missing %q:\n%s", want, out)
		}
	}
	// No styling may leak into a piped stream.
	if strings.Contains(out, "\x1b") {
		t.Errorf("plain output contains ANSI escapes:\n%q", out)
	}
}

func TestPlainToolsJSONIsParseable(t *testing.T) {
	out, err := PlainToolsJSON(sampleToolList())
	if err != nil {
		t.Fatalf("PlainToolsJSON: %v", err)
	}
	var decoded api.ToolList
	if err := json.Unmarshal([]byte(out), &decoded); err != nil {
		t.Fatalf("output is not valid JSON: %v\n%s", err, out)
	}
	if decoded.Count != 3 || len(decoded.Tools) != 3 {
		t.Errorf("round-trip lost data: count=%d tools=%d", decoded.Count, len(decoded.Tools))
	}
}

func TestPlainToolShowsParametersAndSchema(t *testing.T) {
	tool := sampleToolList().Tools[0]
	out := PlainTool(tool, json.RawMessage(`{"name":"read_file"}`))

	for _, want := range []string{"read_file", "category: developer", "mcp: true", "parameters:", "path", "required", "encoding", "optional", "schema:"} {
		if !strings.Contains(out, want) {
			t.Errorf("plain tool output is missing %q:\n%s", want, out)
		}
	}
}

// TestPlainToolJSONNestsTheSchema checks the schema is embedded as an object, not
// as a JSON string containing JSON.
func TestPlainToolJSONNestsTheSchema(t *testing.T) {
	tool := sampleToolList().Tools[0]
	out, err := PlainToolJSON(tool, json.RawMessage(`{"type":"object"}`))
	if err != nil {
		t.Fatalf("PlainToolJSON: %v", err)
	}
	var decoded map[string]any
	if err := json.Unmarshal([]byte(out), &decoded); err != nil {
		t.Fatalf("output is not JSON: %v", err)
	}
	if _, ok := decoded["json_schema"].(map[string]any); !ok {
		t.Errorf("json_schema = %#v, want an object", decoded["json_schema"])
	}
}

// TestPlainToolWithoutASchemaStillRenders keeps a failed schema route from
// producing an empty screen.
func TestPlainToolWithoutASchemaStillRenders(t *testing.T) {
	out := PlainTool(sampleToolList().Tools[0], nil)
	if !strings.Contains(out, "parameters:") {
		t.Errorf("output lost the parameters:\n%s", out)
	}
	if strings.Contains(out, "schema:") {
		t.Errorf("a missing schema should not print a schema heading:\n%s", out)
	}
}

func TestPlainFramesReportsSuccessAndData(t *testing.T) {
	frames := []ws.Frame{
		{Type: "tool_result", Name: "read_file", Result: &ws.ToolResult{
			Success: true, Data: json.RawMessage(`{"ok":true}`), ExecutionTimeMS: 2.5,
		}},
		{Type: "done"},
	}
	out := PlainFrames("read_file", frames)

	for _, want := range []string{"run: read_file", "ok", "done", "data:", "ok"} {
		if !strings.Contains(out, want) {
			t.Errorf("plain frames output is missing %q:\n%s", want, out)
		}
	}
}

func TestPlainFramesReportsFailure(t *testing.T) {
	reason := "Missing required parameter: path"
	frames := []ws.Frame{
		{Type: "tool_result", Name: "read_file", Result: &ws.ToolResult{Success: false, Error: &reason}},
		{Type: "done"},
	}
	out := PlainFrames("read_file", frames)
	if !strings.Contains(out, "fail") || !strings.Contains(out, reason) {
		t.Errorf("failure not reported:\n%s", out)
	}
}

// TestPlainFramesJSONExposesSuccessForScripts is the contract a CI check needs.
func TestPlainFramesJSONExposesSuccessForScripts(t *testing.T) {
	reason := "boom"
	frames := []ws.Frame{
		{Type: "tool_result", Name: "read_file", Result: &ws.ToolResult{Success: false, Error: &reason}},
		{Type: "done"},
	}
	out, err := PlainFramesJSON("read_file", frames)
	if err != nil {
		t.Fatalf("PlainFramesJSON: %v", err)
	}
	var decoded map[string]any
	if err := json.Unmarshal([]byte(out), &decoded); err != nil {
		t.Fatalf("output is not JSON: %v", err)
	}
	if decoded["success"] != false {
		t.Errorf("success = %v, want false", decoded["success"])
	}
	if decoded["error"] != reason {
		t.Errorf("error = %v, want %q", decoded["error"], reason)
	}
	if decoded["tool"] != "read_file" {
		t.Errorf("tool = %v", decoded["tool"])
	}
}

func TestPlainSandboxReportsTheWorkspace(t *testing.T) {
	out := PlainSandbox(repo.Sandbox{Workspace: "local", ToolCount: 23})
	if !strings.Contains(out, "workspace: local") {
		t.Errorf("output = %q", out)
	}
	if !strings.Contains(out, "in-process") {
		t.Errorf("the unsandboxed case should say so: %q", out)
	}
	if !strings.Contains(out, "sandbox_required: none") {
		t.Errorf("output = %q", out)
	}
}

func TestPlainSandboxListsRequiredTools(t *testing.T) {
	out := PlainSandbox(repo.Sandbox{
		Workspace: "docker", ToolCount: 2, SandboxRequired: []string{"execute_shell"},
	})
	if strings.Contains(out, "in-process") {
		t.Error("an isolated workspace must not be described as in-process")
	}
	if !strings.Contains(out, "execute_shell") {
		t.Errorf("output = %q, want the sandboxed tool named", out)
	}
}

func TestIndentLinesPrefixesEveryLine(t *testing.T) {
	got := indentLines("a\nb", "  ")
	if got != "  a\n  b" {
		t.Errorf("indentLines = %q", got)
	}
}
