// Command archcheck fails when a package imports something its layer may not.
// It is the check behind docs/adr/0001-architecture-hexagonale.md and runs in CI.
//
//	go run ./tools/archcheck            # exit 0, or 1 with one line per violation
//	go run ./tools/archcheck -json      # same, as a JSON array
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

const module = "example.test/ledger"

// Violation is one forbidden import.
type Violation struct {
	File   string `json:"file"`
	Import string `json:"import"`
	Rule   string `json:"rule"`
}

type rule struct {
	layer     string   // directory prefix the rule applies to
	forbidden []string // import path prefixes
	why       string
}

var rules = []rule{
	{"internal/domain", []string{module + "/internal/app", module + "/internal/adapters", "net/http", "database/sql", "encoding/json", "os"},
		"the domain depends on nothing: no use case, no adapter, no I/O"},
	{"internal/app", []string{module + "/internal/adapters", "net/http", "database/sql"},
		"a use case knows ports, never an adapter nor a transport"},
	{"internal/adapters/httpapi", []string{module + "/internal/adapters/postgres", module + "/internal/adapters/memory", "database/sql"},
		"adapters do not know each other"},
	{"internal/adapters/postgres", []string{module + "/internal/adapters/httpapi", module + "/internal/adapters/memory", "net/http"},
		"adapters do not know each other"},
	{"internal/adapters/memory", []string{module + "/internal/adapters/httpapi", module + "/internal/adapters/postgres", "net/http", "database/sql"},
		"adapters do not know each other"},
}

// Check walks root and returns every forbidden import. Test files are exempt:
// a test may wire a real adapter.
func Check(root string) ([]Violation, error) {
	var violations []Violation
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		rel, _ := filepath.Rel(root, path)
		rel = filepath.ToSlash(rel)
		for _, r := range rules {
			if !strings.HasPrefix(rel, r.layer+"/") {
				continue
			}
			file, err := parser.ParseFile(token.NewFileSet(), path, nil, parser.ImportsOnly)
			if err != nil {
				return err
			}
			for _, spec := range file.Imports {
				imported, _ := strconv.Unquote(spec.Path.Value)
				for _, f := range r.forbidden {
					if imported == f || strings.HasPrefix(imported, f+"/") {
						violations = append(violations, Violation{File: rel, Import: imported, Rule: r.why})
					}
				}
			}
		}
		return nil
	})
	return violations, err
}

func main() {
	asJSON := flag.Bool("json", false, "print violations as JSON")
	root := flag.String("root", ".", "repository root")
	flag.Parse()
	violations, err := Check(*root)
	if err != nil {
		fmt.Fprintln(os.Stderr, "archcheck:", err)
		os.Exit(2)
	}
	if *asJSON {
		if violations == nil {
			violations = []Violation{}
		}
		_ = json.NewEncoder(os.Stdout).Encode(violations)
	} else {
		for _, v := range violations {
			fmt.Printf("%s: import %q forbidden: %s\n", v.File, v.Import, v.Rule)
		}
	}
	if len(violations) > 0 {
		os.Exit(1)
	}
}
