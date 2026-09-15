// Package tui is the Go terminal front-end: a read-only peer of the Python CLI
// and the Svelte frontend, built on charm.land/bubbletea/v2 with huh/v2 forms
// and a plain renderer for non-TTY use.
//
// It owns no tool logic. Tools, schemas and execution come from the repository's
// own HTTP server (agent_tooling.server); the provider catalogue, the execution
// workspace and the sandbox flags come from the repository's own Python; live
// runs come from the repository's own WebSocket session. A Go user and a Python
// user therefore see identical results.
package tui

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"charm.land/bubbles/v2/help"
	"charm.land/bubbles/v2/key"
	"charm.land/bubbles/v2/spinner"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/huh/v2"

	"github.com/jasperan/agent-tooling/gotui/internal/api"
	"github.com/jasperan/agent-tooling/gotui/internal/repo"
	"github.com/jasperan/agent-tooling/gotui/internal/ws"
)

// screen identifies the active view.
type screen int

const (
	screenTools screen = iota
	screenDetail
	screenRun
	screenProviders
	screenSandbox
)

// screens is the tab order.
var screens = []screen{screenTools, screenDetail, screenRun, screenProviders, screenSandbox}

func (s screen) label() string {
	switch s {
	case screenTools:
		return "Tools"
	case screenDetail:
		return "Schema"
	case screenRun:
		return "Run"
	case screenProviders:
		return "Providers"
	case screenSandbox:
		return "Sandbox"
	default:
		return "?"
	}
}

// ToolSource is the slice of the repository's HTTP server this front-end uses.
//
// It is an interface so the model can be tested without a server, and so the
// only thing the UI can do to the project is read a list and ask it to run a
// tool.
type ToolSource interface {
	Info(ctx context.Context) (api.Info, error)
	Tools(ctx context.Context) (api.ToolList, error)
	Tool(ctx context.Context, name string) (api.Tool, error)
	Categories(ctx context.Context) (api.Categories, error)
	Schema(ctx context.Context, name, format string) (json.RawMessage, error)
}

// Runner executes one tool on the repository's live session channel.
type Runner interface {
	RunTool(ctx context.Context, toolName string, parameters map[string]any) ([]ws.Frame, error)
}

// ProjectSource reaches the parts of the project the server does not expose.
type ProjectSource interface {
	Providers(ctx context.Context) (string, error)
	SandboxStatus(ctx context.Context) (repo.Sandbox, error)
}

// Options configures the root model.
type Options struct {
	BaseURL string
	Tools   ToolSource
	Runner  Runner
	Project ProjectSource
	// Interval drives the live refresh. Zero means the default; a negative value
	// disables it, which is what tests use so no timer command is ever produced.
	Interval time.Duration
	// RunTimeout bounds one delegated run.
	RunTimeout time.Duration
}

// DefaultInterval matches a dashboard-style refresh rather than a busy loop.
const DefaultInterval = 5 * time.Second

// Model is the root bubbletea model.
//
// It is a pointer model on purpose: every huh field binds through a pointer, and
// a value-typed Bubble Tea model would silently persist defaults because Update
// receives a copy.
type Model struct {
	width  int
	height int
	opts   Options

	screen  screen
	notice  string
	failure string
	busy    string

	// tools
	tools      []api.Tool
	expanded   map[string]bool
	toolCursor int
	// selected is the tool the cursor last resolved to. It is tracked separately
	// from the cursor because the cursor is an index into a list a refresh can
	// rebuild: acting on a stale name would dispatch a tool the user never chose.
	selected string
	filter   string

	// detail
	detail     *api.Tool
	detailJSON json.RawMessage
	detailVP   viewport.Model
	detailErr  string
	detailTool string

	// run
	runTool   string
	runParams map[string]any
	runFrames []ws.Frame
	runResult *ws.ToolResult
	runErr    string
	runVP     viewport.Model

	// providers / sandbox
	providersText string
	providersVP   viewport.Model
	sandbox       *repo.Sandbox
	sandboxErr    string

	form        *huh.Form
	formPurpose formPurpose
	answers     Answers

	spinner spinner.Model
	help    help.Model
	keys    keyMap
	loaded  map[screen]bool
}

type formPurpose int

const (
	purposeNone formPurpose = iota
	purposeFilter
	purposeRunParams
)

