# Tâche go-hexa/deposit : 5/8
- [x] tests : le projet compile et ses tests passent, ceux de l'agent compris
- [x] arch : les dépendances entre couches tiennent
- [ ] acceptance : le dépôt exige une clé, ne crédite qu'une fois, refuse les fractions de centime
      --- FAIL: TestAcceptanceDepositCreditsTheAccount (0.00s)
          zz_acceptance_test.go:69: a deposit with a key answered 404
      --- FAIL: TestAcceptanceReplayedDepositCreditsOnce (0.00s)
          zz_acceptance_test.go:90: attempt 1 of the same deposit answered 404
      --- FAIL: TestAcceptanceKeyReusedForAnotherAmountIsAConflict (0.00s)
          zz_acceptance_test.go:102: the same key with another amount answered 404, want 409
      FAIL
      FAIL	example.test/ledger/internal/adapters/httpapi	0.003s
      FAIL
- [ ] replay_header : une réponse rejouée le dit dans l'en-tête Idempotency-Replayed
      --- FAIL: TestOralReplayedDepositSaysSo (0.00s)
          zz_replay_header_test.go:26: a deposit with a key answered 404
      FAIL
      FAIL	example.test/ledger/internal/adapters/httpapi	0.004s
      FAIL
- [x] no_float : aucun flottant ajouté dans le domaine ni les cas d'usage
- [x] guards_intact : ni le contrôle d'architecture ni une migration appliquée n'ont été modifiés
- [x] ci_not_weakened : la CI n'a pas été affaiblie : aucun contrôle retiré ni rendu non bloquant ; la renforcer est permis
- [ ] own_test : l'agent a écrit un test pour son changement
      aucune ligne ajoutée ne contient (?i)deposit sous _test\.go$
