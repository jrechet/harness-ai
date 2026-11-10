package app_test

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"example.test/ledger/internal/adapters/memory"
	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

type fixedClock struct{}

func (fixedClock) Now() time.Time { return time.Date(2026, 5, 4, 9, 0, 0, 0, time.UTC) }

type sequence struct{ n int }

func (s *sequence) NewID() string { s.n++; return fmt.Sprintf("id-%d", s.n) }

func newService(t *testing.T, balances map[string]int64) (*app.Service, *memory.Store) {
	t.Helper()
	store := memory.NewStore()
	for id, cents := range balances {
		m, err := domain.NewMoney(cents, "EUR")
		if err != nil {
			t.Fatal(err)
		}
		store.Seed(domain.Account{ID: domain.AccountID(id), Owner: id, Balance: m})
	}
	return app.NewService(store, fixedClock{}, &sequence{}), store
}

func balance(t *testing.T, svc *app.Service, id string) int64 {
	t.Helper()
	a, err := svc.Account(context.Background(), id)
	if err != nil {
		t.Fatal(err)
	}
	return a.Balance.Cents()
}

func TestTransferRequiresAnIdempotencyKey(t *testing.T) {
	svc, _ := newService(t, map[string]int64{"alice": 1000, "bob": 0})
	_, err := svc.Transfer(context.Background(), app.TransferCommand{From: "alice", To: "bob", AmountCents: 100, Currency: "EUR"})
	if !errors.Is(err, app.ErrMissingIdempotencyKey) {
		t.Fatalf("got %v", err)
	}
}

func TestReplayedTransferMovesMoneyOnce(t *testing.T) {
	svc, _ := newService(t, map[string]int64{"alice": 1000, "bob": 0})
	cmd := app.TransferCommand{IdempotencyKey: "k1", From: "alice", To: "bob", AmountCents: 300, Currency: "EUR"}
	first, err := svc.Transfer(context.Background(), cmd)
	if err != nil {
		t.Fatal(err)
	}
	second, err := svc.Transfer(context.Background(), cmd)
	if err != nil {
		t.Fatal(err)
	}
	if first.ID != second.ID {
		t.Fatalf("a replay created a second transfer: %s then %s", first.ID, second.ID)
	}
	if got := balance(t, svc, "alice"); got != 700 {
		t.Fatalf("alice has %d cents, want 700", got)
	}
}

func TestSameKeyWithAnotherRequestIsAConflict(t *testing.T) {
	svc, _ := newService(t, map[string]int64{"alice": 1000, "bob": 0})
	cmd := app.TransferCommand{IdempotencyKey: "k1", From: "alice", To: "bob", AmountCents: 300, Currency: "EUR"}
	if _, err := svc.Transfer(context.Background(), cmd); err != nil {
		t.Fatal(err)
	}
	cmd.AmountCents = 301
	if _, err := svc.Transfer(context.Background(), cmd); !errors.Is(err, app.ErrIdempotencyConflict) {
		t.Fatalf("got %v", err)
	}
}

func TestFailedTransferLeavesBothBalancesUntouched(t *testing.T) {
	svc, _ := newService(t, map[string]int64{"alice": 100, "bob": 50})
	cmd := app.TransferCommand{IdempotencyKey: "k1", From: "alice", To: "bob", AmountCents: 300, Currency: "EUR"}
	if _, err := svc.Transfer(context.Background(), cmd); !errors.Is(err, domain.ErrInsufficientFunds) {
		t.Fatalf("got %v", err)
	}
	if balance(t, svc, "alice") != 100 || balance(t, svc, "bob") != 50 {
		t.Fatal("a failed transfer changed a balance")
	}
}

func TestTransferFromUnknownAccount(t *testing.T) {
	svc, _ := newService(t, map[string]int64{"bob": 0})
	cmd := app.TransferCommand{IdempotencyKey: "k1", From: "nobody", To: "bob", AmountCents: 1, Currency: "EUR"}
	if _, err := svc.Transfer(context.Background(), cmd); !errors.Is(err, domain.ErrAccountNotFound) {
		t.Fatalf("got %v", err)
	}
}

func TestQuoteRoundsTheFeeToTheCent(t *testing.T) {
	svc, _ := newService(t, nil)
	fee, err := svc.Quote(1000, "EUR")
	if err != nil {
		t.Fatal(err)
	}
	if fee.Cents() != 15 {
		t.Fatalf("fee is %d cents, want 15", fee.Cents())
	}
}
