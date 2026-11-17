# ledger

Ledger service: open an account, read a balance, transfer money from one account to another, quote the fee of a transfer. Go, standard library, PostgreSQL in staging and in production.

**Synthetic** repository: a fixture of the harness-ai project. The SQL driver is not linked in this fixture, so the binary runs in memory.

## Getting started

```bash
make run          # serves on :8080, in-memory storage as long as DATABASE_URL is empty
make test         # unit tests
make arch         # checks the dependencies between layers
make lint         # golangci-lint
make e2e          # end-to-end scenarios
```

## Layout

```
cmd/ledgerd/                  the binary: wires the adapters together
internal/domain/              business rules, no dependency
internal/app/                 use cases and ports
internal/adapters/httpapi/    HTTP
internal/adapters/memory/     in-memory storage
internal/adapters/postgres/   SQL storage
migrations/                   schema, numbered files
tools/archcheck/              check of the dependencies between layers
docs/                         decisions, incidents, operations
```

## API

| Method | Path | Role |
|---|---|---|
| POST | `/accounts` | open an account |
| GET | `/accounts/{id}` | read an account |
| POST | `/transfers` | transfer; `Idempotency-Key` header required |
| GET | `/transfers/quote` | fee of a transfer |

See `docs/` for the architecture decisions, the incidents and operations.