// keyMap is the keymap, kept in one place so the footer and the handler cannot
// drift apart.
type keyMap struct {
	Quit    key.Binding
	NextTab key.Binding
	PrevTab key.Binding
	Up      key.Binding
	Down    key.Binding
	Reload  key.Binding
	Schema  key.Binding
	Run     key.Binding
	Filter  key.Binding
	Back    key.Binding
	Expand  key.Binding
	Help    key.Binding
}

func defaultKeys() keyMap {
	return keyMap{
		Quit:    key.NewBinding(key.WithKeys("q", "ctrl+c"), key.WithHelp("q", "quit")),
		NextTab: key.NewBinding(key.WithKeys("tab", "l"), key.WithHelp("tab", "next")),
		PrevTab: key.NewBinding(key.WithKeys("shift+tab", "h"), key.WithHelp("shift+tab", "prev")),
		Up:      key.NewBinding(key.WithKeys("up", "k"), key.WithHelp("↑/k", "up")),
		Down:    key.NewBinding(key.WithKeys("down", "j"), key.WithHelp("↓/j", "down")),
		Reload:  key.NewBinding(key.WithKeys("r"), key.WithHelp("r", "reload")),
		Schema:  key.NewBinding(key.WithKeys("enter"), key.WithHelp("enter", "schema")),
		Run:     key.NewBinding(key.WithKeys("x"), key.WithHelp("x", "run")),
		Filter:  key.NewBinding(key.WithKeys("/"), key.WithHelp("/", "filter")),
		Back:    key.NewBinding(key.WithKeys("esc"), key.WithHelp("esc", "back")),
		Expand:  key.NewBinding(key.WithKeys(" "), key.WithHelp("space", "expand")),
		Help:    key.NewBinding(key.WithKeys("?"), key.WithHelp("?", "help")),
	}
}

// ShortHelp implements help.KeyMap.
func (k keyMap) ShortHelp() []key.Binding {
	return []key.Binding{k.NextTab, k.PrevTab, k.Up, k.Down, k.Schema, k.Run, k.Filter, k.Reload, k.Quit}
}

// FullHelp implements help.KeyMap.
func (k keyMap) FullHelp() [][]key.Binding {
	return [][]key.Binding{
		{k.NextTab, k.PrevTab, k.Back},
		{k.Up, k.Down, k.Expand},
		{k.Schema, k.Run, k.Filter},
		{k.Reload, k.Quit},
	}
}

// New builds the root model.
func New(opts Options) *Model {
	if opts.Interval == 0 {
		opts.Interval = DefaultInterval
	}
	if opts.RunTimeout <= 0 {
		opts.RunTimeout = 2 * time.Minute
	}
	if opts.BaseURL == "" {
		opts.BaseURL = api.DefaultBaseURL
	}

	sp := spinner.New()
	sp.Spinner = spinner.Dot
	sp.Style = styleInfo

	h := help.New()
	h.Styles.ShortKey = styleSubtext
	h.Styles.ShortDesc = styleMuted
	h.Styles.ShortSeparator = styleDim
	h.Styles.Ellipsis = styleMuted

	m := &Model{
		width:     100,
		height:    30,
		opts:      opts,
		screen:    screenTools,
		expanded:  map[string]bool{},
		loaded:    map[screen]bool{},
		spinner:   sp,
		help:      h,
		keys:      defaultKeys(),
		runParams: map[string]any{},
	}
	// Size the viewports up front. They are otherwise 0x0 until the first
	// WindowSizeMsg arrives, which renders every viewport-backed pane as empty.
	m.resizeViewports()
	return m
}

// Init loads the tool list and the project facts.
func (m *Model) Init() tea.Cmd {
	return tea.Batch(m.loadTools(), m.loadServerInfo(), m.tickCmd())
}

// tickCmd schedules the next live refresh, unless the interval is negative, in
// which case no timer is produced at all.
func (m *Model) tickCmd() tea.Cmd {
	if m.opts.Interval < 0 {
		return nil
	}
	return tea.Tick(m.opts.Interval, func(time.Time) tea.Msg { return refreshMsg{} })
}

// --- messages ----------------------------------------------------------------

type refreshMsg struct{}

type serverInfoMsg struct {
	info api.Info
	err  error
}

type toolsMsg struct {
	list api.ToolList
	err  error
}

