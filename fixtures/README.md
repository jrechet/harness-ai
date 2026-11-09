# Fixtures

Des dépôts synthétiques avec des pièges d'instrumentation IA plantés et documentés. C'est le L3 de nos propres skills : la seule façon de savoir si une modification de SKILL.md améliore ou dégrade ce que l'agent trouve.

```
fixtures/repos/<nom>/
├── repo/            # le dépôt synthétique, tel qu'un dev l'aurait laissé
├── traps.md         # chaque piège : id, emplacement, ce que l'audit et status doivent en dire
├── expected.json    # la partie vérifiable par le CLI
└── runs/            # exécutions datées du skill : <date>-audit.md + .json, notées par fixture check
```

Les exécutions se gardent dans `runs/` pour comparer deux versions du skill sur la même fixture. Une exécution faite par la session qui a écrit les pièges est une **base de régression**, pas une mesure : seule une exécution à l'aveugle, par un agent qui n'a lu ni `traps.md` ni `expected.json`, mesure le skill.

## Deux niveaux de vérification

**Déterministe**, à chaque commit : `harness fixture check <nom>` lance `harness status` sur `repo/` et compare au bloc `status` d'`expected.json` (palier, vérifications qui passent et qui échouent, garde-fous détectés). C'est un test unitaire ordinaire, il tourne dans `cli/tests`.

**Éval du skill**, à la main ou en CI avec un agent : on lance harness-audit sur `repo/`, on récupère son bloc JSON dans `repo/.harness/audit.json`, puis `harness fixture check <nom> --audit repo/.harness/audit.json` compare les verdicts au bloc `audit` : chaque piège `T*` doit apparaître avec un verdict accepté sur le bon chemin, chaque élément sain `S*` doit être KEEP, les fuites attendues doivent être dans `process_leaks`, le test « coupe l'agent » doit donner le résultat attendu. Le résultat est un score simple, trouvés / attendus, et la liste de ce qui manque ou est faux.

Un audit qui trouve plus que les pièges n'est pas pénalisé, sauf s'il signale un élément sain : c'est le biais « PUSH_DOWN partout » que la section « Ce qui n'est pas un défaut » du skill est censée empêcher.

## Fixtures disponibles

| Nom | Typologie | Pièges | Ce qu'elle teste |
|---|---|---|---|
| `java-back` | Spring Boot, Gradle, Checkstyle, ArchUnit, release par workflow_dispatch | 12 + 3 sains | CLAUDE.md monolithe, règles racontées vs vérifiées, pré-condition dans un skill, scripts dupliqués, workflow prod sans garde-fou, script mort, retour non structuré, jugement codé en dur |

| `node-front` | Vue 3, Vite, eslint custom, stylelint, size-limit, husky, agent planifié en CI | 11 + 4 sains | Harness qui a l'air sain, au palier 1 : mode déclaré contredit par un agent autonome, « Vérifiée par » mensonger, fichiers d'instructions multi-outils divergents, procédure dupliquée qui diverge du contrat, marqueur de harvest périmé, couverture racontée |

À venir : `python-cli`, `monorepo`.

## Écrire un expected.json

Les verdicts et priorités sont du jugement : deux audits sérieux divergent sur SPLIT contre PUSH_DOWN, ou P1 contre P2. Les premières exécutions à l'aveugle l'ont montré. Être **généreux sur les verdicts et les priorités** (lister toutes les lectures défendables), **strict sur le reste** : le piège doit être trouvé avec une preuve au bon chemin, les règles racontées doivent être dans `process_leaks` (`require_leak`), les éléments sains doivent rester KEEP, les conventions de style ne doivent pas être des fuites (`forbidden_leak_keywords`), un garde-fou mensonger ne doit pas être cru (`forbidden_guarded_paths`).

## Lancer

```bash
python3 cli/harness.py fixture check java-back
python3 cli/harness.py fixture check java-back --audit fixtures/repos/java-back/repo/.harness/audit.json
```
