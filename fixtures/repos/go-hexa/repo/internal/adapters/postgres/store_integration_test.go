//go:build integration

package postgres

import (
	"context"
	"database/sql"
	"os"
	"testing"

	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

// Runs against DATABASE_URL: `make test-integration`. Needs a migrated database.
func TestAccountRoundTrip(t *testing.T) {
	db, err := sql.Open("pgx", os.Getenv("DATABASE_URL"))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	store := NewStore(db)
	a, _ := domain.OpenAccount("it-1", "integration", "EUR")
	err = store.Do(context.Background(), func(tx app.Tx) error { return tx.Accounts().Save(context.Background(), a) })
	if err != nil {
		t.Fatal(err)
	}
}
