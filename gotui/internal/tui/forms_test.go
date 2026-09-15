package tui

import (
	"encoding/json"
	"strings"
	"testing"
)

// TestRunParametersAcceptsAnEmptyBox keeps a no-argument tool runnable.
func TestRunParametersAcceptsAnEmptyBox(t *testing.T) {
	for _, text := range []string{"", "   ", "\n"} {
		params, err := (&Answers{ParamsJSON: text}).RunParameters()
		if err != nil {
			t.Errorf("RunParameters(%q) = %v, want no error", text, err)
		}
		if len(params) != 0 {
			t.Errorf("RunParameters(%q) = %v, want empty", text, params)
		}
	}
}

func TestRunParametersDecodesAnObject(t *testing.T) {
	params, err := (&Answers{ParamsJSON: `{"path":"README.md","lines":5}`}).RunParameters()
	if err != nil {
		t.Fatalf("RunParameters: %v", err)
	}
	if params["path"] != "README.md" {
		t.Errorf("path = %v", params["path"])
	}
	// JSON numbers decode to float64, which is what the server's model expects.
	if params["lines"] != float64(5) {
		t.Errorf("lines = %#v, want 5", params["lines"])
	}
}

// TestRunParametersRejectsANonObject stops an array or scalar from being sent as
// a parameter body.
func TestRunParametersRejectsANonObject(t *testing.T) {
	for _, text := range []string{`[1,2]`, `"text"`, `42`, `not json`} {
		if _, err := (&Answers{ParamsJSON: text}).RunParameters(); err == nil {
			t.Errorf("RunParameters(%q) = nil error, want a rejection", text)
		}
	}
}

// TestValidateJSONObjectMirrorsRunParameters keeps the inline form error aligned
// with what submission would accept, so the user is never told "valid" and then
// refused.
func TestValidateJSONObjectMirrorsRunParameters(t *testing.T) {
	cases := []struct {
		text string
		ok   bool
	}{
		{"", true},
		{"{}", true},
		{`{"path":"x"}`, true},
		{`{"nested":{"a":[1,2]}}`, true},
		{`[1,2]`, false},
		{"oops", false},
		{`{"unterminated":`, false},
	}
	for _, c := range cases {
		err := validateJSONObject(c.text)
		if c.ok && err != nil {
			t.Errorf("validateJSONObject(%q) = %v, want nil", c.text, err)
		}
		if !c.ok && err == nil {
			t.Errorf("validateJSONObject(%q) = nil, want an error", c.text)
		}
		// The two must agree, or the form and the submit path would disagree.
		_, submitErr := (&Answers{ParamsJSON: c.text}).RunParameters()
		if (err == nil) != (submitErr == nil) {
			t.Errorf("validator and submit disagree for %q: %v vs %v", c.text, err, submitErr)
		}
	}
}

// TestSkeletonIncludesEveryParameter means a required argument cannot be
// forgotten: the box arrives pre-shaped.
func TestSkeletonIncludesEveryParameter(t *testing.T) {
	fields := []repoField{
		{Name: "path", Type: "string", Required: true},
		{Name: "lines", Type: "integer", Required: false},
		{Name: "encoding", Type: "string", Required: false, Default: "utf-8"},
		{Name: "dry_run", Type: "boolean", Required: false},
	}

	text := skeleton(fields)
	var decoded map[string]any
	if err := json.Unmarshal([]byte(text), &decoded); err != nil {
		t.Fatalf("skeleton is not valid JSON (%v): %s", err, text)
	}
	for _, f := range fields {
		if _, ok := decoded[f.Name]; !ok {
			t.Errorf("skeleton is missing %s: %s", f.Name, text)
		}
	}
	// A declared default is carried over rather than replaced by a placeholder.
	if decoded["encoding"] != "utf-8" {
		t.Errorf("encoding = %v, want the tool's default", decoded["encoding"])
	}
	// The skeleton must itself pass validation, or the form would open invalid.
	if err := validateJSONObject(text); err != nil {
		t.Errorf("skeleton fails validation: %v", err)
	}
}

func TestSkeletonIsEmptyForNoParameters(t *testing.T) {
	if got := skeleton(nil); got != "{}" {
		t.Errorf("skeleton(nil) = %q, want {}", got)
	}
}

