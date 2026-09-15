package tui

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/repo"
	"github.com/jasperan/agent-tooling/gotui/internal/ws"
)

// --- fakes -------------------------------------------------------------------
//
// The suite is hermetic on purpose: no server, no Python, no network. Every seam
// the UI reaches is an interface, so a fake can stand in for each.

type fakeTools struct {
	info   api.Info
	list   api.ToolList
	tool   api.Tool
	schema json.RawMessage
	err    error
	// detailErr fails only the per-tool calls, which is how a schema route can
	// fail while the list still works.
	detailErr error
	calls     int
}

func (f *fakeTools) Info(context.Context) (api.Info, error) { return f.info, f.err }

func (f *fakeTools) Tools(context.Context) (api.ToolList, error) {
	f.calls++
	return f.list, f.err
}

func (f *fakeTools) Tool(context.Context, string) (api.Tool, error) {
	if f.detailErr != nil {
		return api.Tool{}, f.detailErr
	}
	return f.tool, f.err
}

func (f *fakeTools) Schema(context.Context, string, string) (json.RawMessage, error) {
	if f.detailErr != nil {
		return nil, f.detailErr
	}
	return f.schema, nil
}

func (f *fakeTools) Categories(context.Context) (api.Categories, error) {
	return api.Categories{}, nil
}

type fakeRunner struct {
	frames []ws.Frame
	err    error
	calls  int
	tool   string
	params map[string]any
}

func (f *fakeRunner) RunTool(_ context.Context, tool string, params map[string]any) ([]ws.Frame, error) {
	f.calls++
	f.tool = tool
	f.params = params
	return f.frames, f.err
}

type fakeProject struct {
	providers string
	sandbox   repo.Sandbox
	err       error
}

func (f *fakeProject) Providers(context.Context) (string, error) { return f.providers, f.err }

func (f *fakeProject) SandboxStatus(context.Context) (repo.Sandbox, error) {
	return f.sandbox, f.err
}

// --- helpers -----------------------------------------------------------------

func sampleToolList() api.ToolList {
	return api.ToolList{
		Count: 3,
		Tools: []api.Tool{
			{
				Name: "read_file", Description: "Read the contents of a file.",
				Category: "developer", MCPEnabled: true,
				Parameters: []api.Parameter{
					{Name: "path", Type: "string", Description: "Path to the file", Required: true},
					{Name: "encoding", Type: "string", Description: "Encoding", Required: false, Default: "utf-8"},
				},
			},
			{Name: "calculate", Description: "Evaluate a mathematical expression.",
				Category: "cognitive", MCPEnabled: true},
			{Name: "fetch_json", Description: "Fetch JSON data from a URL.",
				Category: "data", MCPEnabled: true},
		},
	}
}

// newTestModel builds a model whose live refresh is disabled.
//
// A negative Interval makes tickCmd return nil, so no timer command is ever
// produced and drain cannot block on one. Tests that assert the tick was
// re-armed restore a real interval for that check only.
func newTestModel(t *testing.T, tools ToolSource, runner Runner, proj ProjectSource) *Model {
	t.Helper()
	if tools == nil {
		tools = &fakeTools{list: sampleToolList()}
	}
	if runner == nil {
		runner = &fakeRunner{}
	}
	if proj == nil {
		proj = &fakeProject{}
	}
	return New(Options{
		BaseURL:  "http://127.0.0.1:8082",
		Tools:    tools,
		Runner:   runner,
		Project:  proj,
		Interval: -1,
	})
}

// loadAll drains the active screen's load command so the model holds real data.
func loadAll(t *testing.T, m *Model) *Model {
	t.Helper()
	drained := drain(m, m.loadTools(), 0)
	model, ok := drained.(*Model)
	if !ok {
		t.Fatalf("drain returned %T, want *Model", drained)
	}
	return model
}

// press sends a key press and returns the resulting model and command.
func press(m *Model, key tea.KeyPressMsg) (*Model, tea.Cmd) {
	updated, cmd := m.Update(key)
	model, ok := updated.(*Model)
	if !ok {
		panic("Update returned a non-*Model")
	}
	return model, cmd
}

func pressRunes(text string) tea.KeyPressMsg {
	return tea.KeyPressMsg{Text: text, Code: rune(text[0])}
}

func loadedModel(t *testing.T) *Model {
	t.Helper()
	return loadAll(t, newTestModel(t, nil, nil, nil))
}

