# 2026-11-15 — harness-design à l'aveugle sur release-skill, après `incident=forget`

Un agent neuf, sur un kit sans corrigé, skill et CLI au commit 3d4643e. Environ 100 000 tokens. Une seule exécution.

**Résultat : 7 pièges trouvés sur 7, aucun élément sain déplacé** (`check.md`).

## Ce que ça montre, et ce que ça ne montre pas

Même fixture, même corrigé que `runs/2026-11-15-blind-3` (6/7) : seuls la grille et le skill ont changé entre les deux. L'agent a rangé la pré-condition « fichiers non commités » en règle, `incident=forget`, `bypass_rule=agent`, vers une vérification lancée par un hook : le chemin ajouté, sans détour par une limite.

C'est un point contre un point, sur une fixture que la correction visait. Ça montre que le chemin se trouve ; ça ne dit pas à quelle fréquence. `ticket-vers-pr`, tenue à l'écart, n'a pas été rejouée.

## Remontées (`notes.md`)

- Quatrième fois : sous `compute`, la gravité d'une erreur ne change rien.
- Une préférence propre à un skill n'a pas de `scope` « dans ce skill ».
- « Ne publie jamais hors de main » se lit en limite ou en pré-condition (vers l'étape bloquante de livraison) ; le skill ne départage pas. Les deux destinations sont défendables.
- La destination « vérification lancée par un hook » parle d'« après édition, ou à l'arrêt » ; il faut ici un hook avant le lancement.
- Le `current` d'un calcul ou d'une vérification racontés dans un skill : `skill` ou `session` ?
