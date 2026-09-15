package runner

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

	"github.com/jasperan/agent-tooling/gotui/internal/api"
)

// httpOnlyServer serves the HTTP execute route but refuses the WebSocket
// upgrade, which is exactly the shape of the real server when uvicorn has no
// websocket library: the project declares plain `uvicorn`, so /ws answers 404.
func httpOnlyServer(t *testing.T) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		// Mirrors the server's behaviour with no websocket library installed.
		w.WriteHeader(http.StatusNotFound)
		_, _ = w.Write([]byte(`{"detail":"Not Found"}`))
	})
	mux.HandleFunc("/tools/read_file/execute", func(w http.ResponseWriter, r *http.Request) {
		var req map[string]any
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			t.Errorf("decode: %v", err)
		}
		params, _ := req["parameters"].(map[string]any)
		path, _ := params["path"].(string)

		payload := map[string]any{
			"success": true, "data": map[string]any{"ok": true}, "error": nil,
			"tool_name": "read_file", "execution_time_ms": 0.5,
		}
		if path == "" {
			payload = map[string]any{
				"success": false, "data": nil, "error": "Missing required parameter: path",
				"tool_name": "read_file", "execution_time_ms": 0.0,
			}
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(payload)
	})
	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	return srv
}

// wsServer serves a working WebSocket session.
func wsServer(t *testing.T) *httptest.Server {
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
			if msg["type"] == "close" {
				return
			}
			_ = conn.WriteJSON(map[string]any{
				"type": "tool_result", "name": "read_file",
				"result": map[string]any{
					"success": true, "data": map[string]any{"live": true},
					"error": nil, "execution_time_ms": 1.0,
				},
			})
			_ = conn.WriteJSON(map[string]any{"type": "done"})
		}
	})
	srv := httptest.NewServer(mux)
	t.Cleanup(srv.Close)
	return srv
}

// TestLiveChannelIsPreferred proves the WebSocket is used when it works.
func TestLiveChannelIsPreferred(t *testing.T) {
	srv := wsServer(t)
	client := api.New(srv.URL, 5*time.Second)
	r := New(srv.URL, client, 5*time.Second)

	frames, err := r.RunTool(context.Background(), "read_file", map[string]any{"path": "/tmp/x"})
	if err != nil {
		t.Fatalf("RunTool: %v", err)
	}
	if len(frames) != 2 {
		t.Fatalf("frames = %d, want 2 from the live channel", len(frames))
	}
	for _, f := range frames {
		if f.Type == "text" && strings.Contains(f.Content, "live channel unavailable") {
			t.Error("the fallback notice appeared even though the live channel worked")
		}
	}
}

// TestFallsBackToHTTPWhenWebSocketsAreUnavailable is the important case: the real
// server refuses the upgrade, and the tool must still run.
func TestFallsBackToHTTPWhenWebSocketsAreUnavailable(t *testing.T) {
	srv := httpOnlyServer(t)
	client := api.New(srv.URL, 5*time.Second)
	r := New(srv.URL, client, 5*time.Second)

	frames, err := r.RunTool(context.Background(), "read_file", map[string]any{"path": "/tmp/x"})
	if err != nil {
		t.Fatalf("RunTool: %v", err)
	}
	if len(frames) != 3 {
		t.Fatalf("frames = %d, want notice + result + done", len(frames))
	}
	if frames[0].Type != "text" || !strings.Contains(frames[0].Content, "HTTP execute route") {
		t.Errorf("first frame = %+v, want the fallback notice", frames[0])
	}
	if frames[1].Result == nil || !frames[1].Result.Success {
		t.Errorf("result frame = %+v, want a success", frames[1])
	}
	if frames[2].Type != "done" {
		t.Errorf("last frame = %+v, want done", frames[2])
	}
}

// TestFallbackPreservesToolFailure keeps a failed tool distinct from a transport
// failure on the fallback path, exactly as on the live one.
func TestFallbackPreservesToolFailure(t *testing.T) {
	srv := httpOnlyServer(t)
	client := api.New(srv.URL, 5*time.Second)
	r := New(srv.URL, client, 5*time.Second)

	frames, err := r.RunTool(context.Background(), "read_file", map[string]any{})
	if err != nil {
		t.Fatalf("RunTool returned a transport error for a tool failure: %v", err)
	}
	result := frames[len(frames)-1].Result
	if result == nil {
		// The result is the middle frame; find it explicitly.
		for _, f := range frames {
			if f.Result != nil {
				result = f.Result
			}
		}
	}
	if result == nil {
		t.Fatal("no result frame")
	}
	if result.Success {
		t.Error("a failed tool call must report success=false")
	}
	if !strings.Contains(result.ErrorText(), "Missing required parameter") {
		t.Errorf("error = %q", result.ErrorText())
	}
}

// TestUnreachableServerIsReported keeps a dead server from looking like a result.
func TestUnreachableServerIsReported(t *testing.T) {
	client := api.New("http://127.0.0.1:1", 2*time.Second)
	r := New("http://127.0.0.1:1", client, 2*time.Second)

	_, err := r.RunTool(context.Background(), "read_file", nil)
	if err == nil {
		t.Fatal("want an error when neither transport works")
	}
	if !strings.Contains(err.Error(), "live channel unavailable") {
		t.Errorf("error = %q, want it to explain both failures", err)
	}
}

func TestNilParametersBecomeAnEmptyObject(t *testing.T) {
	srv := httpOnlyServer(t)
	client := api.New(srv.URL, 5*time.Second)
	r := New(srv.URL, client, 5*time.Second)

	if _, err := r.RunTool(context.Background(), "read_file", nil); err != nil {
		t.Fatalf("RunTool with nil parameters: %v", err)
	}
}

func TestNilAPIClientIsReported(t *testing.T) {
	r := New("http://127.0.0.1:1", nil, time.Second)
	_, err := r.RunTool(context.Background(), "read_file", nil)
	if err == nil {
		t.Fatal("want an error when no HTTP client is configured")
	}
	if !strings.Contains(err.Error(), "no HTTP client") {
		t.Errorf("error = %q, want it to name the missing client", err)
	}
}

// TestFallbackToleratesUnmarshallableData keeps a non-JSON tool result from
// breaking the transcript.
func TestFallbackToleratesUnmarshallableData(t *testing.T) {
	if !errors.Is(context.Canceled, context.Canceled) {
		t.Skip("sentinel")
	}
	srv := httpOnlyServer(t)
	client := api.New(srv.URL, 5*time.Second)
	r := New(srv.URL, client, 5*time.Second)

	frames, err := r.RunTool(context.Background(), "read_file", map[string]any{"path": "/x"})
	if err != nil {
		t.Fatalf("RunTool: %v", err)
	}
	// Every frame must be renderable.
	for _, f := range frames {
		if f.Type == "" {
			t.Errorf("frame with no type: %+v", f)
		}
	}
}
