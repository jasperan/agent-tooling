package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// DefaultBaseURL is where the repository's own server binds by default.
const DefaultBaseURL = "http://127.0.0.1:8082"

// Client talks to the Agent Tooling HTTP server.
type Client struct {
	base string
	http *http.Client
}

// New builds a client for baseURL. An empty baseURL uses DefaultBaseURL.
func New(baseURL string, timeout time.Duration) *Client {
	base := strings.TrimRight(strings.TrimSpace(baseURL), "/")
	if base == "" {
		base = DefaultBaseURL
	}
	if timeout <= 0 {
		timeout = DefaultTimeout
	}
	return &Client{base: base, http: &http.Client{Timeout: timeout}}
}

// DefaultTimeout bounds one request. Tool execution happens server-side and the
// server has no deadline of its own, so the client must impose one or a hung
// tool would freeze the UI.
const DefaultTimeout = 60 * time.Second

// BaseURL reports the server this client is pointed at.
func (c *Client) BaseURL() string { return c.base }

// Health probes readiness.
func (c *Client) Health(ctx context.Context) (Health, error) {
	var out Health
	err := c.get(ctx, "/health", &out)
	return out, err
}

// Info reads the server identity and tool count.
func (c *Client) Info(ctx context.Context) (Info, error) {
	var out Info
	err := c.get(ctx, "/", &out)
	return out, err
}

// Tools lists every registered tool.
func (c *Client) Tools(ctx context.Context) (ToolList, error) {
	var out ToolList
	err := c.get(ctx, "/tools", &out)
	return out, err
}

// Tool fetches one tool, including its JSON schema.
func (c *Client) Tool(ctx context.Context, name string) (Tool, error) {
	var out Tool
	err := c.get(ctx, "/tools/"+url.PathEscape(name), &out)
	return out, err
}

// Categories lists the registered tool categories.
func (c *Client) Categories(ctx context.Context) (Categories, error) {
	var out Categories
	err := c.get(ctx, "/categories", &out)
	return out, err
}

// Schema fetches a tool's schema in one of the server's formats: "openai",
// "mcp" or "json". The response shape differs per format, so it comes back raw.
func (c *Client) Schema(ctx context.Context, name, format string) (json.RawMessage, error) {
	if format == "" {
		format = "openai"
	}
	var out json.RawMessage
	err := c.get(ctx, "/tools/"+url.PathEscape(name)+"/schema?format="+url.QueryEscape(format), &out)
	return out, err
}

// Execute runs a tool through POST /tools/{name}/execute.
//
// parameters is marshalled as the request body's "parameters" object. A tool
// that fails still returns HTTP 200 with success=false, which is reported as a
// result rather than a transport error.
func (c *Client) Execute(ctx context.Context, name string, parameters map[string]any) (ExecuteResult, error) {
	if parameters == nil {
		parameters = map[string]any{}
	}
	// The server reads "parameters" from the body; "name" is also required by the
	// model even on the per-tool route, and is harmless there.
	body := map[string]any{"name": name, "parameters": parameters}
	payload, err := json.Marshal(body)
	if err != nil {
		return ExecuteResult{}, fmt.Errorf("encode parameters for %s: %w", name, err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.base+"/tools/"+url.PathEscape(name)+"/execute", bytes.NewReader(payload))
	if err != nil {
		return ExecuteResult{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	var out ExecuteResult
	if err := c.do(req, &out); err != nil {
		return ExecuteResult{}, err
	}
	return out, nil
}

func (c *Client) get(ctx context.Context, path string, out any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.base+path, nil)
	if err != nil {
		return err
	}
	return c.do(req, out)
}

func (c *Client) do(req *http.Request, out any) error {
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		detail, _ := io.ReadAll(io.LimitReader(resp.Body, 400))
		msg := strings.TrimSpace(string(detail))
		if msg == "" {
			msg = http.StatusText(resp.StatusCode)
		}
		return fmt.Errorf("%s %s: HTTP %d: %s", req.Method, req.URL.Path, resp.StatusCode, msg)
	}

	// A schema response is stored as raw JSON, which is already bytes; decoding
	// into json.RawMessage would otherwise re-quote it.
	if raw, ok := out.(*json.RawMessage); ok {
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return err
		}
		*raw = json.RawMessage(body)
		return nil
	}

	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("decode %s: %w", req.URL.Path, err)
	}
	return nil
}

// IsUnreachable reports whether err means the server is not listening, which is
// the common first-run case and deserves its own actionable message.
func IsUnreachable(err error) bool {
	if err == nil {
		return false
	}
	var urlErr *url.Error
	if errors.As(err, &urlErr) {
		return true
	}
	return errors.Is(err, context.DeadlineExceeded)
}
