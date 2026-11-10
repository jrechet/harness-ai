package app

import (
	"context"
	"errors"

	"example.test/ledger/internal/domain"
)

var (
	ErrMissingIdempotencyKey = errors.New("idempotency key is required")
	ErrIdempotencyConflict   = errors.New("idempotency key already used for a different request")
)

// Service exposes the use cases of the ledger.
type Service struct {
	uow   UnitOfWork
	clock Clock
	ids   IDGenerator
}

func NewService(uow UnitOfWork, clock Clock, ids IDGenerator) *Service {
	return &Service{uow: uow, clock: clock, ids: ids}
}

// OpenAccount creates an empty account.
func (s *Service) OpenAccount(ctx context.Context, owner, currency string) (*domain.Account, error) {
	account, err := domain.OpenAccount(domain.AccountID(s.ids.NewID()), owner, currency)
	if err != nil {
		return nil, err
	}
	err = s.uow.Do(ctx, func(tx Tx) error { return tx.Accounts().Save(ctx, account) })
	if err != nil {
		return nil, err
	}
	return account, nil
}

// Account returns one account.
func (s *Service) Account(ctx context.Context, id string) (*domain.Account, error) {
	var account *domain.Account
	err := s.uow.Do(ctx, func(tx Tx) error {
		a, err := tx.Accounts().Get(ctx, domain.AccountID(id))
		account = a
		return err
	})
	return account, err
}

// TransferCommand is the input of Transfer.
type TransferCommand struct {
	IdempotencyKey string
	From, To       string
	AmountCents    int64
	Currency       string
}

// Transfer moves money once per idempotency key. A replay of the same request
// returns the first transfer; the same key with another request is a conflict.
func (s *Service) Transfer(ctx context.Context, cmd TransferCommand) (*domain.Transfer, error) {
	if cmd.IdempotencyKey == "" {
		return nil, ErrMissingIdempotencyKey
	}
	amount, err := domain.NewMoney(cmd.AmountCents, cmd.Currency)
	if err != nil {
		return nil, err
	}
	var result *domain.Transfer
	err = s.uow.Do(ctx, func(tx Tx) error {
		// The lookup and the write share one transaction. Looking the key up
		// before opening it is what debited an account twice in April 2026.
		previous, err := tx.Transfers().FindByIdempotencyKey(ctx, cmd.IdempotencyKey)
		if err != nil {
			return err
		}
		if previous != nil {
			if !sameRequest(previous, cmd, amount) {
				return ErrIdempotencyConflict
			}
			result = previous
			return nil
		}
		from, err := tx.Accounts().Get(ctx, domain.AccountID(cmd.From))
		if err != nil {
			return err
		}
		to, err := tx.Accounts().Get(ctx, domain.AccountID(cmd.To))
		if err != nil {
			return err
		}
		if err := domain.Execute(from, to, amount); err != nil {
			return err
		}
		transfer := &domain.Transfer{
			ID:             domain.TransferID(s.ids.NewID()),
			From:           from.ID,
			To:             to.ID,
			Amount:         amount,
			IdempotencyKey: cmd.IdempotencyKey,
			CreatedAt:      s.clock.Now(),
		}
		if err := tx.Accounts().Save(ctx, from); err != nil {
			return err
		}
		if err := tx.Accounts().Save(ctx, to); err != nil {
			return err
		}
		if err := tx.Transfers().Save(ctx, transfer); err != nil {
			return err
		}
		result = transfer
		return nil
	})
	if err != nil {
		return nil, err
	}
	return result, nil
}

func sameRequest(t *domain.Transfer, cmd TransferCommand, amount domain.Money) bool {
	return string(t.From) == cmd.From && string(t.To) == cmd.To && t.Amount == amount
}
