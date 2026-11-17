package httpapi

import (
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"testing"
)

// Guard for the AGENTS.md rule "every endpoint that changes a balance requires
// Idempotency-Key" (docs/postmortems/2026-04-double-debit.md: "a new write
// endpoint can still forget the key"). Every route that is not a
// read must answer 400 idempotency_key_required when the header is missing.
//
// A route may only be skipped here with a reason. Removing an entry is
// welcome; adding one needs the owner's agreement.
var withoutIdempotencyKey = map[string]string{
	"POST /accounts": "not applied yet, known and written in AGENTS.md",
}

var pathParam = regexp.MustCompile(`\{[^}]*\}`)

func TestWriteRoutesRequireIdempotencyKey(t *testing.T) {
	srv := NewServer(nil)
	h := newServer(t)
	for _, r := range srv.routes() {
		method, path, _ := strings.Cut(r.pattern, " ")
		if method == http.MethodGet || method == http.MethodHead {
			continue
		}
		if reason, ok := withoutIdempotencyKey[r.pattern]; ok {
			t.Logf("%s exempt: %s", r.pattern, reason)
			continue
		}
		t.Run(r.pattern, func(t *testing.T) {
			req := httptest.NewRequest(method, pathParam.ReplaceAllString(path, "x"), strings.NewReader(`{}`))
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)
			if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), "idempotency_key_required") {
				t.Fatalf("%s without Idempotency-Key: got %d %s, want 400 idempotency_key_required "+
					"(AGENTS.md rule, postmortem 2026-04-double-debit)", r.pattern, rec.Code, rec.Body)
			}
		})
	}
}

func TestIdempotencyExemptionsStillExist(t *testing.T) {
	known := map[string]bool{}
	for _, r := range NewServer(nil).routes() {
		known[r.pattern] = true
	}
	for pattern := range withoutIdempotencyKey {
		if !known[pattern] {
			t.Errorf("exemption %q matches no route: remove it", pattern)
		}
	}
}