type detailMsg struct {
	name   string
	tool   api.Tool
	schema json.RawMessage
	err    error
}

type providersMsg struct {
	text string
	err  error
}

type sandboxMsg struct {
	info repo.Sandbox
	err  error
}

type runMsg struct {
	tool   string
	frames []ws.Frame
	err    error
}

// --- commands ----------------------------------------------------------------

func (m *Model) loadServerInfo() tea.Cmd {
	src := m.opts.Tools
	if src == nil {
		return nil
	}
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), api.DefaultTimeout)
		defer cancel()
		info, err := src.Info(ctx)
		return serverInfoMsg{info: info, err: err}
	}
}

func (m *Model) loadTools() tea.Cmd {
	src := m.opts.Tools
	if src == nil {
		return nil
	}
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), api.DefaultTimeout)
		defer cancel()
		list, err := src.Tools(ctx)
		return toolsMsg{list: list, err: err}
	}
}

func (m *Model) loadDetail(name string) tea.Cmd {
	src := m.opts.Tools
	if src == nil || name == "" {
		return nil
	}
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), api.DefaultTimeout)
		defer cancel()
		tool, err := src.Tool(ctx, name)
		if err != nil {
			return detailMsg{name: name, err: err}
		}
		schema, serr := src.Schema(ctx, name, "openai")
		// A missing schema is not fatal: the parameter table still renders.
		return detailMsg{name: name, tool: tool, schema: schema, err: serr}
	}
}

func (m *Model) loadProviders() tea.Cmd {
	src := m.opts.Project
	if src == nil {
		return nil
	}
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), api.DefaultTimeout)
		defer cancel()
		text, err := src.Providers(ctx)
		return providersMsg{text: text, err: err}
	}
}

func (m *Model) loadSandbox() tea.Cmd {
	src := m.opts.Project
	if src == nil {
		return nil
	}
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), api.DefaultTimeout)
		defer cancel()
		info, err := src.SandboxStatus(ctx)
		return sandboxMsg{info: info, err: err}
	}
}

func (m *Model) runToolCmd(tool string, params map[string]any) tea.Cmd {
	runner := m.opts.Runner
	if runner == nil {
		return nil
	}
	timeout := m.opts.RunTimeout
	return func() tea.Msg {
		ctx, cancel := context.WithTimeout(context.Background(), timeout)
		defer cancel()
		frames, err := runner.RunTool(ctx, tool, params)
		return runMsg{tool: tool, frames: frames, err: err}
	}
}

// --- update ------------------------------------------------------------------

// Update implements tea.Model.
//
// Only tea.KeyPressMsg is acted on. bubbletea v2 also delivers key RELEASES, and
// acting on both makes every binding fire twice -- so releases fall through to
// the focused component untouched.
func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		m.resizeViewports()
		if m.form != nil {
			m.form = m.sized(m.form)
		}
		return m, nil

	case tea.KeyPressMsg:
		return m.handleKey(msg)

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case refreshMsg:
		if m.form != nil || m.busy != "" {
			// Never steal focus from an open form; just re-arm.
			return m, m.tickCmd()
		}
		return m, tea.Batch(m.loadTools(), m.loadServerInfo(), m.tickCmd())

	case serverInfoMsg:
		if msg.err != nil && api.IsUnreachable(msg.err) {
			m.failure = fmt.Sprintf("server unreachable at %s", m.opts.BaseURL)
		}
		return m, nil

	case toolsMsg:
		m.busy = ""
		if msg.err != nil {
			m.failure = msg.err.Error()
			return m, nil
		}
		m.failure = ""
		m.tools = msg.list.Tools
		m.clampToolCursor()
		return m, nil

	case detailMsg:
		m.busy = ""
		m.detailTool = msg.name
		m.detailErr = ""
		if msg.err != nil {
			// The schema route can fail while the tool itself loaded; keep what we
			// have and show the reason rather than blanking the screen.
			m.detailErr = msg.err.Error()
		}
		tool := msg.tool
		m.detail = &tool
		m.detailJSON = msg.schema
		m.detailVP.SetContent(m.detailContent())
		m.detailVP.GotoTop()
		return m, nil

	case providersMsg:
		m.busy = ""
		if msg.err != nil {
			m.failure = msg.err.Error()
			return m, nil
		}
		m.failure = ""
		m.providersText = msg.text
		m.providersVP.SetContent(msg.text)
		m.providersVP.GotoTop()
		return m, nil

	case sandboxMsg:
		m.busy = ""
		if msg.err != nil {
			// Reported, never guessed: an unavailable probe must not look like a
			// confident "unsandboxed" answer.
			m.sandboxErr = msg.err.Error()
			m.sandbox = nil
			return m, nil
		}
		m.sandboxErr = ""
		info := msg.info
		m.sandbox = &info
		return m, nil

	case runMsg:
		m.busy = ""
		m.runTool = msg.tool
		if msg.err != nil {
			m.runErr = msg.err.Error()
			return m, nil
		}
		m.runErr = ""
		m.runFrames = msg.frames
		m.runResult = lastResult(msg.frames)
		m.runVP.SetContent(m.runContent())
		m.runVP.GotoBottom()
		return m, nil
	}

	// Unhandled messages still go to the form, so huh keeps working.
	return m.updateForm(msg)
}

