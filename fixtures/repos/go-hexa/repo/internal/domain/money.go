// Package domain holds the business rules of the ledger. It imports nothing but
// pure standard-library packages: no HTTP, no SQL, no adapter.
package domain

import "fmt"

// Money is an amount in minor units (cents) of one currency.
// See docs/adr/0002-amounts-in-cents.md.
type Money struct {
	cents    int64
	currency string
}

var currencies = map[string]bool{"EUR": true, "USD": true, "GBP": true}

// NewMoney builds an amount. Negative amounts do not exist in this ledger:
// a movement has a direction, not a sign.
func NewMoney(cents int64, currency string) (Money, error) {
	if !currencies[currency] {
		return Money{}, fmt.Errorf("%w: %q", ErrUnknownCurrency, currency)
	}
	if cents < 0 {
		return Money{}, ErrNegativeAmount
	}
	return Money{cents: cents, currency: currency}, nil
}

// Zero is the empty balance of a currency.
func Zero(currency string) Money { return Money{currency: currency} }

func (m Money) Cents() int64     { return m.cents }
func (m Money) Currency() string { return m.currency }
func (m Money) IsZero() bool     { return m.cents == 0 }

func (m Money) Add(o Money) (Money, error) {
	if m.currency != o.currency {
		return Money{}, ErrCurrencyMismatch
	}
	return Money{cents: m.cents + o.cents, currency: m.currency}, nil
}

// Sub fails rather than produce a negative amount.
func (m Money) Sub(o Money) (Money, error) {
	if m.currency != o.currency {
		return Money{}, ErrCurrencyMismatch
	}
	if o.cents > m.cents {
		return Money{}, ErrInsufficientFunds
	}
	return Money{cents: m.cents - o.cents, currency: m.currency}, nil
}

func (m Money) String() string {
	return fmt.Sprintf("%d.%02d %s", m.cents/100, m.cents%100, m.currency)
}
