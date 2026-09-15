package repo

import (
	"context"
	"fmt"
	"net"
	"time"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/proc"
)

// ServerModule is the module that hosts the HTTP server.
//
// It is launched as `python -m agent_tooling.server` rather than through the
// installed `agent-tooling-server` console script, because that script calls
// main() directly with its defaults: its argparse block only runs under
// __main__, so `agent-tooling-server --port N` silently ignores --port and binds
// 8082 regardless. Running the module gives a working --port.
const ServerModule = "agent_tooling.server"

// CLIModule hosts the project's CLI, which owns the provider catalogue.
const CLIModule = "agent_tooling.cli"

// DefaultPort is where the server binds when no port is requested.
const DefaultPort = 8082

// Launcher starts and stops the repository's own server.
type Launcher struct {
	root   string
	port   int
	cmd    *proc.BoundedCommand
	exited chan struct{}
}

// NewLauncher prepares a launcher for root on port (0 picks a free port).
func NewLauncher(root string, port int) *Launcher {
	return &Launcher{root: root, port: port, exited: make(chan struct{})}
}

// Port reports the port the server was started on.
func (l *Launcher) Port() int { return l.port }

// URL reports the base URL of the started server.
func (l *Launcher) URL() string { return fmt.Sprintf("http://127.0.0.1:%d", l.port) }

// FreePort asks the kernel for an unused localhost port.
//
// The port is released immediately before Start rebinds it, which is racy in
// principle but is the standard approach and is only used for the convenience
// path; callers who care can pass an explicit --port.
func FreePort() (int, error) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer l.Close()
	addr, ok := l.Addr().(*net.TCPAddr)
	if !ok {
		return 0, fmt.Errorf("unexpected listener address %T", l.Addr())
	}
	return addr.Port, nil
}

// Start launches the server and waits until it answers /health.
//
// The wait matters: a caller that connects immediately would otherwise race the
// server's own startup and report a confusing connection error.
func (l *Launcher) Start(ctx context.Context) error {
	if l.port == 0 {
		port, err := FreePort()
		if err != nil {
			return err
		}
		l.port = port
	}

	argv := append(Python(l.root), "-m", ServerModule, "--host", "127.0.0.1", "--port", fmt.Sprint(l.port))
	cmd, err := proc.Start(l.root, nil, argv...)
	if err != nil {
		return fmt.Errorf("start %s: %w", ServerModule, err)
	}
	l.cmd = cmd

	if err := l.waitReady(ctx); err != nil {
		// Do not leave an orphaned server behind on the failure path.
		_ = l.Stop()
		return err
	}
	return nil
}

// waitReady polls /health until the server answers or the budget runs out.
func (l *Launcher) waitReady(ctx context.Context) error {
	client := api.New(l.URL(), 5*time.Second)
	deadline := time.Now().Add(proc.Starting)

	var lastErr error
	for time.Now().Before(deadline) {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		probeCtx, cancel := context.WithTimeout(ctx, 3*time.Second)
		_, err := client.Health(probeCtx)
		cancel()
		if err == nil {
			return nil
		}
		lastErr = err
		time.Sleep(250 * time.Millisecond)
	}
	return fmt.Errorf("server did not become ready on %s within %s: %w", l.URL(), proc.Starting, lastErr)
}

// Stop shuts the server down, taking its process group with it.
func (l *Launcher) Stop() error {
	if l == nil || l.cmd == nil {
		return nil
	}
	return l.cmd.Stop()
}

// Started reports whether this launcher spawned a server.
func (l *Launcher) Started() bool { return l != nil && l.cmd != nil }
