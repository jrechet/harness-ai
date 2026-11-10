# Fixtures

Des dépôts synthétiques avec des pièges d'instrumentation IA plantés et documentés. C'est le L3 de nos propres skills : la seule façon de savoir si une modification de SKILL.md améliore ou dégrade ce que l'agent trouve.

```
fixtures/repos/<nom>/
├── repo/            # le dépôt synthétique, tel qu'un dev l'aurait laissé
├── traps.md         # chaque piège ou fait planté : id, emplacement, ce que le skill doit en dire
├── expected.json    # la partie vérifiable par le CLI : rôle, blocs status, audit, init
├── owner.md         # projets types : les réponses du propriétaire fictif à l'entretien
├── tasks/<id>/      # projets types : une tâche type, ses tests cachés, sa solution, une solution tentée
└── runs/            # exécutions datées, notées par fixture check ; <date>-pas1-author = le pas 1 de l'auteur
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

Modèles à lire avant d'écrire : `repos/go-hexa` (départ nu) et `repos/ts-monorepo` (départ généré jamais relu).

- **Le code tourne.** Les commandes du README passent dans un conteneur nu, avec la chaîne d'outils du langage et au plus un `install`. `traps.md` donne la ligne exacte. Un projet dont on ne peut pas lancer les tests ne peut pas porter de tâche.
- **Les faits sont dans le dépôt, pas dans la tête du propriétaire.** Un incident se plante dans un post-mortem daté et chiffré, une décision dans un ADR, un danger dans une note d'exploitation. `owner.md` ne répond qu'à l'entretien et ne révèle aucun fait planté.
- **Chaque fait a son contraire.** À côté de l'incident réel, une règle générique sans incident ; à côté du garde-fou qui bloque, un garde-fou déclaré qui ne bloque pas ; à côté de la commande qui marche, une commande périmée. C'est l'écart entre les deux qu'on mesure.
- **Le README du dépôt** contient une ligne avec le mot « fixture » : elle est retirée des copies de travail. Il ne cite jamais `traps.md`.
- **Un pas 1 d'auteur** dans `runs/<date>-pas1-author/` : `AGENTS.md`, le stub `CLAUDE.md`, les notes de sous-dossier gardées, et `RUN.md` qui dit ce qui a été retiré et pourquoi. Le palier 1 et rien d'autre : ni Maintenance, ni marqueur, ni Processus de travail, ni contrat. Chaque règle porte sa date `[AAAA-MM]`, celle de l'incident ou de la décision. C'est la base de régression du noteur et le bras `harness` du banc.

### expected.json

```json
{
  "fixture": "<nom>",
  "role": "tuning",            // ou "holdout" : tenu à l'écart du réglage des skills, sert seulement à mesurer
  "status": { "level_reached": 0, "source_path": "CLAUDE.md", "failing_checks": [], "passing_checks": [], "guardrail_tools": [], "contracts": 0 },
  "init": {
    "min_level": 1,
    "only_level_material": true,
    "must_surface":   [{ "id": "I1", "what": "…", "any_of": ["identifiant-du-dépôt"] }],
    "must_not_write": [{ "id": "N1", "what": "…", "any_of": ["texte du bruit"] }],
    "guards_cited": ["chemin-du-vrai-garde-fou"],
    "forbidden_guards": [{ "path": "garde-fou-qui-ne-bloque-pas", "rule_keywords": ["…"] }]
  },
  "audit": {
    "traps": [], "sane": [], "guarded_rules_paths": [], "forbidden_guarded_paths": [], "forbidden_leak_keywords": [],
    "removals":  [{ "id": "N3", "any_of": ["texte de la ligne"], "reasons": ["useless", "harmful", "outdated"], "ask_owner": false }],
    "must_keep": [{ "id": "I1", "any_of": ["identifiant de la ligne à garder"] }]
  }
}
```

Chaque `id` des blocs `init` et `audit` a sa ligne `| id |` dans un tableau de `traps.md` : un test le vérifie. Les mots cherchés sont des identifiants du dépôt (`reset-db`, `archcheck`, `packages/shared`), pas des tournures : la note ne dépend pas de la langue du rapport.

Un retrait a un motif : `useless` (découvrable, ou ce qu'un modèle fait sans qu'on le dise), `harmful` (dégrade le travail d'un agent actuel, ou contredit un garde-fou), `outdated` (vrai hier, plus aujourd'hui). `ask_owner` vaut vrai quand seul le propriétaire sait que la ligne est périmée : l'audit doit alors poser la question, pas trancher.

### Une tâche

`tasks/<id>/` porte la tâche type de l'équipe, celle qu'un agent sans harness rate d'une façon prévisible :

```
task.md                 l'énoncé donné à l'agent ; il ne dit rien des règles plantées
task.json               les contrôles, voir ci-dessous
acceptance/             les tests cachés, copiés dans le dépôt au moment de noter
solution.patch          la solution de référence : passe tous les contrôles
tempted/<nom>.patch     la solution qu'on écrit naturellement : marche, et échoue aux contrôles déclarés
```

Contrôles de `task.json` : `run` (une commande, verte si elle sort à 0 ; `"acceptance": true` pour celles qui ont besoin des tests cachés), `forbid_added` et `require_added` (un motif dans les lignes ajoutées sous des chemins), `forbid_changed` (des chemins qu'on ne touche pas : un garde-fou, la CI, une migration appliquée), `max_changed_lines`. `setup` lance une installation avant les commandes. Les tests cachés n'utilisent que la surface publique du projet, pour compiler quelle que soit la solution.

```bash
python3 cli/harness.py bench selftest <nom>     # dépôt intact rouge, solution verte, tentation rouge où elle le déclare
```

Un patch se fabrique dans une copie de travail : `bench prepare <nom> <dir> --arm asis` (ou `bare` si le dépôt n'a aucune instruction), le changement, puis `git add -A && git diff --cached HEAD > solution.patch`.

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

## Le banc avant et après

Une tâche se joue sur plusieurs bras du même dépôt : `bare` (aucune instruction), `asis` (le dépôt tel qu'on l'a trouvé), `harness` (après le pas 1, par défaut celui de l'auteur). L'écart entre les bras dit si le harness sert. Rejoué sans une ligne ou sur un nouveau modèle, il dit si elle sert encore.

```bash
python3 cli/harness.py bench plan                          # les exécutions d'agent d'une campagne et leur coût
python3 cli/harness.py bench prepare go-hexa /tmp/w --arm harness
python3 cli/harness.py bench check go-hexa deposit /tmp/w  # après le travail de l'agent
python3 cli/harness.py bench record --kind task --fixture go-hexa --task deposit --arm harness --score 6/6 --ok
python3 cli/harness.py bench report                        # le registre fixtures/results.jsonl
```

Le banc ne lance aucun agent : il prépare, note et tient le registre. Lancer une campagne est le travail du skill `harness-stress`, à la demande.

## Lancer

```bash
python3 cli/harness.py fixture check java-back
python3 cli/harness.py fixture check java-back --audit fixtures/repos/java-back/repo/.harness/audit.json
python3 cli/harness.py fixture check go-hexa --init fixtures/repos/go-hexa/runs/2026-11-10-pas1-author
```