// handleKey routes a key press.
func (m *Model) handleKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	// A live form owns the keyboard.
	if m.form != nil {
		return m.updateForm(msg)
	}

	switch {
	case key.Matches(msg, m.keys.Quit):
		return m, tea.Quit

	case key.Matches(msg, m.keys.NextTab):
		return m, m.switchScreen(screens[(indexOf(m.screen)+1)%len(screens)])

	case key.Matches(msg, m.keys.PrevTab):
		return m, m.switchScreen(screens[(indexOf(m.screen)+len(screens)-1)%len(screens)])

	case key.Matches(msg, m.keys.Reload):
		m.busy = "reloading"
		return m, tea.Batch(m.loadTools(), m.reloadForCurrentScreen())

	case key.Matches(msg, m.keys.Filter):
		return m, m.openFormWith(purposeFilter, func(a *Answers) *huh.Form {
			a.Search = m.filter
			return FilterForm(a)
		})

	case key.Matches(msg, m.keys.Run):
		if m.screen == screenTools {
			// Validate the selection instead of trusting it: the list may have been
			// rebuilt by a refresh since the cursor settled, and running a name that
			// is no longer registered would dispatch a stale tool silently.
			if m.selected == "" {
				m.notice = "select a tool first"
				return m, nil
			}
			if !m.toolExists(m.selected) {
				m.notice = m.selected + " is no longer registered; press r to reload"
				m.selected = ""
				return m, nil
			}
			tool := m.selected
			return m, m.openFormWith(purposeRunParams, func(a *Answers) *huh.Form {
				return RunForm(a, tool, m.paramFields(tool))
			})
		}
		return m, nil

	case key.Matches(msg, m.keys.Schema):
		if tool := m.cursorTool(); tool != "" {
			m.screen = screenDetail
			m.busy = "loading schema"
			return m, m.loadDetail(tool)
		}
		return m, nil

	case key.Matches(msg, m.keys.Expand):
		if m.screen == screenTools {
			if tool := m.cursorTool(); tool != "" {
				m.expanded[tool] = !m.expanded[tool]
			}
		}
		return m, nil

	case key.Matches(msg, m.keys.Back):
		if m.screen != screenTools {
			m.screen = screenTools
		}
		return m, nil
	}

	// Screen-local movement.
	switch m.screen {
	case screenTools:
		switch {
		case key.Matches(msg, m.keys.Up):
			if m.toolCursor > 0 {
				m.toolCursor--
				m.selected = m.cursorTool()
			}
		case key.Matches(msg, m.keys.Down):
			if m.toolCursor < len(m.visibleTools())-1 {
				m.toolCursor++
				m.selected = m.cursorTool()
			}
		}
	case screenDetail:
		var cmd tea.Cmd
		m.detailVP, cmd = m.detailVP.Update(msg)
		return m, cmd
	case screenRun:
		var cmd tea.Cmd
		m.runVP, cmd = m.runVP.Update(msg)
		return m, cmd
	case screenProviders:
		var cmd tea.Cmd
		m.providersVP, cmd = m.providersVP.Update(msg)
		return m, cmd
	}
	return m, nil
}

