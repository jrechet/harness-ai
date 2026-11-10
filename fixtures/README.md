# Fixtures

Des dépôts synthétiques avec des pièges d'instrumentation IA plantés et documentés. C'est le L3 de nos propres skills : la seule façon de savoir si une modification de SKILL.md améliore ou dégrade ce que l'agent trouve.

```
fixtures/repos/<nom>/
├── repo/            # le dépôt synthétique, tel qu'un dev l'aurait laissé
├── traps.md         # chaque piège ou fait planté : id, emplacement, ce que le skill doit en dire
├── expected.json    # la partie vérifiable par le CLI : blocs status, audit, init
├── owner.md         # projets types seulement : les réponses du propriétaire fictif à l'entretien
└── runs/            # exécutions datées du skill, notées par fixture check
```

Deux familles. Les **fixtures d'audit** (`java-back`, `node-front`, `python-cli`) portent un harness abîmé et peu de code : elles mesurent ce que l'audit trouve. Les **projets types** (`go-hexa`, `ts-monorepo`) sont de vrais petits projets, un par style d'architecture, dont le code tourne et dont les tests passent : ils mesurent le parcours, du palier 0 vers le haut. `owner.md` se donne à l'agent évalué ; `traps.md`, `expected.json` et `runs/` jamais.

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

| `python-cli` | CLI Python 3.12, uv, ruff, mypy en pre-commit, pytest, publication PyPI sur tag | 11 + 4 sains | Harness au **palier 2** mesuré mais creux : jeton PyPI dans un skill, publication depuis le poste qui contourne la CI, garde-fou local pris pour un garde-fou pipeline, `addopts` qui désélectionne les tests lents, `rule:` collecté par harvest mais jamais poussé en garde-fou, AGENTS.md de sous-dossier qui contredit la racine |

| `go-hexa` | **Projet type.** Service Go, architecture hexagonale, bibliothèque standard, ADR, post-mortem, contrôle d'imports testé | 5 faits + 3 pièges + 2 sains | Départ **nu**, palier 0 : ce qu'un init fait remonter du dépôt (incident, action destructrice, garde-fou réel), ce qu'il ne recopie pas (commande périmée, principes génériques), garde-fou déclaré dans un ADR mais non bloquant en CI |
| `ts-monorepo` | **Projet type.** Monorepo npm workspaces TypeScript : API, web, package partagé, contrôle des frontières | 4 faits + 7 bruits + 3 pièges + 2 sains | Départ **généré jamais relu** : un `CLAUDE.md` de `/init` de 104 lignes. Savoir retirer : découvrable, générique, écrit pour d'anciens modèles, nuisible, périmé, contredit par un garde-fou ; et garder les deux lignes qui comptent. Trou de filtre de chemins en CI |

Styles d'architecture à venir, dans l'ordre proposé : monolithe MVC avec ORM et migrations, projet fait à l'arrache et jamais relu, microservices avec contrat d'API, pipeline de données, infrastructure as code.

## Écrire un projet type

- **Le code tourne.** Les commandes du README passent dans un conteneur nu, avec la chaîne d'outils du langage et au plus un `install`. `traps.md` donne la ligne exacte. Un projet dont on ne peut pas lancer les tests ne peut pas porter de tâche.
- **Les faits sont dans le dépôt, pas dans la tête du propriétaire.** Un incident se plante dans un post-mortem daté et chiffré, une décision dans un ADR, un danger dans une note d'exploitation. `owner.md` ne répond qu'à l'entretien.
- **Chaque fait a son contraire.** À côté de l'incident réel, une règle générique sans incident ; à côté du garde-fou qui bloque, un garde-fou déclaré qui ne bloque pas ; à côté de la commande qui marche, une commande périmée. C'est l'écart entre les deux qu'on mesure.
- **Des tentations.** `traps.md` liste les raccourcis qu'un agent sans harness prend sur la tâche type de l'équipe : c'est la matière d'une mesure avant et après.
- **Un init d'auteur** dans `runs/<date>-init-author/` : ce que le skill doit produire, écrit par qui a planté les faits. Base de régression du noteur, pas mesure du skill.

## Écrire un expected.json

Les verdicts et priorités sont du jugement : deux audits sérieux divergent sur SPLIT contre PUSH_DOWN, ou P1 contre P2. Les premières exécutions à l'aveugle l'ont montré. Être **généreux sur les verdicts et les priorités** (lister toutes les lectures défendables), **strict sur le reste** : le piège doit être trouvé avec une preuve au bon chemin, les règles racontées doivent être dans `process_leaks` (`require_leak`), les éléments sains doivent rester KEEP, les conventions de style ne doivent pas être des fuites (`forbidden_leak_keywords`), un garde-fou mensonger ne doit pas être cru (`forbidden_guarded_paths`).

## Évaluer harness-init

harness-init n'a pas de pièges à trouver : il écrit. On l'évalue sur un dépôt **nu**, une fixture dont on retire l'instrumentation IA (`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.cursor/`, `.agents/`, stub Copilot, `.harness/`) :

```bash
python3 cli/harness.py fixture bare java-back /tmp/bare
```

Sur un projet type, le bloc `init` d'`expected.json` rend la note déterministe :

```bash
python3 cli/harness.py fixture check go-hexa --init <dépôt produit par l'init>
```

Il vérifie le palier atteint, les faits non découvrables remontés (`must_surface`), le bruit recopié (`must_not_write`), les garde-fous réels cités après « Vérifiée par » (`guards_cited`) et les garde-fous mensongers crus (`forbidden_guards`). Les mots cherchés sont des identifiants du dépôt (`reset-db`, `archcheck`, `packages/shared`), pas des tournures : la note ne dépend pas de la langue du rapport.

Sur une fixture d'audit, sans bloc `init` : un agent neuf reçoit le skill, le dépôt nu et les réponses d'entretien d'un propriétaire fictif. On note ensuite : `harness status` sur ce qu'il a produit (palier 1 attendu, 5/5), son audit de gate contre les pièges de la fixture d'origine encore présents (`fixture check --audit`), et une relecture des règles écrites : non-découvrables seulement, justifications réelles ou déclarées absentes, garde-fous nommés. Deux exécutions : `repos/java-back/runs/2026-11-09-init-blind/` (dépôt nu) et `repos/node-front/runs/2026-11-09-init-blind/` (repo déjà instrumenté, à fusionner : le cas le plus fréquent).

## Lancer

```bash
python3 cli/harness.py fixture check java-back
python3 cli/harness.py fixture check java-back --audit fixtures/repos/java-back/repo/.harness/audit.json
```
