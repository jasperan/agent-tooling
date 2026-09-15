package ws

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

// testServer mirrors the repository's own /ws handler: a message carrying
// tool_name executes a tool and answers tool_result then done; a plain message
// answers text then done. Replaying that contract is what keeps this client
// honest without needing a live model.
func testServer(t *testing.T) *httptest.Server {
	t.Helper()
	upgrader := websocket.Upgrader{}

	mux := http.NewServeMux()
	mux.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			t.Errorf("upgrade: %v", err)
			return
		}
		defer conn.Close()

		for {
			var msg map[string]any
			if err := conn.ReadJSON(&msg); err != nil {
				return
			}
			switch msg["type"] {
			case "close":
				return
			case "message":
				if name, ok := msg["tool_name"].(string); ok && name != "" {
					params, _ := msg["parameters"].(map[string]any)
					path, _ := params["path"].(string)

					payload := map[string]any{
						"success": true, "data": `{"read": true}`, "error": nil,
						"execution_time_ms": 1.5,
					}
					if path == "" {
						payload = map[string]any{
							"success": false, "data": nil,
							"error":             "Missing required parameter: path",
							"execution_time_ms": 0.0,
						}
					}
					_ = conn.WriteJSON(map[string]any{
						"type":   "tool_result",
						"name":   name,
						"result": payload,
					})
				} else {
					_ = conn.WriteJSON(map[string]any{
						"type":    "text",
						"content": "Received: " + toString(msg["content"]),
					})
				}
				_ = conn.WriteJSON(map[string]any{"type": "done"})
			}
		}
	})

	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	return srv
}

func toString(v any) string {
	s, _ := v.(string)
	return s
}

func dial(t *testing.T, srv *httptest.Server) *Client {
	t.Helper()
	client, err := Dial(context.Background(), srv.URL)
	if err != nil {
		t.Fatalf("Dial: %v", err)
	}
	t.Cleanup(func() { _ = client.Close() })
	return client
}