// switchScreen changes the tab and kicks off whatever that screen needs. Each
// screen loads lazily, once.
func (m *Model) switchScreen(next screen) tea.Cmd {
	if next == m.screen {
		return nil
	}
	m.screen = next
	if m.loaded[next] {
		return nil
	}
	m.loaded[next] = true

	switch next {
	case screenDetail:
		if tool := m.cursorTool(); tool != "" {
			m.busy = "loading schema"
			return m.loadDetail(tool)
		}
	case screenProviders:
		m.busy = "loading providers"
		return m.loadProviders()
	case screenSandbox:
		m.busy = "probing workspace"
		return m.loadSandbox()
	}
	return nil
}

// reloadForCurrentScreen refreshes the non-tool data behind the active screen.
func (m *Model) reloadForCurrentScreen() tea.Cmd {
	switch m.screen {
	case screenDetail:
		m.loaded[screenDetail] = true
		if tool := m.cursorTool(); tool != "" {
			return m.loadDetail(tool)
		}
	case screenProviders:
		return m.loadProviders()
	case screenSandbox:
		return m.loadSandbox()
	case screenRun:
		if m.runTool != "" {
			return m.runToolCmd(m.runTool, m.runParams)
		}
	}
	return nil
}

// updateForm drives the active form.
func (m *Model) updateForm(msg tea.Msg) (tea.Model, tea.Cmd) {
	if m.form == nil {
		return m, nil
	}
	updated, cmd := m.form.Update(msg)
	if form, ok := updated.(*huh.Form); ok {
		m.form = form
	}
	if m.form.State != huh.StateNormal {
		return m, m.advance()
	}
	return m, cmd
}

// openFormWith installs a form whose fields are bound to the model's own
// Answers, then runs build against it.
//
// The binding is the point: huh writes into the Answers instance it was given,
// so the model must hold that same instance. Handing the form a throwaway
// &Answers{} leaves advance() reading zeros and every submission silently does
// nothing.
func (m *Model) openFormWith(purpose formPurpose, build func(*Answers) *huh.Form) tea.Cmd {
	m.answers = Answers{}
	return m.openForm(purpose, build(&m.answers))
}

// openForm installs a form, sized, and returns its first command.
//
// Every transition goes through here so no form is ever left at huh's zero
// width, which renders as blank lines.
func (m *Model) openForm(purpose formPurpose, form *huh.Form) tea.Cmd {
	m.form = m.sized(form)
	m.formPurpose = purpose
	m.notice = ""
	return m.form.Init()
}

// sized pins a form to the model's dimensions.
func (m *Model) sized(f *huh.Form) *huh.Form {
	width := clampWidth(m.width - 4)
	return f.WithWidth(width).WithHeight(m.height)
}

// advance reacts to a finished form.
func (m *Model) advance() tea.Cmd {
	state := m.form.State
	purpose := m.formPurpose
	answers := m.answers
	m.form = nil
	m.formPurpose = purposeNone

	if state == huh.StateAborted {
		m.notice = "Cancelled."
		return nil
	}

	switch purpose {
	case purposeFilter:
		m.filter = strings.TrimSpace(answers.Search)
		m.toolCursor = 0
		m.clampToolCursor()
		return nil
	case purposeRunParams:
		tool := answers.RunTool
		if tool == "" {
			tool = m.selected
		}
		params, err := answers.RunParameters()
		if err != nil {
			m.failure = err.Error()
			return nil
		}
		m.runTool = tool
		m.runParams = params
		m.screen = screenRun
		m.loaded[screenRun] = true
		m.busy = "running " + tool
		m.runFrames = nil
		m.runResult = nil
		m.runErr = ""
		m.runVP.SetContent("")
		return m.runToolCmd(tool, params)
	}
	return nil
}

// --- view --------------------------------------------------------------------

// View implements tea.Model.
//
// Bubble Tea v2 returns a tea.View rather than a string, and the full-screen UI
// belongs in the alternate screen buffer so quitting restores the shell.
func (m *Model) View() tea.View {
	view := tea.NewView(m.viewContent())
	view.AltScreen = true
	return view
}

// viewContent renders the whole frame as a string, so tests can assert on what a
// user would see without constructing a tea.View.
func (m *Model) viewContent() string {
	width := clampWidth(m.width)
	height := m.height

	header := m.headerView(width)
	tabs := tabBar(screens, m.screen, width)
	body := m.bodyView(width)

	// Reserve the header, tabs, status and help lines.
	footerLines := 2
	bodyHeight := height - 3 - footerLines
	if bodyHeight < 3 {
		bodyHeight = 3
	}
	body = clampHeight(body, bodyHeight)

	mode := m.screen.label()
	message := m.statusMessage()
	status := statusLine(mode, message, width)
	footer := m.help.View(m.keys)

	return header + "\n" + tabs + "\n" + body + "\n" + status + "\n" + truncate(footer, width)
}

