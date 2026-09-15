// Package runner executes one tool against the repository's server.
//
// Two transports reach the same server-side interceptor:
//
//   - the live WebSocket session (WS /ws), which streams frames as they arrive;
//   - the HTTP execute route (POST /tools/{name}/execute), which returns the
//     finished result.
//
// The WebSocket is preferred, but it is not always available: the project
// declares `uvicorn>=0.23.0` rather than `uvicorn[standard]`, so unless
// `websockets` or `wsproto` is installed the server logs "No supported WebSocket
// library detected" and refuses the upgrade with 404. Falling back keeps the
// feature working instead of turning a missing optional dependency into a broken
// front-end.
package runner

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/ws"
)

// Runner runs tools, preferring the live channel.
type Runner struct {
	BaseURL string
	API     *api.Client
	Timeout time.Duration
}

// New builds a runner for a server.
func New(baseURL string, client *api.Client, timeout time.Duration) *Runner {
	return &Runner{BaseURL: baseURL, API: client, Timeout: timeout}
}

// LiveNotice is the frame text shown when the HTTP route had to stand in. It is
// a frame rather than a silent switch so the transcript never implies a live
// stream it did not have.
const LiveNotice = "live channel unavailable (the server has no WebSocket support); used the HTTP execute route"

// RunTool executes one tool and returns the frames to display.
//
// A WebSocket that cannot be dialled or that fails before producing any frame
// falls through to HTTP. A failure that happens after frames have already
// arrived is reported as-is, because the run genuinely started on the live
// channel and retrying it would execute the tool twice.
func (r *Runner) RunTool(ctx context.Context, toolName string, parameters map[string]any) ([]ws.Frame, error) {
	if parameters == nil {
		parameters = map[string]any{}
	}

	live, dialErr := ws.Dial(ctx, r.BaseURL)
	if dialErr == nil {
		frames, err := live.RunTool(ctx, toolName, parameters)
		_ = live.Close()
		if err == nil || len(frames) > 0 {
			return frames, err
		}
		// Nothing arrived, so the tool has not run: falling back is safe.
		return r.viaHTTP(ctx, toolName, parameters, err)
	}
	return r.viaHTTP(ctx, toolName, parameters, dialErr)
}

// viaHTTP runs the tool on the HTTP route and synthesises the frames the UI
// expects, so both transports render identically.
func (r *Runner) viaHTTP(ctx context.Context, toolName string, parameters map[string]any, cause error) ([]ws.Frame, error) {
	if r.API == nil {
		return nil, fmt.Errorf("live channel unavailable (%w) and no HTTP client is configured", cause)
	}

	result, err := r.API.Execute(ctx, toolName, parameters)
	if err != nil {
		return nil, fmt.Errorf("live channel unavailable (%w) and the HTTP execute route also failed: %w", cause, err)
	}

	// Re-encode the value so the frame carries the same JSON shape the live
	// channel would have delivered.
	encoded, marshalErr := json.Marshal(result.Data)
	if marshalErr != nil {
		encoded = nil
	}

	frame := ws.ToolResult{
		Success:         result.Success,
		Data:            encoded,
		Error:           result.Error,
		ExecutionTimeMS: result.ExecutionTimeMS,
	}

	return []ws.Frame{
		{Type: "text", Content: LiveNotice},
		{Type: "tool_result", Name: toolName, Result: &frame},
		{Type: "done"},
	}, nil
}
