// Package proc runs bounded subprocesses for the repository's own Python CLI.
//
// Every child is bounded three ways: a context deadline, a signal to the whole
// process group, and WaitDelay for the pipes. Any one of them alone is not
// enough -- see procgroup_unix.go for why the group matters.
package proc

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// PipeGrace bounds how long Wait keeps draining pipes after the process is gone.
//
// Without it a surviving grandchild that still holds stdout open keeps Wait
// blocked for as long as that grandchild lives, which is the exact case the
// deadline exists to prevent.
const PipeGrace = 5 * time.Second

// Result is the outcome of one bounded run.
type Result struct {
	Stdout   string
	Stderr   string
	Err      error
	TimedOut bool
}

// Combined is stdout followed by stderr, for display.
func (r Result) Combined() string {
	switch {
	case r.Stderr == "":
		return r.Stdout
	case r.Stdout == "":
		return r.Stderr
	default:
		return r.Stdout + r.Stderr
	}
}

// ErrNotFound marks a binary that is not on PATH, which is actionable: the user
// needs to install or sync the project rather than retry.
var ErrNotFound = errors.New("executable not found")

// Run executes argv, bounded by timeout (0 means the default), and returns its
// output. A non-zero exit is reported through Result.Err, never as a panic.
func Run(ctx context.Context, dir string, env []string, timeout time.Duration, argv ...string) Result {
	if len(argv) == 0 {
		return Result{Err: errors.New("empty argv")}
	}
	if timeout <= 0 {
		timeout = DefaultTimeout
	}

	runCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(runCtx, argv[0], argv[1:]...)
	if dir != "" {
		cmd.Dir = dir
	}
	if env != nil {
		cmd.Env = env
	}

	// Group + Cancel + WaitDelay together are what actually enforce the deadline.
	setProcessGroup(cmd)
	cmd.Cancel = func() error { return killProcessGroup(cmd) }
	cmd.WaitDelay = PipeGrace

	var out, errBuf strings.Builder
	cmd.Stdout = &out
	cmd.Stderr = &errBuf

	err := cmd.Run()
	res := Result{Stdout: out.String(), Stderr: errBuf.String(), Err: err}

	if runCtx.Err() == context.DeadlineExceeded {
		res.TimedOut = true
		res.Err = fmt.Errorf("timed out after %s", timeout)
		return res
	}
	if err != nil {
		if _, lookErr := exec.LookPath(argv[0]); lookErr != nil {
			res.Err = fmt.Errorf("%w: %s", ErrNotFound, argv[0])
		}
	}
	return res
}

// DefaultTimeout bounds a delegated CLI call.
const DefaultTimeout = 2 * time.Minute

// Starting bounds how long a service is given to become ready.
const Starting = 30 * time.Second

// BoundedCommand is a long-lived child (a server) that must be stoppable.
type BoundedCommand struct {
	cmd *exec.Cmd
	mu  sync.Mutex
}

// Start launches argv in its own process group so Stop can take the whole tree
// down, including any worker processes the server forks.
func Start(dir string, env []string, argv ...string) (*BoundedCommand, error) {
	if len(argv) == 0 {
		return nil, errors.New("empty argv")
	}
	cmd := exec.Command(argv[0], argv[1:]...)
	if dir != "" {
		cmd.Dir = dir
	}
	if env != nil {
		cmd.Env = env
	}
	setProcessGroup(cmd)

	if err := cmd.Start(); err != nil {
		if _, lookErr := exec.LookPath(argv[0]); lookErr != nil {
			return nil, fmt.Errorf("%w: %s", ErrNotFound, argv[0])
		}
		return nil, err
	}
	return &BoundedCommand{cmd: cmd}, nil
}

// Stop terminates the whole process group and reaps the child.
func (b *BoundedCommand) Stop() error {
	if b == nil || b.cmd == nil {
		return nil
	}
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.cmd.Process == nil {
		return nil
	}
	// Signal the group first so children die with the parent.
	killErr := killProcessGroup(b.cmd)
	// Wait reaps the zombie; WaitDelay keeps it from hanging on open pipes.
	waitErr := b.cmd.Wait()
	if killErr != nil && waitErr != nil {
		return waitErr
	}
	return nil
}

// Pid reports the child's pid, or 0 when it never started.
func (b *BoundedCommand) Pid() int {
	if b == nil || b.cmd == nil || b.cmd.Process == nil {
		return 0
	}
	return b.cmd.Process.Pid
}
