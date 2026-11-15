# 2026-11-15 — harness-design à l'aveugle sur release-skill, après révision

Un agent neuf, sur un kit neuf sans corrigé. Environ 103 000 tokens, 62 secondes. Une seule exécution.

**Résultat : 6 pièges trouvés sur 6, aucun élément sain déplacé sur 3** (`check.md`).

## Ce résultat ne se compare pas au précédent

Entre `2026-11-15-blind` et celle-ci, la fixture, le noteur, la grille et le skill ont changé (`traps.md`, section Révisions). C'est une base neuve, pas la mesure d'un progrès : le corrigé a été révisé par la session qui venait de lire la première exécution. Le plan de la première exécution, renoté avec le corrigé révisé, donne 6/6 et un élément sain déplacé (S4).

Ce qu'on peut dire : avec le workflow présent dans l'artefact et la consigne ajoutée au skill, l'agent a ouvert le workflow et gardé la règle qui cite son check.

## Ce que l'agent dit du skill et de la grille (`notes.md`)

- Un check « requis » ne se lit pas dans le dépôt : c'est un réglage de la forge. Le skill ne dit pas comment trancher.
- La grille n'a pas de réponse « rien ne se publie sans » : une règle qui se vérifie à la publication tombe sur un check de fusion.
- « Incident » n'existe pas pour un calcul : une version mal calculée ne pèse rien dans la branche `compute`.
- Hors plan, comme le skill le demande maintenant : une phrase à retirer, un outil manquant au sous-agent, une limite de commitlint sur les fusions en squash.
