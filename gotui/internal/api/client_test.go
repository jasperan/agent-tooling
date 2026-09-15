package api

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// testServer stands in for the repository's own server, replaying the exact
// payloads captured from a live one so the client is pinned to real shapes.
func testServer(t *testing.T) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, map[string]any{"status": "healthy"})
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		writeJSON(w, map[string]any{"name": "Agent Tooling Server", "version": "0.2.0", "tools_count": 23})
	})
	mux.HandleFunc("/tools", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, map[string]any{
			"tools": []map[string]any{{
				"name":        "read_file",
				"description": "Read the contents of a file.",
				"category":    "developer",
				"mcp_enabled": true,
				"parameters": []map[string]any{
					{"name": "path", "type": "string", "description": "Path to the file to read",
						"required": true, "default": nil, "enum": nil},
					{"name": "encoding", "type": "string", "description": "File encoding (default: utf-8)",
						"required": false, "default": "utf-8", "enum": nil},
				},
			}},
			"count": 23,
		})
	})
	mux.HandleFunc("/tools/read_file", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, map[string]any{
			"name": "read_file", "description": "Read the contents of a file.",
			"category": "developer", "mcp_enabled": true,
			"parameters":  []map[string]any{},
			"json_schema": map[string]any{"type": "object"},
		})
	})
	mux.HandleFunc("/tools/read_file/schema", func(w http.ResponseWriter, r *http.Request) {
		if got := r.URL.Query().Get("format"); got != "openai" {
			t.Errorf("format = %q, want openai", got)
		}
		writeJSON(w, map[string]any{"name": "read_file", "parameters": map[string]any{"type": "object"}})
	})
	mux.HandleFunc("/tools/read_file/execute", func(w http.ResponseWriter, r *http.Request) {
		var req map[string]any
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Errorf("decode request: %v", err)
		}
		if req["name"] != "read_file" {
			t.Errorf("request name = %v, want read_file", req["name"])
		}
		params, _ := req["parameters"].(map[string]any)
		// Note the type assertion: comparing an absent key to "" directly would
		// compare a nil interface to a string and never match.
		path, _ := params["path"].(string)
		if path == "" {
			// A missing required parameter is a 200 with success=false, which is
			// exactly the shape the live server produces.
			writeJSON(w, map[string]any{
				"success": false, "data": nil, "error": "Missing required parameter: path",
				"tool_name": "read_file", "execution_time_ms": 0.0,
			})
			return
		}
		writeJSON(w, map[string]any{
			"success": true, "data": `{"ok": true}`, "error": nil,
			"tool_name": "read_file", "execution_time_ms": 0.21,
		})
	})
	mux.HandleFunc("/categories", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, map[string]any{"categories": []string{"developer", "data", "cognitive", "media"}})
	})
	mux.HandleFunc("/missing", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		writeJSON(w, map[string]any{"detail": "Tool not found: missing"})
	})

	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	return srv
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(v)
}

func TestHealthAndInfo(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)
	ctx := context.Background()

	health, err := client.Health(ctx)
	if err != nil {
		t.Fatalf("Health: %v", err)
	}
	if health.Status != "healthy" {
		t.Errorf("status = %q, want healthy", health.Status)
	}

	info, err := client.Info(ctx)
	if err != nil {
		t.Fatalf("Info: %v", err)
	}
	if info.Name != "Agent Tooling Server" || info.ToolsCount != 23 {
		t.Errorf("info = %+v, want the server's identity and count", info)
	}
}

func TestToolsDecodesParameters(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)

	list, err := client.Tools(context.Background())
	if err != nil {
		t.Fatalf("Tools: %v", err)
	}
	if list.Count != 23 || len(list.Tools) != 1 {
		t.Fatalf("count = %d, tools = %d; want 23 and 1", list.Count, len(list.Tools))
	}

	tool := list.Tools[0]
	if tool.Name != "read_file" || !tool.MCPEnabled || tool.Category != "developer" {
		t.Errorf("tool = %+v, want read_file/developer/mcp", tool)
	}
	if len(tool.Parameters) != 2 {
		t.Fatalf("parameters = %d, want 2", len(tool.Parameters))
	}
	if !tool.Parameters[0].Required {
		t.Error("path should be required")
	}
	// The default must survive as a value, not be dropped as a false-y zero.
	if got, ok := tool.Parameters[1].Default.(string); !ok || got != "utf-8" {
		t.Errorf("encoding default = %v, want utf-8", tool.Parameters[1].Default)
	}
}