func (m *Model) headerView(width int) string {
	left := styleTitle.Render("agent-tooling")
	right := styleMuted.Render(m.opts.BaseURL)
	if m.busy != "" {
		right = m.spinner.View() + " " + styleMuted.Render(m.busy)
	}
	gap := width - lipglossWidth(left) - lipglossWidth(right)
	if gap < 1 {
		return truncate(left, width)
	}
	return left + strings.Repeat(" ", gap) + right
}

func (m *Model) statusMessage() string {
	if m.form != nil {
		return styleSubtext.Render("editing — enter to submit, esc to cancel")
	}
	switch {
	case m.failure != "":
		return styleError.Render(m.failure)
	case m.notice != "":
		return styleWarning.Render(m.notice)
	case m.sandboxErr != "":
		return styleWarning.Render(m.sandboxErr)
	}
	return fmt.Sprintf("%d tools", len(m.tools))
}

func (m *Model) bodyView(width int) string {
	// An open form owns the body. It is modal: if it were not rendered the user
	// would be typing into an invisible prompt, which is exactly what happened
	// before this was added -- the model held the form, the view never drew it,
	// and every unit test still passed because they only checked m.form != nil.
	if m.form != nil {
		return pane(m.form.View(), width, true)
	}
	switch m.screen {
	case screenTools:
		return m.toolsView(width)
	case screenDetail:
		return m.detailView(width)
	case screenRun:
		return m.runView(width)
	case screenProviders:
		return m.providersView(width)
	case screenSandbox:
		return m.sandboxView(width)
	}
	return ""
}

// toolsView lists tools grouped by category, with the cursor marked.
func (m *Model) toolsView(width int) string {
	if len(m.tools) == 0 {
		if m.failure != "" {
			return pane(styleError.Render("cannot list tools")+"\n\n"+
				styleMuted.Render(m.failure)+"\n\n"+
				styleSubtext.Render("Start the server with:  agent-tooling-tui --start-service"), width, true)
		}
		return pane(styleMuted.Render("no tools registered"), width, true)
	}

	visible := m.visibleTools()
	if len(visible) == 0 {
		return pane(styleMuted.Render("no tools match "+quote(m.filter)), width, true)
	}

	var b strings.Builder
	lastCategory := ""
	for i, t := range visible {
		if t.Category != lastCategory {
			if lastCategory != "" {
				b.WriteString("\n")
			}
			b.WriteString(styleTitle.Render(strings.ToUpper(t.Category)) + "\n")
			lastCategory = t.Category
		}
		line := fmt.Sprintf("%-24s %s", t.Name, styleMuted.Render(truncate(t.Description, max(10, width-32))))
		if i == m.toolCursor {
			line = styleSelected.Render(fmt.Sprintf(" %-22s %s", t.Name, truncate(t.Description, max(8, width-34))))
		} else {
			line = " " + line
		}
		b.WriteString(line + "\n")

		if m.expanded[t.Name] {
			for _, p := range t.Parameters {
				req := "optional"
				if p.Required {
					req = styleWarning.Render("required")
				}
				b.WriteString(styleDim.Render("    ") +
					fmt.Sprintf("%-16s %-8s %s\n", p.Name, p.Type, req))
			}
		}
	}
	return pane(strings.TrimRight(b.String(), "\n"), width, true)
}

func (m *Model) detailView(width int) string {
	if m.detail == nil {
		if m.busy != "" {
			return pane(styleMuted.Render("loading schema…"), width, true)
		}
		return pane(styleMuted.Render("select a tool and press enter"), width, true)
	}
	body := m.detailVP.View()
	if m.detailErr != "" {
		body += "\n\n" + styleWarning.Render("schema unavailable: "+m.detailErr)
	}
	return pane(body, width, true)
}

func (m *Model) runView(width int) string {
	if m.runTool == "" {
		return pane(styleMuted.Render("press x on a tool to run it"), width, true)
	}
	body := m.runVP.View()
	if m.runErr != "" {
		body += "\n\n" + styleError.Render(m.runErr)
	}
	return pane(body, width, true)
}

