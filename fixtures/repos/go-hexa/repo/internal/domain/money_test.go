package domain

import (
	"errors"
	"testing"
)

func TestNewMoneyRejectsNegativeAndUnknownCurrency(t *testing.T) {
	if _, err := NewMoney(-1, "EUR"); !errors.Is(err, ErrNegativeAmount) {
		t.Fatalf("negative amount: got %v", err)
	}
	if _, err := NewMoney(100, "XXX"); !errors.Is(err, ErrUnknownCurrency) {
		t.Fatalf("unknown currency: got %v", err)
	}
}

func TestSubNeverGoesNegative(t *testing.T) {
	a, _ := NewMoney(500, "EUR")
	b, _ := NewMoney(501, "EUR")
	if _, err := a.Sub(b); !errors.Is(err, ErrInsufficientFunds) {
		t.Fatalf("got %v", err)
	}
}

func TestAddRefusesMixedCurrencies(t *testing.T) {
	a, _ := NewMoney(500, "EUR")
	b, _ := NewMoney(500, "USD")
	if _, err := a.Add(b); !errors.Is(err, ErrCurrencyMismatch) {
		t.Fatalf("got %v", err)
	}
}

func TestStringShowsMinorUnits(t *testing.T) {
	m, _ := NewMoney(1205, "EUR")
	if got := m.String(); got != "12.05 EUR" {
		t.Fatalf("got %q", got)
	}
}