// --- double-fire guard -------------------------------------------------------

// TestKeyReleaseDoesNotAct is the guard for this workspace's known bug:
// bubbletea v2 delivers key releases as well as presses, and acting on both makes
// every binding fire twice.
func TestKeyReleaseDoesNotAct(t *testing.T) {
	m := loadedModel(t)
	if len(m.tools) == 0 {
		t.Fatal("no tools loaded")
	}
	before := m.toolCursor

	updated, _ := m.Update(tea.KeyReleaseMsg{Text: "j", Code: 'j'})
	after, ok := updated.(*Model)
	if !ok {
		t.Fatalf("Update returned %T", updated)
	}
	if after.toolCursor != before {
		t.Errorf("a key RELEASE moved the cursor %d -> %d; bindings would fire twice",
			before, after.toolCursor)
	}
}

// TestKeyPressDoesAct is the positive half.
func TestKeyPressDoesAct(t *testing.T) {
	m := loadedModel(t)
	before := m.toolCursor

	m, _ = press(m, pressRunes("j"))
	if m.toolCursor != before+1 {
		t.Errorf("cursor = %d after j, want %d", m.toolCursor, before+1)
	}
	m, _ = press(m, pressRunes("k"))
	if m.toolCursor != before {
		t.Errorf("cursor = %d after k, want %d", m.toolCursor, before)
	}
}

// --- tools screen ------------------------------------------------------------

func TestToolsLoadAndRender(t *testing.T) {
	m := loadedModel(t)
	if len(m.tools) != 3 {
		t.Fatalf("tools = %d, want 3", len(m.tools))
	}
	view := m.viewContent()
	for _, name := range []string{"read_file", "calculate", "fetch_json"} {
		if !strings.Contains(view, name) {
			t.Errorf("view does not mention %s", name)
		}
	}
	// Categories are rendered as headings.
	if !strings.Contains(view, "DEVELOPER") {
		t.Error("category heading missing")
	}
}

func TestCursorCannotRunOffTheList(t *testing.T) {
	m := loadedModel(t)

	// Push far past the end.
	for i := 0; i < 20; i++ {
		m, _ = press(m, pressRunes("j"))
	}
	if m.toolCursor != len(m.visibleTools())-1 {
		t.Errorf("cursor = %d, want the last index %d", m.toolCursor, len(m.visibleTools())-1)
	}

	for i := 0; i < 20; i++ {
		m, _ = press(m, pressRunes("k"))
	}
	if m.toolCursor != 0 {
		t.Errorf("cursor = %d, want 0", m.toolCursor)
	}
}

// TestCursorToolIsSafeWhenTheListShrinks covers the panic case: the cursor can
// outlive the list a refresh rebuilt.
func TestCursorToolIsSafeWhenTheListShrinks(t *testing.T) {
	m := loadedModel(t)
	m.toolCursor = 2

	// A refresh returns a shorter list.
	m.tools = m.tools[:1]
	if got := m.cursorTool(); got != "" {
		t.Errorf("cursorTool = %q for an out-of-range cursor, want empty", got)
	}
	// Clamping recovers rather than staying invalid.
	m.clampToolCursor()
	if m.toolCursor != 0 {
		t.Errorf("cursor = %d after clamping, want 0", m.toolCursor)
	}
}

// TestRunRefusesAStaleTool is the Select-seed lesson in this UI's terms: a name
// the model no longer knows must not be dispatched.
func TestRunRefusesAStaleTool(t *testing.T) {
	m := loadedModel(t)
	m.toolCursor = 2
	m.selected = m.cursorTool()
	stale := m.selected

	// The tool disappears from the registry behind the cursor's back.
	m.tools = m.tools[:1]

	m, _ = press(m, pressRunes("x"))
	if m.form != nil {
		t.Fatal("a run form was opened for a tool that is no longer registered")
	}
	if !strings.Contains(m.notice, stale) {
		t.Errorf("notice = %q, want it to name the stale tool %q", m.notice, stale)
	}
}

// TestRunWithNoSelectionIsRefused keeps an empty selection from dispatching.
func TestRunWithNoSelectionIsRefused(t *testing.T) {
	m := loadedModel(t)
	m.selected = ""

	m, _ = press(m, pressRunes("x"))
	if m.form != nil {
		t.Fatal("a run form was opened with nothing selected")
	}
	if m.notice == "" {
		t.Error("no notice explained why nothing happened")
	}
}

