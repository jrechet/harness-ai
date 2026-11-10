// Package memory is the in-memory adapter: local development and tests.
package memory

import (
	"context"
	"maps"
	"sync"

	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

// Store implements app.UnitOfWork. A transaction works on a copy that replaces
// the stored state only when it succeeds.
type Store struct {
	mu        sync.Mutex
	accounts  map[domain.AccountID]domain.Account
	transfers map[string]domain.Transfer // by idempotency key
}

func NewStore() *Store {
	return &Store{accounts: map[domain.AccountID]domain.Account{}, transfers: map[string]domain.Transfer{}}
}

// Seed puts accounts in the store, bypassing the use cases. Tests only.
func (s *Store) Seed(accounts ...domain.Account) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, a := range accounts {
		s.accounts[a.ID] = a
	}
}

func (s *Store) Do(_ context.Context, fn func(tx app.Tx) error) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	work := &tx{accounts: maps.Clone(s.accounts), transfers: maps.Clone(s.transfers)}
	if err := fn(work); err != nil {
		return err
	}
	s.accounts, s.transfers = work.accounts, work.transfers
	return nil
}

type tx struct {
	accounts  map[domain.AccountID]domain.Account
	transfers map[string]domain.Transfer
}

func (t *tx) Accounts() app.AccountRepository   { return accountRepo{t} }
func (t *tx) Transfers() app.TransferRepository { return transferRepo{t} }

type accountRepo struct{ tx *tx }

func (r accountRepo) Get(_ context.Context, id domain.AccountID) (*domain.Account, error) {
	a, ok := r.tx.accounts[id]
	if !ok {
		return nil, domain.ErrAccountNotFound
	}
	return &a, nil
}

func (r accountRepo) Save(_ context.Context, a *domain.Account) error {
	r.tx.accounts[a.ID] = *a
	return nil
}

type transferRepo struct{ tx *tx }

func (r transferRepo) FindByIdempotencyKey(_ context.Context, key string) (*domain.Transfer, error) {
	t, ok := r.tx.transfers[key]
	if !ok {
		return nil, nil
	}
	return &t, nil
}

func (r transferRepo) Save(_ context.Context, t *domain.Transfer) error {
	r.tx.transfers[t.IdempotencyKey] = *t
	return nil
}
