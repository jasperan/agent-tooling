// Package ws drives the repository's real-time session endpoint (WS /ws).
//
// It exists because the HTTP execute route only returns a finished result. The
// WebSocket route is the repository's own live channel, so the TUI can show
// frames as they arrive instead of a single reply, which is why the Run view
// uses it.
package ws

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// Frame is one server event.
//
// The server emits four types. ToolCall is part of the documented protocol even
// though the current server build only sends tool_result and done for a tool
// call; it is handled so an agent-backed session would already render.
type Frame struct {
	Type    string          `json:"type"`
	Content string          `json:"content,omitempty"`
	Name    string          `json:"name,omitempty"`
	Input   json.RawMessage `json:"input,omitempty"`
	Result  *ToolResult     `json:"result,omitempty"`
}

// ToolResult is the payload of a tool_result frame.
type ToolResult struct {
	Success         bool            `json:"success"`
	Data            json.RawMessage `json:"data"`
	Error           *string         `json:"error"`
	ExecutionTimeMS float64         `json:"execution_time_ms"`
}

// ErrorText returns the failure message, or "" on success.
func (r *ToolResult) ErrorText() string {
	if r == nil || r.Error == nil {
		return ""
	}
	return *r.Error
}

// DialTimeout bounds the handshake, and ReadTimeout bounds the wait for the next
// frame, so a server that accepts the socket and then goes quiet cannot hang the
// UI. A tool genuinely runs server-side here, so ReadTimeout is generous.
const (
	DialTimeout = 10 * time.Second
	ReadTimeout = 5 * time.Minute
)

// Client is one WebSocket session.
type Client struct {
	conn *websocket.Conn
}

// Dial opens a session against a base URL such as http://127.0.0.1:8082,
// rewriting the scheme to ws/wss.
func Dial(ctx context.Context, baseURL string) (*Client, error) {
	u, err := sessionURL(baseURL)
	if err != nil {
		return nil, err
	}

	dialer := websocket.Dialer{HandshakeTimeout: DialTimeout}
	conn, resp, err := dialer.DialContext(ctx, u, nil)
	if err != nil {
		if resp != nil {
			return nil, fmt.Errorf("websocket handshake to %s: HTTP %d: %w", u, resp.StatusCode, err)
		}
		return nil, fmt.Errorf("websocket handshake to %s: %w", u, err)
	}
	return &Client{conn: conn}, nil
}

// sessionURL converts an HTTP base URL into the /ws endpoint.
func sessionURL(baseURL string) (string, error) {
	base := strings.TrimSpace(baseURL)
	if base == "" {
		base = "http://127.0.0.1:8082"
	}
	u, err := url.Parse(base)
	if err != nil {
		return "", fmt.Errorf("parse server URL %q: %w", base, err)
	}
	switch u.Scheme {
	case "http":
		u.Scheme = "ws"
	case "https":
		u.Scheme = "wss"
	case "ws", "wss":
		// already a websocket URL
	default:
		return "", fmt.Errorf("unsupported server scheme %q", u.Scheme)
	}
	u.Path = strings.TrimRight(u.Path, "/") + "/ws"
	return u.String(), nil
}

// Close ends the session, telling the server first so it can close cleanly.
//
// The close message is best-effort: if the socket is already gone there is
// nothing to clean up, and reporting that as an error would be noise.
func (c *Client) Close() error {
	if c == nil || c.conn == nil {
		return nil
	}
	_ = c.conn.WriteJSON(map[string]any{"type": "close"})
	return c.conn.Close()
}

// RunTool executes one tool on the live channel and returns every frame the
// server sends up to and including done.
//
// The final frame carries the outcome; the caller renders the whole slice so the
// view shows the exchange, not just its end state.
func (c *Client) RunTool(ctx context.Context, toolName string, parameters map[string]any) ([]Frame, error) {
	if parameters == nil {
		parameters = map[string]any{}
	}
	// The server branches on tool_name being present: with it, it executes the
	// tool; without it, it merely echoes the text back.
	request := map[string]any{
		"type":       "message",
		"content":    "",
		"tool_name":  toolName,
		"parameters": parameters,
	}
	if err := c.conn.WriteJSON(request); err != nil {
		return nil, fmt.Errorf("send tool call for %s: %w", toolName, err)
	}
	return c.readUntilDone(ctx)
}

// Send delivers a plain chat message and returns the frames it produces.
func (c *Client) Send(ctx context.Context, content string) ([]Frame, error) {
	if err := c.conn.WriteJSON(map[string]any{"type": "message", "content": content}); err != nil {
		return nil, fmt.Errorf("send message: %w", err)
	}
	return c.readUntilDone(ctx)
}

// readUntilDone collects frames until the server says it is done.
func (c *Client) readUntilDone(ctx context.Context) ([]Frame, error) {
	// A deadline is applied per read; the caller's context still cancels first.
	_ = c.conn.SetReadDeadline(time.Now().Add(ReadTimeout))

	stop := make(chan struct{})
	defer close(stop)
	go func() {
		select {
		case <-ctx.Done():
			// Unblock a pending read so cancellation is honoured promptly.
			_ = c.conn.SetReadDeadline(time.Now())
		case <-stop:
		}
	}()

	var frames []Frame
	for {
		var frame Frame
		if err := c.conn.ReadJSON(&frame); err != nil {
			if ctx.Err() != nil {
				return frames, ctx.Err()
			}
			return frames, fmt.Errorf("read frame: %w", err)
		}
		frames = append(frames, frame)
		if frame.Type == "done" {
			return frames, nil
		}
	}
}
