package domain

import "time"

// TransferID identifies a transfer.
type TransferID string

// Transfer is the record of money that moved between two accounts.
type Transfer struct {
	ID             TransferID
	From, To       AccountID
	Amount         Money
	IdempotencyKey string
	CreatedAt      time.Time
}

// Execute moves amount from one account to the other, or changes nothing.
// Every check happens before the first balance is touched.
func Execute(from, to *Account, amount Money) error {
	if from.ID == to.ID {
		return ErrSameAccount
	}
	if amount.IsZero() {
		return ErrZeroAmount
	}
	if from.Frozen || to.Frozen {
		return ErrAccountFrozen
	}
	if amount.Currency() != from.Balance.Currency() || amount.Currency() != to.Balance.Currency() {
		return ErrCurrencyMismatch
	}
	if err := from.Debit(amount); err != nil {
		return err
	}
	return to.Credit(amount)
}
