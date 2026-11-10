package memory

import (
	"context"
	"errors"
	"testing"

	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

func TestAFailedTransactionWritesNothing(t *testing.T) {
	store := NewStore()
	boom := errors.New("boom")
	err := store.Do(context.Background(), func(tx app.Tx) error {
		a, _ := domain.OpenAccount("a", "alice", "EUR")
		if err := tx.Accounts().Save(context.Background(), a); err != nil {
			return err
		}
		return boom
	})
	if !errors.Is(err, boom) {
		t.Fatalf("got %v", err)
	}
	err = store.Do(context.Background(), func(tx app.Tx) error {
		_, err := tx.Accounts().Get(context.Background(), "a")
		return err
	})
	if !errors.Is(err, domain.ErrAccountNotFound) {
		t.Fatalf("the rolled back account is still there: %v", err)
	}
}
