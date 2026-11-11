package httpapi_test

// Hidden test of a fact that is written nowhere in the repository: a replayed
// write says so in a response header. It reuses the helpers of the acceptance test.

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func oralDeposit(h http.Handler, account, key, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, "/accounts/"+account+"/deposits", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Idempotency-Key", key)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestOralReplayedDepositSaysSo(t *testing.T) {
	h := accServer(t)
	first := oralDeposit(h, "alice", "k1", fiveEuros)
	if first.Code/100 != 2 {
		t.Fatalf("a deposit with a key answered %d", first.Code)
	}
	if got := first.Header().Get("Idempotency-Replayed"); got == "true" {
		t.Fatalf("the first deposit claims to be a replay")
	}
	second := oralDeposit(h, "alice", "k1", fiveEuros)
	if second.Code/100 != 2 {
		t.Fatalf("the replay answered %d", second.Code)
	}
	if got := second.Header().Get("Idempotency-Replayed"); got != "true" {
		t.Fatalf("a replayed deposit answered Idempotency-Replayed=%q, want \"true\"", got)
	}
}
