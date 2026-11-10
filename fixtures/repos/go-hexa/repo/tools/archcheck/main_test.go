package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestTheRepositoryRespectsItsLayers(t *testing.T) {
	violations, err := Check("../..")
	if err != nil {
		t.Fatal(err)
	}
	for _, v := range violations {
		t.Errorf("%s imports %s: %s", v.File, v.Import, v.Rule)
	}
}

func TestADomainFileImportingAnAdapterIsReported(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "internal", "domain")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	src := "package domain\n\nimport _ \"example.test/ledger/internal/adapters/postgres\"\nimport _ \"net/http\"\n"
	if err := os.WriteFile(filepath.Join(dir, "leak.go"), []byte(src), 0o644); err != nil {
		t.Fatal(err)
	}
	violations, err := Check(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(violations) != 2 {
		t.Fatalf("got %d violations, want 2: %+v", len(violations), violations)
	}
}