// TestSelectionFollowsTheCursor keeps the tracked name in step with the cursor,
// which is what makes the stale check above meaningful.
func TestSelectionFollowsTheCursor(t *testing.T) {
	m := loadedModel(t)
	if m.selected != m.cursorTool() {
		t.Fatalf("selected = %q, cursorTool = %q", m.selected, m.cursorTool())
	}

	m, _ = press(m, pressRunes("j"))
	if m.selected != "calculate" {
		t.Errorf("selected = %q after j, want calculate", m.selected)
	}
	if m.selected != m.cursorTool() {
		t.Error("the tracked selection drifted from the cursor")
	}
}

// --- detail screen -----------------------------------------------------------

// TestEnterLoadsTheSchema drains before asserting: pressing enter returns the
// command that loads the schema, so the data only exists once it has run.
func TestEnterLoadsTheSchema(t *testing.T) {
	tools := &fakeTools{
		list:   sampleToolList(),
		tool:   sampleToolList().Tools[0],
		schema: json.RawMessage(`{"name":"read_file","parameters":{"type":"object"}}`),
	}
	m := loadAll(t, newTestModel(t, tools, nil, nil))

	m, cmd := press(m, tea.KeyPressMsg{Code: tea.KeyEnter})
	m = drain(m, cmd, 0).(*Model)

	if m.screen != screenDetail {
		t.Errorf("screen = %v, want detail", m.screen)
	}
	if m.detail == nil {
		t.Fatal("detail was not loaded")
	}
	if m.detail.Name != "read_file" {
		t.Errorf("detail name = %q", m.detail.Name)
	}

	content := m.detailContent()
	for _, want := range []string{"read_file", "Parameters", "path", "encoding", "OpenAI schema"} {
		if !strings.Contains(content, want) {
			t.Errorf("detail content is missing %q", want)
		}
	}
}

// TestDetailSurvivesAMissingSchema keeps a failed schema route from blanking a
// screen that has perfectly good tool data.
func TestDetailSurvivesAMissingSchema(t *testing.T) {
	tools := &fakeTools{
		list:      sampleToolList(),
		tool:      sampleToolList().Tools[0],
		detailErr: errors.New("schema route unavailable"),
	}
	m := loadAll(t, newTestModel(t, tools, nil, nil))

	m, cmd := press(m, tea.KeyPressMsg{Code: tea.KeyEnter})
	m = drain(m, cmd, 0).(*Model)

	if m.detail == nil {
		t.Fatal("the tool itself should still be shown")
	}
	if m.detailErr == "" {
		t.Error("the schema failure was not reported")
	}
	if !strings.Contains(m.bodyView(80), "schema unavailable") {
		t.Error("the view does not explain the missing schema")
	}
}

// --- run flow ----------------------------------------------------------------

// TestRunFlowSubmitsAndRendersFrames drives the whole path: open the form, submit
// it, drain, and check the transcript.
func TestRunFlowSubmitsAndRendersFrames(t *testing.T) {
	runner := &fakeRunner{frames: []ws.Frame{
		{Type: "tool_result", Name: "read_file", Result: &ws.ToolResult{
			Success: true, Data: json.RawMessage(`{"ok":true}`), ExecutionTimeMS: 2.5,
		}},
		{Type: "done"},
	}}
	m := loadAll(t, newTestModel(t, nil, runner, nil))

	m, cmd := press(m, pressRunes("x"))
	m = drain(m, cmd, 0).(*Model)
	if m.form == nil {
		t.Fatal("the run form did not open")
	}
	if m.formPurpose != purposeRunParams {
		t.Fatalf("formPurpose = %v, want run-params", m.formPurpose)
	}

	// Submit. Enter returns the command that completes the form, so the run only
	// starts once that command has been drained.
	m, cmd = press(m, tea.KeyPressMsg{Code: tea.KeyEnter})
	m = drain(m, cmd, 0).(*Model)

	if m.form != nil {
		t.Error("the form was not cleared after submitting")
	}
	if runner.calls != 1 {
		t.Fatalf("runner calls = %d, want 1", runner.calls)
	}
	if runner.tool != "read_file" {
		t.Errorf("ran %q, want read_file", runner.tool)
	}
	// The skeleton should have supplied the required parameter, so the run has
	// something to send rather than failing validation.
	if _, ok := runner.params["path"]; !ok {
		t.Errorf("params = %v, want the skeleton to include path", runner.params)
	}

	if m.screen != screenRun {
		t.Errorf("screen = %v, want run", m.screen)
	}
	content := m.runContent()
	for _, want := range []string{"Run: read_file", "result", "session done", "Data"} {
		if !strings.Contains(content, want) {
			t.Errorf("run transcript is missing %q:\n%s", want, content)
		}
	}
}

