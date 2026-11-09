# Exécution à l'aveugle de harness-init sur un repo déjà instrumenté — 2026-11-09

Cas le plus fréquent en pratique : le repo a déjà un AGENTS.md, des stubs qui divergent, un contrat. Copie de node-front telle quelle, branche `develop`. Réponses d'entretien : délégation (« on a déjà un agent de nuit, autant l'assumer »), 4 devs, GitHub Actions + eslint maison + stylelint + size-limit + husky « et un script i18n dont je ne sais plus ce qu'il vérifie », Claude Code + Copilot + Cursor, première tâche « ajouter un composant, on a un skill mais je ne sais pas s'il est bon », interdits : `src/payment`, tokens sans ticket, PR d'agent sans relecture humaine.

Résultat : palier 1 **5/5**, AGENTS.md 44 → 51 lignes fusionné et non écrasé, Copilot et Cursor ramenés à des stubs, contrat `add-component` complété, `.harness/` commité. Voir `diff.patch`.

Ce qu'il a fait des pièges de la fixture, sans les connaître :

| Piège | Ce que l'init en a fait |
|---|---|
| T1 mode contredit par l'agent de nuit | Délégation assumée ; nouvel Interdit « pas de PR d'agent fusionnée sans relecture humaine » ; `agent-fix-i18n.yml` BLOCK P1 à l'audit |
| T3 « Vérifiée par » mensonger | Règle `t()` **requalifiée** (non vérifiée) après lecture de `check-i18n.mjs` ; le script n'est crédité que pour la parité des clés ; `NewBadge.vue:6` cité comme violation |
| T5 procédure dupliquée qui diverge | Section retirée d'AGENTS.md, story **obligatoire** tranchée dans le contrat |
| T6 Copilot et Cursor divergents | Remplacés par les stubs du template, six contradictions listées dans le compte rendu |
| T7 marqueur périmé | **Gardé tel quel**, « pour ne pas simuler un harvest » : le bon réflexe, désormais dans le skill |
| T8 couverture racontée | Requalifiée (non vérifiée), cible `coverage.thresholds` |
| T10 bruit | Retiré (PascalCase, `const`) |
| T11 `<script setup>` gardé par eslint sans le dire | Passé en « Vérifiée par : eslint.config.js » |

Son audit de gate contre les pièges : 6/7 ; le seul écart est T6, que l'init venait justement de corriger, donc KEEP est le bon verdict. Aucune faiblesse notable ; les trois questions qu'il a posées en fin de compte rendu (retirer l'auto-merge, supprimer le script mort, branche par défaut) sont exactement celles qu'un propriétaire doit trancher.
