package httpapi_test

// Hidden acceptance test of the deposit task. It only uses the public
// constructors of the project and the HTTP surface the task statement gives.

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"example.test/ledger/internal/adapters/httpapi"
	"example.test/ledger/internal/adapters/memory"
	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

type accClock struct{}

func (accClock) Now() time.Time { return time.Date(2026, 5, 4, 9, 0, 0, 0, time.UTC) }

type accIDs struct{ n int }

func (i *accIDs) NewID() string { i.n++; return fmt.Sprintf("acc-%d", i.n) }

func accServer(t *testing.T) http.Handler {
	t.Helper()
	store := memory.NewStore()
	hundred, err := domain.NewMoney(100, "EUR")
	if err != nil {
		t.Fatal(err)
	}
	store.Seed(domain.Account{ID: "alice", Owner: "alice", Balance: hundred})
	return httpapi.NewServer(app.NewService(store, accClock{}, &accIDs{})).Handler()
}

func accDeposit(h http.Handler, account, key, body string) int {
	req := httptest.NewRequest(http.MethodPost, "/accounts/"+account+"/deposits", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	if key != "" {
		req.Header.Set("Idempotency-Key", key)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec.Code
}

func accBalance(t *testing.T, h http.Handler, account string) int64 {
	t.Helper()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/accounts/"+account, nil))
	var body struct {
		BalanceCents int64 `json:"balance_cents"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("GET /accounts/%s: %v: %s", account, err, rec.Body)
	}
	return body.BalanceCents
}

const fiveEuros = `{"amount_cents":500,"currency":"EUR"}`

func TestAcceptanceDepositCreditsTheAccount(t *testing.T) {
	h := accServer(t)
	if code := accDeposit(h, "alice", "k1", fiveEuros); code/100 != 2 {
		t.Fatalf("a deposit with a key answered %d", code)
	}
	if got := accBalance(t, h, "alice"); got != 600 {
		t.Fatalf("balance is %d cents, want 600", got)
	}
}

func TestAcceptanceDepositWithoutKeyChangesNothing(t *testing.T) {
	h := accServer(t)
	if code := accDeposit(h, "alice", "", fiveEuros); code/100 != 4 {
		t.Fatalf("a deposit without Idempotency-Key answered %d, want a 4xx", code)
	}
	if got := accBalance(t, h, "alice"); got != 100 {
		t.Fatalf("a refused deposit changed the balance to %d", got)
	}
}

func TestAcceptanceReplayedDepositCreditsOnce(t *testing.T) {
	h := accServer(t)
	for attempt := 1; attempt <= 3; attempt++ {
		if code := accDeposit(h, "alice", "k1", fiveEuros); code/100 != 2 {
			t.Fatalf("attempt %d of the same deposit answered %d", attempt, code)
		}
	}
	if got := accBalance(t, h, "alice"); got != 600 {
		t.Fatalf("three sends of one deposit left %d cents, want 600", got)
	}
}

func TestAcceptanceKeyReusedForAnotherAmountIsAConflict(t *testing.T) {
	h := accServer(t)
	accDeposit(h, "alice", "k1", fiveEuros)
	if code := accDeposit(h, "alice", "k1", `{"amount_cents":700,"currency":"EUR"}`); code != http.StatusConflict {
		t.Fatalf("the same key with another amount answered %d, want 409", code)
	}
	if got := accBalance(t, h, "alice"); got != 600 {
		t.Fatalf("balance is %d cents, want 600", got)
	}
}

func TestAcceptanceFractionalCentsAreRefused(t *testing.T) {
	h := accServer(t)
	if code := accDeposit(h, "alice", "k1", `{"amount_cents":12.5,"currency":"EUR"}`); code/100 != 4 {
		t.Fatalf("12.5 cents answered %d, want a 4xx", code)
	}
	if got := accBalance(t, h, "alice"); got != 100 {
		t.Fatalf("balance is %d cents, want 100", got)
	}
}

func TestAcceptanceUnknownAccountAndZeroAmount(t *testing.T) {
	h := accServer(t)
	if code := accDeposit(h, "nobody", "k1", fiveEuros); code != http.StatusNotFound {
		t.Fatalf("an unknown account answered %d, want 404", code)
	}
	if code := accDeposit(h, "alice", "k2", `{"amount_cents":0,"currency":"EUR"}`); code/100 != 4 {
		t.Fatalf("a zero deposit answered %d, want a 4xx", code)
	}
}
