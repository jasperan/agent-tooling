package tui

import (
	"strings"
	"testing"

	"charm.land/lipgloss/v2"
)

// TestTabBarNeverExceedsTheTerminal is the regression guard for a real bug in
// this workspace: the bar summed label lengths and ignored the padding, so every
// narrow width overflowed by exactly the padding.
func TestTabBarNeverExceedsTheTerminal(t *testing.T) {
	for width := 0; width <= 120; width++ {
		bar := tabBar(screens, screenTools, width)
		if got := lipgloss.Width(bar); got > width {
			t.Errorf("width %d: bar rendered %d cells: %q", width, got, bar)
		}
	}
}

// TestTabBarAlwaysShowsTheActiveTab checks the elision keeps the informative tab
// rather than trimming to nothing.
func TestTabBarAlwaysShowsTheActiveTab(t *testing.T) {
	for _, width := range []int{40, 60, 100} {
		bar := tabBar(screens, screenRun, width)
		if !strings.Contains(bar, "Run") {
			t.Errorf("width %d: the active tab is missing from %q", width, bar)
		}
	}
}

// TestTabBarElidesFromTheRight checks the tail is what gets dropped.
func TestTabBarElidesFromTheRight(t *testing.T) {
	wide := tabBar(screens, screenTools, 120)
	narrow := tabBar(screens, screenTools, 24)

	if !strings.Contains(wide, "Sandbox") {
		t.Fatalf("a wide bar should show the last tab: %q", wide)
	}
	if strings.Contains(narrow, "Sandbox") {
		t.Errorf("a narrow bar should have dropped the last tab: %q", narrow)
	}
	if !strings.Contains(narrow, "Tools") {
		t.Errorf("a narrow bar must keep the first tab: %q", narrow)
	}
}

func TestStatusLineFitsTheWidth(t *testing.T) {
	for width := 0; width <= 120; width++ {
		line := statusLine("Tools", "23 tools", width)
		if got := lipgloss.Width(line); got > width {
			t.Errorf("width %d: status rendered %d cells", width, got)
		}
	}
}

func TestStatusLineKeepsTheModeLabelWhenTight(t *testing.T) {
	line := statusLine("Sandbox", "a very long message that cannot possibly fit", 8)
	if !strings.Contains(line, "Sandbox") {
		t.Errorf("status line = %q, want the mode preserved", line)
	}
}

func TestTruncateRespectsDisplayWidth(t *testing.T) {
	cases := []struct {
		in    string
		width int
		want  int // maximum cells
	}{
		{"hello", 10, 10},
		{"hello world", 5, 5},
		{"", 4, 4},
		{"hello", 0, 0},
		{"日本語テキスト", 6, 6},
	}
	for _, c := range cases {
		got := truncate(c.in, c.width)
		if w := lipgloss.Width(got); w > c.want {
			t.Errorf("truncate(%q, %d) = %q (%d cells), want <= %d",
				c.in, c.width, got, w, c.want)
		}
	}
}

func TestTruncateAddsAnEllipsisOnlyWhenItCuts(t *testing.T) {
	if got := truncate("short", 20); got != "short" {
		t.Errorf("truncate = %q, want it unchanged", got)
	}
	if got := truncate("a long sentence here", 6); !strings.HasSuffix(got, "…") {
		t.Errorf("truncate = %q, want an ellipsis", got)
	}
}

// TestTruncateNeverSplitsARune keeps multi-byte characters intact.
func TestTruncateNeverSplitsARune(t *testing.T) {
	got := truncate("日本語テキスト", 4)
	for _, r := range got {
		if r == '\uFFFD' {
			t.Fatalf("truncate produced an invalid rune: %q", got)
		}
	}
}

func TestClampWidthKeepsTheFramePossible(t *testing.T) {
	for _, in := range []int{-10, 0, 1, MinWidth - 1} {
		if got := clampWidth(in); got < MinWidth {
			t.Errorf("clampWidth(%d) = %d, want >= %d", in, got, MinWidth)
		}
	}
	if got := clampWidth(200); got != 200 {
		t.Errorf("clampWidth(200) = %d, want it unchanged", got)
	}
}

// TestPaneRendersAFrameAtAnyWidth keeps the negative-content-width crash fixed.
func TestPaneRendersAFrameAtAnyWidth(t *testing.T) {
	for width := -5; width <= 40; width++ {
		func() {
			defer func() {
				if r := recover(); r != nil {
					t.Fatalf("width %d panicked: %v", width, r)
				}
			}()
			if out := pane("content", width, false); out == "" {
				t.Errorf("width %d rendered nothing", width)
			}
		}()
	}
}

func TestFocusedPaneUsesThePrimaryBorder(t *testing.T) {
	// Design rule 2: focus is a border-COLOUR change, not a thickness change.
	// The rendered frame must still be exactly one line of border.
	plain := pane("x", 20, false)
	focused := pane("x", 20, true)

	if lipgloss.Height(plain) != lipgloss.Height(focused) {
		t.Errorf("focus changed the frame height: %d vs %d",
			lipgloss.Height(plain), lipgloss.Height(focused))
	}
	if plain == focused {
		t.Error("the focused pane is visually identical to the unfocused one")
	}
}

func TestClampHeightLimitsLines(t *testing.T) {
	block := "a\nb\nc\nd\ne"
	if got := clampHeight(block, 3); strings.Count(got, "\n") != 2 {
		t.Errorf("clampHeight(_, 3) = %q, want 3 lines", got)
	}
	if got := clampHeight(block, 100); got != block {
		t.Errorf("clampHeight should not change a short block: %q", got)
	}
	if got := clampHeight(block, 0); got != "" {
		t.Errorf("clampHeight(_, 0) = %q, want empty", got)
	}
}

// TestScreenLabelsAreUnique keeps the tab bar unambiguous.
func TestScreenLabelsAreUnique(t *testing.T) {
	seen := map[string]bool{}
	for _, s := range screens {
		label := s.label()
		if label == "" || label == "?" {
			t.Errorf("screen %d has no label", s)
		}
		if seen[label] {
			t.Errorf("duplicate tab label %q", label)
		}
		seen[label] = true
	}
}