// TestRunReportsAFailedTool keeps a tool failure visible with its message.
func TestRunReportsAFailedTool(t *testing.T) {
	reason := "Missing required parameter: path"
	runner := &fakeRunner{frames: []ws.Frame{
		{Type: "tool_result", Name: "read_file", Result: &ws.ToolResult{
			Success: false, Error: &reason,
		}},
		{Type: "done"},
	}}
	m := loadAll(t, newTestModel(t, nil, runner, nil))

	m, cmd := press(m, pressRunes("x"))
	m = drain(m, cmd, 0).(*Model)
	m, cmd = press(m, tea.KeyPressMsg{Code: tea.KeyEnter})
	m = drain(m, cmd, 0).(*Model)

	content := m.runContent()
	if !strings.Contains(content, "failed") || !strings.Contains(content, reason) {
		t.Errorf("transcript does not report the failure:\n%s", content)
	}
}

// TestRunTransportErrorIsShown keeps a dead socket from looking like a result.
func TestRunTransportErrorIsShown(t *testing.T) {
	runner := &fakeRunner{err: errors.New("websocket: close 1006")}
	m := loadAll(t, newTestModel(t, nil, runner, nil))

	m, cmd := press(m, pressRunes("x"))
	m = drain(m, cmd, 0).(*Model)
	m, cmd = press(m, tea.KeyPressMsg{Code: tea.KeyEnter})
	m = drain(m, cmd, 0).(*Model)

	if m.runErr == "" {
		t.Error("the transport error was not recorded")
	}
	if !strings.Contains(m.bodyView(80), "websocket") {
		t.Error("the view does not surface the transport error")
	}
}

// TestNarrowTerminalDoesNotPanic sweeps widths across and below the minimum,
// including 0 and negatives, because a negative content width was a real crash.
func TestNarrowTerminalDoesNotPanic(t *testing.T) {
	m := loadedModel(t)

	for width := -5; width <= 120; width++ {
		m.width = width
		m.height = 24
		m.resizeViewports()

		// Every screen must render at every width.
		for _, s := range screens {
			m.screen = s
			func() {
				defer func() {
					if r := recover(); r != nil {
						t.Fatalf("width %d screen %v panicked: %v", width, s, r)
					}
				}()
				if rendered := m.viewContent(); rendered == "" && width > 0 {
					t.Errorf("width %d screen %v rendered nothing", width, s)
				}
			}()
		}
	}
}

// TestVeryNarrowDoesNotOverflow checks the chrome is clamped instead of trusting
// the terminal: below the minimum the frame stops shrinking.
func TestVeryNarrowDoesNotOverflow(t *testing.T) {
	m := loadedModel(t)
	m.width = 3

	rendered := m.viewContent()
	if rendered == "" {
		t.Fatal("nothing rendered at width 3")
	}
	// The pane's own frame is the floor, so the line cannot be narrower than it.
	if !strings.Contains(rendered, "╭") {
		t.Errorf("expected a rounded frame at width 3:\n%s", rendered)
	}
}

// --- filter ------------------------------------------------------------------

func TestFilterNarrowsTheList(t *testing.T) {
	m := loadedModel(t)

	m, cmd := press(m, pressRunes("/"))
	m = drain(m, cmd, 0).(*Model)
	if m.form == nil {
		t.Fatal("the filter form did not open")
	}

	for _, r := range "calc" {
		m, _ = press(m, tea.KeyPressMsg{Text: string(r), Code: r})
	}
	// Drain first: the filter is applied when the returned command completes.
	m, cmd = press(m, tea.KeyPressMsg{Code: tea.KeyEnter})
	m = drain(m, cmd, 0).(*Model)

	if m.filter != "calc" {
		t.Fatalf("filter = %q, want calc", m.filter)
	}
	visible := m.visibleTools()
	if len(visible) != 1 || visible[0].Name != "calculate" {
		t.Errorf("visible = %+v, want only calculate", visible)
	}
	if m.toolCursor != 0 {
		t.Errorf("cursor = %d, want it reset to 0", m.toolCursor)
	}
}

