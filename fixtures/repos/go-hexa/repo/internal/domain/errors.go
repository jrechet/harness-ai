package domain

import "errors"

// Sentinel errors of the ledger. Adapters translate them; they never invent their own.
var (
	ErrCurrencyMismatch  = errors.New("currency mismatch")
	ErrNegativeAmount    = errors.New("amount must not be negative")
	ErrZeroAmount        = errors.New("amount must not be zero")
	ErrInsufficientFunds = errors.New("insufficient funds")
	ErrAccountFrozen     = errors.New("account is frozen")
	ErrSameAccount       = errors.New("source and destination are the same account")
	ErrAccountNotFound   = errors.New("account not found")
	ErrUnknownCurrency   = errors.New("unknown currency")
)
