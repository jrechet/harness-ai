# 2026-11-15 — harness-design à l'aveugle sur release-skill, avec T7

Un agent neuf, sur un kit sans corrigé, skill et CLI au commit 23de229. Environ 100 000 tokens. Une seule exécution.

**Résultat : 6 pièges trouvés sur 7, aucun élément sain déplacé** (`check.md`). Noté avant toute correction.

## L'écart : T7, le même que C2 sur la fixture tenue à l'écart

La pré-condition « pas de release avec des fichiers non commités », que le propriétaire dit sans gravité mais à ne pas oublier, part en permission de l'agent. L'agent écrit dans `notes.md` ce que l'agent de `ticket-vers-pr` avait écrit : en `rule`, `incident=no` mène à du texte, et il a pris `limit` pour obtenir un verrou.

Deux agents indépendants, deux fixtures, la même impasse et le même détour : c'est la grille. La correction suit dans le commit d'après ; ce plan reste noté tel quel.

## Autres remontées (`notes.md`)

- Sous `compute`, « une version mal calculée est un incident » ne change rien : troisième fois que c'est dit.
- Le skill ne dit pas si une revue peut ajouter un morceau sans `current`, ni quel `current` donner à une vérification seulement racontée dans un SKILL.md.
