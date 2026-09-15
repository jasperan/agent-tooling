package tui

import (
	"time"

	"charm.land/bubbles/v2/cursor"
	tea "charm.land/bubbletea/v2"
)

// cmdTimeout bounds how long drain waits for one command to produce a message.
//
// It is a safety net. Commands that block on a timer -- tea.Tick, tea.Every, the
// cursor blink -- do not return until their timer fires, so calling one
// synchronously stalls for its whole duration; a previous suite hung for an hour
// that way. The primary defence is that tests disable the refresh timer (a
// negative Interval makes tickCmd return nil), and this window covers anything
// else while staying far above the cost of a real in-process command.
const cmdTimeout = 2 * time.Second

// runCmd executes cmd but never blocks for longer than cmdTimeout, so a
// timer-driven command cannot stall the caller.
func runCmd(cmd tea.Cmd) tea.Msg {
	// Buffered so a late result cannot leak the goroutine by blocking on send.
	done := make(chan tea.Msg, 1)
	go func() {
		defer func() {
			// A command can panic when invoked outside the Bubble Tea runtime.
			// That is not a message, so treat it as one that never arrived.
			_ = recover()
		}()
		done <- cmd()
	}()
	select {
	case msg := <-done:
		return msg
	case <-time.After(cmdTimeout):
		return nil
	}
}

// drain runs a command tree to completion so tests can assert on the model as a
// user would see it. Timer-driven commands are skipped rather than waited on.
func drain(m tea.Model, cmd tea.Cmd, depth int) tea.Model {
	if cmd == nil || depth > 64 {
		return m
	}
	msg := runCmd(cmd)
	if msg == nil {
		return m
	}
	if batch, ok := msg.(tea.BatchMsg); ok {
		for _, c := range batch {
			m = drain(m, c, depth+1)
		}
		return m
	}
	// The blink message carries no state; acting on it would only re-arm itself.
	if _, blink := msg.(cursor.BlinkMsg); blink {
		return m
	}
	next, nextCmd := m.Update(msg)
	return drain(next, nextCmd, depth+1)
}