func TestFilterMatchesCategoryAndDescription(t *testing.T) {
	m := loadedModel(t)
	for _, needle := range []string{"developer", "mathematical", "DATA"} {
		m.filter = needle
		if len(m.visibleTools()) == 0 {
			t.Errorf("filter %q matched nothing", needle)
		}
	}
}

// --- other screens -----------------------------------------------------------

func TestProvidersScreenShowsTheCLIText(t *testing.T) {
	proj := &fakeProject{providers: "┃ Provider/Model ┃\n│ ollama/* │ Local Ollama models │"}
	m := loadAll(t, newTestModel(t, nil, nil, proj))

	m, cmd := press(m, pressRunes("l")) // next tab -> detail
	m = drain(m, cmd, 0).(*Model)
	for m.screen != screenProviders {
		m, cmd = press(m, pressRunes("l"))
		m = drain(m, cmd, 0).(*Model)
	}

	if !strings.Contains(m.bodyView(80), "ollama") {
		t.Errorf("providers view is missing the CLI output:\n%s", m.bodyView(80))
	}
}

func TestSandboxScreenReportsTheWorkspace(t *testing.T) {
	proj := &fakeProject{sandbox: repo.Sandbox{
		Workspace: "local", ToolCount: 23, SandboxRequired: nil,
	}}
	m := loadAll(t, newTestModel(t, nil, nil, proj))

	m, cmd := press(m, pressRunes("h")) // previous tab wraps to the last screen
	m = drain(m, cmd, 0).(*Model)
	for m.screen != screenSandbox {
		m, cmd = press(m, pressRunes("h"))
		m = drain(m, cmd, 0).(*Model)
	}

	body := m.bodyView(90)
	for _, want := range []string{"Execution workspace", "local", "in-process", "Declaring sandbox_required", "none"} {
		if !strings.Contains(body, want) {
			t.Errorf("sandbox view is missing %q:\n%s", want, body)
		}
	}
}

// TestSandboxUnavailableIsNotGuessed is the honesty guard: a failed probe must
// never render as a confident "unsandboxed" answer.
func TestSandboxUnavailableIsNotGuessed(t *testing.T) {
	proj := &fakeProject{err: errors.New("python3 not found")}
	m := loadAll(t, newTestModel(t, nil, nil, proj))

	for m.screen != screenSandbox {
		cmd := m.switchScreen(screenSandbox)
		m = drain(m, cmd, 0).(*Model)
	}

	body := m.bodyView(90)
	if !strings.Contains(body, "unavailable") {
		t.Errorf("sandbox view does not report the failure:\n%s", body)
	}
	if strings.Contains(body, "in-process on the host") {
		t.Error("the view invented a workspace answer from a failed probe")
	}
	if m.sandbox != nil {
		t.Error("a failed probe must not leave a sandbox value behind")
	}
}

// TestTabCyclesWraps keeps tab navigation total.
func TestTabCyclesWraps(t *testing.T) {
	m := loadedModel(t)
	seen := map[screen]bool{}
	for i := 0; i < len(screens); i++ {
		seen[m.screen] = true
		cmd := m.switchScreen(screens[(indexOf(m.screen)+1)%len(screens)])
		m = drain(m, cmd, 0).(*Model)
	}
	if len(seen) != len(screens) {
		t.Errorf("visited %d screens, want %d", len(seen), len(screens))
	}
	if m.screen != screens[0] {
		t.Errorf("after a full cycle screen = %v, want %v", m.screen, screens[0])
	}
}

// --- refresh -----------------------------------------------------------------

// TestRefreshIsSkippedWhileAFormIsOpen keeps the live tick from stealing focus.
func TestRefreshIsSkippedWhileAFormIsOpen(t *testing.T) {
	m := loadedModel(t)
	cmd := m.openForm(purposeFilter, FilterForm(&Answers{}))
	m = drain(m, cmd, 0).(*Model)
	if m.form == nil {
		t.Fatal("the form did not open")
	}

	// Restore a real interval: with the refresh disabled the tick command is nil,
	// which would make the assertion below vacuous.
	m.opts.Interval = time.Second

	updated, cmd := m.Update(refreshMsg{})
	after := updated.(*Model)
	if after.form == nil {
		t.Error("the live refresh closed the open form")
	}
	if cmd == nil {
		t.Error("the refresh did not re-arm the tick")
	}
}

