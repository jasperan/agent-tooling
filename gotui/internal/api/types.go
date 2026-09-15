// Package api is a thin client for the repository's own HTTP server
// (agent_tooling.server), which is started by `agent-tooling-server`.
//
// Nothing here decides anything about tools: every list, schema and result comes
// from the server so a Go user and a Python user see identical data. The types
// below mirror the server's Pydantic models exactly, and were written against
// live responses captured from a running server.
package api

// Health is the /health response.
//
// The server answers this endpoint only once the tool registry is loaded, so it
// doubles as a readiness probe when the TUI starts the server itself.
type Health struct {
	Status string `json:"status"`
}

// Info is the / response: server identity plus how many tools are registered.
type Info struct {
	Name       string `json:"name"`
	Version    string `json:"version"`
	ToolsCount int    `json:"tools_count"`
}

// Parameter is one entry of a tool's parameters, mirroring ToolParameter in
// tools/base.py.
type Parameter struct {
	Name        string `json:"name"`
	Type        string `json:"type"`
	Description string `json:"description"`
	Required    bool   `json:"required"`
	// Default is absent (null) for most parameters, so it stays untyped.
	Default any `json:"default"`
	// Enum is the allowed-value list, or null when unconstrained.
	Enum []any `json:"enum"`
}

// Tool mirrors a single entry of ToolRegistry.list_tools().
//
// Note the server does NOT expose sandbox_required here, even though BaseTool
// carries it. This client therefore cannot report it from the API and does not
// pretend to; see the Sandbox view in internal/tui.
type Tool struct {
	Name        string      `json:"name"`
	Description string      `json:"description"`
	Category    string      `json:"category"`
	MCPEnabled  bool        `json:"mcp_enabled"`
	Parameters  []Parameter `json:"parameters"`
	// JSONSchema is only present on the /tools/{name} response.
	JSONSchema map[string]any `json:"json_schema,omitempty"`
}

// ToolList is the /tools response.
type ToolList struct {
	Tools []Tool `json:"tools"`
	Count int    `json:"count"`
}

// Categories is the /categories response.
type Categories struct {
	Categories []string `json:"categories"`
}

// ExecuteResult mirrors ToolCallResponse.
//
// The server answers HTTP 200 even when the call failed, so Success -- not the
// status code -- is the field that decides whether anything worked.
type ExecuteResult struct {
	Success         bool    `json:"success"`
	Data            any     `json:"data"`
	Error           *string `json:"error"`
	ToolName        string  `json:"tool_name"`
	ExecutionTimeMS float64 `json:"execution_time_ms"`
}

// Failed reports whether the tool ran but returned a failure.
func (r ExecuteResult) Failed() bool { return !r.Success }

// ErrorText returns the server's error, or "" when the call succeeded.
func (r ExecuteResult) ErrorText() string {
	if r.Error == nil {
		return ""
	}
	return *r.Error
}
