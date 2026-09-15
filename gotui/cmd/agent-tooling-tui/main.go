// Command agent-tooling-tui is an ADDITIONAL way to run agent-tooling: a Go
// front-end in the charm v2 + huh stack.
//
// It never reimplements tooling. The tool catalogue, its schemas and every
// execution come from the repository's own HTTP server (agent_tooling.server);
// the provider catalogue, the execution workspace and the sandbox flags come
// from the repository's own Python; and a run is driven over the repository's own
// WebSocket session. A Go user and a Python user therefore get identical
// results, and the server is the single place tool semantics live.
//
// Scripted actions (--list, --schema, --run, --providers, --sandbox, --health)
// work with no terminal at all, so this binary is also usable from a pipe, a
// script or CI.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	tea "charm.land/bubbletea/v2"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/huhstyle"
	"github.com/jasperan/agent-tooling/gotui/internal/repo"
	"github.com/jasperan/agent-tooling/gotui/internal/runner"
	"github.com/jasperan/agent-tooling/gotui/internal/tui"
	"github.com/jasperan/agent-tooling/gotui/internal/ws"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "agent-tooling-tui: "+err.Error())
		os.Exit(1)
	}
}

type options struct {
	serverURL   string
	port        int
	startSvc    bool
	projectRoot string

	list      bool
	schemaOf  string
	runTool   string
	params    string
	providers bool
	sandbox   bool
	health    bool
	asJSON    bool
	format    string

	timeout  time.Duration
	interval time.Duration
	noInput  bool
}

func run() error {
	var opts options

	flag.StringVar(&opts.serverURL, "server", "", "server base URL (default "+api.DefaultBaseURL+")")
	flag.IntVar(&opts.port, "port", 0, "port for the server started with --start-service (0 picks a free one)")
	flag.BoolVar(&opts.startSvc, "start-service", false, "start the repository's own server before connecting")
	flag.StringVar(&opts.projectRoot, "project-root", "", "agent-tooling checkout (default: discovered from the working directory)")

	flag.BoolVar(&opts.list, "list", false, "list tools and exit")
	flag.StringVar(&opts.schemaOf, "schema", "", "print one tool's schema and exit")
	flag.StringVar(&opts.runTool, "run", "", "run one tool and exit (see --params)")
	flag.StringVar(&opts.params, "params", "", "JSON object of parameters for --run")
	flag.BoolVar(&opts.providers, "providers", false, "print the provider catalogue and exit")
	flag.BoolVar(&opts.sandbox, "sandbox", false, "print the execution workspace and sandbox flags and exit")
	flag.BoolVar(&opts.health, "health", false, "probe the server and exit")
	flag.BoolVar(&opts.asJSON, "json", false, "emit JSON for --list, --schema and --run")
	flag.StringVar(&opts.format, "format", "openai", "schema format for --schema: openai, mcp or json")

	flag.DurationVar(&opts.timeout, "timeout", 2*time.Minute, "deadline for one delegated run")
	flag.DurationVar(&opts.interval, "interval", tui.DefaultInterval, "live refresh interval (0 disables)")
	flag.BoolVar(&opts.noInput, "no-input", false, "never prompt; fail instead")

	flag.Usage = usage
	flag.Parse()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// A launcher owns the server only when this process started it, so the TUI
	// never shuts down a server someone else is using.
	var launcher *repo.Launcher
	if opts.startSvc {
		root, err := repo.FindRoot(opts.projectRoot)
		if err != nil {
			return err
		}
		launcher = repo.NewLauncher(root, opts.port)
		if err := launcher.Start(ctx); err != nil {
			return err
		}
		defer func() { _ = launcher.Stop() }()
		opts.serverURL = launcher.URL()
	}
	if opts.serverURL == "" {
		opts.serverURL = api.DefaultBaseURL
	}

	client := api.New(opts.serverURL, opts.timeout)

	// Scripted, non-interactive paths. These never open a TUI.
	if handled, err := runScripted(ctx, opts, client); handled {
		return err
	}

	// The full-screen UI needs a terminal and a human; refuse clearly otherwise
	// rather than rendering into a pipe and appearing to hang.
	if !huhstyle.Interactive() {
		return errors.New("stdin is not a terminal: use --list, --schema, --run, --providers or --sandbox")
	}
	if opts.noInput {
		return errors.New("--no-input was set, so no interactive screen was started")
	}

	return runInteractive(ctx, opts, client, launcher)
}

