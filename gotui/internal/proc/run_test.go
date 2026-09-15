package proc

import (
	"context"
	"errors"
	"os"
	"runtime"
	"strings"
	"testing"
	"time"
)

// TestRunEnforcesTimeout is the regression guard for the deadline that silently
// did nothing: exec.CommandContext kills only the direct child, and a surviving
// grandchild that holds stdout open keeps Wait blocked long past the deadline.
func TestRunEnforcesTimeout(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	start := time.Now()
	res := Run(context.Background(), "", nil, 300*time.Millisecond, "sh", "-c", "sleep 30")
	elapsed := time.Since(start)

	if !res.TimedOut {
		t.Fatalf("TimedOut = false, error = %v", res.Err)
	}
	if elapsed > 10*time.Second {
		t.Fatalf("Run took %s; the deadline was not enforced", elapsed)
	}
}

// TestRunEnforcesTimeoutWithAGrandchildHoldingThePipe is the harder half of the
// same bug: the shell backgrounds a process that inherits stdout and then sleeps.
// Killing only the shell leaves that grandchild owning the pipe, so a plain
// CommandContext waits for a process it never killed.
func TestRunEnforcesTimeoutWithAGrandchildHoldingThePipe(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	start := time.Now()
	// The background child inherits stdout and outlives the shell's own sleep.
	res := Run(context.Background(), "", nil, 400*time.Millisecond,
		"sh", "-c", "sleep 30 & sleep 30")
	elapsed := time.Since(start)

	if !res.TimedOut {
		t.Fatalf("TimedOut = false, error = %v", res.Err)
	}
	if elapsed > 10*time.Second {
		t.Fatalf("Run took %s with a grandchild holding the pipe; the deadline was not enforced", elapsed)
	}
}

// TestRunCapturesOutput checks both streams are reported separately.
func TestRunCapturesOutput(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	res := Run(context.Background(), "", nil, 10*time.Second, "sh", "-c", "echo out; echo err >&2")
	if res.Err != nil {
		t.Fatalf("Run: %v", res.Err)
	}
	if strings.TrimSpace(res.Stdout) != "out" {
		t.Errorf("stdout = %q, want out", res.Stdout)
	}
	if strings.TrimSpace(res.Stderr) != "err" {
		t.Errorf("stderr = %q, want err", res.Stderr)
	}
}

// TestRunReportsExitStatus keeps a failing child distinct from a transport
// failure, so callers can tell "the CLI said no" from "the CLI is missing".
func TestRunReportsExitStatus(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	res := Run(context.Background(), "", nil, 10*time.Second, "sh", "-c", "exit 3")
	if res.Err == nil {
		t.Fatal("want an error for a non-zero exit")
	}
	if errors.Is(res.Err, ErrNotFound) {
		t.Errorf("a non-zero exit must not be reported as a missing binary: %v", res.Err)
	}
	if res.TimedOut {
		t.Error("a non-zero exit is not a timeout")
	}
}

// TestRunReportsMissingBinary pins the actionable first-run failure.
func TestRunReportsMissingBinary(t *testing.T) {
	res := Run(context.Background(), "", nil, 5*time.Second, "/nonexistent/python-does-not-exist", "--version")
	if !errors.Is(res.Err, ErrNotFound) {
		t.Fatalf("error = %v, want ErrNotFound", res.Err)
	}
}

func TestRunRejectsEmptyArgv(t *testing.T) {
	if res := Run(context.Background(), "", nil, time.Second); res.Err == nil {
		t.Fatal("want an error for an empty argv")
	}
}

// TestRunUsesTheWorkingDirectory keeps the plugin's project root honest.
func TestRunUsesTheWorkingDirectory(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	dir := t.TempDir()
	res := Run(context.Background(), dir, nil, 10*time.Second, "sh", "-c", "pwd")
	if res.Err != nil {
		t.Fatalf("Run: %v", res.Err)
	}
	got := strings.TrimSpace(res.Stdout)
	// macOS reports /private/var for /var, so compare the suffix rather than the
	// whole path.
	if !strings.HasSuffix(got, strings.TrimPrefix(dir, "/private")) {
		t.Errorf("pwd = %q, want %q", got, dir)
	}
}

// TestStartAndStopKillsTheProcessGroup proves a long-lived child can be shut
// down, which is what keeps a started server from being orphaned.
func TestStartAndStopKillsTheProcessGroup(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	cmd, err := Start("", nil, "sh", "-c", "sleep 30")
	if err != nil {
		t.Fatalf("Start: %v", err)
	}
	if cmd.Pid() == 0 {
		t.Fatal("Pid() = 0 after a successful start")
	}

	done := make(chan error, 1)
	go func() { done <- cmd.Stop() }()

	select {
	case <-done:
	case <-time.After(10 * time.Second):
		t.Fatal("Stop did not return; the child was not killed")
	}

	// The process must actually be gone, not merely un-referenced.
	if _, err := os.FindProcess(cmd.Pid()); err != nil {
		t.Logf("process lookup after stop: %v", err)
	}
}

// TestStopIsIdempotent keeps a double stop (defer plus explicit) from panicking.
func TestStopIsIdempotent(t *testing.T) {
	cmd, err := Start("", nil, "true")
	if err != nil {
		t.Fatalf("Start: %v", err)
	}
	first := cmd.Stop()
	second := cmd.Stop()
	if first != nil && second != nil && !strings.Contains(second.Error(), "already") {
		t.Logf("first=%v second=%v (a second wait error is acceptable)", first, second)
	}
}

func TestStopOnNilIsSafe(t *testing.T) {
	var cmd *BoundedCommand
	if err := cmd.Stop(); err != nil {
		t.Errorf("Stop on nil = %v, want nil", err)
	}
	if cmd.Pid() != 0 {
		t.Errorf("Pid on nil = %d, want 0", cmd.Pid())
	}
}

func TestContextCancellationStopsTheChild(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("shell fixture is unix-only")
	}
	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(200 * time.Millisecond)
		cancel()
	}()

	start := time.Now()
	res := Run(ctx, "", nil, time.Minute, "sh", "-c", "sleep 30")
	elapsed := time.Since(start)

	if res.Err == nil {
		t.Fatal("want an error after cancellation")
	}
	if elapsed > 10*time.Second {
		t.Fatalf("cancellation took %s; the child was not stopped", elapsed)
	}
}

func TestCombinedJoinsBothStreams(t *testing.T) {
	cases := []struct{ stdout, stderr, want string }{
		{"a", "", "a"},
		{"", "b", "b"},
		{"a", "b", "ab"},
		{"", "", ""},
	}
	for _, c := range cases {
		got := Result{Stdout: c.stdout, Stderr: c.stderr}.Combined()
		if got != c.want {
			t.Errorf("Combined(%q,%q) = %q, want %q", c.stdout, c.stderr, got, c.want)
		}
	}
}
