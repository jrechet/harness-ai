// Command ledgerd serves the ledger over HTTP.
package main

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"log"
	"net/http"
	"os"
	"time"

	"example.test/ledger/internal/adapters/httpapi"
	"example.test/ledger/internal/adapters/memory"
	"example.test/ledger/internal/adapters/postgres"
	"example.test/ledger/internal/app"
)

type systemClock struct{}

func (systemClock) Now() time.Time { return time.Now().UTC() }

type randomIDs struct{}

func (randomIDs) NewID() string {
	b := make([]byte, 12)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	return hex.EncodeToString(b)
}

// openStore picks the adapter: SQL when DATABASE_URL is set, memory otherwise.
func openStore() (app.UnitOfWork, error) {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		log.Print("DATABASE_URL is empty: in-memory store, nothing is kept")
		return memory.NewStore(), nil
	}
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(10)
	return postgres.NewStore(db), nil
}

func main() {
	store, err := openStore()
	if err != nil {
		log.Fatal(err)
	}
	addr := os.Getenv("LEDGER_ADDR")
	if addr == "" {
		addr = ":8080"
	}
	server := &http.Server{
		Addr:              addr,
		Handler:           httpapi.NewServer(app.NewService(store, systemClock{}, randomIDs{})).Handler(),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("ledgerd listening on %s", addr)
	log.Fatal(server.ListenAndServe())
}
