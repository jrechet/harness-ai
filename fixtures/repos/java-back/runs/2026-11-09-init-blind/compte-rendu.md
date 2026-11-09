# Compte rendu — harness-init sur billing-api

**Dépôt** : `init-eval/repo` (branche `develop`, commit `a7b8f90`) · **Date** : 2026-11-09 · **Mode retenu** : délégation

## Palier atteint selon `harness status`

**Palier 1 — Cadré : 5/5, complet.** Prochain : palier 2.

Vérifications restantes :
- Palier 2 (3/4) : il manque un harvest qui trouve un signal réel (S1–S4) ; la boucle ne tourne pas encore, harness-harvest n'est pas installé, la collecte des `rule:` est manuelle.
- Palier 3 (2/4) : 17 % des règles « Vérifiée par » (cible 50 %) ; l'audit a trois P1 ouverts.
- Palier 4 (3/5) : pas de harvest ; le test « coupe l'agent » de l'audit échoue (5 étapes de la release n'existent que dans des prompts).

## Fichiers créés ou modifiés

| Fichier | Lignes | Rôle |
|---|---|---|
| `AGENTS.md` | 44 | source unique, mode délégation, 3 règles, 3 interdits, processus, contrat référencé, maintenance, marqueur harvest |
| `CLAUDE.md` | 1 | stub `@AGENTS.md` |
| `.claude/skills/release/SKILL.md` | 45 | premier contrat de tâche : release / hotfix via `release.yml` |
| `.harness/state.json` | 345 | écrit par `harness status` |
| `.harness/audit.json` | 201 | sortie machine du harness-audit (gate) |

Pas de stub Copilot ni Cursor : l'équipe n'utilise que Claude Code. Aucun fichier d'instructions préexistant, rien n'a été écrasé.

## Secrets trouvés

Aucun secret en clair. Les deux occurrences (`release.yml:25`, `:30`) sont des références `${{ secrets.REGISTRY_PASSWORD }}` et `${{ secrets.PROD_SSH_KEY }}`, correctement tenues en L4. Rien à régénérer ni à purger.

## Mode retenu et pourquoi

**Délégation**, choisi par le propriétaire (des agents ouvriront des PRs entières) et cohérent avec l'équipe (3 développeurs plus des agents : le fichier sert à tous, pas à la mémoire d'un seul). Conséquence : la section « Processus de travail » est obligatoire, un contrat existe dès la première tâche, et chaque règle racontée sans garde-fou est une dette P1 pour l'audit.

## Règles écrites et statut

| Règle | Statut |
|---|---|
| Un contrôleur ne dépend jamais d'un repository ; la logique métier vit dans les services | **vérifiée par** `src/test/java/com/acme/billing/ArchitectureTest.java` (`controllers_do_not_touch_repositories`), lancé par `ci.yml` |
| Une migration Flyway appliquée ne se modifie jamais ; on ajoute un `V<n+1>__*.sql` | **non vérifiée** ; cible : test de checksum des migrations dans `ci.yml` |
| Une release ou un hotfix passe par `release.yml` selon le contrat `release`, jamais par `old-deploy.sh` ni `docker`/`ssh` à la main | **non vérifiée** ; cible : suppression de `old-deploy.sh`, job `deploy` sous `environment: production` |

