# Fixtures

Des dépôts synthétiques avec des pièges d'instrumentation IA plantés et documentés. C'est le L3 de nos propres skills : la seule façon de savoir si une modification de SKILL.md améliore ou dégrade ce que l'agent trouve.

```
fixtures/repos/<nom>/
├── repo/            # le dépôt synthétique, tel qu'un dev l'aurait laissé
├── traps.md         # chaque piège ou fait planté : id, emplacement, ce que le skill doit en dire
├── expected.json    # la partie vérifiable par le CLI : rôle, blocs status, audit, init
├── owner.md         # projets types : les réponses du propriétaire fictif, données d'avance
├── owner.json       # facultatif : le même propriétaire, qui ne répond qu'à ce qu'on lui demande
├── tasks/<id>/      # projets types : une tâche type, ses tests cachés, sa solution, une solution tentée
└── runs/            # exécutions datées, notées par fixture check ; <date>-pas1-author = le pas 1 de l'auteur
```

Deux familles. Les **fixtures d'audit** (`java-back`, `node-front`, `python-cli`) portent un harness abîmé et peu de code : elles mesurent ce que l'audit trouve. Les **projets types** (`go-hexa`, `ts-monorepo`, `django-mvc`, `vibe-app`, `microservices`) sont de vrais petits projets, un par style d'architecture, dont le code tourne et dont les tests passent : ils mesurent le parcours, du palier 0 vers le haut. `owner.md` se donne à l'agent évalué ; `traps.md`, `expected.json`, `owner.json` et `runs/` jamais : le propriétaire d'`owner.json` répond pendant la séance, par une commande que `bench init` pose dans le kit.

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
| `django-mvc` | **Projet type.** Monolithe Django 5.1, MVC, ORM, migrations, SQLite, deux apps, trois post-mortems | 4 faits + 7 bruits + 5 pièges + 2 sains | Départ **vieilli** : un AGENTS.md soigné de deux ans jamais relu, et un CLAUDE.md recopié qui a divergé. Trier un fichier qui a eu raison : garder les règles nées d'incidents, raccourcir celle qui a reçu son garde-fou, ne plus croire celle dont le job a disparu, demander au propriétaire pour le périmé |
| `ts-monorepo` | **Projet type.** Monorepo npm workspaces TypeScript : API, web, package partagé, contrôle des frontières | 4 faits + 7 bruits + 3 pièges + 2 sains | Départ **généré jamais relu** : un `CLAUDE.md` de `/init` de 104 lignes. Savoir retirer : découvrable, générique, écrit pour d'anciens modèles, nuisible, périmé, contredit par un garde-fou ; et garder les deux lignes qui comptent. Trou de filtre de chemins en CI, et aucune commande qui rejoue tout |
| `vibe-app` | **Projet type.** Application Node 22 sans dépendance, faite à l'arrache avec un agent : commandes d'une boulangerie, webhook de paiement, fichier JSON, pas de CI | 4 faits + 8 bruits + 6 pièges + 2 sains | Départ **notes accumulées** : un `CLAUDE.md` décharge de mémoire de 133 lignes, `PLAN.md`, `NOTES.md`, `TODO.md`, et un propriétaire qui ne sait rien du code. Garder trois faits datés, retirer le reste, ne rien dire vérifié ; implémentation morte, tests creux, clé en clair |
| `microservices` | **Projet type, tenu à l'écart** (`holdout`). Trois services Python en bibliothèque standard, contrats JSON, événements livrés au moins une fois, validateur de schéma et contrôle d'imports testés | 7 faits + 3 défauts + nombreux sains | Départ **sain** : un harness au palier 1, daté, aux garde-fous réels. Mesure le zèle : un bon audit garde presque tout, un bon init ne réécrit presque rien. Trois défauts subtils : un garde-fou qui ne couvre qu'un côté du contrat, une consigne manuelle devenue redondante, une limite de broker périmée |

Styles d'architecture à venir : pipeline de données, infrastructure as code.

## Écrire un projet type

Modèles à lire avant d'écrire : `repos/go-hexa` (départ nu) et `repos/ts-monorepo` (départ généré jamais relu).

