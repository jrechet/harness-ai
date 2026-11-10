// Package postgres is the SQL adapter used in staging and production.
package postgres

import (
	"context"
	"database/sql"
	"errors"

	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

// Store implements app.UnitOfWork on top of database/sql.
type Store struct{ db *sql.DB }

func NewStore(db *sql.DB) *Store { return &Store{db: db} }

func (s *Store) Do(ctx context.Context, fn func(tx app.Tx) error) error {
	sqlTx, err := s.db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
	if err != nil {
		return err
	}
	if err := fn(&tx{sqlTx}); err != nil {
		return errors.Join(err, sqlTx.Rollback())
	}
	return sqlTx.Commit()
}

type tx struct{ sql *sql.Tx }

func (t *tx) Accounts() app.AccountRepository   { return accountRepo{t.sql} }
func (t *tx) Transfers() app.TransferRepository { return transferRepo{t.sql} }

type accountRepo struct{ sql *sql.Tx }

func (r accountRepo) Get(ctx context.Context, id domain.AccountID) (*domain.Account, error) {
	var (
		owner, currency string
		cents           int64
		frozen          bool
	)
	row := r.sql.QueryRowContext(ctx,
		`SELECT owner, balance_cents, currency, frozen FROM accounts WHERE id = $1 FOR UPDATE`, string(id))
	if err := row.Scan(&owner, &cents, &currency, &frozen); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, domain.ErrAccountNotFound
		}
		return nil, err
	}
	balance, err := domain.NewMoney(cents, currency)
	if err != nil {
		return nil, err
	}
	return &domain.Account{ID: id, Owner: owner, Balance: balance, Frozen: frozen}, nil
}

func (r accountRepo) Save(ctx context.Context, a *domain.Account) error {
	_, err := r.sql.ExecContext(ctx,
		`INSERT INTO accounts (id, owner, balance_cents, currency, frozen) VALUES ($1, $2, $3, $4, $5)
		 ON CONFLICT (id) DO UPDATE SET balance_cents = EXCLUDED.balance_cents, frozen = EXCLUDED.frozen`,
		string(a.ID), a.Owner, a.Balance.Cents(), a.Balance.Currency(), a.Frozen)
	return err
}

type transferRepo struct{ sql *sql.Tx }

func (r transferRepo) FindByIdempotencyKey(ctx context.Context, key string) (*domain.Transfer, error) {
	var (
		t        domain.Transfer
		id       string
		from, to string
		cents    int64
		currency string
	)
	row := r.sql.QueryRowContext(ctx,
		`SELECT id, from_account, to_account, amount_cents, currency, created_at
		 FROM transfers WHERE idempotency_key = $1`, key)
	if err := row.Scan(&id, &from, &to, &cents, &currency, &t.CreatedAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	amount, err := domain.NewMoney(cents, currency)
	if err != nil {
		return nil, err
	}
	t.ID, t.From, t.To, t.Amount, t.IdempotencyKey = domain.TransferID(id), domain.AccountID(from), domain.AccountID(to), amount, key
	return &t, nil
}

func (r transferRepo) Save(ctx context.Context, t *domain.Transfer) error {
	_, err := r.sql.ExecContext(ctx,
		`INSERT INTO transfers (id, from_account, to_account, amount_cents, currency, idempotency_key, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7)`,
		string(t.ID), string(t.From), string(t.To), t.Amount.Cents(), t.Amount.Currency(), t.IdempotencyKey, t.CreatedAt)
	return err
}
