// Package httpapi is the HTTP adapter: it translates requests into use cases
// and domain errors into status codes. No business rule lives here.
package httpapi

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"

	"example.test/ledger/internal/app"
	"example.test/ledger/internal/domain"
)

type Server struct{ svc *app.Service }

func NewServer(svc *app.Service) *Server { return &Server{svc: svc} }

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusNoContent) })
	mux.HandleFunc("POST /accounts", s.openAccount)
	mux.HandleFunc("GET /accounts/{id}", s.getAccount)
	mux.HandleFunc("POST /transfers", s.createTransfer)
	mux.HandleFunc("GET /transfers/quote", s.quote)
	return mux
}

type accountBody struct {
	ID           string `json:"id"`
	Owner        string `json:"owner"`
	BalanceCents int64  `json:"balance_cents"`
	Currency     string `json:"currency"`
	Frozen       bool   `json:"frozen"`
}

func toAccountBody(a *domain.Account) accountBody {
	return accountBody{ID: string(a.ID), Owner: a.Owner, BalanceCents: a.Balance.Cents(), Currency: a.Balance.Currency(), Frozen: a.Frozen}
}

func (s *Server) openAccount(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Owner    string `json:"owner"`
		Currency string `json:"currency"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Owner == "" {
		writeError(w, http.StatusBadRequest, "invalid_body", "owner and currency are required")
		return
	}
	account, err := s.svc.OpenAccount(r.Context(), body.Owner, body.Currency)
	if err != nil {
		writeDomainError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, toAccountBody(account))
}

func (s *Server) getAccount(w http.ResponseWriter, r *http.Request) {
	account, err := s.svc.Account(r.Context(), r.PathValue("id"))
	if err != nil {
		writeDomainError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, toAccountBody(account))
}

func (s *Server) createTransfer(w http.ResponseWriter, r *http.Request) {
	var body struct {
		From        string `json:"from"`
		To          string `json:"to"`
		AmountCents int64  `json:"amount_cents"`
		Currency    string `json:"currency"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_body", "the body is not valid JSON")
		return
	}
	transfer, err := s.svc.Transfer(r.Context(), app.TransferCommand{
		IdempotencyKey: r.Header.Get("Idempotency-Key"),
		From:           body.From,
		To:             body.To,
		AmountCents:    body.AmountCents,
		Currency:       body.Currency,
	})
	if err != nil {
		writeDomainError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, map[string]any{
		"id":           string(transfer.ID),
		"from":         string(transfer.From),
		"to":           string(transfer.To),
		"amount_cents": transfer.Amount.Cents(),
		"currency":     transfer.Amount.Currency(),
		"created_at":   transfer.CreatedAt,
	})
}

func (s *Server) quote(w http.ResponseWriter, r *http.Request) {
	cents, err := strconv.ParseInt(r.URL.Query().Get("amount_cents"), 10, 64)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_amount", "amount_cents must be an integer")
		return
	}
	fee, err := s.svc.Quote(cents, r.URL.Query().Get("currency"))
	if err != nil {
		writeDomainError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"fee_cents": fee.Cents(), "currency": fee.Currency()})
}

// writeDomainError is the only place where an error becomes a status code.
func writeDomainError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, app.ErrMissingIdempotencyKey):
		writeError(w, http.StatusBadRequest, "idempotency_key_required", err.Error())
	case errors.Is(err, app.ErrIdempotencyConflict):
		writeError(w, http.StatusConflict, "idempotency_conflict", err.Error())
	case errors.Is(err, domain.ErrAccountNotFound):
		writeError(w, http.StatusNotFound, "account_not_found", err.Error())
	case errors.Is(err, domain.ErrInsufficientFunds), errors.Is(err, domain.ErrAccountFrozen),
		errors.Is(err, domain.ErrSameAccount), errors.Is(err, domain.ErrZeroAmount),
		errors.Is(err, domain.ErrCurrencyMismatch), errors.Is(err, domain.ErrNegativeAmount),
		errors.Is(err, domain.ErrUnknownCurrency):
		writeError(w, http.StatusUnprocessableEntity, "rejected", err.Error())
	default:
		writeError(w, http.StatusInternalServerError, "internal", "internal error")
	}
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, map[string]string{"code": code, "message": message})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