func TestSchemaRequestsTheRequestedFormat(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)

	raw, err := client.Schema(context.Background(), "read_file", "openai")
	if err != nil {
		t.Fatalf("Schema: %v", err)
	}
	// Raw bytes must come back unquoted, not as a JSON string containing JSON.
	if strings.HasPrefix(string(raw), `"`) {
		t.Errorf("schema came back quoted: %s", raw)
	}
	var decoded map[string]any
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatalf("schema is not JSON: %v", err)
	}
	if decoded["name"] != "read_file" {
		t.Errorf("schema name = %v", decoded["name"])
	}
}

// TestExecuteSuccess pins the success shape.
func TestExecuteSuccess(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)

	result, err := client.Execute(context.Background(), "read_file", map[string]any{"path": "/tmp/x"})
	if err != nil {
		t.Fatalf("Execute: %v", err)
	}
	if result.Failed() {
		t.Errorf("unexpected failure: %s", result.ErrorText())
	}
	if result.ToolName != "read_file" {
		t.Errorf("tool_name = %q", result.ToolName)
	}
	if result.ExecutionTimeMS <= 0 {
		t.Error("execution_time_ms should be reported")
	}
}

// TestExecuteFailureIsNotATransportError is the important one: the live server
// answers HTTP 200 for a failed tool call, so a client that trusted the status
// code would report a bogus success.
func TestExecuteFailureIsNotATransportError(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)

	result, err := client.Execute(context.Background(), "read_file", map[string]any{})
	if err != nil {
		t.Fatalf("Execute returned a transport error for a tool failure: %v", err)
	}
	if !result.Failed() {
		t.Fatal("a failed tool call must be reported as failed")
	}
	if !strings.Contains(result.ErrorText(), "Missing required parameter") {
		t.Errorf("error = %q, want the server's message", result.ErrorText())
	}
}

// TestNilParametersBecomeAnEmptyObject guards the request body: a nil map would
// marshal as null and the server's model expects an object.
func TestNilParametersBecomeAnEmptyObject(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)
	if _, err := client.Execute(context.Background(), "read_file", nil); err != nil {
		t.Fatalf("Execute with nil parameters: %v", err)
	}
}

func TestHTTPErrorCarriesTheServerDetail(t *testing.T) {
	client := New(testServer(t).URL, 5*time.Second)

	_, err := client.Tool(context.Background(), "missing")
	if err == nil {
		t.Fatal("want an error for a 404")
	}
	if !strings.Contains(err.Error(), "404") {
		t.Errorf("error = %q, want the status code", err)
	}
}

func TestUnreachableServerIsRecognised(t *testing.T) {
	// Port 1 is reserved and never has a listener, so this cannot succeed.
	client := New("http://127.0.0.1:1", 2*time.Second)

	_, err := client.Health(context.Background())
	if err == nil {
		t.Fatal("want an error for an unreachable server")
	}
	if !IsUnreachable(err) {
		t.Errorf("IsUnreachable(%v) = false, want true", err)
	}
}

func TestBaseURLNormalisation(t *testing.T) {
	cases := []struct{ in, want string }{
		{"", DefaultBaseURL},
		{"http://127.0.0.1:8082", "http://127.0.0.1:8082"},
		{"http://127.0.0.1:8082/", "http://127.0.0.1:8082"},
		{"  http://host:9  ", "http://host:9"},
	}
	for _, c := range cases {
		if got := New(c.in, time.Second).BaseURL(); got != c.want {
			t.Errorf("New(%q).BaseURL() = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestIsUnreachableIgnoresRealErrors(t *testing.T) {
	if IsUnreachable(nil) {
		t.Error("nil must not count as unreachable")
	}
	if IsUnreachable(errors.New("boom")) {
		t.Error("a plain error must not count as unreachable")
	}
}