- **Le code tourne.** Les commandes du README passent dans un conteneur nu, avec la chaîne d'outils du langage et au plus un `install`. `traps.md` donne la ligne exacte. Un projet dont on ne peut pas lancer les tests ne peut pas porter de tâche.
- **Les faits sont dans le dépôt, pas dans la tête du propriétaire.** Un incident se plante dans un post-mortem daté et chiffré, une décision dans un ADR, un danger dans une note d'exploitation. `owner.md` ne répond qu'à l'entretien et ne révèle aucun fait planté.
- **Au moins un fait n'est écrit nulle part ailleurs.** Un fait rangé dans un ADR ou un post-mortem, un agent soigneux le trouve seul : les deux premières campagnes l'ont montré, les bras y faisaient jeu égal. Chaque projet type porte donc au moins un fait qui ne se lit que dans ses instructions, ou ne se tient que de son propriétaire (`owner.md`, section « Ce que l'équipe ajoute d'elle-même »). Il a un identifiant propre (un en-tête, un réglage, un chemin), absent du reste du dépôt, et aucun de ses morceaux ne s'y lit non plus : un validateur qui liste `deprecated` parmi ses annotations mène à `"deprecated": true`, et l'agent sans instructions l'a posé seul (`microservices`, 2026-11-13). Un mot-clé standard d'un format ou d'un outil ne fait pas un fait oral : un agent soigneux le connaît. Un contrôle de la tâche l'exerce, et une solution tentée, la meilleure qu'on puisse écrire sans ce fait, échoue à ce contrôle et à lui seul. `fixture check` le vérifie.
- **Un propriétaire qui ne dit rien de lui-même.** Avec `owner.md`, les réponses sont données d'avance, y compris ce que le propriétaire ajoute de lui-même : un entretien qui ne pose aucune question recueille quand même le fait oral, et la mesure ne dit rien de l'entretien. `owner.json` porte les mêmes réponses, chacune derrière ses déclencheurs (`any_of`, mots entiers, sans casse ni accents, `*` pour une fin de mot). La réponse qui porte le fait oral le dit par `fact` ; ses déclencheurs sont ce qu'un vrai propriétaire entendrait comme une invitation à le dire : ce qui n'est écrit nulle part, ce qu'on redit en revue, un piège pour un nouveau venu, « autre chose à ajouter ? », ou le sujet lui-même. Ni la mode, ni l'équipe, ni la CI ne le déclenchent. `fixture check` vérifie que le fait ne s'échappe par aucune autre réponse, ni par l'accueil, ni par la réponse par défaut. `bench init` garde l'échange dans `entretien.md` et dit si le fait a été demandé. Aucun modèle ne joue le propriétaire : une question reçoit toujours la même réponse.
- **Chaque fait a son contraire.** À côté de l'incident réel, une règle générique sans incident ; à côté du garde-fou qui bloque, un garde-fou déclaré qui ne bloque pas ; à côté de la commande qui marche, une commande périmée. C'est l'écart entre les deux qu'on mesure.
- **Le README du dépôt** avoue le banc sur une seule ligne, « Dépôt **synthétique** : une fixture du projet harness-ai » : elle est retirée des copies de travail. Il ne cite jamais `traps.md`.
- **Un pas 1 d'auteur** dans `runs/<date>-pas1-author/` : `AGENTS.md`, le stub `CLAUDE.md`, les notes de sous-dossier gardées, `REMOVE.txt` s'il supprime des fichiers du dépôt (un chemin par ligne), et `RUN.md` qui dit ce qui a été retiré et pourquoi. Le palier 1 et rien d'autre : ni Maintenance, ni marqueur, ni Processus de travail, ni contrat. Chaque règle porte sa date `[AAAA-MM]`, celle de l'incident ou de la décision. C'est la base de régression du noteur et le bras `harness` du banc.

### expected.json

