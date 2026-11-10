package httpapi

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"example.test/ledger/internal/adapters/memory"
	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

type clock struct{}

func (clock) Now() time.Time { return time.Date(2026, 5, 4, 9, 0, 0, 0, time.UTC) }

type ids struct{ n int }

func (i *ids) NewID() string { i.n++; return fmt.Sprintf("id-%d", i.n) }

func newServer(t *testing.T) http.Handler {
	t.Helper()
	store := memory.NewStore()
	thousand, _ := domain.NewMoney(1000, "EUR")
	store.Seed(
		domain.Account{ID: "alice", Owner: "alice", Balance: thousand},
		domain.Account{ID: "bob", Owner: "bob", Balance: domain.Zero("EUR")},
	)
	return NewServer(app.NewService(store, clock{}, &ids{})).Handler()
}

func post(h http.Handler, path, key, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	if key != "" {
		req.Header.Set("Idempotency-Key", key)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

const transferBody = `{"from":"alice","to":"bob","amount_cents":250,"currency":"EUR"}`

func TestTransferWithoutKeyIsRejected(t *testing.T) {
	rec := post(newServer(t), "/transfers", "", transferBody)
	if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), "idempotency_key_required") {
		t.Fatalf("got %d %s", rec.Code, rec.Body)
	}
}

func TestTransferReplayReturnsTheSameTransfer(t *testing.T) {
	h := newServer(t)
	first, second := post(h, "/transfers", "k1", transferBody), post(h, "/transfers", "k1", transferBody)
	if first.Code != http.StatusCreated || second.Code != http.StatusCreated {
		t.Fatalf("got %d then %d", first.Code, second.Code)
	}
	var a, b struct{ ID string }
	_ = json.Unmarshal(first.Body.Bytes(), &a)
	_ = json.Unmarshal(second.Body.Bytes(), &b)
	if a.ID == "" || a.ID != b.ID {
		t.Fatalf("ids differ: %q and %q", a.ID, b.ID)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/accounts/alice", nil))
	if !strings.Contains(rec.Body.String(), `"balance_cents":750`) {
		t.Fatalf("alice was debited more than once: %s", rec.Body)
	}
}

func TestErrorsMapToStatusCodes(t *testing.T) {
	h := newServer(t)
	cases := map[string]struct {
		key, body string
		want      int
	}{
		"insufficient funds": {"k2", `{"from":"bob","to":"alice","amount_cents":1,"currency":"EUR"}`, http.StatusUnprocessableEntity},
		"unknown account":    {"k3", `{"from":"nobody","to":"alice","amount_cents":1,"currency":"EUR"}`, http.StatusNotFound},
		"broken json":        {"k4", `{`, http.StatusBadRequest},
	}
	for name, c := range cases {
		t.Run(name, func(t *testing.T) {
			if rec := post(h, "/transfers", c.key, c.body); rec.Code != c.want {
				t.Fatalf("got %d %s, want %d", rec.Code, rec.Body, c.want)
			}
		})
	}
}

func TestOpenAccountAndQuote(t *testing.T) {
	h := newServer(t)
	if rec := post(h, "/accounts", "", `{"owner":"carol","currency":"EUR"}`); rec.Code != http.StatusCreated {
		t.Fatalf("got %d %s", rec.Code, rec.Body)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/transfers/quote?amount_cents=1000&currency=EUR", nil))
	if !strings.Contains(rec.Body.String(), `"fee_cents":15`) {
		t.Fatalf("got %s", rec.Body)
	}
}
