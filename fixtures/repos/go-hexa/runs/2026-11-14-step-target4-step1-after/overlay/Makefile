.PHONY: run test test-integration arch lint migrate reset-db

run:
	go run ./cmd/ledgerd

test:
	go test ./...

# Needs a migrated database at DATABASE_URL.
test-integration:
	go test -tags integration ./internal/adapters/postgres/...

arch:
	go run ./tools/archcheck

lint:
	golangci-lint run

# migrate and reset-db refuse any DATABASE_URL that is not a local database.
migrate:
	@DATABASE_URL="$(DATABASE_URL)" go run ./tools/localdb
	for f in migrations/*.sql; do psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -f $$f; done

reset-db:
	@DATABASE_URL="$(DATABASE_URL)" go run ./tools/localdb
	psql "$(DATABASE_URL)" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) migrate