func (m *Model) providersView(width int) string {
	if m.providersText == "" {
		if m.busy != "" {
			return pane(styleMuted.Render("loading providers…"), width, true)
		}
		return pane(styleMuted.Render("no provider data"), width, true)
	}
	return pane(m.providersVP.View(), width, true)
}

// sandboxView reports where tools run, and only what was actually observed.
func (m *Model) sandboxView(width int) string {
	if m.sandbox == nil {
		if m.sandboxErr != "" {
			return pane(styleWarning.Render("sandbox status unavailable")+"\n\n"+
				styleMuted.Render(m.sandboxErr)+"\n\n"+
				styleSubtext.Render("This comes from the project's own registry and\n"+
					"interceptor; it is not inferred, so nothing is\n"+
					"shown when the probe cannot run."), width, true)
		}
		if m.busy != "" {
			return pane(styleMuted.Render("probing workspace…"), width, true)
		}
		return pane(styleMuted.Render("press r to probe"), width, true)
	}

	s := *m.sandbox
	var b strings.Builder
	b.WriteString(styleTitle.Render("Execution workspace") + "\n")
	if s.Unsandboxed() {
		b.WriteString("  " + styleWarning.Render(s.Workspace) + "  " +
			styleMuted.Render("tools run in-process on the host") + "\n")
	} else {
		b.WriteString("  " + styleSuccess.Render(s.Workspace) + "  " +
			styleMuted.Render("tools run isolated") + "\n")
	}
	b.WriteString("\n" + styleTitle.Render("Registered tools") + "\n")
	b.WriteString(fmt.Sprintf("  %d in the registry\n", s.ToolCount))

	b.WriteString("\n" + styleTitle.Render("Declaring sandbox_required") + "\n")
	if len(s.SandboxRequired) == 0 {
		b.WriteString("  " + styleMuted.Render("none") + "  " +
			styleMuted.Render("(the decorator supports it; no tool sets it today)") + "\n")
	} else {
		for _, name := range s.SandboxRequired {
			b.WriteString("  " + styleWarning.Render(name) + "\n")
		}
	}
	b.WriteString("\n" + styleDim.Render("Read from the project's own ToolRegistry and\n"+
		"ToolingInterceptor, the same source the server uses."))
	return pane(b.String(), width, true)
}