Interdits (du propriétaire, repris tels quels) : déclencher `release.yml` ou tout déploiement prod sans validation humaine explicite ; modifier une migration Flyway appliquée ; pousser directement sur `main`. Aucun des trois n'a de garde-fou aujourd'hui (pas d'`environment` protégé, pas de test de checksum, protection de branche non vérifiable sans remote).

Hypothèses prises sans question : une PR vise `develop` sauf demande explicite (déduit de l'Interdit « pas de push sur main » et des scripts qui releasent depuis `develop`) ; le « pourquoi » de la règle ArchUnit vient du commentaire du test (« pas de logique métier dans les contrôleurs »).

## Commandes confirmées et non confirmées

Confirmées (exécutées ici) :
- `python3 harness.py status . --today 2026-11-09` → palier 1, 5/5.
- `node --check scripts/release.mjs`, `node --check scripts/hotfix.mjs`, `bash -n scripts/old-deploy.sh` → syntaxe valide (aucune exécution réelle : elles déclencheraient `release.yml`).

Non confirmées (pas de toolchain Gradle disponible ; recopiées de `ci.yml`, et donc gardées dans le tableau d'AGENTS.md comme « ce que la CI lance ») :
- `./gradlew checkstyleMain checkstyleTest`, `./gradlew test`. Nombre de tests inconnu.
- De plus, **aucun `gradlew` ni `gradle/wrapper/` n'est versionné** sur `develop` : si c'est l'état du remote, `ci.yml:13-14` et `release.yml:23` échouent à la première étape. Idem pour le **`Dockerfile`** absent alors que `release.yml:24` lance `docker build .`. À confirmer avant toute release.

## Résultat du gate (harness-audit)

Score de santé **0/100** (3 P1, 4 P2, 1 P3 ; test « coupe l'agent » en échec, plafond 60). Rapport complet en annexe, JSON dans `.harness/audit.json`.

Constats structurels corrigés pendant l'init : les deux règles `(non vérifiée)` nomment maintenant leur garde-fou cible (exigence du mode délégation). Longueur (44 lignes), part de référence (~25 %), clause de maintenance, stub cohérent : conformes.

Constats de fond, non corrigés ici (ils demandent de créer du code ou un check CI) :
1. **P1 `release.yml`** : un seul job publie et déploie en prod, sans `environment` protégé, sans `dry_run`, tag posé après la publication, input `hotfix` ignoré, fin signalée par `echo SUCCESS`.
2. **P1 `scripts/old-deploy.sh`** : mort et dangereux, déploie en prod par ssh direct en contournant l'Interdit n°1.
3. **P1 `.claude/skills/release/SKILL.md`** : les pré-conditions (CI verte, tag absent, version croissante, migrations non modifiées) sont racontées, pas imposées par du code.
4. P2 : `release.mjs` déduit le type de version du nom de branche (cause plausible des erreurs de release) ; `hotfix.mjs` le duplique ; wrapper Gradle absent ; aucune garde sur les migrations Flyway.
5. P3 : le commentaire d'`ArchitectureTest` pointe vers « CLAUDE.md, Conventions », qui n'existe pas.

Point d'attention : `release.yml` est un `workflow_dispatch`, GitHub ne l'accepte que depuis la branche par défaut. Tout garde-fou posé dessus (ou tout job planifié) fusionné sur `develop` seul est inerte ; il doit aussi arriver sur `main`.

## Trois prochaines étapes

1. **Pousser la première règle non vérifiée en CI** : scinder `release.yml` en `build-publish` puis `deploy` sous `environment: production` avec reviewers requis, ajouter `dry_run`, supprimer `scripts/old-deploy.sh` (approbation du propriétaire : suppression et changement de workflow), et fusionner jusqu'à `main`. L'Interdit n°1 devient « Vérifiée par ».
2. Réécrire `scripts/release.mjs` en `release plan <version> --ref <ref> [--hotfix]` / `release run` : la version est un argument décidé par l'humain, les quatre pré-conditions sortent en `exit 1`, le plan est du JSON ; supprimer `hotfix.mjs` ; le skill `release` ne garde que la séquence et la validation.
3. Versionner le wrapper Gradle (ou `gradle/actions/setup-gradle`) pour que `ci.yml` tourne réellement, puis ajouter un test de checksum des migrations Flyway et activer la protection de branche sur `main` : les deux autres Interdits deviennent vérifiés et le palier 3 passe à portée.

---

# Annexe — Audit du harness — Release de billing-api et instrumentation IA

**Périmètre** : repo billing-api (branche `develop`) : `AGENTS.md`, `CLAUDE.md`, `.claude/skills/release`, `scripts/`, `.github/workflows/`, `config/checkstyle`, test ArchUnit, migrations Flyway · **Date** : 2026-11-09 · **Éléments inventoriés** : 11

## 1. Synthèse

- **Score de santé** : 0 — l'agent est un pilier : sans lui, personne ne vérifie quoi que ce soit avant qu'un déploiement prod parte (100 − 3×25 − 4×8 − 1×2 < 0, borné à 0 ; le test « coupe l'agent » plafonne de toute façon à 60).
- **Résultat du test « coupe l'agent »** : ÉCHEC — 5 étape(s) du processus n'existent que dans des prompts (décider la version, vérifier CI verte / tag absent / version croissante, validation humaine avant déploiement, vérification de la prod, mise à jour de `VERSION`).
- **Points bloquants (P1)** : 3
- **Les trois actions qui changent le plus les choses** :
  1. Scinder `release.yml` et mettre le job `deploy` sous `environment: production` à reviewers requis, avec `dry_run`.
  2. Supprimer `scripts/old-deploy.sh`.
  3. Porter les pré-conditions de release dans `release plan` (exit 1) à la place du SKILL.md.

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md | `AGENTS.md` | L2 | L2 | CLAUDE.md | skill release, ci.yml, ArchitectureTest |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2 | — (chargé par Claude Code) | AGENTS.md |
| 3 | Contrat release | `.claude/skills/release/SKILL.md` | L2 | MIXED (procédure + pré-conditions racontées) | AGENTS.md | release.yml |
| 4 | Workflow release | `.github/workflows/release.yml` | L4 | L4 | skill release, release.mjs, hotfix.mjs | — |
| 5 | Ancien déploiement | `scripts/old-deploy.sh` | L3 | L4 (déploie en prod) | personne | — |
| 6 | release.mjs | `scripts/release.mjs` | L3 | MIXED (jugement + déclenchement L4) | personne (manuel) | release.yml |
| 7 | hotfix.mjs | `scripts/hotfix.mjs` | L3 | L3 | personne (manuel) | release.yml |
| 8 | Workflow CI | `.github/workflows/ci.yml` | L4 | L4 | AGENTS.md | checkstyle, tests |
| 9 | Checkstyle | `config/checkstyle/checkstyle.xml` | L3 | L3 | ci.yml | — |
| 10 | ArchUnit | `src/test/java/com/acme/billing/ArchitectureTest.java` | L3 | L3 | ci.yml | — |
| 11 | Migrations Flyway | `src/main/resources/db/migration/` | L3 | L3 | — (aucun garde-fou) | — |

Processus nominal : la release.

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| Décider la version x.y.z | humain, via SKILL.md §1 (release.mjs la déduit à tort de la branche) | non | — |
| Vérifier CI verte sur la ref | SKILL.md §2 | non | — |
| Vérifier que le tag v<x.y.z> n'existe pas | SKILL.md §2 | non | — |
| Vérifier version croissante / migrations non modifiées | SKILL.md §2 | non | — |
| Validation humaine avant déploiement prod | SKILL.md §3, Interdit AGENTS.md | non (pas d'`environment` protégé) | non |
| Build jar + image + push | release.yml:23-26 | oui | non |
| Tag v<x.y.z> | release.yml:27 | oui (mais après la publication) | non |
| Déploiement prod | release.yml:28-32 | oui | non |
| Vérifier la prod | SKILL.md §5 ; `echo SUCCESS` | non (retour non structuré) | — |
| Mettre à jour VERSION sur develop | SKILL.md §6 | non | — |

## 3. Fuites : règles et étapes racontées sans vérification

- **Pré-conditions de release** (CI verte, tag absent, version croissante, migrations non modifiées) — racontées en `.claude/skills/release/SKILL.md:15-19`. Si sautées : une version déjà publiée ou un commit à CI rouge part en production. Doit vivre en L3 : sous-commande `release plan` avec `exit 1` (réécriture de `scripts/release.mjs`).
- **Validation humaine avant tout déploiement prod** — `AGENTS.md:22`, `SKILL.md:22`. Si sautée : un agent déploie en prod d'un seul `gh workflow run`. Doit vivre en L4 : job `deploy` sous `environment: production` avec reviewers requis.
- **Une migration Flyway appliquée ne se modifie jamais** — `AGENTS.md:18`, `AGENTS.md:23`. Si sautée : Flyway refuse le checksum, l'application ne redémarre plus. Doit vivre en L3 : test de checksum des migrations ou `flyway validate` dans `ci.yml`.
- **Pas de push direct sur main** — `AGENTS.md:24`. Si sautée : code non revu en prod. Doit vivre en L4 : protection de branche GitHub (non vérifiable ici, pas de remote).
- **VERSION mis à jour après chaque release** — `SKILL.md:36`. Si sautée : la prochaine release calcule depuis une version périmée. Doit vivre en L4 : étape de `release.yml`.

Règles qui ont leur garde-fou :
- Un contrôleur ne dépend jamais d'un repository — `AGENTS.md:17` — `ArchitectureTest.controllers_do_not_touch_repositories`, lancé par `ci.yml`.
- Style Java (120 colonnes, imports, une classe par fichier, nommage) — volontairement non racontée — `config/checkstyle/checkstyle.xml` via `ci.yml:13`.

## 3b. Coût de contexte

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| `AGENTS.md` | 44 | 75 % / 25 % / 0 % | chaque session |
| `CLAUDE.md` | 44 (stub → AGENTS.md) | 0 / 100 / 0 | chaque session |
| `.claude/skills/release/SKILL.md` | 45 | 85 % / 15 % / 0 % | à la demande (tâche release) |

Les trois règles d'AGENTS.md disent pourquoi (une cite le mécanisme Flyway, une l'incident « on se trompe souvent », une la testabilité) ; la clause de maintenance est présente avec la convention `rule:` et le marqueur harvest.

## 4. Constats par élément

### [SPLIT] [P1] Workflow release — `.github/workflows/release.yml`
- **Fait aujourd'hui** : un job `build-and-deploy` construit, publie l'image, tague, puis déploie en prod par ssh.
- **Problème** : aucun `environment` protégé ni point d'arrêt humain, pas d'input `dry_run`, tag posé après la publication (`:27`), input `hotfix` jamais lu (`:11-14`), fin signalée par `echo SUCCESS` (`:32`). (preuve : `release.yml:16-32`)
- **Doit devenir** : jobs `build-publish` puis `deploy` sous `environment: production` avec reviewers requis ; input `dry_run` ; sorties de job (tag, digest, URL) ; input `hotfix` consommé ou supprimé.
- **Critère de vérification** : un run s'arrête en attente d'approbation avant `deploy` ; `dry_run=true` ne pousse aucune image ; `gh run view --json jobs` montre deux jobs.

### [BLOCK] [P1] Ancien déploiement — `scripts/old-deploy.sh`
- **Fait aujourd'hui** : build, push et `ssh deploy@prod.acme.io … docker compose up -d` directs.
- **Problème** : mort (« plus appelé nulle part », `:2`) et contourne tag, trace et validation : viole l'Interdit n°1. (preuve : `scripts/old-deploy.sh:5-7`)
- **Doit devenir** : supprimé.
- **Critère de vérification** : fichier absent ; aucun `ssh deploy@prod.acme.io` hors `release.yml`.

### [PUSH_DOWN] [P1] Contrat release — `.claude/skills/release/SKILL.md`
- **Fait aujourd'hui** : décrit la séquence, la validation et quatre pré-conditions à vérifier à la main avec `gh` et `git`.
- **Problème** : des pré-conditions racontées en L2 ; l'agent peut les sauter ou mal lire un JSON de `gh run list`. (preuve : `SKILL.md:15-19`, `:25-29`)
- **Doit devenir** : `release plan <version> --ref <ref> [--hotfix]` qui vérifie et sort en 1, plan en JSON ; `release run` après plan valide ; le skill ne garde que séquence et validation.
- **Critère de vérification** : `release plan` sort en 1 sur une ref à CI rouge ou un tag existant ; le skill ne contient plus de vérification à interpréter.

### [PROMOTE] [P2] release.mjs — `scripts/release.mjs`
- **Fait aujourd'hui** : déduit la prochaine version du nom de branche puis lance `gh workflow run release.yml`.
- **Problème** : jugement codé en dur (`develop` → mineure, `feat/breaking-*` → majeure, `:11-17`), cause plausible des erreurs de release ; aucune pré-condition avant le déclenchement (`:23`).
- **Doit devenir** : version en argument obligatoire décidé par l'humain ; devient le socle de `release plan|run`.
- **Critère de vérification** : sans argument version, exit 1 avec message.

### [MERGE] [P2] hotfix.mjs — `scripts/hotfix.mjs`
- **Fait aujourd'hui** : même mécanique que release.mjs, incrément de patch, flag `hotfix=true`.
- **Problème** : duplication (`:2`, `:11-16`) et flag ignoré par le workflow.
- **Doit devenir** : `release run --hotfix`.
- **Critère de vérification** : fichier absent ; `release run --hotfix` depuis `hotfix/*` déclenche le workflow.

### [KEEP] [P2] Workflow CI — `.github/workflows/ci.yml`
- **Fait aujourd'hui** : Checkstyle et tests sur PR, `develop`, `main`.
- **Problème** : appelle `./gradlew` (`:13-14`) alors qu'aucun wrapper n'est versionné ; si c'est l'état du remote, chaque run échoue à la première étape.
- **Doit devenir** : wrapper versionné ou `gradle/actions/setup-gradle` ; ajout d'un contrôle des migrations.
- **Critère de vérification** : `git ls-files gradlew gradle/wrapper/gradle-wrapper.properties` renvoie deux fichiers ; un run vert sur `develop`.

### [PUSH_DOWN] [P2] Migrations Flyway — `src/main/resources/db/migration/`
- **Fait aujourd'hui** : une migration `V1__init.sql`, aucun garde-fou.
- **Problème** : la règle et l'Interdit ne tiennent que par le texte (`AGENTS.md:18`, `:23`).
- **Doit devenir** : test de checksum des migrations versionnées (ou `flyway validate`) dans `ci.yml`.
- **Critère de vérification** : modifier un caractère de `V1__init.sql` fait échouer `ci.yml`.

### [KEEP] [P3] ArchUnit — `src/test/java/com/acme/billing/ArchitectureTest.java`
- **Fait aujourd'hui** : garde-fou sain de « contrôleur ne dépend pas d'un repository ».
- **Problème** : le commentaire (`:12`) renvoie à « CLAUDE.md, Conventions », qui n'existe pas.
- **Doit devenir** : pointer vers AGENTS.md, section Règles.
- **Critère de vérification** : `grep CLAUDE.md` sur le test ne renvoie rien.

### [KEEP] AGENTS.md — `AGENTS.md`
44 lignes, mode explicite, règles justifiées, Interdits, Processus, Maintenance ; les deux règles racontées nomment leur garde-fou cible.

### [KEEP] CLAUDE.md — `CLAUDE.md`
Stub `@AGENTS.md`, source unique respectée.

### [KEEP] Checkstyle — `config/checkstyle/checkstyle.xml`
Quatre règles de style portées par l'outil, rien à raconter dans AGENTS.md.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | SPLIT | release.yml | Scinder build-publish / deploy, `environment: production` à reviewers, `dry_run`, sorties de job ; fusionner jusqu'à `main` | — | Run en attente d'approbation avant deploy ; dry_run ne pousse rien | oui |
| 2 | P1 | BLOCK | old-deploy.sh | Supprimer | — | Fichier absent | oui |
| 3 | P1 | PUSH_DOWN | skill release | `release plan|run` avec pré-conditions en exit 1 ; skill réduit à la séquence | — | `release plan` sort en 1 sur CI rouge / tag existant | non |
| 4 | P2 | PROMOTE | release.mjs | Version en argument, plus de déduction par branche | 3 | Sans version, exit 1 | non |
| 5 | P2 | MERGE | hotfix.mjs | Supprimer, remplacé par `release run --hotfix` | 3 | Fichier absent | oui |
| 6 | P2 | KEEP | ci.yml | Versionner le wrapper Gradle | — | Run vert sur develop | non |
| 7 | P2 | PUSH_DOWN | migrations Flyway | Test de checksum / `flyway validate` dans ci.yml ; raccourcir la règle | 6 | Modifier V1 casse la CI | non |
| 8 | P2 | PUSH_DOWN | AGENTS.md (Interdit main) | Protection de branche sur `main` | — | `gh api …/branches/main/protection` | oui |
| 9 | P3 | KEEP | ArchitectureTest | Corriger le commentaire | — | grep vide | non |

## 6. Ce que l'audit n'a pas pu vérifier

- Les commandes Gradle (`./gradlew checkstyleMain checkstyleTest`, `./gradlew test`) : pas de toolchain ; recopiées de `ci.yml`.
- Absence de `gradlew` / `gradle/wrapper/` et de `Dockerfile` : constatée en local, à confirmer sur le remote.
- Protection de la branche `main` et branche par défaut : pas de remote ; `workflow_dispatch` n'est accepté que depuis la branche par défaut.
- Point de santé de la production : inconnu.
- Nombre de tests exécutés par `ci.yml` : inconnu.
- Scripts Node : syntaxe seulement (`node --check`), pas d'exécution réelle.

## 7. Données machine

Le bloc JSON est écrit tel quel dans `repo/.harness/audit.json` (201 lignes) ; reproduit ci-dessous.

```json
{
  "audit": {
    "process": "Release de billing-api et instrumentation IA (harness-init)",
    "scope": "repo billing-api (branche develop) : AGENTS.md, CLAUDE.md, .claude/skills/release, scripts/, .github/workflows/, config/checkstyle, src/test ArchUnit, migrations Flyway",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 5 }
  },
  "elements": [
    {
      "id": "agents-md",
      "path": "AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["claude-md"],
      "calls": ["skill-release", "ci-yml", "archunit-test"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "44 lignes, mode explicite, trois règles justifiées dont une vérifiée, Interdits, Processus, Maintenance ; deux règles racontées marquées (non vérifiée).",
      "evidence": ["AGENTS.md:3", "AGENTS.md:17-19", "AGENTS.md:37-42"],
      "target": "Rester sous 60 lignes ; chaque règle (non vérifiée) gagne son garde-fou puis se raccourcit.",
      "check": "harness status : L1 5/5, L2.maintenance et L2.rule_convention vrais."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["agents-md"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Stub d'une ligne @AGENTS.md : source unique respectée.",
      "evidence": ["CLAUDE.md:1"],
      "target": "Inchangé.",
      "check": "harness status : L1.single_source vrai."
    },
    {
      "id": "skill-release",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["agents-md"],
      "calls": ["release-yml"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "Les pré-conditions de release (CI verte sur la ref, tag absent, version croissante, migrations non modifiées) sont racontées dans le skill ; aucun code ne les impose avant `gh workflow run`.",
      "evidence": [".claude/skills/release/SKILL.md:15-19", ".claude/skills/release/SKILL.md:25-29"],
      "target": "Une sous-commande `release plan <version> --ref <ref>` (réécriture de scripts/release.mjs) qui vérifie les quatre pré-conditions avec exit 1 et imprime le plan en JSON ; `release run` ne s'exécute qu'après un plan valide. Le skill ne garde que la séquence et la demande de validation.",
      "check": "Depuis une branche à CI rouge ou avec un tag existant, `release plan` sort en 1 sans rien déclencher ; le skill ne contient plus de commande `gh run list`/`git ls-remote` à interpréter."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["skill-release", "script-release-mjs", "script-hotfix-mjs"],
      "calls": [],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "Un seul job construit, publie, tague et déploie en production : aucun `environment` protégé, aucun point d'arrêt humain, pas d'input dry_run, le tag est posé après la publication de l'image, l'input `hotfix` n'est lu par aucune étape, et la fin de job se signale par `echo SUCCESS` (non structuré).",
      "evidence": [".github/workflows/release.yml:16-32", ".github/workflows/release.yml:11-14", ".github/workflows/release.yml:27", ".github/workflows/release.yml:32"],
      "target": "Deux jobs : `build-publish` (jar, image, tag) puis `deploy` sous `environment: production` avec reviewers requis ; input `dry_run` qui s'arrête après le plan ; sorties de job (tag, digest d'image, URL) à la place d'`echo SUCCESS` ; supprimer ou consommer l'input `hotfix`.",
      "check": "Un `gh workflow run release.yml` s'arrête en attente d'approbation avant le job deploy ; avec `dry_run=true` aucune image n'est poussée ; `gh run view --json jobs` montre les deux jobs."
    },
    {
      "id": "script-old-deploy",
      "path": "scripts/old-deploy.sh",
      "declared_layer": "L3",
      "actual_layer": "L4",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "Script mort (« plus appelé nulle part ») qui déploie en production par ssh direct sans tag, sans trace et sans validation : contourne l'Interdit n°1 d'AGENTS.md.",
      "evidence": ["scripts/old-deploy.sh:2", "scripts/old-deploy.sh:5-7"],
      "target": "Supprimer le fichier.",
      "check": "`ls scripts/old-deploy.sh` échoue ; aucun autre fichier ne contient `ssh deploy@prod.acme.io` hors release.yml."
    },
    {
      "id": "script-release-mjs",
      "path": "scripts/release.mjs",
      "declared_layer": "L3",
      "actual_layer": "MIXED",
      "called_by": [],
      "calls": ["release-yml"],
      "verdict": "PROMOTE",
      "priority": "P2",
      "finding": "Déduit le type de version du nom de branche (develop → mineure, feat/breaking-* → majeure) : du jugement codé en dur, cause plausible des erreurs de release signalées par l'équipe ; ne vérifie aucune pré-condition (CI, tag, VERSION) avant de déclencher le workflow.",
      "evidence": ["scripts/release.mjs:11-17", "scripts/release.mjs:23"],
      "target": "La version devient un argument obligatoire décidé par l'humain ; le script devient `release plan|run` et porte les pré-conditions (voir skill-release).",
      "check": "`node scripts/release.mjs` sans argument version sort en 1 avec un message explicite."
    },
    {
      "id": "script-hotfix-mjs",
      "path": "scripts/hotfix.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": ["release-yml"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Même mécanique que release.mjs (lecture de VERSION, calcul, `gh workflow run`) dupliquée avec une variation d'incrément et un flag `hotfix=true` que le workflow ignore.",
      "evidence": ["scripts/hotfix.mjs:2", "scripts/hotfix.mjs:11-16"],
      "target": "Absorbé par `release plan|run --hotfix`.",
      "check": "Le fichier n'existe plus ; `release run --hotfix` depuis `hotfix/*` déclenche le workflow avec les bons inputs."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["agents-md"],
      "calls": ["checkstyle", "archunit-test"],
      "verdict": "KEEP",
      "priority": "P2",
      "finding": "Checkstyle et tests sur PR, develop et main : bonne couche. Mais `./gradlew` est appelé alors qu'aucun wrapper (gradlew, gradle/wrapper/) n'est versionné : si c'est l'état réel du dépôt, chaque run échoue à la première étape et rien n'est vérifié.",
      "evidence": [".github/workflows/ci.yml:13-14", "build.gradle:1"],
      "target": "Versionner le wrapper (`gradle wrapper`) ou remplacer par `gradle/actions/setup-gradle` ; ajouter un job `flyway validate` ou un test de checksum des migrations.",
      "check": "`git ls-files gradlew gradle/wrapper/gradle-wrapper.properties` renvoie deux fichiers ; un run ci.yml vert existe sur develop."
    },
    {
      "id": "checkstyle",
      "path": "config/checkstyle/checkstyle.xml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Quatre règles de style (120 colonnes, pas d'import étoile, une classe par fichier, nommage) portées par l'outil : aucune n'a besoin d'être racontée dans AGENTS.md.",
      "evidence": ["config/checkstyle/checkstyle.xml:4-10", "build.gradle:24-27"],
      "target": "Inchangé.",
      "check": "`./gradlew checkstyleMain checkstyleTest` vert en CI."
    },
    {
      "id": "archunit-test",
      "path": "src/test/java/com/acme/billing/ArchitectureTest.java",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": "P3",
      "finding": "Garde-fou sain de la règle « contrôleur ne dépend pas d'un repository » ; son commentaire renvoie à « CLAUDE.md, Conventions », fichier qui n'existait pas et qui est maintenant un stub.",
      "evidence": ["src/test/java/com/acme/billing/ArchitectureTest.java:12-16"],
      "target": "Pointer le commentaire vers AGENTS.md, section Règles.",
      "check": "`grep -n 'CLAUDE.md' src/test/java/com/acme/billing/ArchitectureTest.java` ne renvoie rien."
    },
    {
      "id": "flyway-migrations",
      "path": "src/main/resources/db/migration/",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Une seule migration (V1__init.sql) et aucun test ni job qui gèle les migrations appliquées : la règle et l'Interdit correspondants d'AGENTS.md ne tiennent que par le texte.",
      "evidence": ["src/main/resources/db/migration/V1__init.sql:1", "AGENTS.md:18", "AGENTS.md:23"],
      "target": "Un test qui compare les checksums des migrations versionnées à une liste gelée (ou `flyway validate` contre une base de référence) dans ci.yml.",
      "check": "Modifier un caractère de V1__init.sql fait échouer ci.yml."
    }
  ],
  "process_leaks": [
    { "rule": "Pré-conditions de release : CI verte sur la ref, tag v<version> absent, version strictement croissante, migrations non modifiées", "told_in": ".claude/skills/release/SKILL.md:15-19", "if_skipped": "Une version déjà publiée ou un commit à CI rouge part en production", "belongs_in": "L3", "guard_tool": "sous-commande `release plan` avec exit 1 (réécriture de scripts/release.mjs)" },
    { "rule": "Validation humaine explicite avant tout déploiement en production", "told_in": "AGENTS.md:22 ; .claude/skills/release/SKILL.md:22", "if_skipped": "Un agent déploie en production d'un seul `gh workflow run`", "belongs_in": "L4", "guard_tool": "job deploy sous `environment: production` avec reviewers requis dans release.yml" },
    { "rule": "Une migration Flyway appliquée ne se modifie jamais", "told_in": "AGENTS.md:18 ; AGENTS.md:23", "if_skipped": "Flyway refuse le checksum, l'application ne redémarre plus en production", "belongs_in": "L3", "guard_tool": "test de checksum des migrations ou `flyway validate` dans ci.yml" },
    { "rule": "Pas de push direct sur main", "told_in": "AGENTS.md:24", "if_skipped": "Du code non revu ni testé arrive sur la branche de production", "belongs_in": "L4", "guard_tool": "protection de branche GitHub sur main (PR + ci.yml requis) — non vérifiable ici, pas de remote" },
    { "rule": "VERSION est mis à jour sur develop après chaque release", "told_in": ".claude/skills/release/SKILL.md:36", "if_skipped": "La prochaine release calcule depuis une version périmée et republie un numéro existant", "belongs_in": "L4", "guard_tool": "étape de release.yml qui commite VERSION ou ouvre la PR" }
  ],
  "guarded_rules": [
    { "rule": "Un contrôleur ne dépend jamais d'un repository", "told_in": "AGENTS.md:17", "guarded_by": "src/test/java/com/acme/billing/ArchitectureTest.java (controllers_do_not_touch_repositories), lancé par ci.yml" },
    { "rule": "Style Java : 120 colonnes, pas d'import étoile, une classe par fichier, nommage des constantes et méthodes", "told_in": "non racontée (volontairement)", "guarded_by": "config/checkstyle/checkstyle.xml via ci.yml:13" }
  ],
  "instruction_files": [
    { "path": "AGENTS.md", "loaded_lines": 44, "instruction_pct": 75, "reference_pct": 25, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": "CLAUDE.md", "loaded_lines": 44, "instruction_pct": 0, "reference_pct": 100, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": ".claude/skills/release/SKILL.md", "loaded_lines": 45, "instruction_pct": 85, "reference_pct": 15, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "SPLIT", "element": "release-yml", "action": "Séparer build-publish et deploy ; placer deploy sous `environment: production` avec reviewers requis ; ajouter un input dry_run ; remplacer `echo SUCCESS` par des sorties de job ; fusionner aussi sur main (workflow_dispatch ne part que de la branche par défaut).", "depends_on": [], "check": "Un run s'arrête en attente d'approbation avant deploy ; dry_run=true ne pousse aucune image.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "BLOCK", "element": "script-old-deploy", "action": "Supprimer scripts/old-deploy.sh.", "depends_on": [], "check": "Fichier absent ; aucun `ssh deploy@prod.acme.io` hors release.yml.", "needs_human_approval": true },
    { "order": 3, "priority": "P1", "verdict": "PUSH_DOWN", "element": "skill-release", "action": "Réécrire scripts/release.mjs en `release plan <version> --ref <ref> [--hotfix]` (vérifie CI verte, tag absent, version croissante, migrations non modifiées, exit 1 ; plan en JSON) et `release run` ; le skill ne garde que la séquence et la validation.", "depends_on": [], "check": "`release plan` sort en 1 sur une ref à CI rouge ou un tag existant ; le skill ne contient plus de vérification à interpréter.", "needs_human_approval": false },
    { "order": 4, "priority": "P2", "verdict": "PROMOTE", "element": "script-release-mjs", "action": "La version devient un argument obligatoire ; supprimer la déduction par nom de branche.", "depends_on": [3], "check": "Sans argument version, exit 1 avec message.", "needs_human_approval": false },
    { "order": 5, "priority": "P2", "verdict": "MERGE", "element": "script-hotfix-mjs", "action": "Supprimer scripts/hotfix.mjs, remplacé par `release run --hotfix`.", "depends_on": [3], "check": "Fichier absent ; `release run --hotfix` depuis hotfix/* fonctionne.", "needs_human_approval": true },
    { "order": 6, "priority": "P2", "verdict": "KEEP", "element": "ci-yml", "action": "Versionner le wrapper Gradle (gradlew, gradle/wrapper/) ou passer par gradle/actions/setup-gradle.", "depends_on": [], "check": "Un run ci.yml vert sur develop.", "needs_human_approval": false },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "flyway-migrations", "action": "Ajouter un test de checksum des migrations versionnées (ou `flyway validate`) lancé par ci.yml ; raccourcir la règle d'AGENTS.md en « Vérifiée par ».", "depends_on": [6], "check": "Modifier V1__init.sql fait échouer ci.yml.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Activer la protection de branche sur main (PR obligatoire, check ci.yml requis) et noter « Vérifiée par : protection de branche » sur l'Interdit.", "depends_on": [], "check": "`gh api repos/:owner/:repo/branches/main/protection` renvoie required_pull_request_reviews et required_status_checks.", "needs_human_approval": true },
    { "order": 9, "priority": "P3", "verdict": "KEEP", "element": "archunit-test", "action": "Remplacer « CLAUDE.md, Conventions » par « AGENTS.md, Règles » dans le commentaire.", "depends_on": [], "check": "grep CLAUDE.md sur le test ne renvoie rien.", "needs_human_approval": false }
  ],
  "unverified": [
    "Les commandes Gradle (`./gradlew checkstyleMain checkstyleTest`, `./gradlew test`) n'ont pas été exécutées : pas de toolchain disponible pendant l'init ; elles sont recopiées de ci.yml.",
    "Absence de gradlew et de gradle/wrapper/ dans le dépôt : constatée sur la branche develop locale, à confirmer sur le remote.",
    "Absence de Dockerfile alors que release.yml:24 lance `docker build .` : à confirmer sur le remote.",
    "Protection de la branche main et branche par défaut du dépôt : pas de remote configuré, non vérifiables (workflow_dispatch n'est accepté que depuis la branche par défaut).",
    "Point de santé de la production pour vérifier une release : inconnu, à fournir par l'équipe.",
    "Nombre de tests réellement exécutés par ci.yml : inconnu.",
    "Scripts Node : seule la syntaxe a été vérifiée (`node --check`), aucune exécution réelle (elles déclencheraient release.yml)."
  ]
}
```
