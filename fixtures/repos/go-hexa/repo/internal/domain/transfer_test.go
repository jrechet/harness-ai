package domain

import (
	"errors"
	"testing"
)

func account(t *testing.T, id string, cents int64, currency string) *Account {
	t.Helper()
	a, err := OpenAccount(AccountID(id), "owner-"+id, currency)
	if err != nil {
		t.Fatal(err)
	}
	m, err := NewMoney(cents, currency)
	if err != nil {
		t.Fatal(err)
	}
	a.Balance = m
	return a
}

func TestExecuteMovesMoney(t *testing.T) {
	from, to := account(t, "a", 1000, "EUR"), account(t, "b", 0, "EUR")
	amount, _ := NewMoney(250, "EUR")
	if err := Execute(from, to, amount); err != nil {
		t.Fatal(err)
	}
	if from.Balance.Cents() != 750 || to.Balance.Cents() != 250 {
		t.Fatalf("balances: %s / %s", from.Balance, to.Balance)
	}
}

func TestExecuteChangesNothingWhenItFails(t *testing.T) {
	amount, _ := NewMoney(250, "EUR")
	cases := map[string]struct {
		from, to *Account
		want     error
	}{
		"insufficient funds": {account(t, "a", 100, "EUR"), account(t, "b", 0, "EUR"), ErrInsufficientFunds},
		"same account":       {account(t, "a", 1000, "EUR"), account(t, "a", 1000, "EUR"), ErrSameAccount},
		"mixed currencies":   {account(t, "a", 1000, "EUR"), account(t, "b", 0, "USD"), ErrCurrencyMismatch},
		"frozen destination": {account(t, "a", 1000, "EUR"), func() *Account { a := account(t, "b", 0, "EUR"); a.Frozen = true; return a }(), ErrAccountFrozen},
	}
	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			beforeFrom, beforeTo := c.from.Balance, c.to.Balance
			if err := Execute(c.from, c.to, amount); !errors.Is(err, c.want) {
				t.Fatalf("got %v, want %v", err, c.want)
			}
			if c.from.Balance != beforeFrom || c.to.Balance != beforeTo {
				t.Fatalf("a failed transfer changed a balance")
			}
		})
	}
}
