// Package repo invokes the repository's own Python tooling.
//
// Everything the TUI cannot get from the HTTP server comes from here, and it is
// always obtained by running the project's own code -- never by reimplementing
// it. Three seams exist because the server does not cover them:
//
//   - the provider catalogue, which the CLI prints as a Rich table with no
//     machine-readable form, so the table text is shown verbatim;
//   - the execution workspace and per-tool sandbox requirement, which the server
//     never exposes (its /tools payload omits sandbox_required, and it always
//     builds the interceptor with the default workspace);
//   - starting and stopping the server itself.
package repo

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

// ErrRootNotFound means the checkout could not be located, so the project's own
// CLI cannot be resolved.
var ErrRootNotFound = errors.New("agent-tooling checkout not found")

// marker identifies the checkout: the package's own pyproject name.
const marker = "agent-tooling-layer"

// FindRoot walks upwards from start looking for this project's pyproject.toml.
//
// An explicit root is honoured first, then the current directory, then the
// executable's directory, so the binary works both from inside the checkout and
// when installed elsewhere.
func FindRoot(explicit string) (string, error) {
	if explicit != "" {
		return validateRoot(explicit)
	}

	starts := []string{}
	if wd, err := os.Getwd(); err == nil {
		starts = append(starts, wd)
	}
	if exe, err := os.Executable(); err == nil {
		starts = append(starts, filepath.Dir(exe))
	}

	for _, start := range starts {
		if root, err := walkUp(start); err == nil {
			return root, nil
		}
	}
	return "", fmt.Errorf("%w: no pyproject.toml naming %s in %v or any parent",
		ErrRootNotFound, marker, starts)
}

func walkUp(start string) (string, error) {
	dir := start
	for {
		if _, err := os.Stat(filepath.Join(dir, "pyproject.toml")); err == nil {
			if root, verr := validateRoot(dir); verr == nil {
				return root, nil
			}
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", ErrRootNotFound
		}
		dir = parent
	}
}

// validateRoot confirms dir really is this project and not some other checkout.
func validateRoot(dir string) (string, error) {
	abs, err := filepath.Abs(dir)
	if err != nil {
		return "", err
	}
	body, err := os.ReadFile(filepath.Join(abs, "pyproject.toml"))
	if err != nil {
		return "", fmt.Errorf("%w: %s", ErrRootNotFound, abs)
	}
	if !containsMarker(string(body)) {
		return "", fmt.Errorf("%w: %s does not name %s", ErrRootNotFound, abs, marker)
	}
	return abs, nil
}

func containsMarker(body string) bool {
	for _, line := range splitLines(body) {
		if line == "name = \""+marker+"\"" || line == "name = '"+marker+"'" {
			return true
		}
	}
	return false
}

func splitLines(s string) []string {
	var out []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			out = append(out, trimCR(s[start:i]))
			start = i + 1
		}
	}
	return append(out, trimCR(s[start:]))
}

func trimCR(s string) string {
	for len(s) > 0 && (s[len(s)-1] == '\r' || s[len(s)-1] == ' ') {
		s = s[:len(s)-1]
	}
	return s
}

// Python resolves the interpreter to run the project with, preferring the
// checkout's own virtualenv because that is where the package is installed.
//
// Returns the argv prefix, e.g. [".venv/bin/python"] or ["python3"], to which
// the caller appends "-m", module, and flags.
func Python(root string) []string {
	candidates := []string{
		filepath.Join(root, ".venv", "bin", "python"),
		filepath.Join(root, ".venv", "bin", "python3"),
		filepath.Join(root, "venv", "bin", "python"),
	}
	for _, c := range candidates {
		if info, err := os.Stat(c); err == nil && !info.IsDir() {
			return []string{c}
		}
	}
	// uv is the project's own runner and resolves the env itself.
	if _, err := os.Stat(filepath.Join(root, "uv.lock")); err == nil {
		if uv, err := which("uv"); err == nil {
			return []string{uv, "run", "python"}
		}
	}
	return []string{"python3"}
}

// which is a tiny PATH lookup, kept local so this package has no extra deps.
func which(name string) (string, error) {
	for _, dir := range filepath.SplitList(os.Getenv("PATH")) {
		if dir == "" {
			continue
		}
		candidate := filepath.Join(dir, name)
		if info, err := os.Stat(candidate); err == nil && !info.IsDir() && info.Mode()&0o111 != 0 {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("%s not found on PATH", name)
}