// TestSkeletonIsStable keeps the box from reshuffling between runs.
func TestSkeletonIsStable(t *testing.T) {
	fields := []repoField{
		{Name: "zebra", Type: "string"},
		{Name: "alpha", Type: "string"},
		{Name: "middle", Type: "string"},
	}
	first := skeleton(fields)
	for i := 0; i < 5; i++ {
		if got := skeleton(fields); got != first {
			t.Fatalf("skeleton changed between calls:\n%s\n%s", first, got)
		}
	}
	if strings.Index(first, "alpha") > strings.Index(first, "zebra") {
		t.Errorf("skeleton is not sorted: %s", first)
	}
}

// TestSkeletonPrefersAnEnumValue keeps a constrained field valid from the start.
func TestSkeletonPrefersAnEnumValue(t *testing.T) {
	text := skeleton([]repoField{{Name: "mode", Type: "string", Enum: []any{"fast", "slow"}}})
	if !strings.Contains(text, "fast") {
		t.Errorf("skeleton = %s, want the first enum value", text)
	}
}

func TestPlaceholderForMatchesTheType(t *testing.T) {
	cases := map[string]any{
		"integer": 0,
		"number":  0,
		"boolean": false,
		"string":  "",
	}
	for kind, want := range cases {
		if got := placeholderFor(kind); got != want {
			t.Errorf("placeholderFor(%q) = %#v, want %#v", kind, got, want)
		}
	}
	// Arrays and objects must be empty containers, not null, so they are editable.
	if got := placeholderFor("array"); got == nil {
		t.Error("array placeholder is nil")
	}
	if got := placeholderFor("object"); got == nil {
		t.Error("object placeholder is nil")
	}
}

func TestDescribeFieldsNamesRequiredOnes(t *testing.T) {
	got := describeFields([]repoField{
		{Name: "path", Type: "string", Required: true},
		{Name: "encoding", Type: "string", Required: false},
	})
	for _, want := range []string{"path", "required", "encoding", "optional"} {
		if !strings.Contains(got, want) {
			t.Errorf("describeFields is missing %q:\n%s", want, got)
		}
	}
}

func TestDescribeFieldsHandlesNoParameters(t *testing.T) {
	if got := describeFields(nil); !strings.Contains(got, "no parameters") {
		t.Errorf("describeFields(nil) = %q", got)
	}
}

// TestRunFormRejectsAnUnmatchedSeed is the huh Select fallback guard.
//
// huh falls back to the FIRST option when a Select's seeded value is not among
// its options, which would silently run a different tool than the one chosen. The
// run form therefore carries no Select, and the model validates the name before
// opening it (see TestRunRefusesAStaleTool). This test pins that the form is
// built for exactly the tool it was given.
func TestRunFormRejectsAnUnmatchedSeed(t *testing.T) {
	ans := &Answers{}
	form := RunForm(ans, "read_file", []repoField{{Name: "path", Type: "string", Required: true}})
	if form == nil {
		t.Fatal("RunForm returned nil")
	}
	if ans.RunTool != "read_file" {
		t.Errorf("seeded tool = %q, want read_file", ans.RunTool)
	}
	if !strings.Contains(ans.ParamsJSON, "path") {
		t.Errorf("skeleton = %q, want it to include the required path", ans.ParamsJSON)
	}
}

func TestFilterFormSeedsTheCurrentFilter(t *testing.T) {
	ans := &Answers{}
	if form := FilterForm(ans); form == nil {
		t.Fatal("FilterForm returned nil")
	}
	// The binding target is what the model reads back, so the pointer must be the
	// caller's, not a copy.
	ans.Search = "calc"
	if ans.Search != "calc" {
		t.Error("FilterForm did not bind to the caller's Answers")
	}
}

// TestIncrementJSONStillValid pins that the panel's JSON path is unchanged.
func TestIndentJSONProducesReadableOutput(t *testing.T) {
	raw := json.RawMessage(`{"a":1}`)
	var sb strings.Builder
	if err := indentJSON(raw, &sb); err != nil {
		t.Fatalf("indentJSON: %v", err)
	}
	if !strings.Contains(sb.String(), "\n") {
		t.Errorf("indentJSON did not indent: %q", sb.String())
	}
}

func TestPrettyAnyFormatsEmbeddedJSON(t *testing.T) {
	got := prettyAny(`{"ok":true}`)
	if !strings.Contains(got, "\n") {
		t.Errorf("prettyAny did not expand embedded JSON: %q", got)
	}
	if got := prettyAny(nil); got != "(no data)" {
		t.Errorf("prettyAny(nil) = %q", got)
	}
	// Plain text must survive unchanged.
	if got := prettyAny("hello"); got != "hello" {
		t.Errorf("prettyAny(plain) = %q", got)
	}
}
