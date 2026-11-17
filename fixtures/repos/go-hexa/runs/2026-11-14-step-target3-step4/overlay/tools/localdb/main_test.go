package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestCheck(t *testing.T) {
	cases := []struct {
		name   string
		dsn    string
		pghost string
		ok     bool
	}{
		{"empty", "", "", false},
		{"localhost", "postgres://u@localhost:5432/ledger", "", true},
		{"loopback v4", "postgresql://u:p@127.0.0.1/ledger", "", true},
		{"loopback v6", "postgres://u@[::1]:5432/ledger", "", true},
		{"unix socket, no host", "postgres:///ledger", "", true},
		{"unix socket via query", "postgres:///ledger?host=/var/run/postgresql", "", true},
		{"keyword form local", "host=localhost dbname=ledger", "", true},
		{"staging", "postgres://u@staging.example/ledger_staging", "", false},
		{"staging via query host", "postgres://u@localhost/ledger?host=db.staging.example", "", false},
		{"staging via PGHOST", "postgres:///ledger_staging", "db.staging.example", false},
		{"multi-host with one remote", "postgres://u@localhost:5432,prod.example:5432/ledger", "", false},
		{"keyword form remote", "host=prod.example dbname=ledger_prod", "", false},
		{"unparseable", "ledger_staging", "", false},
	}
	for _, c := range cases {
		env := func(k string) string {
			if k == "PGHOST" {
				return c.pghost
			}
			return ""
		}
		if err := Check(c.dsn, env); (err == nil) != c.ok {
			t.Errorf("%s: Check(%q) = %v, want ok=%v", c.name, c.dsn, err, c.ok)
		}
	}
}

// TestMakeTargetsRefuseRemote runs the real Makefile targets with a fake psql
// that records its calls: a remote DATABASE_URL must stop before psql.
func TestMakeTargetsRefuseRemote(t *testing.T) {
	if _, err := exec.LookPath("make"); err != nil {
		t.Skip("make not installed")
	}
	bin := t.TempDir()
	calls := filepath.Join(bin, "calls")
	fake := "#!/bin/sh\necho \"$@\" >> " + calls + "\n"
	if err := os.WriteFile(filepath.Join(bin, "psql"), []byte(fake), 0o755); err != nil {
		t.Fatal(err)
	}
	for _, target := range []string{"reset-db", "migrate"} {
		for _, tc := range []struct {
			url    string
			wantOK bool
		}{
			{"postgres://u@staging.example/ledger_staging", false},
			{"postgres://u@localhost/ledger", true},
		} {
			os.Remove(calls)
			cmd := exec.Command("make", "-s", "-C", "../..", target)
			cmd.Env = append(os.Environ(), "PATH="+bin+string(os.PathListSeparator)+os.Getenv("PATH"),
				"DATABASE_URL="+tc.url, "PGHOST=", "PGHOSTADDR=")
			out, err := cmd.CombinedOutput()
			_, statErr := os.Stat(calls)
			psqlCalled := statErr == nil
			if (err == nil) != tc.wantOK || psqlCalled != tc.wantOK {
				t.Errorf("make %s with %s: err=%v psql called=%v, want ok=%v\n%s", target, tc.url, err, psqlCalled, tc.wantOK, out)
			}
		}
	}
}
