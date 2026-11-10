package app

import (
	"math"

	"example.test/ledger/internal/domain"
)

// feeRate is the share kept on every transfer between two owners.
const feeRate = 0.015

// Quote returns the fee a transfer of this amount would cost.
func (s *Service) Quote(amountCents int64, currency string) (domain.Money, error) {
	amount, err := domain.NewMoney(amountCents, currency)
	if err != nil {
		return domain.Money{}, err
	}
	fee := math.Round(float64(amount.Cents()) * feeRate)
	return domain.NewMoney(int64(fee), currency)
}
