package tui

import (
	"strings"

	"charm.land/lipgloss/v2"
)

// Design tokens from docs/tui-design-tokens.md. These 14 hex literals are the
// only colours this front-end may use, and scripts/tui-shot/check_palette.py
// enforces that (it scans comments too, so no auxiliary shade is written here).
const (
	hexBG        = "#1e1e2e" // bg
	hexSurface   = "#181825" // surface
	hexElevated  = "#313244" // elevated
	hexHighest   = "#45475a" // highest
	hexText      = "#cdd6f4" // text
	hexSubtext   = "#a6adc8" // subtext
	hexMuted     = "#6c7086" // muted
	hexDim       = "#585b70" // dim
	hexPrimary   = "#89b4fa" // primary
	hexSecondary = "#cba6f7" // secondary
	hexInfo      = "#89dceb" // info
	hexSuccess   = "#a6e3a1" // success
	hexWarning   = "#f9e2af" // warning
	hexError     = "#f38ba8" // error
)

var (
	colText      = lipgloss.Color(hexText)
	colSubtext   = lipgloss.Color(hexSubtext)
	colMuted     = lipgloss.Color(hexMuted)
	colDim       = lipgloss.Color(hexDim)
	colPrimary   = lipgloss.Color(hexPrimary)
	colSecondary = lipgloss.Color(hexSecondary)
	colInfo      = lipgloss.Color(hexInfo)
	colSuccess   = lipgloss.Color(hexSuccess)
	colWarning   = lipgloss.Color(hexWarning)
	colError     = lipgloss.Color(hexError)
	colBG        = lipgloss.Color(hexBG)
	colSurface   = lipgloss.Color(hexSurface)
	colElevated  = lipgloss.Color(hexElevated)
	colHighest   = lipgloss.Color(hexHighest)
)

var (
	styleTitle     = lipgloss.NewStyle().Bold(true).Foreground(colPrimary)
	styleSubtext   = lipgloss.NewStyle().Foreground(colSubtext)
	styleMuted     = lipgloss.NewStyle().Foreground(colMuted)
	styleDim       = lipgloss.NewStyle().Foreground(colDim)
	styleText      = lipgloss.NewStyle().Foreground(colText)
	styleSuccess   = lipgloss.NewStyle().Foreground(colSuccess)
	styleWarning   = lipgloss.NewStyle().Foreground(colWarning)
	styleError     = lipgloss.NewStyle().Foreground(colError)
	styleInfo      = lipgloss.NewStyle().Foreground(colInfo)
	styleSecondary = lipgloss.NewStyle().Foreground(colSecondary)

	// Rounded borders everywhere; focus is a border-colour change, never a
	// thickness change (design rule 2).
	stylePane = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colHighest).
			Padding(0, 1)

	stylePaneFocused = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colPrimary).
				Padding(0, 1)

	// Selection is inverted: accent background with dark text, bold.
	styleSelected = lipgloss.NewStyle().
			Background(colPrimary).
			Foreground(colBG).
			Bold(true)

	styleTabActive = lipgloss.NewStyle().
			Background(colPrimary).
			Foreground(colBG).
			Bold(true).
			Padding(0, 1)

	styleTabIdle = lipgloss.NewStyle().
			Foreground(colSubtext).
			Padding(0, 1)

	styleBadgeOK = lipgloss.NewStyle().
			Background(colElevated).
			Foreground(colSuccess).
			Padding(0, 1)

	styleBadgeOff = lipgloss.NewStyle().
			Background(colElevated).
			Foreground(colMuted).
			Padding(0, 1)

	styleBadgeSandbox = lipgloss.NewStyle().
				Background(colElevated).
				Foreground(colWarning).
				Padding(0, 1)
)

// MinWidth is the narrowest layout the chrome is allowed to shrink to.
//
// Below this the panes would have a negative content width and lipgloss would
// mis-render, so the frame is clamped instead of following the terminal down.
const MinWidth = 6

// pane renders content inside the standard rounded frame, clamped so a very
// narrow terminal cannot produce a negative content width.
func pane(content string, width int, focused bool) string {
	style := stylePane
	if focused {
		style = stylePaneFocused
	}
	return style.Width(clampWidth(width)).Render(content)
}

// clampWidth keeps a pane width at or above the frame's minimum.
func clampWidth(width int) int {
	if width < MinWidth {
		return MinWidth
	}
	return width
}

// tabBar renders the screen tabs, eliding from the right when the terminal is
// too narrow rather than overflowing.
//
// Widths are measured from the rendered tab, not guessed: an earlier version
// summed the label lengths and ignored the padding, which overflowed by exactly
// the padding on every narrow width.
func tabBar(screens []screen, active screen, width int) string {
	var parts []string
	for _, s := range screens {
		style := styleTabIdle
		if s == active {
			style = styleTabActive
		}
		candidate := append(parts, style.Render(s.label()))
		if lipgloss.Width(strings.Join(candidate, " ")) > width {
			break
		}
		parts = candidate
	}
	return strings.Join(parts, " ")
}

// statusLine renders the bottom bar: a mode-aware segment plus a message.
func statusLine(mode, message string, width int) string {
	if width <= 0 {
		return ""
	}
	label := styleTabActive.Render(mode)
	// Below the label's own width nothing can be laid out beside it, so the mode
	// is elided rather than allowed to overflow the terminal.
	if lipgloss.Width(label) > width {
		return truncate(mode, width)
	}
	text := styleMuted.Render(message)

	remaining := width - lipgloss.Width(label) - 1
	if remaining < 1 {
		return label
	}
	if lipgloss.Width(text) > remaining {
		text = truncate(text, remaining)
	}
	return label + " " + text
}

// truncate cuts a string to width cells, appending an ellipsis when it had to.
func truncate(s string, width int) string {
	if width <= 0 {
		return ""
	}
	if lipgloss.Width(s) <= width {
		return s
	}
	if width == 1 {
		return "…"
	}
	// Trim rune by rune so multi-byte characters are never split.
	runes := []rune(s)
	for len(runes) > 0 {
		runes = runes[:len(runes)-1]
		if lipgloss.Width(string(runes))+1 <= width {
			return string(runes) + "…"
		}
	}
	return "…"
}
