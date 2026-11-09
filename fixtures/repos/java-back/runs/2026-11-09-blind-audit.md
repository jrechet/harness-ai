# Audit du harness — Release de billing-api (+ instrumentation IA du dépôt)

**Périmètre** : `fixtures/repos/java-back/repo/` — `CLAUDE.md`, `.claude/skills/release/`, `scripts/`, `.github/workflows/`, `config/checkstyle/`, `build.gradle`, `VERSION`, tests d'architecture · **Date** : 2026-11-09 · **Éléments inventoriés** : 11

## 1. Synthèse

- **Score de santé** : 0 — L'agent est un pilier, pas un accélérateur : toutes les pré-conditions de release, la détection du succès et la gestion d'échec ne vivent que dans des prompts ; le seul code existant (deux scripts non testés) déclenche directement le déploiement prod sans dry-run ni point d'arrêt humain. Calcul : 100 − 4 × 25 (P1) − 2 × 8 (P2) = −16, borné à 0 (et de toute façon plafonné à 60 par l'échec du test « coupe l'agent »).
- **Résultat du test « coupe l'agent »** : ÉCHEC — 5 étape(s) du processus n'existent que dans des prompts (CI verte, migrations Flyway appliquées, branche à jour, détection du succès, conduite à tenir en cas d'échec), et une étape obligatoire (mise à jour de `VERSION`) n'existe nulle part.
- **Points bloquants (P1)** : 4
- **Les trois actions qui changent le plus les choses** :
  1. Protéger `release.yml` : `environment: production` avec reviewers requis, input `dry_run`, vérification en workflow que la CI est verte sur le SHA et que `ref` est une branche autorisée, tag *après* déploiement réussi, sortie structurée (job outputs) au lieu de `echo "SUCCESS"`.
  2. Remplacer `scripts/release.mjs` + `scripts/hotfix.mjs` par une CLI testée à trois sous-commandes (`release check` / `release plan --type` / `release run --plan`) qui encode les pré-conditions en `exit 1`, rend le choix du type de version à l'agent et produit du JSON ; puis réécrire le SKILL.md pour n'être que la séquence qui les appelle.
  3. Supprimer `scripts/old-deploy.sh` (déploiement prod depuis un poste, sans CI ni tag) et corriger `CLAUDE.md` (exemple qui contredit sa propre règle, procédure de release dupliquée et déjà divergente, règles obligatoires sans garde-fou → ArchUnit/Checkstyle/PR gate).

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | Fichier d'instructions | `CLAUDE.md` | L2 | L2 (contient aussi la procédure de release, doublon du skill) | Chargé automatiquement par Claude Code à chaque session | `release-skill`, `release-mjs`, `hotfix-mjs`, `ci-yml`, `release-yml`, `checkstyle`, `archunit-test` |
| 2 | Skill release | `.claude/skills/release/SKILL.md` | L2 | MIXED (procédure + pré-conditions L3 racontées + lecture de logs à la place d'un retour L1 structuré) | `claude-md:46`, déclenchement par mots-clés (`SKILL.md:3`) | `release-mjs`, `hotfix-mjs`, `release-yml` (via `gh run watch`), `ci-yml` (lecture onglet Actions) |
| 3 | Script de release | `scripts/release.mjs` | L3 | MIXED (jugement L1 codé en dur : type de version déduit de la branche ; déclenchement L4 direct) | `release-skill:14`, `claude-md:97` | `version-file`, `release-yml` (`gh workflow run`) |
| 4 | Script de hotfix | `scripts/hotfix.mjs` | L3 | L3 (doublon de `release.mjs`, déclenchement L4 direct) | `release-skill:19`, `claude-md:101` | `version-file`, `release-yml` |
| 5 | Ancien déploiement manuel | `scripts/old-deploy.sh` | L3 | L4 (build + push + ssh prod depuis un poste) | Personne (`old-deploy.sh:2`) | Registry + hôte prod directement |
| 6 | Workflow release | `.github/workflows/release.yml` | L4 | L4 | `release-mjs:23`, `hotfix-mjs:16` | `build-gradle` (bootJar), registry, tag, ssh prod |
| 7 | Workflow CI | `.github/workflows/ci.yml` | L4 | L4 | Événements push `develop`/`main`, pull_request | `build-gradle` (checkstyle, test) → `checkstyle`, `archunit-test` |
| 8 | Checkstyle | `config/checkstyle/checkstyle.xml` | L3 | L3 | `build-gradle:26`, `ci-yml:13` | — |
| 9 | Test d'architecture | `src/test/java/com/acme/billing/ArchitectureTest.java` | L3 | L3 | `ci-yml:14` (via `gradlew test`) | — |
| 10 | Build | `build.gradle` | L3 | L3 | `ci-yml:13-14`, `release-yml:23` | `checkstyle`, `version-file` |
| 11 | Source de vérité de version | `VERSION` | L3 | L3 (donnée jamais mise à jour par le processus) | `release-mjs:7`, `hotfix-mjs:11`, `build-gradle:9` | — |

Absents de l'inventaire (vérifié) : aucune définition d'agent ou de sous-agent, aucun `.cursor/rules`, aucun hook, aucun template de PR, aucun `CODEOWNERS`, aucun `.harness/`.

Processus nominal, étape par étape :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| 1. S'assurer que la CI de `develop` est verte | `SKILL.md:9`, `CLAUDE.md:96` (L2, « ouvre l'onglet Actions ») | Non — ni `release.mjs` ni `release.yml` n'interrogent le statut de la CI | — |
| 2. Vérifier qu'aucune migration Flyway n'est en attente en prod | `SKILL.md:10` (L2, « demande un dump au propriétaire ») | Non — dépend d'un humain, non reproductible | — |
| 3. Être sur `develop` à jour | `SKILL.md:11` (L2) | Non — `release.mjs:11` vérifie le *nom* de la branche, pas la synchronisation ni la propreté de l'arbre | — |
| 4. Calculer la prochaine version | `release.mjs:10-20`, `hotfix.mjs:13` (L3 non testé, jugement codé) | Partiel — `exit 1` sur branche inattendue (`release.mjs:18-19`, `hotfix.mjs:8-9`) | Non — affiche le plan et déclenche dans la foulée (`release.mjs:22-23`) |
| 5. Mettre à jour `VERSION` et committer | **Personne** | Non — `VERSION` est lu (`release.mjs:7`) mais jamais écrit ; la release suivante recalcule la même version | — |
| 6. Déclencher `release.yml` | `release.mjs:23`, `hotfix.mjs:16` (L3→L4) | Aucune pré-condition vérifiée avant l'appel | Non |
| 7. Build jar, image Docker, push registry | `release.yml:23-26` (L4) | Oui (codes de sortie des steps) | Non — pas d'input `dry_run` (`release.yml:3-14`) |
| 8. Tag git `vX.Y.Z` | `release.yml:27` (L4) | Oui, mais **avant** le déploiement : un deploy raté laisse un tag orphelin | Non |
| 9. Déploiement prod par SSH | `release.yml:28-31` (L4) | Pas d'`environment` protégé, pas de validation humaine, pas de contrôle de `ref` | Non |
| 10. Constater le succès | `SKILL.md:15`, `CLAUDE.md:98` (L2 : chercher `SUCCESS` dans le log) | Non — `echo "SUCCESS"` (`release.yml:32`) est du texte libre, pas un output de job | — |
| 11. Conduite en cas d'échec | `SKILL.md:16` (L2) | Non | — |
| 12. Annoncer dans #releases avec la liste des PRs | `SKILL.md:22`, `CLAUDE.md:99` (L1/L2, humain) | Non — acceptable : c'est de la communication, donc L1 | — |

## 3. Fuites : règles et étapes racontées sans vérification

**Étapes du processus de release qui ne vivent que dans un prompt**

| Règle / étape | Racontée où | Si l'agent la saute | Doit vivre en | Outil cible |
|---|---|---|---|---|
| « Ne release jamais sur un develop rouge » | `SKILL.md:9`, `CLAUDE.md:96` | Une image non testée part en prod ; l'agent peut lire le mauvais run ou halluciner un vert | L3 + L4 | Sous-commande `release check` (`gh api repos/:o/:r/commits/<sha>/check-runs` → `exit 1`) **et** step de garde dans `release.yml` avant `bootJar` |
| Aucune migration Flyway en attente en prod | `SKILL.md:10` | Déploiement d'un schéma non validé ; l'étape dépend d'un dump demandé à un humain | L3 | `release check --migrations` comparant `db/migration` à `flyway_schema_history` via une connexion read-only, ou test Testcontainers `flyway.validate()` en CI |
| Sur `develop` à jour, arbre propre | `SKILL.md:11` | `ref=develop` est envoyé au workflow : les commits locaux non poussés sont silencieusement exclus de la release | L3 | `release check` : `git status --porcelain` vide, `git rev-parse HEAD == origin/develop`, tag `v<next>` inexistant |
| Mise à jour de `VERSION` après release | Nulle part (`release.mjs:7` lit, personne n'écrit) | La release suivante recalcule `1.5.0`, `git tag` échoue (`release.yml:27`) **après** le push de l'image | L3/L4 | `release run` bump + commit + push de `VERSION`, ou step `release.yml` qui committe |
| Succès = `SUCCESS` dans le log | `SKILL.md:15`, `CLAUDE.md:98`, produit par `release.yml:32` | Succès halluciné (chaîne présente ailleurs, run partiellement vert) | L4 → L1 | `outputs:` du job (`version`, `image`, `deployed_sha`, `health_url`) + `gh run view --json conclusion` lu par la CLI |
| Si `ERROR`/`FAILED` : prévenir, ne pas relancer | `SKILL.md:16` | Relance en boucle d'un deploy prod | L3 | `release run` refuse si un run `release.yml` est en cours ou a échoué sur la même version ; `concurrency:` dans le workflow |
| Le type de version est décidé par le nom de branche | `release.mjs:11-16`, `SKILL.md:14`, `CLAUDE.md:97` | Pas de saut possible, mais un jugement L1 est figé en L3 : une release *majeure* depuis `develop` est impossible sans contourner le script | L1 | `release plan --type minor|major|patch` : la CLI expose les options, l'agent/humain choisit |

**Règles de CLAUDE.md racontées sans garde-fou**

| Règle | Racontée où | Si l'agent la saute | Doit vivre en | Outil cible |
|---|---|---|---|---|
| Injection par constructeur, jamais `@Autowired` sur un champ | `CLAUDE.md:51` | Déjà violée dans le code (`InvoiceService.java:10-11`) **et** dans l'exemple du fichier lui-même (`CLAUDE.md:74-75`) | L3 | ArchUnit : `noFields().should().beAnnotatedWith(Autowired.class)` dans `ArchitectureTest.java` |
| Chaque endpoint a un test d'autorisation (403 avec le mauvais rôle) | `CLAUDE.md:57` | Aucun test de ce type n'existe (`InvoiceControllerTest.java:8`) ; une API de facturation sans contrôle d'accès testé | L3 | Test JUnit générique énumérant `RequestMappingHandlerMapping` et appelant chaque route avec `@WithMockUser(roles="NONE")` → 403, exécuté par `ci.yml` |
| Ne jamais modifier une migration Flyway appliquée | `CLAUDE.md:63` | `FlywayValidateException` découverte au déploiement prod (`CLAUDE.md:104`) | L3 (PR gate) | Step `ci.yml` : `git diff --diff-filter=MD --name-only origin/develop... -- src/main/resources/db/migration` doit être vide |
| Pas de `@MockBean` dans les tests unitaires | `CLAUDE.md:92` | Suite lente, contexte Spring démarré | L3 | Checkstyle `IllegalImport` sur `org.springframework.boot.test.mock.mockito.MockBean` dans `checkstyleTest`, ou règle ArchUnit sur les classes `*Test` |
| 4 espaces, pas de tabulation | `CLAUDE.md:84` | Diff bruité | L3 | Checkstyle `FileTabCharacter` (absent de `checkstyle.xml`) |
| Imports groupés java / javax / org / com | `CLAUDE.md:85` | Diff bruité | L3 | Checkstyle `CustomImportOrder` (absent) |
| Classes en PascalCase, champs en camelCase | `CLAUDE.md:66` | Incohérence de nommage | L3 | Checkstyle `TypeName`, `MemberName`, `ParameterName` (seuls `ConstantName` et `MethodName` existent, `checkstyle.xml:8-9`) |
| Tests nommés `<Class>Test` / `<Class>IT` | `CLAUDE.md:67` | Tests non ramassés par un filtre Gradle futur | L3 | ArchUnit sur `src/test` (`classes().that().areAnnotatedWith(SpringBootTest).should().haveSimpleNameEndingWith("IT")`) — P3 |
| DTOs en `record` | `CLAUDE.md:87` | Hygiène | L3 | ArchUnit `classes().that().resideInAPackage("..dto..").should().beRecords()` — P3 |
| Commentaires `given / when / then` | `CLAUDE.md:91` | Hygiène | — | Bruit : un modèle récent le fait ; supprimer ou garder en une ligne |
| Try-with-resources | `CLAUDE.md:60` | Hygiène | — | Bruit : comportement par défaut d'un modèle récent ; supprimer |

**Règles qui ont leur garde-fou (partie saine, à raccourcir dans CLAUDE.md)**

- « Un contrôleur qui touche un repository est un bug » (`CLAUDE.md:27`, `CLAUDE.md:54`) → `ArchitectureTest.java:14-16`, avec le *pourquoi* en Javadoc (`ArchitectureTest.java:12`). Garde partiel : couvre la dépendance au repository, pas « pas de logique métier ».
- Longueur de ligne 120 (`CLAUDE.md:84`) → `checkstyle.xml:4`.
- Pas d'import wildcard (`CLAUDE.md:85`) → `checkstyle.xml:6`.
- Une classe publique par fichier (`CLAUDE.md:68`) → `checkstyle.xml:7`.
- Constantes `UPPER_SNAKE_CASE`, méthodes `camelCase` (`CLAUDE.md:66`) → `checkstyle.xml:8-9`.
- « Lancer la suite complète avant d'ouvrir une PR » (`CLAUDE.md:93`) → `ci.yml:5,14` (`pull_request` + `gradlew test`).
- Checkstyle sur chaque push (`CLAUDE.md:45`) → `ci.yml:13`.
- Un hotfix part d'une branche `hotfix/*` (`SKILL.md:19`) → `hotfix.mjs:7-10` (`exit 1`).

## 3b. Coût de contexte

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| `CLAUDE.md` | 111 (aucun `@include`) | ≈ 40 % instruction (Conventions, Code style, Testing : l. 48-69, 83-93) / ≈ 45 % référence (Build & Run l. 5-13, Stack l. 15-19, Package structure et Key files l. 31-46, Release l. 95-101, Troubleshooting l. 103-111) / ≈ 15 % bruit (naming standard l. 66, try-with-resources l. 60, exemple erroné l. 70-81) | Chaque session Claude Code |
| `.claude/skills/release/SKILL.md` | 22 | ≈ 90 % procédure / 10 % en-tête | À la demande (mots-clés release / mise en prod / déploiement / hotfix, `SKILL.md:3`) |

Justification des règles : trois règles disent *pourquoi* (`CLAUDE.md:51` « hides dependencies and breaks unit tests », `CLAUDE.md:92` « it starts the context », `CLAUDE.md:104` cause de `FlywayValidateException`) ; toutes les autres sont des MUST nus, et aucun incident ni issue n'est cité. **Aucune clause de maintenance** (comment une règle entre ou sort du fichier). Aucune description du processus de travail (quand s'arrêter et demander, critère de « fini », test flaky) alors que le dépôt délègue bien une tâche entière à l'agent (la release).

Cohérence interne : l'exemple « a well-formed service » (`CLAUDE.md:70-81`) utilise `@Autowired` sur un champ, exactement ce que la règle de `CLAUDE.md:51` interdit, et référence `Invoice.from(command)` / `CreateInvoiceCommand` qui n'existent pas ; il a vraisemblablement déjà été copié (`InvoiceService.java:10-11`). La procédure de release de `CLAUDE.md:95-101` a déjà divergé du skill (elle omet la vérification Flyway et la conduite en cas d'échec de `SKILL.md:10,16`). Plusieurs références pointent vers des fichiers inexistants : `InvoiceServiceTest` (`CLAUDE.md:9`), `docker compose` (`CLAUDE.md:12,105`, aucun fichier compose), packages `customer/payment/config/security` (`CLAUDE.md:33-37`), `gradle.properties` (`CLAUDE.md:109`).

## 4. Constats par élément

### [SPLIT] [P1] Script de release — `scripts/release.mjs`
- **Fait aujourd'hui** : lit la branche courante et `VERSION`, déduit le type de version du nom de branche (`develop` → mineure, `feat/breaking-*` → majeure, `release/x.y.z` → version littérale), affiche une ligne et déclenche immédiatement `gh workflow run release.yml` (`release.mjs:6-24`).
- **Problème** : (a) jugement L1 figé en L3 — le type de release est décidé par une convention de nommage, pas par un humain ou l'agent (`release.mjs:11-16`) ; (b) action L4 irréversible déclenchée sans aucune pré-condition vérifiée ni dry-run — pas de contrôle d'arbre propre, de synchronisation avec `origin`, de statut CI, d'existence du tag (`release.mjs:22-23`) ; (c) `VERSION` n'est jamais mis à jour ni committé (`release.mjs:7`, `build.gradle:9`), donc la release suivante recalcule la même version et le `git tag` de `release.yml:27` échoue après que l'image a été poussée ; (d) `ref=${branch}` envoie un nom de branche, pas le SHA local — tout commit non poussé est exclu silencieusement ; (e) sortie non structurée (`console.log`, `release.mjs:22,24`), pas d'URL de run ; (f) aucun test, pas de `package.json`.
- **Doit devenir** : une CLI testée (`scripts/release/` ou package `release`) à trois sous-commandes : `check` (pré-conditions → `exit 1` typé), `plan --type minor|major|patch` (JSON : `current`, `next`, `sha`, `ref`, sans effet de bord), `run --plan plan.json [--dry-run]` (bump + commit `VERSION`, déclenche, renvoie `{run_url, version}`). Le choix du type est un argument donné par l'agent (L1).
- **Critère de vérification** : `release plan --type minor` sur un arbre sale ou désynchronisé sort en code ≠ 0 avec un message typé ; `release run --dry-run` ne déclenche aucun workflow ; tests unitaires du calcul de version et des pré-conditions verts en CI ; `scripts/release.mjs` supprimé.

### [BLOCK] [P1] Ancien déploiement manuel — `scripts/old-deploy.sh`
- **Fait aujourd'hui** : build, push registry et `ssh deploy@prod.acme.io … docker compose up -d` depuis le poste de l'opérateur (`old-deploy.sh:5-7`).
- **Problème** : script mort (`old-deploy.sh:2` « Plus appelé nulle part ») qui reste exécutable : il déploie en prod sans CI, sans tag, sans trace dans Actions, en dupliquant `release.yml:24-31`. Un agent qui explore `scripts/` peut le trouver et le lancer ; la présence de credentials locaux (docker login, clé SSH) n'est pas vérifiable dans le dépôt.
- **Doit devenir** : supprimé (ou, le temps de la transition, neutralisé par `exit 1` en tête avec un message pointant vers `release run`).
- **Critère de vérification** : fichier absent du dépôt ; `grep -r old-deploy` ne renvoie rien ; approbation explicite du propriétaire avant suppression.

### [PUSH_DOWN] [P1] Workflow release — `.github/workflows/release.yml`
- **Fait aujourd'hui** : `workflow_dispatch` avec inputs `version`, `ref`, `hotfix` ; checkout de `ref`, `bootJar -Pversion`, build/push image, tag, SSH prod, `echo "SUCCESS"` (`release.yml:3-32`).
- **Problème** : (a) pas d'`environment: production` donc aucun reviewer requis, aucun point d'arrêt humain entre plan et déploiement (`release.yml:16-17`) ; (b) pas d'input `dry_run` (`release.yml:4-14`) ; (c) `ref` libre : n'importe quelle branche ou commit peut être déployé en prod (`release.yml:8-10,20`), et le workflow ne vérifie ni que la CI est verte sur ce SHA ni ne relance `gradlew test` lui-même (`release.yml:23`) ; (d) le tag est poussé avant le déploiement (`release.yml:27` puis `28-31`) : un deploy raté laisse `vX.Y.Z` sur un commit jamais livré ; (e) `-Pversion=${{ inputs.version }}` est écrasé par `build.gradle:9` (`version = file('VERSION')…`) : l'image `1.5.0` contient un jar `1.4.2` ; (f) `inputs.hotfix` n'est jamais utilisé (`release.yml:11-14` vs `hotfix.mjs:16`) ; (g) le seul signal de succès est `echo "SUCCESS"` (`release.yml:32`), pas de `outputs`, pas de healthcheck post-deploy, pas de `concurrency`. Point positif : les secrets restent en L4 (`release.yml:25,30`), aucun secret dans les scripts.
- **Doit devenir** : job `plan` (valide `version` contre `VERSION`, valide `ref ∈ {develop, release/*, hotfix/*}`, vérifie `check-runs` verts sur le SHA, publie un résumé) → job `deploy` avec `environment: production` (reviewers requis) sauté si `dry_run=true`, tests ou garde CI avant `bootJar`, tag après healthcheck réussi, `outputs: version, image, sha, run_url`, `concurrency: release-prod`.
- **Critère de vérification** : un dispatch avec `dry_run=true` se termine sans toucher registry/prod/tags ; un dispatch sur une branche `feat/*` échoue au job `plan` ; le job `deploy` affiche « Waiting for review » dans Actions ; `gh run view --json jobs` expose les outputs ; `-Pversion` honoré (`build.gradle` lit `project.hasProperty('version') ? … : VERSION`).

### [PUSH_DOWN] [P1] Skill release — `.claude/skills/release/SKILL.md`
- **Fait aujourd'hui** : décrit 8 étapes : trois pré-conditions manuelles (CI verte via l'onglet Actions, migrations Flyway via un dump demandé au propriétaire, `git pull`), lancement de `release.mjs`, lecture de `SUCCESS`/`ERROR` dans `gh run watch`, hotfix, annonce (`SKILL.md:8-22`).
- **Problème** : les trois pré-conditions obligatoires sont racontées, pas vérifiées — l'agent peut les sauter ou mal lire l'onglet Actions (`SKILL.md:9-11`) ; l'étape 10 n'est pas reproductible sans humain ; la décision L1 « est-ce un succès » repose sur un grep de log (`SKILL.md:15-16`), ce que le skill harness identifie comme source de succès hallucinés. Le skill contient en revanche ce qui doit y être : vocabulaire, séquence, cas d'abandon (`SKILL.md:16`), point de communication (`SKILL.md:22`).
- **Doit devenir** : un SKILL.md qui ne décrit que la séquence `release check` → `release plan --type <choisi avec l'utilisateur>` → **point d'arrêt : montrer le plan JSON et demander confirmation** → `release run --plan` → lire `gh run view --json conclusion,jobs` → annoncer. Les cas d'abandon restent, les pré-conditions deviennent « si `release check` sort en erreur, arrête-toi et rapporte le message ».
- **Critère de vérification** : le SKILL.md ne contient plus aucune instruction du type « ouvre l'onglet », « compare avec la table », « quand la sortie contient SUCCESS » ; chaque commande citée existe et a un test.

### [MERGE] [P2] Script de hotfix — `scripts/hotfix.mjs`
- **Fait aujourd'hui** : même mécanique que `release.mjs` avec incrément de patch et garde sur `hotfix/*` (`hotfix.mjs:6-16`).
- **Problème** : duplication de la lecture de `VERSION`, du parsing semver et de l'appel `gh workflow run` (`hotfix.mjs:11-16` ≡ `release.mjs:7-8,23`) — CLI implicite non testée qui divergera ; passe `-f hotfix=true` que le workflow ignore (`release.yml:11-14` jamais référencé dans les steps). Même absence de dry-run et de pré-conditions que `release.mjs`. La garde de branche (`hotfix.mjs:7-10`) est la seule pré-condition codée de tout le harness : à conserver dans la CLI.
- **Doit devenir** : `release plan --type patch` avec, dans `release check`, la règle « `--type patch` exige une branche `hotfix/*` ».
- **Critère de vérification** : `scripts/hotfix.mjs` supprimé ; `release plan --type patch` depuis `develop` sort en erreur ; `SKILL.md` et `CLAUDE.md` ne le mentionnent plus.

### [SPLIT] [P2] Fichier d'instructions — `CLAUDE.md`
- **Fait aujourd'hui** : 111 lignes chargées à chaque session mêlant commandes, stack, architecture, conventions, style, tests, procédure de release et troubleshooting (`CLAUDE.md:5-111`).
- **Problème** : (a) l'exemple de référence contredit la règle qu'il illustre (`CLAUDE.md:51` vs `CLAUDE.md:74-75`) et sera copié tel quel — il l'a probablement déjà été (`InvoiceService.java:10-11`) ; (b) la procédure de release (`CLAUDE.md:95-101`) duplique `SKILL.md` et a déjà divergé (omet les étapes `SKILL.md:10,16`) ; (c) ≈ 45 % de référence (Build, Stack, Key files, Troubleshooting) chargée à chaque session, et des références à des fichiers inexistants (`CLAUDE.md:9,12,33-37,105,109`) ; (d) 11 règles obligatoires sans garde-fou (section 3), dont deux déjà violées dans le code ; (e) bruit : naming standard (`CLAUDE.md:66`), try-with-resources (`CLAUDE.md:60`) ; (f) aucune clause de maintenance, peu de *pourquoi*, aucun incident cité.
- **Doit devenir** : un CLAUDE.md ≤ 50 lignes : règles avec leur *pourquoi* et la mention du garde-fou (« vérifié par `ArchitectureTest` »), pointeur vers `.claude/skills/release/SKILL.md` pour la release (section 95-101 supprimée), exemple corrigé en injection par constructeur, clause de maintenance (« toute règle ajoutée l'est dans la PR qui a motivé le commentaire de review ; une règle avec garde-fou peut être raccourcie à une ligne »). Référence (commandes, troubleshooting, structure) déplacée dans `docs/dev.md` chargé à la demande. Règles obligatoires poussées en L3 (voir plan).
- **Critère de vérification** : `wc -l CLAUDE.md` ≤ 50 ; aucune commande ou chemin cité n'est absent du dépôt ; l'exemple compile contre le code réel ; la procédure de release n'existe qu'à un endroit.

### [KEEP] Workflow CI — `.github/workflows/ci.yml`
Bonne couche, bon périmètre : checkstyle + tests (dont ArchUnit) sur push `develop`/`main` et sur PR (`ci.yml:3-14`) ; c'est sur lui que `release.yml` doit s'appuyer plutôt que sur une lecture d'onglet. Hôte naturel des PR gates à ajouter (immutabilité Flyway).

### [KEEP] Checkstyle — `config/checkstyle/checkstyle.xml`
Garde-fou L3 sain et appelé par la CI (`ci.yml:13`) ; couvre 4 des règles de style de `CLAUDE.md`. À étendre (`FileTabCharacter`, `CustomImportOrder`, `TypeName`, `MemberName`, `IllegalImport`) pour absorber les règles racontées, sans changer de couche.

### [KEEP] Test d'architecture — `src/test/java/com/acme/billing/ArchitectureTest.java`
Modèle de ce que doit être une règle de CLAUDE.md : une ligne dans le fichier, un test ArchUnit qui la porte, et une Javadoc qui cite la règle d'origine (`ArchitectureTest.java:12-16`). Hôte naturel des règles « pas de `@Autowired` sur un champ » et « pas de `@MockBean` en test unitaire ».

### [KEEP] Build — `build.gradle`
Bonne couche ; une seule correction, rattachée au constat `release.yml` : `version = file('VERSION').text.trim()` (`build.gradle:9`) écrase le `-Pversion` passé par `release.yml:23`.

### [KEEP] Source de vérité de version — `VERSION`
Bonne idée (un seul fichier lu par Gradle et les scripts, `build.gradle:9`, `release.mjs:7`, `hotfix.mjs:11`) ; le défaut est que personne ne l'écrit — traité dans le constat `release.mjs`.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | `scripts/old-deploy.sh` | Supprimer le fichier (ou `exit 1` immédiat avec message pointant vers `release run`). | — | Fichier absent ; `grep -r old-deploy` vide. | Oui (suppression + accès prod) |
| 2 | P1 | PUSH_DOWN | `.github/workflows/release.yml` | Ajouter `dry_run`, job `plan` (valide `version` vs `VERSION`, `ref` autorisée, check-runs verts sur le SHA), job `deploy` sous `environment: production` avec reviewers, tag après healthcheck, `outputs`, `concurrency`, suppression ou usage de `hotfix`. Corriger `build.gradle:9` pour honorer `-Pversion`. | 1 | Dispatch `dry_run=true` sans effet ; dispatch sur `feat/*` refusé au job `plan` ; « Waiting for review » visible ; `gh run view --json jobs` expose `version`/`image`/`sha`. | Oui (création de l'environment GitHub + reviewers ; touche la prod) |
| 3 | P1 | SPLIT | `scripts/release.mjs` | Créer la CLI `release` (`check`, `plan --type`, `run --plan [--dry-run]`) avec tests, sortie JSON, bump + commit de `VERSION`, garde `hotfix/*` pour `--type patch` ; puis supprimer `release.mjs`. | 2 | Tests de la CLI verts dans `ci.yml` ; `release check` échoue sur arbre sale / CI rouge / tag existant ; `release run --dry-run` ne déclenche rien ; `release.mjs` absent. | Oui pour la suppression du script |
| 4 | P2 | MERGE | `scripts/hotfix.mjs` | Supprimer, remplacé par `release plan --type patch`. | 3 | Fichier absent ; `release plan --type patch` depuis `develop` sort en erreur. | Oui (suppression) |
| 5 | P1 | PUSH_DOWN | `.claude/skills/release/SKILL.md` | Réécrire : séquence `check` → `plan` → confirmation utilisateur sur le plan JSON → `run` → lecture `gh run view --json conclusion` → annonce ; retirer toute pré-condition manuelle et tout grep de log. | 3, 4 | Aucune occurrence de « onglet Actions », « dump », « SUCCESS » ; chaque commande citée existe. | Non |
| 6 | P2 | SPLIT | `CLAUDE.md` | Corriger l'exemple (constructeur), supprimer la section Release au profit d'un pointeur vers le skill, déplacer Build/Stack/Troubleshooting vers `docs/dev.md`, retirer les références à des fichiers inexistants, retirer le bruit (naming, try-with-resources), ajouter le *pourquoi* et une clause de maintenance. | 5 | ≤ 50 lignes ; exemple compilable ; aucun chemin cité absent ; une seule procédure de release dans le dépôt. | Non |
| 7 | P2 | PUSH_DOWN | `src/test/java/com/acme/billing/ArchitectureTest.java` | Ajouter `noFields().should().beAnnotatedWith(Autowired.class)` (règle `CLAUDE.md:51`) et corriger `InvoiceService.java:10-11` ; ajouter une règle interdisant `MockBean` dans les classes `*Test` (`CLAUDE.md:92`). | — | `gradlew test` rouge si un champ `@Autowired` est réintroduit ; `InvoiceService` en injection par constructeur. | Non |
| 8 | P2 | PUSH_DOWN | `.github/workflows/ci.yml` | Ajouter un test générique d'autorisation (toutes les routes → 403 avec un rôle inconnu, règle `CLAUDE.md:57`) exécuté par `gradlew test`, et un step PR gate « aucune migration Flyway modifiée/supprimée » (`CLAUDE.md:63`). | — | Un endpoint sans sécurité fait échouer la CI ; une PR qui modifie `V1__init.sql` est rouge. | Non |
| 9 | P3 | PUSH_DOWN | `config/checkstyle/checkstyle.xml` | Ajouter `FileTabCharacter`, `CustomImportOrder` (java/javax/org/com), `TypeName`, `MemberName`, `ParameterName` ; option : `IllegalImport` pour `MockBean` côté `checkstyleTest`. Raccourcir les règles correspondantes dans `CLAUDE.md` à une ligne « vérifié par Checkstyle ». | 6 | `gradlew checkstyleMain checkstyleTest` rouge sur une tabulation ou un import mal groupé. | Non |

## 6. Ce que l'audit n'a pas pu vérifier

- Les réglages GitHub hors dépôt : protection de branche `develop`/`main` (checks requis), existence d'un `environment` `production`, présence et portée des secrets `REGISTRY_PASSWORD` / `PROD_SSH_KEY` (`release.yml:25,30`). Si `develop` est protégé avec `ci` requis, l'étape 1 du processus est partiellement couverte au moment du merge, mais pas au moment de la release.
- Les scripts n'ont pas été exécutés (pas de `gh` authentifié, pas de `package.json`) ; l'analyse est statique.
- Fichiers référencés mais absents du dépôt : `gradlew` (appelé par `ci.yml:13-14`, `release.yml:23`), `Dockerfile` (`release.yml:24`, `old-deploy.sh:5`), fichier compose (`CLAUDE.md:12,105`), `gradle.properties` (`CLAUDE.md:109`), `InvoiceServiceTest` (`CLAUDE.md:9`), packages `customer`/`payment`/`config`/`security` (`CLAUDE.md:33-37`). Hypothèse retenue : simplification de fixture ; dans un vrai dépôt, les deux workflows échoueraient dès le premier step.
- `README.md:3` renvoie vers `../traps.md`, hors du périmètre audité : non ouvert, conformément à la consigne d'évaluation à l'aveugle.
- Le skill demande d'écrire le JSON dans `.harness/audit.json` du dépôt audité ; la consigne de ne modifier aucun fichier du repo prévaut, le JSON est livré à côté du rapport (`blind-audit.json`).
- L'existence de credentials locaux (docker login registry, clé SSH `deploy@prod.acme.io`) qui rendraient `scripts/old-deploy.sh` immédiatement opérant depuis un poste.

## 7. Données machine

```json
{
  "audit": {
    "process": "Release de billing-api (+ instrumentation IA du dépôt : CLAUDE.md)",
    "scope": "fixtures/repos/java-back/repo/ — CLAUDE.md, .claude/skills/release/, scripts/, .github/workflows/, config/checkstyle/, build.gradle, VERSION, src/test (ArchUnit)",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 5 }
  },
  "elements": [
    {
      "id": "release-mjs",
      "path": "scripts/release.mjs",
      "declared_layer": "L3",
      "actual_layer": "MIXED",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["version-file", "release-yml"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "Décide seul du type de version d'après le nom de branche (jugement L1 figé), déclenche le déploiement prod sans pré-condition ni dry-run, ne met jamais à jour VERSION, sortie non structurée, aucun test.",
      "evidence": ["scripts/release.mjs:11-16", "scripts/release.mjs:22-23", "scripts/release.mjs:7", "build.gradle:9", ".github/workflows/release.yml:27"],
      "target": "CLI testée `release check` / `release plan --type` (JSON, sans effet) / `release run --plan [--dry-run]` (bump+commit VERSION, déclenchement, URL de run) ; le type de version devient un argument choisi par l'agent.",
      "check": "`release check` sort en code non nul sur arbre sale, CI rouge ou tag existant ; `release run --dry-run` ne déclenche rien ; tests verts en CI ; release.mjs supprimé."
    },
    {
      "id": "old-deploy-sh",
      "path": "scripts/old-deploy.sh",
      "declared_layer": "L3",
      "actual_layer": "L4",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "Script mort mais exécutable qui build, pousse et déploie en prod par SSH depuis un poste, sans CI, sans tag, en dupliquant release.yml.",
      "evidence": ["scripts/old-deploy.sh:2", "scripts/old-deploy.sh:5-7", ".github/workflows/release.yml:24-31"],
      "target": "Supprimer le fichier (ou exit 1 immédiat pointant vers `release run`).",
      "check": "Fichier absent du dépôt ; `grep -r old-deploy` vide ; approbation du propriétaire obtenue."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["release-mjs", "hotfix-mjs"],
      "calls": ["build-gradle"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "workflow_dispatch sans environment protégé ni dry_run, ref libre déployable en prod sans vérification de CI ni tests, tag poussé avant le déploiement, -Pversion écrasé par build.gradle, input hotfix inutilisé, succès signalé par echo SUCCESS au lieu d'outputs.",
      "evidence": [".github/workflows/release.yml:3-14", ".github/workflows/release.yml:16-17", ".github/workflows/release.yml:20", ".github/workflows/release.yml:23", ".github/workflows/release.yml:27", ".github/workflows/release.yml:32", "build.gradle:9"],
      "target": "Job `plan` (validation version/ref/check-runs) puis job `deploy` sous `environment: production` avec reviewers, input dry_run, tag après healthcheck, outputs structurés, concurrency ; build.gradle honore -Pversion.",
      "check": "Dispatch dry_run=true sans effet ; dispatch sur feat/* refusé ; attente de review visible dans Actions ; `gh run view --json jobs` expose version/image/sha."
    },
    {
      "id": "release-skill",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["claude-md"],
      "calls": ["release-mjs", "hotfix-mjs", "release-yml", "ci-yml"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "Les trois pré-conditions obligatoires (CI verte, migrations Flyway, branche à jour) et la détection du succès (grep SUCCESS) sont racontées et non vérifiées ; l'étape Flyway dépend d'un dump humain.",
      "evidence": [".claude/skills/release/SKILL.md:9-11", ".claude/skills/release/SKILL.md:15-16"],
      "target": "Skill réduit à la séquence `release check` → `release plan` → confirmation utilisateur → `release run` → lecture `gh run view --json conclusion` → annonce ; les pré-conditions deviennent des codes de sortie à rapporter.",
      "check": "Plus aucune mention d'onglet Actions, de dump ou de chaîne SUCCESS ; chaque commande citée existe et est testée."
    },
    {
      "id": "hotfix-mjs",
      "path": "scripts/hotfix.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["version-file", "release-yml"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Duplique la lecture de VERSION, le parsing semver et l'appel gh workflow run de release.mjs ; passe un input hotfix que le workflow ignore ; seule la garde de branche hotfix/* est une vraie pré-condition codée.",
      "evidence": ["scripts/hotfix.mjs:11-16", "scripts/release.mjs:7-8", "scripts/release.mjs:23", ".github/workflows/release.yml:11-14", "scripts/hotfix.mjs:7-10"],
      "target": "Fusionner dans `release plan --type patch`, avec la règle « patch exige une branche hotfix/* » dans `release check`.",
      "check": "hotfix.mjs supprimé ; `release plan --type patch` depuis develop sort en erreur ; plus référencé par SKILL.md ni CLAUDE.md."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["release-skill", "release-mjs", "hotfix-mjs", "ci-yml", "release-yml", "checkstyle", "archunit-test"],
      "verdict": "SPLIT",
      "priority": "P2",
      "finding": "Exemple de code qui contredit sa propre règle (déjà copié dans InvoiceService), procédure de release dupliquée et divergente du skill, ~45 % de référence chargée à chaque session, références à des fichiers inexistants, 11 règles obligatoires sans garde-fou, pas de clause de maintenance.",
      "evidence": ["CLAUDE.md:51", "CLAUDE.md:74-75", "src/main/java/com/acme/billing/invoice/InvoiceService.java:10-11", "CLAUDE.md:95-101", "CLAUDE.md:9", "CLAUDE.md:33-37", "CLAUDE.md:109", "CLAUDE.md:57", "src/test/java/com/acme/billing/InvoiceControllerTest.java:8", "CLAUDE.md:63"],
      "target": "CLAUDE.md ≤ 50 lignes : règles + pourquoi + garde-fou cité, pointeur vers le skill release, exemple corrigé, clause de maintenance ; référence déplacée dans docs/dev.md ; règles obligatoires poussées en ArchUnit/Checkstyle/PR gate.",
      "check": "≤ 50 lignes ; exemple compilable ; aucun chemin cité absent ; une seule procédure de release dans le dépôt."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["build-gradle", "checkstyle", "archunit-test"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Checkstyle et tests (dont ArchUnit) sur push develop/main et sur PR : bonne couche, hôte naturel des PR gates à ajouter.",
      "evidence": [".github/workflows/ci.yml:3-5", ".github/workflows/ci.yml:13-14"],
      "target": "Conserver ; ajouter le test générique d'autorisation et le gate d'immutabilité Flyway (voir remediation).",
      "check": "Un endpoint non sécurisé ou une migration modifiée fait échouer la CI."
    },
    {
      "id": "checkstyle",
      "path": "config/checkstyle/checkstyle.xml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["build-gradle", "ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Garde-fou L3 sain appelé par la CI, couvrant 4 règles de style de CLAUDE.md ; à étendre pour absorber les règles racontées (tabulations, ordre des imports, TypeName/MemberName).",
      "evidence": ["config/checkstyle/checkstyle.xml:4-9", ".github/workflows/ci.yml:13"],
      "target": "Ajouter FileTabCharacter, CustomImportOrder, TypeName, MemberName, ParameterName, IllegalImport(MockBean).",
      "check": "`gradlew checkstyleMain checkstyleTest` rouge sur une tabulation ou un import mal groupé."
    },
    {
      "id": "archunit-test",
      "path": "src/test/java/com/acme/billing/ArchitectureTest.java",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Modèle du couple règle CLAUDE.md / garde-fou ArchUnit, avec la Javadoc qui cite la règle d'origine ; hôte des règles injection-par-constructeur et pas-de-MockBean.",
      "evidence": ["src/test/java/com/acme/billing/ArchitectureTest.java:12-16"],
      "target": "Ajouter noFields().should().beAnnotatedWith(Autowired.class) et une règle sur MockBean dans les classes *Test.",
      "check": "`gradlew test` rouge si un champ @Autowired est réintroduit."
    },
    {
      "id": "build-gradle",
      "path": "build.gradle",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "release-yml"],
      "calls": ["checkstyle", "version-file"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Bonne couche ; `version = file('VERSION')` écrase le -Pversion passé par release.yml, correction rattachée au constat release-yml.",
      "evidence": ["build.gradle:9", ".github/workflows/release.yml:23"],
      "target": "Honorer -Pversion quand il est fourni, sinon lire VERSION.",
      "check": "`gradlew bootJar -Pversion=9.9.9` produit un jar 9.9.9."
    },
    {
      "id": "version-file",
      "path": "VERSION",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-mjs", "hotfix-mjs", "build-gradle"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Source de vérité unique correcte, mais jamais écrite par le processus (traité dans release-mjs).",
      "evidence": ["VERSION:1", "scripts/release.mjs:7", "build.gradle:9"],
      "target": "Conserver ; `release run` le met à jour et le committe.",
      "check": "Après une release, VERSION contient la version taguée."
    }
  ],
  "process_leaks": [
    { "rule": "Ne jamais releaser sur un develop rouge (CI verte)", "told_in": ".claude/skills/release/SKILL.md:9", "if_skipped": "Image non testée déployée en prod ; l'agent peut lire le mauvais run ou halluciner un vert", "belongs_in": "L4", "guard_tool": "Step de garde dans release.yml (check-runs du SHA) + `release check` (exit 1)" },
    { "rule": "Aucune migration Flyway en attente en prod", "told_in": ".claude/skills/release/SKILL.md:10", "if_skipped": "Schéma non validé déployé ; étape non reproductible sans dump humain", "belongs_in": "L3", "guard_tool": "`release check --migrations` ou test Testcontainers flyway.validate() en CI" },
    { "rule": "Être sur develop à jour, arbre propre", "told_in": ".claude/skills/release/SKILL.md:11", "if_skipped": "Commits locaux non poussés exclus silencieusement (ref=branche envoyée au workflow)", "belongs_in": "L3", "guard_tool": "`release check` : git status --porcelain vide, HEAD == origin/develop, tag inexistant" },
    { "rule": "Mettre à jour VERSION après release", "told_in": "scripts/release.mjs:7 (lu, jamais écrit — l'étape n'est racontée nulle part)", "if_skipped": "La release suivante recalcule la même version ; git tag échoue après le push de l'image", "belongs_in": "L3", "guard_tool": "`release run` bump + commit + push de VERSION" },
    { "rule": "Le succès se lit dans la chaîne SUCCESS du log", "told_in": ".claude/skills/release/SKILL.md:15", "if_skipped": "Succès halluciné ; aucun retour structuré pour décider", "belongs_in": "L4", "guard_tool": "outputs du job release.yml + `gh run view --json conclusion`" },
    { "rule": "Si ERROR/FAILED, prévenir et ne pas relancer", "told_in": ".claude/skills/release/SKILL.md:16", "if_skipped": "Relance en boucle d'un deploy prod", "belongs_in": "L4", "guard_tool": "`concurrency:` dans release.yml + refus de `release run` si un run est en cours ou a échoué sur la même version" },
    { "rule": "Injection par constructeur, jamais @Autowired sur un champ", "told_in": "CLAUDE.md:51", "if_skipped": "Déjà violée (InvoiceService.java:10-11) et par l'exemple CLAUDE.md:74-75", "belongs_in": "L3", "guard_tool": "ArchUnit noFields().should().beAnnotatedWith(Autowired.class) dans ArchitectureTest.java" },
    { "rule": "Chaque endpoint a un test d'autorisation (403 avec le mauvais rôle)", "told_in": "CLAUDE.md:57", "if_skipped": "Aucun test 403 n'existe (InvoiceControllerTest.java:8) ; API de facturation sans contrôle d'accès testé", "belongs_in": "L3", "guard_tool": "Test JUnit générique sur RequestMappingHandlerMapping exécuté par ci.yml" },
    { "rule": "Ne jamais modifier une migration Flyway appliquée", "told_in": "CLAUDE.md:63", "if_skipped": "FlywayValidateException découverte au déploiement prod", "belongs_in": "L3", "guard_tool": "Step PR gate dans ci.yml : git diff --diff-filter=MD sur db/migration vide" },
    { "rule": "Pas de @MockBean dans les tests unitaires", "told_in": "CLAUDE.md:92", "if_skipped": "Suite lente, contexte Spring démarré", "belongs_in": "L3", "guard_tool": "Checkstyle IllegalImport (checkstyleTest) ou règle ArchUnit sur *Test" },
    { "rule": "4 espaces, pas de tabulation", "told_in": "CLAUDE.md:84", "if_skipped": "Diff bruité", "belongs_in": "L3", "guard_tool": "Checkstyle FileTabCharacter" },
    { "rule": "Imports groupés java / javax / org / com", "told_in": "CLAUDE.md:85", "if_skipped": "Diff bruité", "belongs_in": "L3", "guard_tool": "Checkstyle CustomImportOrder" },
    { "rule": "Classes PascalCase, champs camelCase", "told_in": "CLAUDE.md:66", "if_skipped": "Incohérence de nommage", "belongs_in": "L3", "guard_tool": "Checkstyle TypeName, MemberName, ParameterName" },
    { "rule": "Tests nommés <Class>Test / <Class>IT", "told_in": "CLAUDE.md:67", "if_skipped": "Hygiène", "belongs_in": "L3", "guard_tool": "ArchUnit sur src/test (P3)" },
    { "rule": "DTOs en record", "told_in": "CLAUDE.md:87", "if_skipped": "Hygiène", "belongs_in": "L3", "guard_tool": "ArchUnit classes().that().resideInAPackage(\"..dto..\").should().beRecords() (P3)" }
  ],
  "guarded_rules": [
    { "rule": "Un contrôleur ne touche pas un repository / pas de logique métier dans les contrôleurs", "told_in": "CLAUDE.md:54", "guarded_by": "src/test/java/com/acme/billing/ArchitectureTest.java:14-16" },
    { "rule": "Longueur de ligne max 120", "told_in": "CLAUDE.md:84", "guarded_by": "config/checkstyle/checkstyle.xml:4" },
    { "rule": "Pas d'import wildcard", "told_in": "CLAUDE.md:85", "guarded_by": "config/checkstyle/checkstyle.xml:6" },
    { "rule": "Une classe publique par fichier", "told_in": "CLAUDE.md:68", "guarded_by": "config/checkstyle/checkstyle.xml:7" },
    { "rule": "Constantes UPPER_SNAKE_CASE, méthodes camelCase", "told_in": "CLAUDE.md:66", "guarded_by": "config/checkstyle/checkstyle.xml:8-9" },
    { "rule": "Suite complète avant d'ouvrir une PR", "told_in": "CLAUDE.md:93", "guarded_by": ".github/workflows/ci.yml:5,14" },
    { "rule": "Checkstyle sur chaque push", "told_in": "CLAUDE.md:45", "guarded_by": ".github/workflows/ci.yml:13" },
    { "rule": "Un hotfix part d'une branche hotfix/*", "told_in": ".claude/skills/release/SKILL.md:19", "guarded_by": "scripts/hotfix.mjs:7-10" }
  ],
  "instruction_files": [
    { "path": "CLAUDE.md", "loaded_lines": 111, "instruction_pct": 40, "reference_pct": 45, "noise_pct": 15, "justified_rules": false, "maintenance_clause": false },
    { "path": ".claude/skills/release/SKILL.md", "loaded_lines": 22, "instruction_pct": 90, "reference_pct": 10, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "old-deploy-sh", "action": "Supprimer scripts/old-deploy.sh (ou exit 1 immédiat pointant vers `release run`).", "depends_on": [], "check": "Fichier absent ; `grep -r old-deploy` vide.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "PUSH_DOWN", "element": "release-yml", "action": "Ajouter dry_run, job plan (version vs VERSION, ref autorisée, check-runs verts), job deploy sous environment: production avec reviewers, tag après healthcheck, outputs, concurrency, retrait/usage de l'input hotfix ; corriger build.gradle:9 pour honorer -Pversion.", "depends_on": ["old-deploy-sh"], "check": "Dispatch dry_run=true sans effet ; dispatch sur feat/* refusé ; attente de review visible ; `gh run view --json jobs` expose version/image/sha.", "needs_human_approval": true },
    { "order": 3, "priority": "P1", "verdict": "SPLIT", "element": "release-mjs", "action": "Créer la CLI release (check, plan --type, run --plan [--dry-run]) avec tests, JSON, bump+commit VERSION, garde hotfix/* pour --type patch ; puis supprimer scripts/release.mjs.", "depends_on": ["release-yml"], "check": "Tests CLI verts en CI ; `release check` échoue sur arbre sale/CI rouge/tag existant ; `release run --dry-run` ne déclenche rien ; release.mjs absent.", "needs_human_approval": true },
    { "order": 4, "priority": "P2", "verdict": "MERGE", "element": "hotfix-mjs", "action": "Supprimer scripts/hotfix.mjs, remplacé par `release plan --type patch`.", "depends_on": ["release-mjs"], "check": "Fichier absent ; `release plan --type patch` depuis develop sort en erreur.", "needs_human_approval": true },
    { "order": 5, "priority": "P1", "verdict": "PUSH_DOWN", "element": "release-skill", "action": "Réécrire SKILL.md : check → plan → confirmation utilisateur sur le plan JSON → run → `gh run view --json conclusion` → annonce ; retirer toute pré-condition manuelle et tout grep de log.", "depends_on": ["release-mjs", "hotfix-mjs"], "check": "Aucune occurrence de « onglet Actions », « dump », « SUCCESS » ; chaque commande citée existe.", "needs_human_approval": false },
    { "order": 6, "priority": "P2", "verdict": "SPLIT", "element": "claude-md", "action": "Corriger l'exemple (constructeur), remplacer la section Release par un pointeur vers le skill, déplacer Build/Stack/Troubleshooting vers docs/dev.md, retirer les références à des fichiers inexistants et le bruit, ajouter le pourquoi et une clause de maintenance.", "depends_on": ["release-skill"], "check": "≤ 50 lignes ; exemple compilable ; aucun chemin cité absent ; une seule procédure de release.", "needs_human_approval": false },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "archunit-test", "action": "Ajouter noFields().should().beAnnotatedWith(Autowired.class) et une règle interdisant MockBean dans les classes *Test ; corriger InvoiceService.java:10-11.", "depends_on": [], "check": "`gradlew test` rouge si un champ @Autowired est réintroduit ; InvoiceService en injection par constructeur.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "PUSH_DOWN", "element": "ci-yml", "action": "Ajouter un test générique d'autorisation (toutes les routes → 403 avec un rôle inconnu) et un step PR gate « aucune migration Flyway modifiée/supprimée ».", "depends_on": [], "check": "Un endpoint sans sécurité fait échouer la CI ; une PR modifiant V1__init.sql est rouge.", "needs_human_approval": false },
    { "order": 9, "priority": "P3", "verdict": "PUSH_DOWN", "element": "checkstyle", "action": "Ajouter FileTabCharacter, CustomImportOrder, TypeName, MemberName, ParameterName, IllegalImport(MockBean) ; raccourcir les règles correspondantes de CLAUDE.md à « vérifié par Checkstyle ».", "depends_on": ["claude-md"], "check": "`gradlew checkstyleMain checkstyleTest` rouge sur une tabulation ou un import mal groupé.", "needs_human_approval": false }
  ],
  "unverified": [
    "Réglages GitHub hors dépôt : protection de branche develop/main, existence d'un environment production, présence des secrets REGISTRY_PASSWORD et PROD_SSH_KEY (release.yml:25,30).",
    "Scripts non exécutés (pas de gh authentifié, pas de package.json) : analyse statique uniquement.",
    "Fichiers référencés mais absents : gradlew (ci.yml:13-14, release.yml:23), Dockerfile (release.yml:24, old-deploy.sh:5), fichier compose (CLAUDE.md:12,105), gradle.properties (CLAUDE.md:109), InvoiceServiceTest (CLAUDE.md:9), packages customer/payment/config/security (CLAUDE.md:33-37) ; hypothèse : simplification de fixture.",
    "README.md:3 renvoie vers ../traps.md, hors périmètre : non ouvert (évaluation à l'aveugle).",
    ".harness/audit.json non écrit dans le dépôt audité (consigne de ne rien modifier) ; JSON livré dans blind-audit.json à côté du rapport.",
    "Existence de credentials locaux (docker login registry, clé SSH deploy@prod.acme.io) rendant scripts/old-deploy.sh immédiatement opérant."
  ]
}
```
