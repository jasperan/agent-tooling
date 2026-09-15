package tui

import (
	"strings"
	"testing"

	"github.com/jasperan/agent-tooling/gotui/internal/huhstyle"
	"github.com/jasperan/agent-tooling/gotui/internal/repo"
)

func sandboxFixture() repo.Sandbox {
	return repo.Sandbox{Workspace: "local", ToolCount: 23}
}

// TestAccessibleFollowsTheEnvironment pins that ACCESSIBLE is the single switch
// for screen-reader mode.
func TestAccessibleFollowsTheEnvironment(t *testing.T) {
	t.Setenv("ACCESSIBLE", "")
	if huhstyle.Accessible() {
		t.Error("Accessible() = true with an empty ACCESSIBLE")
	}

	t.Setenv("ACCESSIBLE", "1")
	if !huhstyle.Accessible() {
		t.Error("Accessible() = false with ACCESSIBLE=1")
	}
}

// TestFormsBuildInAccessibleMode checks every form still constructs and returns a
// command when the accessible flag is set.
//
// NOTE, measured against huh v2.0.3: WithAccessible is consulted only inside
// Form.RunWithContext, so an *embedded* form renders identically with and without
// it. This test therefore asserts the forms build and initialise, not that the
// embedded UI changes -- claiming more than that would be false. The real
// accessible path is the plain renderer, which main.go selects when ACCESSIBLE is
// set or stdin is not a terminal.
func TestFormsBuildInAccessibleMode(t *testing.T) {
	t.Setenv("ACCESSIBLE", "1")

	filterForm := FilterForm(&Answers{})
	if filterForm == nil {
		t.Fatal("FilterForm returned nil")
	}
	if cmd := filterForm.Init(); cmd == nil {
		t.Error("an accessible filter form produced no init command")
	}

	runForm := RunForm(&Answers{}, "read_file", []repoField{{Name: "path", Type: "string", Required: true}})
	if runForm == nil {
		t.Fatal("RunForm returned nil")
	}
	if cmd := runForm.Init(); cmd == nil {
		t.Error("an accessible run form produced no init command")
	}
}

// TestPlainPathNeedsNoTerminal is the substantive accessibility guarantee: the
// renderers used on the accessible path are pure string builders, so they work
// with no terminal at all and produce no escape sequences.
func TestPlainPathNeedsNoTerminal(t *testing.T) {
	renderers := map[string]string{
		"tools":   PlainTools(sampleToolList()),
		"tool":    PlainTool(sampleToolList().Tools[0], nil),
		"sandbox": PlainSandbox(sandboxFixture()),
	}
	for name, out := range renderers {
		if out == "" {
			t.Errorf("%s renderer produced nothing", name)
			continue
		}
		if strings.Contains(out, "\x1b") {
			t.Errorf("%s renderer emitted ANSI escapes, which a screen reader cannot use: %q", name, out)
		}
	}
}

// TestThemeIsStableAcrossTheDarkFlag records the deliberate single-palette
// choice: the project ships one dark theme, so isDark is ignored.
func TestThemeIsStableAcrossTheDarkFlag(t *testing.T) {
	if huhstyle.Theme(true) == nil || huhstyle.Theme(false) == nil {
		t.Fatal("Theme returned nil for one of the modes")
	}
	// The canonical theme ignores isDark by design, so the two must agree on the
	// values that matter rather than drifting into a light variant.
	dark := huhstyle.Theme(true)
	light := huhstyle.Theme(false)
	if dark.Focused.Title.GetForeground() != light.Focused.Title.GetForeground() {
		t.Error("the theme changed colour with isDark; the project ships one palette")
	}
}
