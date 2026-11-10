// Package app holds the use cases. It knows the domain and the ports below,
// never a concrete adapter.
package app

import (
	"context"
	"time"

	"example.test/ledger/internal/domain"
)

// AccountRepository stores accounts.
type AccountRepository interface {
	// Get returns domain.ErrAccountNotFound when the account does not exist.
	Get(ctx context.Context, id domain.AccountID) (*domain.Account, error)
	Save(ctx context.Context, a *domain.Account) error
}

// TransferRepository stores transfers.
type TransferRepository interface {
	// FindByIdempotencyKey returns nil, nil when no transfer carries the key.
	FindByIdempotencyKey(ctx context.Context, key string) (*domain.Transfer, error)
	Save(ctx context.Context, t *domain.Transfer) error
}

// Tx gives access to the repositories of one transaction.
type Tx interface {
	Accounts() AccountRepository
	Transfers() TransferRepository
}

// UnitOfWork runs fn in one transaction: everything it wrote is committed
// together, or nothing is when fn returns an error.
type UnitOfWork interface {
	Do(ctx context.Context, fn func(tx Tx) error) error
}

// Clock and IDGenerator are ports so that use cases stay deterministic in tests.
type Clock interface{ Now() time.Time }

type IDGenerator interface{ NewID() string }
