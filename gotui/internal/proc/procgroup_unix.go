//go:build unix

package proc

import (
	"os/exec"
	"syscall"
)

// setProcessGroup puts the child in its own process group so cancellation can
// take down whatever it spawned.
//
// The Python CLI spawns children of its own (uv, the checkout's interpreter,
// subprocesses inside a tool), and killing only the direct child leaves a
// grandchild holding the inherited stdout pipe open. The copy goroutine then
// never sees EOF, Wait blocks, and the timeout is silently ignored while the UI
// looks frozen.
func setProcessGroup(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
}

// killProcessGroup signals the whole group, which closes inherited pipes
// immediately instead of waiting for grandchildren to exit.
func killProcessGroup(cmd *exec.Cmd) error {
	if cmd.Process == nil {
		return nil
	}
	if err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL); err != nil {
		return cmd.Process.Kill()
	}
	return nil
}
