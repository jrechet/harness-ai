# Task go-hexa/deposit: 6/7
- [x] tests: the project compiles and its tests pass, the agent's included
- [x] arch: the dependencies between layers hold
- [x] acceptance: the deposit requires a key, credits only once, refuses fractions of a cent
- [ ] replay_header: a replayed response says so in the Idempotency-Replayed header
      --- FAIL: TestOralReplayedDepositSaysSo (0.00s)
          zz_replay_header_test.go:36: a replayed deposit answered Idempotency-Replayed="", want "true"
      FAIL
      FAIL	example.test/ledger/internal/adapters/httpapi	0.004s
      FAIL
- [x] no_float: no float added in the domain nor the use cases
- [x] guards_intact: neither the architecture check, nor the CI, nor an applied migration was modified
- [x] own_test: the agent wrote a test for its change