func TestSessionURLRewritesSchemeAndPath(t *testing.T) {
	cases := []struct{ in, want string }{
		{"http://127.0.0.1:8082", "ws://127.0.0.1:8082/ws"},
		{"https://host", "wss://host/ws"},
		{"http://host:9/", "ws://host:9/ws"},
		{"ws://host:9", "ws://host:9/ws"},
		{"", "ws://127.0.0.1:8082/ws"},
	}
	for _, c := range cases {
		got, err := sessionURL(c.in)
		if err != nil {
			t.Errorf("sessionURL(%q): %v", c.in, err)
			continue
		}
		if got != c.want {
			t.Errorf("sessionURL(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestSessionURLRejectsUnknownScheme(t *testing.T) {
	if _, err := sessionURL("ftp://host"); err == nil {
		t.Fatal("want an error for an unsupported scheme")
	}
}

// TestRunToolCollectsFramesThroughDone checks the client reads the whole
// exchange, not just the first frame.
func TestRunToolCollectsFramesThroughDone(t *testing.T) {
	client := dial(t, testServer(t))

	frames, err := client.RunTool(context.Background(), "read_file", map[string]any{"path": "/tmp/x"})
	if err != nil {
		t.Fatalf("RunTool: %v", err)
	}
	if len(frames) != 2 {
		t.Fatalf("frames = %d, want 2 (tool_result then done)", len(frames))
	}
	if frames[0].Type != "tool_result" {
		t.Errorf("first frame type = %q, want tool_result", frames[0].Type)
	}
	if frames[1].Type != "done" {
		t.Errorf("last frame type = %q, want done", frames[1].Type)
	}

	result := lastResult(frames)
	if result == nil {
		t.Fatal("no result frame")
	}
	if !result.Success {
		t.Errorf("success = false, error = %q", result.ErrorText())
	}
	if result.ExecutionTimeMS != 1.5 {
		t.Errorf("execution_time_ms = %v, want 1.5", result.ExecutionTimeMS)
	}
}

// TestRunToolReportsAFailedTool keeps a tool failure distinct from a broken
// socket: the frame arrives normally and carries success=false.
func TestRunToolReportsAFailedTool(t *testing.T) {
	client := dial(t, testServer(t))

	frames, err := client.RunTool(context.Background(), "read_file", map[string]any{})
	if err != nil {
		t.Fatalf("RunTool: %v", err)
	}
	result := lastResult(frames)
	if result == nil {
		t.Fatal("no result frame")
	}
	if result.Success {
		t.Fatal("a failed tool call must report success=false")
	}
	if !strings.Contains(result.ErrorText(), "Missing required parameter") {
		t.Errorf("error = %q, want the server's message", result.ErrorText())
	}
}

func TestSendReturnsTextAndDone(t *testing.T) {
	client := dial(t, testServer(t))

	frames, err := client.Send(context.Background(), "hello")
	if err != nil {
		t.Fatalf("Send: %v", err)
	}
	if len(frames) != 2 {
		t.Fatalf("frames = %d, want 2", len(frames))
	}
	if frames[0].Type != "text" || frames[0].Content != "Received: hello" {
		t.Errorf("first frame = %+v, want the echoed text", frames[0])
	}
}

// TestCloseUnblocksAPendingRead proves cancellation is honoured: without the
// deadline poke in readUntilDone this would block until the read timeout.
func TestCloseUnblocksAPendingRead(t *testing.T) {
	quiet := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := (&websocket.Upgrader{}).Upgrade(w, r, nil)
		if err != nil {
			return
		}
		// Accept and then say nothing at all.
		defer conn.Close()
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				return
			}
		}
	}))
	t.Cleanup(quiet.Close)

	client, err := Dial(context.Background(), quiet.URL)
	if err != nil {
		t.Fatalf("Dial: %v", err)
	}
	defer func() { _ = client.Close() }()

	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(150 * time.Millisecond)
		cancel()
	}()

	start := time.Now()
	done := make(chan error, 1)
	go func() {
		_, err := client.Send(ctx, "hello")
		done <- err
	}()

	select {
	case err := <-done:
		if !errors.Is(err, context.Canceled) {
			t.Errorf("error = %v, want context.Canceled", err)
		}
		if elapsed := time.Since(start); elapsed > 10*time.Second {
			t.Errorf("cancellation took %s; the read was not unblocked", elapsed)
		}
	case <-time.After(15 * time.Second):
		t.Fatal("Send ignored cancellation; a quiet server hung the caller")
	}
}

func TestDialReportsAnUnreachableServer(t *testing.T) {
	// Port 1 is reserved and never has a listener.
	_, err := Dial(context.Background(), "http://127.0.0.1:1")
	if err == nil {
		t.Fatal("want an error dialling an unreachable server")
	}
	if !strings.Contains(err.Error(), "websocket handshake") {
		t.Errorf("error = %q, want it to name the failed handshake", err)
	}
}

func TestCloseIsSafeOnNil(t *testing.T) {
	var client *Client
	if err := client.Close(); err != nil {
		t.Errorf("Close on nil = %v, want nil", err)
	}
}

func TestFrameDecodesToolCallShape(t *testing.T) {
	// The documented protocol includes a tool_call frame; decoding it must work
	// even though the current server build does not emit one.
	raw := `{"type":"tool_call","name":"read_file","input":{"path":"/tmp/x"}}`
	var frame Frame
	if err := json.Unmarshal([]byte(raw), &frame); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if frame.Type != "tool_call" || frame.Name != "read_file" {
		t.Errorf("frame = %+v", frame)
	}
	if len(frame.Input) == 0 {
		t.Error("input was not captured")
	}
}

// lastResult mirrors the helper the TUI uses, so the test asserts the same thing
// the UI shows.
func lastResult(frames []Frame) *ToolResult {
	for i := len(frames) - 1; i >= 0; i-- {
		if frames[i].Result != nil {
			return frames[i].Result
		}
	}
	return nil
}