// TestRefreshDisabledProducesNoTick guards the mechanism the tests rely on: a
// negative interval must yield no timer command at all, or drain could block.
func TestRefreshDisabledProducesNoTick(t *testing.T) {
	m := newTestModel(t, nil, nil, nil) // Interval: -1
	if cmd := m.tickCmd(); cmd != nil {
		t.Error("a negative Interval still produced a tick command")
	}
}

// TestToolLoadFailureIsVisible keeps an unreachable server from looking empty.
func TestToolLoadFailureIsVisible(t *testing.T) {
	tools := &fakeTools{err: errors.New("connection refused")}
	m := loadAll(t, newTestModel(t, tools, nil, nil))

	if m.failure == "" {
		t.Fatal("the load failure was not recorded")
	}
	body := m.bodyView(90)
	if !strings.Contains(body, "connection refused") {
		t.Errorf("the view does not explain the failure:\n%s", body)
	}
	if !strings.Contains(body, "--start-service") {
		t.Error("the failure view should tell the user how to start the server")
	}
}

// TestQuitIsBound keeps q working.
func TestQuitIsBound(t *testing.T) {
	m := loadedModel(t)
	_, cmd := press(m, pressRunes("q"))
	if cmd == nil {
		t.Fatal("q returned no command")
	}
	if _, ok := cmd().(tea.QuitMsg); !ok {
		t.Error("q did not quit")
	}
}

// TestEscReturnsToToolsAndDoesNotQuit pins that escaping a screen is not an exit.
func TestEscReturnsToToolsAndDoesNotQuit(t *testing.T) {
	m := loadedModel(t)
	m.screen = screenProviders

	m, cmd := press(m, tea.KeyPressMsg{Code: tea.KeyEscape})
	if m.screen != screenTools {
		t.Errorf("screen = %v after esc, want tools", m.screen)
	}
	if cmd != nil {
		if _, ok := cmd().(tea.QuitMsg); ok {
			t.Error("esc quit the program instead of going back")
		}
	}
}

// --- form visibility ---------------------------------------------------------

// TestAnOpenFormIsRendered is the guard for a bug that every other test missed:
// the model held the form but the view never drew it, so the user was typing into
// an invisible prompt. Unit tests passed because they only checked m.form != nil.
func TestAnOpenFormIsRendered(t *testing.T) {
	m := loadedModel(t)

	m, cmd := press(m, pressRunes("/"))
	m = drain(m, cmd, 0).(*Model)
	if m.form == nil {
		t.Fatal("the filter form did not open")
	}

	view := m.viewContent()
	if !strings.Contains(view, "Filter tools") {
		t.Errorf("the open form is not visible in the view:\n%s", view)
	}
	// The screen behind it must not be drawn instead.
	if strings.Contains(view, "DEVELOPER") {
		t.Error("the tools list was drawn instead of the modal form")
	}

	// The status line should say what to do with it.
	if !strings.Contains(view, "enter to submit") {
		t.Errorf("the status line does not explain the form:\n%s", view)
	}
}

// TestRunFormIsRenderedAndPrefilled checks the run prompt appears with the tool's
// parameter skeleton, so a required argument cannot be missed.
func TestRunFormIsRenderedAndPrefilled(t *testing.T) {
	m := loadedModel(t)

	m, cmd := press(m, pressRunes("x"))
	m = drain(m, cmd, 0).(*Model)
	if m.form == nil {
		t.Fatal("the run form did not open")
	}

	view := m.viewContent()
	if !strings.Contains(view, "read_file") {
		t.Errorf("the run form does not name the tool:\n%s", view)
	}
	if !strings.Contains(view, "Parameters (JSON object)") {
		t.Errorf("the run form does not show the parameter field:\n%s", view)
	}
}

// TestFormIsDismissedOnEscape keeps esc from leaving a stranded modal.
func TestFormIsDismissedOnEscape(t *testing.T) {
	m := loadedModel(t)

	m, cmd := press(m, pressRunes("/"))
	m = drain(m, cmd, 0).(*Model)
	if m.form == nil {
		t.Fatal("the filter form did not open")
	}

	m, cmd = press(m, tea.KeyPressMsg{Code: tea.KeyEscape})
	m = drain(m, cmd, 0).(*Model)

	if m.form != nil {
		t.Error("esc did not close the form")
	}
	if !strings.Contains(m.viewContent(), "DEVELOPER") {
		t.Error("the tools list did not come back after closing the form")
	}
}
