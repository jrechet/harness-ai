// Command migrationcheck fails when a change touches an existing file of
// migrations/. An applied migration is never edited: staging and production only
// replay what deploy.yml hands them, so a new file with the next number is added
// instead. Runs in CI (job migrations) against the pull request's base commit.
//
//	go run ./tools/migrationcheck -base origin/main   # exit 0, or 1 with one line per violation
package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

// Violation is one existing migration that was modified, renamed or deleted.
type Violation struct {
	Status string
	File   string
}

// Check reads the output of `git diff --name-status` and returns every entry
// that is not a pure addition.
func Check(nameStatus string) []Violation {
	var violations []Violation
	sc := bufio.NewScanner(strings.NewReader(nameStatus))
	for sc.Scan() {
		fields := strings.Split(sc.Text(), "\t")
		if len(fields) < 2 || fields[0] == "" {
			continue
		}
		if fields[0] == "A" {
			continue
		}
		// Renames and copies (R100, C075) list the old path first.
		violations = append(violations, Violation{Status: fields[0], File: fields[1]})
	}
	return violations
}

func main() {
	base := flag.String("base", "origin/main", "commit the change is compared to")
	dir := flag.String("dir", "migrations", "migrations directory")
	repo := flag.String("repo", ".", "repository root")
	flag.Parse()

	// No second commit: the working tree is compared, uncommitted edits included.
	out, err := exec.Command("git", "-C", *repo, "diff", "--name-status", "-M", *base, "--", *dir).Output()
	if err != nil {
		fmt.Fprintln(os.Stderr, "migrationcheck: git diff:", err)
		os.Exit(2)
	}
	violations := Check(string(out))
	for _, v := range violations {
		fmt.Printf("%s: existing migration changed (%s); add a new file with the next number instead\n", v.File, v.Status)
	}
	if len(violations) > 0 {
		os.Exit(1)
	}
}
