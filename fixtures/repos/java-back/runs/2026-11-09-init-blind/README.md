# Exécution à l'aveugle de harness-init — 2026-11-09

Dépôt nu : java-back sans `CLAUDE.md` ni `.claude/` (`harness fixture bare java-back <dest>`), sur une branche `develop`. Réponses d'entretien fournies : délégation, 3 devs, GitHub Actions « je ne sais pas ce qui est vraiment vérifié », Claude Code seul, première tâche « la release, faite à la main avec des scripts », interdits : prod sans validation humaine, migration appliquée, push sur main.

Résultat : `AGENTS.md` de 44 lignes, palier 1 **5/5**, stub `CLAUDE.md`, contrat `release` de 45 lignes, `.harness/state.json` et `audit.json` commités.

Ce que le contrat produit évite, sans avoir vu les pièges : pas de lecture de `SUCCESS` dans un log (`gh run watch --exit-status`), pré-conditions en commandes et non en phrases, validation humaine explicite avant déclenchement, version donnée par l'humain et non déduite de la branche (« `release.mjs` le fait et se trompe »), et la mise à jour de `VERSION` après release, le défaut non planté trouvé par le premier audit aveugle.

Son audit de gate contre les pièges de java-back : 6/8, les deux absents (T1, T2) portaient sur le `CLAUDE.md` retiré ; donc complet sur ce qui existait. Il a aussi relevé `gradlew` absent du dépôt et un commentaire d'`ArchitectureTest` pointant vers un `CLAUDE.md` inexistant, deux faits vrais.

Faiblesse relevée : la règle « un contrôleur ne dépend jamais d'un repository » porte un « Pourquoi » inventé (« garder les règles testables hors HTTP ») alors qu'aucun incident n'est connu. Le skill demande désormais d'écrire « décision d'architecture, pas d'incident connu » plutôt que d'inventer.
