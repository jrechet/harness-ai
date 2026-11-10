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

migrate:
	@test -n "$(DATABASE_URL)" || (echo "DATABASE_URL is empty" && exit 1)
	for f in migrations/*.sql; do psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -f $$f; done

reset-db:
	@test -n "$(DATABASE_URL)" || (echo "DATABASE_URL is empty" && exit 1)
	psql "$(DATABASE_URL)" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) migrate