// detailContent renders the schema screen body.
func (m *Model) detailContent() string {
	if m.detail == nil {
		return ""
	}
	var b strings.Builder
	b.WriteString(styleTitle.Render(m.detail.Name) + "\n")
	b.WriteString(styleSubtext.Render(m.detail.Description) + "\n\n")

	badge := styleBadgeOff.Render("mcp off")
	if m.detail.MCPEnabled {
		badge = styleBadgeOK.Render("mcp on")
	}
	b.WriteString(styleMuted.Render("category ") + styleText.Render(m.detail.Category) + "  " + badge + "\n\n")

	b.WriteString(styleTitle.Render("Parameters") + "\n")
	if len(m.detail.Parameters) == 0 {
		b.WriteString(styleMuted.Render("  none") + "\n")
	}
	for _, p := range m.detail.Parameters {
		req := styleMuted.Render("optional")
		if p.Required {
			req = styleWarning.Render("required")
		}
		b.WriteString(fmt.Sprintf("  %-18s %-8s %s\n", styleText.Render(p.Name), styleInfo.Render(p.Type), req))
		if p.Description != "" {
			b.WriteString(styleMuted.Render("      "+p.Description) + "\n")
		}
	}

	if len(m.detailJSON) > 0 {
		var pretty strings.Builder
		if err := indentJSON(m.detailJSON, &pretty); err == nil {
			b.WriteString("\n" + styleTitle.Render("OpenAI schema") + "\n")
			for _, line := range strings.Split(strings.TrimRight(pretty.String(), "\n"), "\n") {
				b.WriteString(styleSubtext.Render(line) + "\n")
			}
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// runContent renders the live run transcript.
func (m *Model) runContent() string {
	var b strings.Builder
	b.WriteString(styleTitle.Render("Run: "+m.runTool) + "\n")
	if len(m.runParams) > 0 {
		if payload, err := json.Marshal(m.runParams); err == nil {
			b.WriteString(styleMuted.Render(string(payload)) + "\n")
		}
	}
	b.WriteString("\n")

	for _, f := range m.runFrames {
		switch f.Type {
		case "tool_call":
			b.WriteString(styleInfo.Render("→ tool_call "+f.Name) + "\n")
		case "tool_result":
			if f.Result != nil && f.Result.Success {
				b.WriteString(styleSuccess.Render("✓ result") + " " +
					styleMuted.Render(fmt.Sprintf("%.1fms", f.Result.ExecutionTimeMS)) + "\n")
			} else if f.Result != nil {
				b.WriteString(styleError.Render("✗ failed") + " " + styleMuted.Render(f.Result.ErrorText()) + "\n")
			}
		case "text":
			b.WriteString(styleText.Render(f.Content) + "\n")
		case "done":
			b.WriteString(styleDim.Render("— session done —") + "\n")
		}
	}

	if m.runResult != nil && m.runResult.Success {
		b.WriteString("\n" + styleTitle.Render("Data") + "\n")
		b.WriteString(styleText.Render(prettyAny(m.runResult.Data)) + "\n")
	}
	return strings.TrimRight(b.String(), "\n")
}

// --- helpers -----------------------------------------------------------------

// visibleTools applies the active filter.
func (m *Model) visibleTools() []api.Tool {
	if m.filter == "" {
		return m.tools
	}
	needle := strings.ToLower(m.filter)
	var out []api.Tool
	for _, t := range m.tools {
		if strings.Contains(strings.ToLower(t.Name), needle) ||
			strings.Contains(strings.ToLower(t.Description), needle) ||
			strings.Contains(strings.ToLower(t.Category), needle) {
			out = append(out, t)
		}
	}
	return out
}

// cursorTool names the tool under the cursor.
//
// Guarded because the cursor can outlive the list it indexed: a refresh that
// shortens the list would otherwise panic on the next key press.
func (m *Model) cursorTool() string {
	visible := m.visibleTools()
	if m.toolCursor < 0 || m.toolCursor >= len(visible) {
		return ""
	}
	return visible[m.toolCursor].Name
}

// toolExists reports whether name is still in the loaded tool list.
func (m *Model) toolExists(name string) bool {
	for _, t := range m.tools {
		if t.Name == name {
			return true
		}
	}
	return false
}

func (m *Model) clampToolCursor() {
	n := len(m.visibleTools())
	switch {
	case n == 0:
		m.toolCursor = 0
	case m.toolCursor >= n:
		m.toolCursor = n - 1
	case m.toolCursor < 0:
		m.toolCursor = 0
	}
	m.selected = m.cursorTool()
}

// paramFields converts a tool's parameters into huh fields.
func (m *Model) paramFields(tool string) []repoField {
	for _, t := range m.tools {
		if t.Name != tool {
			continue
		}
		fields := make([]repoField, 0, len(t.Parameters))
		for _, p := range t.Parameters {
			fields = append(fields, repoField{
				Name:        p.Name,
				Type:        p.Type,
				Description: p.Description,
				Required:    p.Required,
				Default:     p.Default,
				Enum:        p.Enum,
			})
		}
		return fields
	}
	return nil
}

func (m *Model) resizeViewports() {
	w := clampWidth(m.width - 6)
	h := m.height - 8
	if h < 3 {
		h = 3
	}
	m.detailVP.SetWidth(w)
	m.detailVP.SetHeight(h)
	m.runVP.SetWidth(w)
	m.runVP.SetHeight(h)
	m.providersVP.SetWidth(w)
	m.providersVP.SetHeight(h)
}

// lastResult returns the final tool_result frame, if any.
func lastResult(frames []ws.Frame) *ws.ToolResult {
	for i := len(frames) - 1; i >= 0; i-- {
		if frames[i].Result != nil {
			return frames[i].Result
		}
	}
	return nil
}

func indexOf(s screen) int {
	for i, candidate := range screens {
		if candidate == s {
			return i
		}
	}
	return 0
}

func quote(s string) string { return "\"" + s + "\"" }

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// clampHeight trims a rendered block to at most n lines.
func clampHeight(s string, n int) string {
	if n <= 0 {
		return ""
	}
	lines := strings.Split(s, "\n")
	if len(lines) <= n {
		return s
	}
	return strings.Join(lines[:n], "\n")
}
