package domain

// AccountID identifies an account.
type AccountID string

// Account is a balance owned by someone. Its balance only changes through
// Debit and Credit, and two balances only change together through Execute.
type Account struct {
	ID      AccountID
	Owner   string
	Balance Money
	Frozen  bool
}

// OpenAccount creates an empty account in one currency.
func OpenAccount(id AccountID, owner, currency string) (*Account, error) {
	zero, err := NewMoney(0, currency)
	if err != nil {
		return nil, err
	}
	return &Account{ID: id, Owner: owner, Balance: zero}, nil
}

func (a *Account) Debit(amount Money) error {
	if a.Frozen {
		return ErrAccountFrozen
	}
	next, err := a.Balance.Sub(amount)
	if err != nil {
		return err
	}
	a.Balance = next
	return nil
}

func (a *Account) Credit(amount Money) error {
	if a.Frozen {
		return ErrAccountFrozen
	}
	next, err := a.Balance.Add(amount)
	if err != nil {
		return err
	}
	a.Balance = next
	return nil
}
