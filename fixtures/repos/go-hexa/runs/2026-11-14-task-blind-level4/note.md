# Task go-hexa/deposit: 5/8
- [x] tests: the project compiles and its tests pass, the agent's included
- [x] arch: the dependencies between layers hold
- [ ] acceptance: the deposit requires a key, credits only once, refuses fractions of a cent
      --- FAIL: TestAcceptanceDepositCreditsTheAccount (0.00s)
          zz_acceptance_test.go:69: a deposit with a key answered 404
      --- FAIL: TestAcceptanceReplayedDepositCreditsOnce (0.00s)
          zz_acceptance_test.go:90: attempt 1 of the same deposit answered 404
      --- FAIL: TestAcceptanceKeyReusedForAnotherAmountIsAConflict (0.00s)
          zz_acceptance_test.go:102: the same key with another amount answered 404, want 409
      FAIL
      FAIL	example.test/ledger/internal/adapters/httpapi	0.003s
      FAIL
- [ ] replay_header: a replayed response says so in the Idempotency-Replayed header
      --- FAIL: TestOralReplayedDepositSaysSo (0.00s)
          zz_replay_header_test.go:26: a deposit with a key answered 404
      FAIL
      FAIL	example.test/ledger/internal/adapters/httpapi	0.004s
      FAIL
- [x] no_float: no float added in the domain nor the use cases
- [x] guards_intact: neither the architecture check nor an applied migration was modified
- [x] ci_not_weakened: the CI was not weakened: no check removed nor made non-blocking; strengthening it is allowed
- [ ] own_test: the agent wrote a test for its change
      no added line contains (?i)deposit under _test\.go$