```json
{
  "fixture": "<nom>",
  "role": "tuning",            // ou "holdout" : tenu à l'écart du réglage des skills, sert seulement à mesurer
  "status": { "level_reached": 0, "source_path": "CLAUDE.md", "failing_checks": [], "passing_checks": [], "guardrail_tools": [], "contracts": 0 },
  "init": {
    "min_level": 1,
    "only_level_material": true,
    "must_surface":   [{ "id": "I1", "what": "…", "any_of": ["identifiant-du-dépôt"] },
                       { "id": "I6", "what": "…", "any_of": ["…"], "only_in_instructions": ["mot absent du reste du dépôt"] }],
    "must_not_write": [{ "id": "N1", "what": "…", "any_of": ["texte du bruit"] },
                       { "id": "N2", "what": "commande qui n'existe plus", "any_of": ["make e2e"], "mention_ok": true }],   // la citer pour la démentir n'est pas la recopier
    "guards_cited": ["chemin-du-vrai-garde-fou"],
    "forbidden_guards": [{ "path": "garde-fou-qui-ne-bloque-pas", "rule_keywords": ["…"] }],
    "never_guarded": [{ "what": "…", "rule_keywords": ["l'un"], "rule_all_of": ["tous"] }],   // rien ne la vérifie : « vérifiée par : la revue » est faux aussi
    "no_guard_exists": false,                                     // vrai : dépôt sans CI, toute règle « vérifiée » est fausse
    "must_not_remain": [{ "path": "PLAN.md", "what": "…", "max_lines": 8, "any_of": ["…"] }],  // notes annexes : parties ou réduites
    "report_must_mention": [{ "what": "…", "any_of": ["…"] }],    // le compte rendu, noté avec --report <fichier>
    "report_must_not_mention": [{ "what": "la valeur d'un secret", "any_of": ["…"] }],
    "min_similarity": [{ "path": "AGENTS.md", "ratio": 0.8 }]     // harness déjà sain : le réécrire est du zèle
  },
  "audit": {
    "traps": [{ "id": "T1", "path": "…", "verdicts": [], "priorities": [], "leak_keywords": ["tous, dans une même fuite"], "leak_any_of": ["ou l'un de ceux-ci"], "require_leak": true }],
    "sane": [], "guarded_rules_paths": [], "forbidden_guarded_paths": [], "forbidden_leak_keywords": [],
    "never_guarded": [], "no_guard_exists": false,
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

La solution tentée doit **passer les commandes visibles du projet** et n'échouer qu'aux tests cachés ou aux contrôles de diff. Si les tests du dépôt la rattrapent, un agent qui les lance la corrige seul et la tâche ne mesure plus ce que les instructions apprennent : `bench selftest` l'annonce par un avertissement. De même, un fait que l'énoncé de la tâche exerce ne doit pas se trouver en clair dans un document que tout agent soigneux lit : la campagne du 2026-11-11 sur `go-hexa` l'a montré, l'agent sans instructions a ouvert l'ADR de lui-même. Pour mesurer ce que le harness apporte, le fait doit ne vivre que dans les instructions, ou être noyé.

`agent_bash` liste les commandes que l'agent évalué a le droit de lancer (`"go *"`, `"git *"`) : la chaîne d'outils du projet et git, rien d'autre.

Un contrôle peut porter `"exercises": "I6"` : il exerce le fait écrit nulle part ailleurs, c'est lui qui départage les bras.

Contrôles de `task.json` : `run` (une commande, verte si elle sort à 0 ; `"acceptance": true` pour celles qui ont besoin des tests cachés), `forbid_added` et `require_added` (un motif dans les lignes ajoutées sous des chemins), `forbid_removed` (un motif dans les lignes retirées), `forbid_changed` (des chemins qu'on ne touche pas : un garde-fou, une migration appliquée), `max_changed_lines`. Un contrôle de diff peut en combiner plusieurs.

Deux leçons des campagnes. Un contrôle qui protège la CI interdit de l'**affaiblir**, pas de la toucher : un agent qui répare un trou de filtre fait bien. Un contrôle sur un secret cherche sa **vraie valeur**, pas tout ce qui y ressemble : un agent qui donne à ses tests un secret à eux fait bien aussi. `setup` lance une installation avant les commandes. Les tests cachés n'utilisent que la surface publique du projet, pour compiler quelle que soit la solution.

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

Un mot de `must_not_write` compte où qu'il soit, sauf pour une entrée `mention_ok` : un identifiant du dépôt qu'une règle saine peut avoir à nommer pour le démentir, une commande que le README annonce encore par exemple. La ligne n'est alors qu'une citation si elle dit que la chose n'est plus là **et** ne reprend pas quatre mots de suite d'une ligne d'origine qui porte ce mot. Les citations sont listées sous la note, non comptées, à relire. La liste des tournures qui disent « n'est plus là » dépend de la langue : elle ne sert qu'à excuser, une tournure inconnue laisse la ligne comptée. Ne marquer `mention_ok` ni un secret, ni une préférence de style, ni une consigne d'ancien modèle : ceux-là n'ont aucune raison d'être nommés.

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

`bench play` enchaîne le tout pour un bras : copie de travail à un chemin neutre, agent, note, sorties rangées dans `runs/<date>-task-blind-<bras>/`, registre. L'agent est un processus séparé qui ne reçoit que `task.md` et ne charge que les instructions du dépôt de travail ; ni les consignes ni les outils de la session qui lance la campagne ne l'atteignent. Il est confiné à son dossier, avec les seules commandes de la liste `agent_bash` de la tâche.

```bash
python3 cli/harness.py bench play go-hexa deposit --arm harness --work-root /tmp/banc --label 2026-11
```

`bench init` joue de même le pas 1 : le dépôt tel qu'on le trouve, les skills et le CLI, les réponses du propriétaire données d'avance. Il note ce qui a été écrit et le compte rendu, et range dans `overlay/` ce que le pas a changé. Ce dossier se donne à `bench play --overlay` pour jouer la tâche avec le harness que le skill a produit : c'est la chaîne entière, du skill au travail rendu.

```bash
python3 cli/harness.py bench init go-hexa --work-root /tmp/banc --label 2026-11
python3 cli/harness.py bench play go-hexa deposit --arm harness --work-root /tmp/banc \
    --overlay fixtures/repos/go-hexa/runs/<date>-init-blind/overlay --out fixtures/repos/go-hexa/runs/<date>-task-blind-init
```

Décider d'une campagne et l'interpréter reste le travail du skill `harness-stress`, à la demande.

## Lancer

```bash
python3 cli/harness.py fixture check java-back
python3 cli/harness.py fixture check java-back --audit fixtures/repos/java-back/repo/.harness/audit.json
python3 cli/harness.py fixture check go-hexa --init fixtures/repos/go-hexa/runs/2026-11-10-pas1-author
```
