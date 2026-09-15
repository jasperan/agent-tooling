package tui

import (
	"bytes"
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"charm.land/bubbles/v2/key"
	"charm.land/huh/v2"
	"charm.land/lipgloss/v2"

	"github.com/jasperan/agent-tooling/gotui/internal/huhstyle"
)

// repoField is one parameter of a tool, flattened for form building. It mirrors
// the API's Parameter without importing it, so the form layer stays independent
// of the transport.
type repoField struct {
	Name        string
	Type        string
	Description string
	Required    bool
	Default     any
	Enum        []any
}

// Answers collects what a form produced.
type Answers struct {
	Search string
	// RunTool is the selected tool.
	RunTool string
	// ParamsJSON is the parameter object as text.
	ParamsJSON string
}

// RunParameters decodes the parameters the user typed.
//
// An empty box means "no parameters", which is legitimate for a tool that takes
// none; anything else must be a JSON object.
func (a *Answers) RunParameters() (map[string]any, error) {
	text := strings.TrimSpace(a.ParamsJSON)
	if text == "" {
		return map[string]any{}, nil
	}
	var out map[string]any
	if err := json.Unmarshal([]byte(text), &out); err != nil {
		return nil, fmt.Errorf("parameters must be a JSON object: %w", err)
	}
	return out, nil
}

// formKeyMap is huh's default keymap with esc added to the abort binding.
//
// huh's default binds Quit to ctrl+c alone (huh keymap.go:109), so esc does
// nothing at all and a modal prompt cannot be dismissed the way users expect.
// The other front-ends in this workspace accept that default; this one adds esc
// because the status line tells the user esc cancels, and a hint that lies is
// worse than a small documented deviation.
func formKeyMap() *huh.KeyMap {
	km := huh.NewDefaultKeyMap()
	km.Quit = key.NewBinding(key.WithKeys("esc", "ctrl+c"), key.WithHelp("esc", "cancel"))
	return km
}

// themed applies the project theme, which also carries the accessible flag.
//
// huh.ThemeFunc adapts huhstyle.Theme to huh's Theme interface; the project
// ships one dark palette by design, so the isDark argument is ignored.
func themed(f *huh.Form) *huh.Form {
	return f.
		WithTheme(huh.ThemeFunc(huhstyle.Theme)).
		WithKeyMap(formKeyMap()).
		WithAccessible(huhstyle.Accessible())
}

// FilterForm builds the tool filter prompt.
func FilterForm(ans *Answers) *huh.Form {
	return themed(huh.NewForm(
		huh.NewGroup(
			huh.NewInput().
				Title("Filter tools").
				Description("Matches name, description or category. Submit empty to clear.").
				Placeholder("file").
				Value(&ans.Search),
		),
	))
}

// RunForm builds the run prompt for a tool.
//
// names are the tools that may be run, and current is the one the cursor was on.
//
// The Select is seeded with current. huh falls back to the FIRST option when the
// seeded value is not among the options, which is a silent wrong-tool run, so the
// seed is checked first and the mismatch is reported instead of executed. An
// earlier agent lost real time to exactly this: a seed that did not match made
// the form analyse a completely different input and exit 0.
func RunForm(ans *Answers, current string, fields []repoField) *huh.Form {
	ans.RunTool = current
	ans.ParamsJSON = skeleton(fields)

	groups := []*huh.Group{
		huh.NewGroup(
			huh.NewNote().
				Title("Ready to run "+current).
				Description(describeFields(fields)),
			huh.NewText().
				Title("Parameters (JSON object)").
				Description("Edit the skeleton, or clear it for a no-argument run.").
				Value(&ans.ParamsJSON).
				Validate(validateJSONObject),
		),
	}
	return themed(huh.NewForm(groups...))
}

// skeleton renders a starting parameter object from a tool's fields.
//
// It exists so a required argument cannot be forgotten: the shape is filled in
// and the user replaces the placeholder values.
func skeleton(fields []repoField) string {
	if len(fields) == 0 {
		return "{}"
	}
	// Sorted so the skeleton is stable between runs.
	ordered := append([]repoField(nil), fields...)
	sort.Slice(ordered, func(i, j int) bool { return ordered[i].Name < ordered[j].Name })

	values := map[string]any{}
	for _, f := range ordered {
		switch {
		case len(f.Enum) > 0:
			values[f.Name] = f.Enum[0]
		case f.Default != nil:
			values[f.Name] = f.Default
		default:
			values[f.Name] = placeholderFor(f.Type)
		}
	}
	payload, err := json.MarshalIndent(values, "", "  ")
	if err != nil {
		return "{}"
	}
	return string(payload)
}

// placeholderFor picks an obviously-fake value for a parameter type, so an
// unfilled skeleton is recognisable rather than plausible.
func placeholderFor(kind string) any {
	switch kind {
	case "integer", "number":
		return 0
	case "boolean":
		return false
	case "array":
		return []any{}
	case "object":
		return map[string]any{}
	default:
		return ""
	}
}

// describeFields summarises a tool's parameters for the note above the input.
func describeFields(fields []repoField) string {
	if len(fields) == 0 {
		return "This tool takes no parameters."
	}
	var b strings.Builder
	b.WriteString("Parameters:\n")
	for _, f := range fields {
		req := "optional"
		if f.Required {
			req = "required"
		}
		fmt.Fprintf(&b, "  %s (%s, %s)\n", f.Name, f.Type, req)
	}
	return strings.TrimRight(b.String(), "\n")
}

// validateJSONObject rejects text that is not a JSON object.
//
// huh surfaces the returned error inline, which is the whole point: a malformed
// body never reaches the server as a confusing HTTP 200 with success=false.
func validateJSONObject(value string) error {
	text := strings.TrimSpace(value)
	if text == "" {
		return nil
	}
	var decoded map[string]any
	if err := json.Unmarshal([]byte(text), &decoded); err != nil {
		return fmt.Errorf("must be a JSON object, e.g. {\"path\": \"README.md\"}")
	}
	return nil
}

// lipglossWidth measures rendered text, so layout maths uses display cells and
// not byte length.
func lipglossWidth(s string) int { return lipgloss.Width(s) }

// indentJSON pretty-prints schema bytes for display.
//
// json.Indent writes to a *bytes.Buffer (it needs the byte-oriented API), so the
// result is copied into the caller's builder.
func indentJSON(raw json.RawMessage, out *strings.Builder) error {
	var buf bytes.Buffer
	if err := json.Indent(&buf, raw, "", "  "); err != nil {
		return err
	}
	out.WriteString(buf.String())
	return nil
}

// prettyAny renders a decoded JSON value for display, falling back to a quoted
// string for plain text results.
func prettyAny(value any) string {
	if value == nil {
		return "(no data)"
	}
	if s, ok := value.(string); ok {
		trimmed := strings.TrimSpace(s)
		// Tool results are often JSON held in a string; show it formatted when it
		// parses, and verbatim when it does not.
		var decoded any
		if json.Unmarshal([]byte(trimmed), &decoded) == nil {
			if payload, err := json.MarshalIndent(decoded, "", "  "); err == nil {
				return string(payload)
			}
		}
		return s
	}
	payload, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return fmt.Sprintf("%v", value)
	}
	return string(payload)
}
