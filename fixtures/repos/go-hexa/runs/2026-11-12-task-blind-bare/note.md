# Tâche go-hexa/deposit : 6/7
- [x] tests : le projet compile et ses tests passent, ceux de l'agent compris
- [x] arch : les dépendances entre couches tiennent
- [x] acceptance : le dépôt exige une clé, ne crédite qu'une fois, refuse les fractions de centime
- [ ] replay_header : une réponse rejouée le dit dans l'en-tête Idempotency-Replayed
      --- FAIL: TestOralReplayedDepositSaysSo (0.00s)
          zz_replay_header_test.go:36: a replayed deposit answered Idempotency-Replayed="", want "true"
      FAIL
      FAIL	example.test/ledger/internal/adapters/httpapi	0.004s
      FAIL
- [x] no_float : aucun flottant ajouté dans le domaine ni les cas d'usage
- [x] guards_intact : ni le contrôle d'architecture, ni la CI, ni une migration appliquée n'ont été modifiés
- [x] own_test : l'agent a écrit un test pour son changement
