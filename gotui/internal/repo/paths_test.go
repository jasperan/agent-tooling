package repo

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestFindRootLocatesThisCheckout runs against the real repository, which is the
// strongest available check that discovery works.
func TestFindRootLocatesThisCheckout(t *testing.T) {
	root, err := FindRoot("")
	if err != nil {
		t.Fatalf("FindRoot: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, "pyproject.toml")); err != nil {
		t.Fatalf("root %s has no pyproject.toml", root)
	}
	if filepath.Base(root) != "agent-tooling" {
		t.Errorf("root = %s, want the agent-tooling checkout", root)
	}
}

func TestFindRootRejectsAForeignDirectory(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "pyproject.toml"),
		[]byte("[project]\nname = \"something-else\"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := FindRoot(dir); err == nil {
		t.Fatal("want an error for a directory that is not this project")
	}
}

func TestFindRootAcceptsTheExplicitPath(t *testing.T) {
	dir := t.TempDir()
	body := "[project]\nname = \"" + marker + "\"\n"
	if err := os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	got, err := FindRoot(dir)
	if err != nil {
		t.Fatalf("FindRoot: %v", err)
	}
	if got != dir {
		t.Errorf("root = %q, want %q", got, dir)
	}
}

// TestMarkerMatchingIsExact guards against matching a lookalike name such as
// "agent-tooling-layer-extra".
func TestMarkerMatchingIsExact(t *testing.T) {
	cases := map[string]bool{
		"name = \"" + marker + "\"":       true,
		"name = '" + marker + "'":         true,
		"name = \"agent-tooling-layer2\"": false,
		"name = \"deepagents\"":           false,
	}
	for body, want := range cases {
		if got := containsMarker(body); got != want {
			t.Errorf("containsMarker(%q) = %v, want %v", body, got, want)
		}
	}
}

// TestPythonPrefersTheCheckoutVirtualenv pins the interpreter choice: the package
// is installed in .venv, so that is what must run.
func TestPythonPrefersTheCheckoutVirtualenv(t *testing.T) {
	root := t.TempDir()
	bin := filepath.Join(root, ".venv", "bin")
	if err := os.MkdirAll(bin, 0o755); err != nil {
		t.Fatal(err)
	}
	exe := filepath.Join(bin, "python")
	if err := os.WriteFile(exe, []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatal(err)
	}

	got := Python(root)
	if len(got) != 1 || got[0] != exe {
		t.Errorf("Python() = %v, want [%s]", got, exe)
	}
}

func TestPythonFallsBackWhenThereIsNoVirtualenv(t *testing.T) {
	root := t.TempDir()
	got := Python(root)
	if len(got) == 0 {
		t.Fatal("Python() returned nothing")
	}
	// Either a PATH python3 or a uv prefix is acceptable; it must never be empty.
	if strings.TrimSpace(got[0]) == "" {
		t.Errorf("Python() = %v, want a usable interpreter", got)
	}
}

func TestSandboxUnsandboxed(t *testing.T) {
	if !(Sandbox{Workspace: "local"}).Unsandboxed() {
		t.Error("local must report as unsandboxed")
	}
	for _, ws := range []string{"docker", "remote"} {
		if (Sandbox{Workspace: ws}).Unsandboxed() {
			t.Errorf("%s must not report as unsandboxed", ws)
		}
	}
}

func TestStripANSIRemovesColourButKeepsTheTable(t *testing.T) {
	got := stripANSI("\x1b[1;32mok\x1b[0m ┃ value")
	if strings.Contains(got, "\x1b") {
		t.Errorf("escape sequence survived: %q", got)
	}
	if !strings.Contains(got, "ok") || !strings.Contains(got, "┃") {
		t.Errorf("stripANSI removed content: %q", got)
	}
}

func TestStripANSITrimsTrailingNewlines(t *testing.T) {
	if got := stripANSI("text\n\n"); got != "text" {
		t.Errorf("stripANSI = %q, want text", got)
	}
}

// TestDefaultsMatchTheProject ensures the constants stay aligned with the
// repository's own server defaults.
func TestDefaultsMatchTheProject(t *testing.T) {
	if DefaultPort != 8082 {
		t.Errorf("DefaultPort = %d, want the server's 8082", DefaultPort)
	}
	if ServerModule != "agent_tooling.server" {
		t.Errorf("ServerModule = %q", ServerModule)
	}
	if CLIModule != "agent_tooling.cli" {
		t.Errorf("CLIModule = %q", CLIModule)
	}
}
