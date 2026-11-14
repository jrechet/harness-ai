package httpapi

import (
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"testing"
)

// Guard for the AGENTS.md rule "tout endpoint qui modifie un solde exige
// Idempotency-Key" (docs/postmortems/2026-04-double-debit.md: "un nouvel
// endpoint d'écriture peut encore oublier la clé"). Every route that is not a
// read must answer 400 idempotency_key_required when the header is missing.
//
// A route may only be skipped here with a reason. Removing an entry is
// welcome; adding one needs the owner's agreement.
var withoutIdempotencyKey = map[string]string{
	"POST /accounts": "pas encore appliquée, connu et écrit dans AGENTS.md",
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
			t.Logf("%s exemptée : %s", r.pattern, reason)
			continue
		}
		t.Run(r.pattern, func(t *testing.T) {
			req := httptest.NewRequest(method, pathParam.ReplaceAllString(path, "x"), strings.NewReader(`{}`))
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)
			if rec.Code != http.StatusBadRequest || !strings.Contains(rec.Body.String(), "idempotency_key_required") {
				t.Fatalf("%s sans Idempotency-Key : got %d %s, want 400 idempotency_key_required "+
					"(règle AGENTS.md, postmortem 2026-04-double-debit)", r.pattern, rec.Code, rec.Body)
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
			t.Errorf("exemption %q ne correspond à aucune route : la retirer", pattern)
		}
	}
}
