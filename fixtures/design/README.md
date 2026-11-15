# Fixtures de harness-design

Des artefacts mal rangés, avec leur corrigé. Elles mesurent ce que `harness-design` trouve en revue : chaque morceau mal placé est-il envoyé au bon endroit, avec sa preuve, sans toucher à ce qui est sain ?

```
fixtures/design/<nom>/
├── request.md       # la demande et les réponses du propriétaire : se donne à l'agent évalué
├── artifact/        # le skill, l'agent, les règles à revoir : se donne à l'agent évalué
├── traps.md         # chaque piège et chaque élément sain, et ce que le plan doit en dire
├── expected.json    # le corrigé lu par le noteur : fichier, lignes, destinations acceptées
└── runs/            # plans datés ; <date>-author = le plan de l'auteur des pièges
```

`traps.md`, `expected.json` et `runs/` ne se donnent jamais à l'agent évalué. Le plan de l'auteur est une base de régression, pas une mesure : seule une exécution à l'aveugle mesure le skill, et elle se lance à la demande du propriétaire.

## Noter un plan

```bash
python3 cli/harness.py place check <pieces.json> --expected fixtures/design/<nom>/expected.json
```

Le noteur est généreux sur la destination (plusieurs sont acceptées par piège), strict sur la preuve (le morceau cite une ligne de la plage attendue, `chemin:ligne` relatif à `artifact/`) et sur les éléments sains (aucun ne reçoit un verdict autre que KEEP). Sortie 0 si tous les pièges sont trouvés sans élément sain déplacé, 1 sinon.

`cli/tests/test_place.py` vérifie à chaque commit que chaque corrigé cite des lignes qui existent et que le plan de son auteur le passe.

## Fixtures disponibles

| Nom | Artefact | Pièges | Ce qu'elle teste |
|---|---|---|---|
| `release-skill` | Un skill de release, son sous-agent, deux règles d'AGENTS.md | 6 + 3 sains | Limite racontée, calcul en prose, vérification racontée, livraison avec jeton depuis le poste, arborescence recopiée, limite de l'agent écrite en règle ; et ne pas toucher un jugement, un sous-agent justifié, une règle qui cite son check |
| `ticket-vers-pr` | **Tenue à l'écart** (`holdout`), en création : une demande de douze besoins pour un outil ticket → PR | 12 | Donner sa place à chaque nature de morceau à partir d'une demande : lecture et écriture par MCP, pré-condition en code, limite de l'agent contre limite de tous, règle bloquante, sous-agent, jugement, convention de dossier, rien à écrire |

Une fixture de création porte `"mode": "create"` dans son corrigé : rien n'existe, les morceaux n'ont pas de `current`, et le noteur compte la destination rendue. Une fixture `holdout` ne sert jamais à corriger le skill ou la grille.