// runScripted executes any action that does not need a terminal.
func runScripted(ctx context.Context, opts options, client *api.Client) (bool, error) {
	switch {
	case opts.health:
		health, err := client.Health(ctx)
		if err != nil {
			return true, fmt.Errorf("server unreachable at %s: %w", client.BaseURL(), err)
		}
		if opts.asJSON {
			return true, printJSON(health)
		}
		fmt.Printf("%s: %s\n", client.BaseURL(), health.Status)
		return true, nil

	case opts.list:
		list, err := client.Tools(ctx)
		if err != nil {
			return true, unreachable(client, err)
		}
		if opts.asJSON {
			out, jerr := tui.PlainToolsJSON(list)
			if jerr != nil {
				return true, jerr
			}
			fmt.Println(out)
			return true, nil
		}
		fmt.Println(tui.PlainTools(list))
		return true, nil

	case opts.schemaOf != "":
		tool, err := client.Tool(ctx, opts.schemaOf)
		if err != nil {
			return true, unreachable(client, err)
		}
		schema, serr := client.Schema(ctx, opts.schemaOf, opts.format)
		if serr != nil {
			// The tool loaded, so report the missing schema without failing.
			fmt.Fprintf(os.Stderr, "note: %v\n", serr)
		}
		if opts.asJSON {
			out, jerr := tui.PlainToolJSON(tool, schema)
			if jerr != nil {
				return true, jerr
			}
			fmt.Println(out)
			return true, nil
		}
		fmt.Println(tui.PlainTool(tool, schema))
		return true, nil

	case opts.runTool != "":
		parameters := map[string]any{}
		if text := strings.TrimSpace(opts.params); text != "" {
			if err := json.Unmarshal([]byte(text), &parameters); err != nil {
				return true, fmt.Errorf("--params must be a JSON object: %w", err)
			}
		}
		// A run goes through the same runner the interactive screen uses, so both
		// paths exercise one code path: the live channel when the server supports
		// it, and the HTTP execute route when it does not.
		run := runner.New(client.BaseURL(), client, opts.timeout)
		frames, err := run.RunTool(ctx, opts.runTool, parameters)
		if err != nil && len(frames) == 0 {
			return true, err
		}
		if opts.asJSON {
			out, jerr := tui.PlainFramesJSON(opts.runTool, frames)
			if jerr != nil {
				return true, jerr
			}
			fmt.Println(out)
		} else {
			fmt.Println(tui.PlainFrames(opts.runTool, frames))
		}
		// Exit non-zero when the tool itself failed, so scripts can branch on it.
		if result := lastFrameResult(frames); result != nil && !result.Success {
			return true, fmt.Errorf("tool %s failed: %s", opts.runTool, result.ErrorText())
		}
		return true, nil

	case opts.providers:
		text, err := project().Providers(ctx)
		if err != nil {
			return true, err
		}
		fmt.Println(text)
		return true, nil

	case opts.sandbox:
		info, err := project().SandboxStatus(ctx)
		if err != nil {
			return true, err
		}
		if opts.asJSON {
			return true, printJSON(info)
		}
		fmt.Println(tui.PlainSandbox(info))
		return true, nil
	}
	return false, nil
}

// runInteractive starts the full-screen UI.
//
// The runner dials lazily rather than up front: the server may have no WebSocket
// support at all, and that must not stop the tool list and schemas -- which come
// over HTTP -- from being usable.
func runInteractive(ctx context.Context, opts options, client *api.Client, launcher *repo.Launcher) error {
	_ = ctx
	run := runner.New(client.BaseURL(), client, opts.timeout)

	model := tui.New(tui.Options{
		BaseURL:    client.BaseURL(),
		Tools:      client,
		Runner:     run,
		Project:    project(),
		Interval:   opts.interval,
		RunTimeout: opts.timeout,
	})

	program := tea.NewProgram(model)
	_ = launcher // ownership is handled by the caller's defer

	if _, err := program.Run(); err != nil {
		return err
	}
	return nil
}

// unreachable turns a transport failure into an actionable message.
func unreachable(client *api.Client, err error) error {
	if api.IsUnreachable(err) {
		return fmt.Errorf("server unreachable at %s: start it with `agent-tooling-tui --start-service` "+
			"or `agent-tooling-server` (cause: %w)", client.BaseURL(), err)
	}
	return err
}

func printJSON(v any) error {
	payload, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	fmt.Println(string(payload))
	return nil
}

// lastFrameResult returns the final tool_result in a run.
func lastFrameResult(frames []ws.Frame) *ws.ToolResult {
	for i := len(frames) - 1; i >= 0; i-- {
		if frames[i].Result != nil {
			return frames[i].Result
		}
	}
	return nil
}

// project adapts the repo package to the TUI's ProjectSource.
type projectSource struct{}

func project() projectSource { return projectSource{} }

func (projectSource) Providers(ctx context.Context) (string, error) {
	return repo.Providers(ctx)
}

func (projectSource) SandboxStatus(ctx context.Context) (repo.Sandbox, error) {
	return repo.SandboxStatus(ctx)
}

func usage() {
	out := flag.CommandLine.Output()
	fmt.Fprintf(out, `agent-tooling-tui — Go terminal front-end for agent-tooling

It delegates to the repository's own server and Python; it implements no tool
logic itself.

Usage:
  agent-tooling-tui [flags]

Interactive:
  agent-tooling-tui                       full-screen UI against %s
  agent-tooling-tui --start-service       start the repository's server first
  agent-tooling-tui --start-service --port 9000

Scripted (no terminal needed):
  agent-tooling-tui --list [--json]
  agent-tooling-tui --schema read_file [--format openai|mcp|json] [--json]
  agent-tooling-tui --run read_file --params '{"path":"README.md"}' [--json]
  agent-tooling-tui --providers
  agent-tooling-tui --sandbox [--json]
  agent-tooling-tui --health

Environment:
  ACCESSIBLE=1   use plain prompts instead of the full-screen UI

Flags:
`, api.DefaultBaseURL)
	flag.PrintDefaults()
}
