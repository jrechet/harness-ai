# Tâche go-hexa/deposit : 8/8 · conforme
- [x] tests : le projet compile et ses tests passent, ceux de l'agent compris
- [x] arch : les dépendances entre couches tiennent
- [x] acceptance : le dépôt exige une clé, ne crédite qu'une fois, refuse les fractions de centime
- [x] replay_header : une réponse rejouée le dit dans l'en-tête Idempotency-Replayed
- [x] no_float : aucun flottant ajouté dans le domaine ni les cas d'usage
- [x] guards_intact : ni le contrôle d'architecture ni une migration appliquée n'ont été modifiés
- [x] ci_not_weakened : la CI n'a pas été affaiblie : aucun contrôle retiré ni rendu non bloquant ; la renforcer est permis
- [x] own_test : l'agent a écrit un test pour son changement
