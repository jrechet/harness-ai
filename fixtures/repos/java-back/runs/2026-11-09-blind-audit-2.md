# Audit du harness — Release / déploiement production de billing-api + instrumentation IA (CLAUDE.md, skill release)

**Périmètre** : `fixtures/repos/java-back/repo` — `CLAUDE.md`, `.claude/skills/release/`, `scripts/`, `.github/workflows/`, `config/checkstyle/`, `build.gradle`, `src/test` (ArchUnit) · **Date** : 2026-11-09 · **Éléments inventoriés** : 10

## 1. Synthèse

- **Score de santé** : 0 — l'agent n'est pas un accélérateur mais le seul porteur des pré-conditions de release et du point d'arrêt avant la prod : 4 P1 (−100) et 2 P2 (−16) ramènent le score à 0, et le test « coupe l'agent » est en échec (plafond 60 de toute façon).
- **Résultat du test « coupe l'agent »** : ÉCHEC — 4 étape(s) du processus n'existent que dans des prompts (CI develop verte, migrations Flyway alignées avec la prod, develop à jour, lecture structurée du succès). Un cinquième manque partout : il n'y a aucun point d'arrêt humain entre le plan et le déploiement prod.
- **Points bloquants (P1)** : 4 — `SKILL.md` (pré-conditions racontées), `scripts/release.mjs` (jugement codé en dur + déclenchement prod sans dry-run, VERSION jamais incrémenté), `.github/workflows/release.yml` (dispatch prod sans `environment` protégé ni `dry_run`), `scripts/old-deploy.sh` (chemin mort mais exécutable vers la prod).
- **Les trois actions qui changent le plus les choses** :
  1. Protéger `release.yml` : séparer `publish` et `deploy-prod`, mettre `deploy-prod` sous `environment: production` à reviewers obligatoires, ajouter `dry_run`, valider la version et le tag, poser une `concurrency` — c'est le seul garde-fou qui tient quel que soit l'appelant (agent, humain, cron).
  2. Remplacer `release.mjs` + `hotfix.mjs` par une CLI testée `release plan` / `release run` : pré-conditions en `exit 1` (CI verte, arbre propre et à jour, tag inexistant), type de version choisi par l'humain/agent (`--type`), plan JSON sans exécution, bump et commit de `VERSION`, URL du run et conclusion en retour. Puis réécrire le skill comme procédure pure autour de ces deux commandes.
  3. Pousser les règles obligatoires de `CLAUDE.md` dans des garde-fous (ArchUnit « pas d'injection par champ », test d'autorisation générique par endpoint, gate CI « migrations immuables »), corriger l'exemple qui contredit sa propre règle, dédoublonner la section Release et supprimer `old-deploy.sh`.

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | Fichier d'instructions repo | `CLAUDE.md` | L2 | MIXED (L2 + procédure release dupliquée + 45 % de référence) | Chargé automatiquement par Claude Code (aucun appelant explicite) | skill release, `release.mjs`, `hotfix.mjs`, `ci.yml`, `release.yml`, Checkstyle, ArchUnit |
| 2 | Skill release | `.claude/skills/release/SKILL.md` | L2 | MIXED (L2 + pré-conditions L3 racontées + lecture de logs) | `CLAUDE.md:46`, déclenchement par mot-clé (`SKILL.md:3`) | `release.mjs`, `hotfix.mjs`, `release.yml` (via `gh run watch`), `ci.yml` (lecture onglet Actions) |
| 3 | Script de release | `scripts/release.mjs` | L3 | MIXED (L1 jugement codé + L3 calcul + déclenchement L4) | `SKILL.md:14`, `CLAUDE.md:97` | `release.yml` (`gh workflow run`), lit `VERSION` |
| 4 | Script de hotfix | `scripts/hotfix.mjs` | L3 | L3 (+ déclenchement L4) | `SKILL.md:19`, `CLAUDE.md:101` | `release.yml`, lit `VERSION` |
| 5 | Ancien déploiement manuel | `scripts/old-deploy.sh` | L3 | L4 (build + push + ssh prod en direct) | Personne (`old-deploy.sh:2`) | registry et `prod.acme.io` directement |
| 6 | Workflow release | `.github/workflows/release.yml` | L4 | L4 | `release.mjs:23`, `hotfix.mjs:16` (`workflow_dispatch`) | Gradle, Docker, registry, SSH prod |
| 7 | Workflow CI | `.github/workflows/ci.yml` | L4 | L4 | Événements push develop/main et PR | Checkstyle, tests (dont ArchUnit) |
| 8 | Checkstyle | `config/checkstyle/checkstyle.xml` | L3 | L3 | `ci.yml:13`, `build.gradle:24` | — |
| 9 | ArchUnit | `src/test/java/com/acme/billing/ArchitectureTest.java` | L3 | L3 | `ci.yml:14` | — |
| 10 | Build Gradle + VERSION | `build.gradle` (+ `VERSION`) | L3 | L3 | `ci.yml`, `release.yml:23`, `release.mjs:7`, `hotfix.mjs:11` | Checkstyle |

Aucun agent, sous-agent, hook, `.claude/settings.json`, `.cursor/rules` ni `@include` n'a été trouvé.

Processus nominal (release depuis `develop`) :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| 1. S'assurer que la CI de `develop` est verte | L2 — `SKILL.md:9`, `CLAUDE.md:96` (regarder l'onglet Actions) | Non — `release.mjs` ne lit pas le statut, `release.yml` ne relance pas les tests | n/a |
| 2. Vérifier les migrations Flyway vs `flyway_schema_history` de prod | L2 — `SKILL.md:10` (demander un dump au propriétaire) | Non — détection seulement au démarrage prod (`FlywayValidateException`, `CLAUDE.md:104`) | n/a |
| 3. Être sur `develop` à jour | L2 — `SKILL.md:11` | Partiel — `release.mjs:11` vérifie le nom de branche, pas la synchro avec origin ni la propreté de l'arbre | n/a |
| 4. Choisir le type de version (majeure / mineure / patch) | L3 — `release.mjs:11-16` (déduit du préfixe de branche) | Oui mais mauvaise couche : jugement L1 figé ; patch depuis develop impossible, majeure = déployer une branche `feat/breaking-*` en prod | Non |
| 5. Calculer la prochaine version | L3 — `release.mjs:7-8`, `hotfix.mjs:11-13` | Oui (non testé) ; `VERSION` jamais incrémenté → la release suivante recalcule la même version | Non |
| 6. Déclencher `release.yml` | L3 → L4 — `release.mjs:23`, `hotfix.mjs:16` | Oui ; aucune confirmation, aucun `--dry-run` | Non |
| 7. Build, image, push, tag, deploy prod | L4 — `release.yml:23-31` | Oui ; pas d'`environment` protégé, pas de validation de `version`/`ref`, pas de `concurrency`, input `hotfix` ignoré | Non (pas d'input `dry_run`) |
| 8. Constater le succès | L2 — `SKILL.md:15`, `CLAUDE.md:98` (grep `SUCCESS` dans les logs) | Non — `SUCCESS` est un `echo` (`release.yml:32`), `gh workflow run` ne retourne pas d'id de run | n/a |
| 9. En cas d'échec : prévenir, ne pas relancer | L1/L2 — `SKILL.md:16` | Jugement : à sa place ; mais aucun rollback n'existe en L4 | n/a |
| 10. Annoncer dans #releases avec la liste des PRs | L1 — `SKILL.md:22`, `CLAUDE.md:99` | Non (choix ouvert, acceptable) ; la liste des PRs pourrait être produite par L4 (`gh release create --generate-notes`) | n/a |
| Hotfix : même chaîne depuis `hotfix/*` avec patch | L2 → L3 — `SKILL.md:19`, `hotfix.mjs:7-16` | Branche vérifiée (`hotfix.mjs:7`) ; `hotfix=true` jamais lu par `release.yml` | Non |

## 3. Fuites : règles et étapes racontées sans vérification

Processus de release :

1. **CI de `develop` verte avant release** — racontée `SKILL.md:9`, `CLAUDE.md:96`. Si sautée : une image bâtie sur un develop rouge part en prod, `release.yml` ne relance ni tests ni Checkstyle. Doit vivre en **L3** : sous-commande `release plan` lisant `gh run list --workflow ci.yml --branch develop --json conclusion` (exit 1 sinon), doublée en **L4** par un step `./gradlew test` dans le job `publish`.
2. **Aucune migration Flyway non appliquée en prod** — racontée `SKILL.md:10` (avec demande d'un dump prod au propriétaire). Si sautée : échec Flyway au démarrage du conteneur, découvert après `docker compose up -d`. Doit vivre en **L4** : step `flyway info` / `flyway validate` contre la base prod dans `deploy-prod`, avant le `docker pull`.
3. **`develop` à jour et arbre propre** — racontée `SKILL.md:11`. Si sautée : `release.mjs` déclenche avec un `ref` et un `VERSION` locaux qui ne correspondent pas à ce qui sera construit. Doit vivre en **L3** : `release plan` fait `git fetch` et sort en exit 1 si behind/ahead ou arbre sale.
4. **Succès = `SUCCESS` dans les logs, échec = `ERROR`/`FAILED`** — racontée `SKILL.md:15-16`, `CLAUDE.md:98`. Si sautée ou mal lue : succès halluciné ; un run à moitié échoué (image poussée, tag refusé) est indiscernable. Doit vivre en **L3/L4** : `release run` retourne l'URL du run et lit `gh run view --json conclusion,jobs` ; `release.yml` expose des outputs.
5. **Point d'arrêt humain avant la prod** — absent : `SKILL.md:14` enchaîne directement sur `node scripts/release.mjs`, qui déclenche sans confirmation (`release.mjs:23`), et `release.yml:16-31` n'a ni `environment` protégé ni `dry_run`. Doit vivre en **L4** (`environment: production` à reviewers) et en **L3** (`plan --dry-run` par défaut, `run` exigeant un plan).

Règles de `CLAUDE.md` (mode « si on supprime le fichier, que laisse passer la CI ? ») :

6. **Injection par constructeur, jamais par champ** — `CLAUDE.md:51`. La CI laisse passer `InvoiceService.java:10-11` (`@Autowired` sur champ) et l'exemple de `CLAUDE.md:74-75` le recommande. → **L3**, règle ArchUnit `noFields().should().beAnnotatedWith(Autowired.class)` dans `ArchitectureTest.java`.
7. **Chaque endpoint a un test d'autorisation (mauvais rôle → 403)** — `CLAUDE.md:57`. `InvoiceControllerTest.java:8` constate qu'aucun n'existe ; aucune configuration Spring Security dans `src/`. Conséquence sécurité. → **L3**, test paramétré sur `RequestMappingHandlerMapping` avec `@WithMockUser(roles="NONE")` attendu 401/403.
8. **Ne jamais modifier une migration appliquée** — `CLAUDE.md:63`. Garde-fou uniquement au démarrage prod (`CLAUDE.md:104`), trop tard. → **L3**, step CI diffant `src/main/resources/db/migration/V*` contre la branche cible (exit 1 sur M/D) ou test Testcontainers `migrate` + `validate`.

Règles d'hygiène racontées, P3 au plus (bruit ou pointeur vers l'outil) : try-with-resources (`CLAUDE.md:60`, un modèle récent le fait déjà → INLINE), commentaires `given / when / then` (`CLAUDE.md:91`), `Optional` / `record` (`CLAUDE.md:86-87`), pas de `@MockBean` en test unitaire (`CLAUDE.md:92`, règle ArchUnit possible sur `src/test`), groupement des imports java/javax/org/com (`CLAUDE.md:85`, module Checkstyle `CustomImportOrder`), nommage des classes/champs (`CLAUDE.md:66`, modules `TypeName`/`MemberName`).

Règles qui **ont** leur garde-fou (partie saine) :

- Pas de logique métier ni d'accès repository dans les contrôleurs (`CLAUDE.md:27`, `CLAUDE.md:54`) → `ArchitectureTest.java:14-16`, avec une javadoc qui cite la règle (`ArchitectureTest.java:12`).
- Longueur de ligne 120 (`CLAUDE.md:84`) → `checkstyle.xml:4`.
- Pas d'import wildcard (`CLAUDE.md:85`) → `checkstyle.xml:6`.
- Une classe publique par fichier (`CLAUDE.md:68`) → `checkstyle.xml:7`.
- Constantes UPPER_SNAKE_CASE / méthodes camelCase (`CLAUDE.md:66`) → `checkstyle.xml:8-9` (partiel).
- Suite complète et Checkstyle avant PR / à chaque push (`CLAUDE.md:93`, `CLAUDE.md:45`) → `ci.yml:5`, `ci.yml:13-14`.
- Un hotfix part de `hotfix/*` (`SKILL.md:19`) → `hotfix.mjs:7-9` (exit 1).
- Une release part de `develop`, `release/*` ou `feat/breaking-*` (`CLAUDE.md:97`) → `release.mjs:17-19` (exit 1) — le périmètre autorisé est lui-même discutable.

## 3b. Coût de contexte (si des fichiers d'instructions sont dans le périmètre)

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| `CLAUDE.md` | 111 (aucun include) | 29 % / 45 % / 26 % — référence : Build (5-14), Stack (15-20), Packages (31-39), Key files (40-47), Release process (95-102, doublon du skill), Troubleshooting (103-111) ; bruit : exemple erroné (70-82), nommage standard (65-68), try-with-resources (59-61), en-tête (1-4) | À chaque session Claude Code |
| `.claude/skills/release/SKILL.md` | 22 | 100 % procédure (dont 3 pré-conditions qui devraient être du code) | À la demande, sur mots-clés release / mise en prod / déploiement / hotfix (`SKILL.md:3`) |

Justification : trois règles disent *pourquoi* (`CLAUDE.md:51` « hides dependencies and breaks unit tests », `CLAUDE.md:92` « it starts the context », `CLAUDE.md:106` « do not disable the rule »), aucune ne cite d'incident ; les autres sont de simples MUST. Aucune clause de maintenance (comment une règle entre ou sort du fichier) dans `CLAUDE.md` ni dans `SKILL.md` ; aucune description du processus de travail (quand s'arrêter et demander, critère de « fini », test flaky). Incohérences internes : l'exemple « well-formed service » (`CLAUDE.md:70-81`) viole la règle `CLAUDE.md:51` ; `CLAUDE.md:97` dit que la version est « picked from the branch name » alors que `release.mjs:7-16` la calcule depuis `VERSION` ; `CLAUDE.md:9` cite `InvoiceServiceTest` (inexistant), `CLAUDE.md:12` un `docker compose` sans fichier compose, `CLAUDE.md:33-37` quatre packages absents de `src/`, `CLAUDE.md:42` un dossier `dto/` absent (le DTO est un record imbriqué, `InvoiceController.java:19`).

## 4. Constats par élément

### [PUSH_DOWN] [P1] Skill release — `.claude/skills/release/SKILL.md`
- **Fait aujourd'hui** : raconte la séquence de release : trois pré-conditions manuelles (regarder l'onglet Actions, comparer les migrations avec un dump prod, `git checkout develop && git pull`), puis `node scripts/release.mjs`, `gh run watch`, grep de `SUCCESS` / `ERROR` / `FAILED`, variante hotfix, annonce #releases.
- **Problème** : les pré-conditions obligatoires ne sont que racontées (preuve : `SKILL.md:9`, `SKILL.md:10`, `SKILL.md:11`) — l'agent peut les sauter ou les croire satisfaites ; le déclenchement du déploiement prod suit immédiatement sans point d'arrêt humain ni dry-run (`SKILL.md:14`) ; le succès est lu dans un log non structuré (`SKILL.md:15-16`), et `gh run watch` sans id de run suppose un choix interactif que `release.mjs:24` ne fournit pas ; l'étape 2 fait demander un dump de base de production dans un prompt (`SKILL.md:10`).
- **Doit devenir** : un skill L2 pur — vocabulaire, séquence `release plan --type …` → présentation du plan JSON à l'humain et attente de son accord → `release run` → lecture de `conclusion` et de l'URL du run ; cas d'abandon conservés (échec = prévenir, ne pas relancer ; plan refusé = s'arrêter) ; annonce #releases alimentée par les notes de release générées.
- **Critère de vérification** : plus aucune vérification manuelle, lecture d'onglet ou grep de log dans le fichier ; une étape de confirmation explicite précède `release run` ; chaque étape pointe vers une sous-commande ou un workflow existant.

### [SPLIT] [P1] Script de release — `scripts/release.mjs`
- **Fait aujourd'hui** : lit la branche courante et `VERSION`, déduit le type de version du préfixe de branche, affiche une ligne et lance `gh workflow run release.yml -f version=… -f ref=…`.
- **Problème** : jugement L1 codé en dur — « une release depuis develop est toujours mineure », « le préfixe de branche décide d'une majeure » (preuve : `release.mjs:11-16`) — ce qui interdit un patch depuis `develop` et fait d'une branche `feat/breaking-*` un `ref` déployé tel quel en prod ; aucune pré-condition vérifiée (CI, synchro origin, arbre propre, tag existant, `gh auth`) ; aucun `--dry-run` ni confirmation avant l'action L4 irréversible (`release.mjs:23`) ; retour en texte libre sans id ni URL de run (`release.mjs:22-24`) ; `VERSION` n'est jamais incrémenté ni committé (`release.mjs:7`, `VERSION:1`), donc la release suivante recalcule `1.5.0`, l'image est réécrite puis `git push origin v1.5.0` échoue (`release.yml:27`) ; aucun test.
- **Doit devenir** : une CLI testée en deux sous-commandes — `release plan --type major|minor|patch [--dry-run]` (pré-conditions en exit 1, calcul de version, plan JSON) et `release run --plan <fichier>` (bump + commit `VERSION`, déclenchement, retour JSON avec URL du run et conclusion) ; le type de version est un choix de l'humain/agent, le script n'expose que les options.
- **Critère de vérification** : `release plan --dry-run` ne déclenche rien et sort en exit ≠ 0 sur develop rouge, en retard ou sale ; `release run` refuse sans plan ; tests unitaires du calcul de version et des pré-conditions verts en CI ; `scripts/release.mjs` supprimé.

### [SPLIT] [P1] Workflow release — `.github/workflows/release.yml`
- **Fait aujourd'hui** : sur `workflow_dispatch(version, ref, hotfix)`, un seul job construit le jar, l'image, la pousse, tague et déploie en prod par SSH, puis `echo "SUCCESS"`.
- **Problème** : déploiement prod sans `environment` protégé ni reviewers et sans input `dry_run` (preuve : `release.yml:3-16`, `release.yml:28-31`) — fuite L4 indépendante de l'agent ; `ref` libre, n'importe quel commit ou branche peut partir en prod (`release.yml:8-10`, `release.yml:20`) ; `version` non validée (format, tag déjà existant) et tag poussé *après* l'image (`release.yml:26-27`) ; pas de tests ni de lecture du statut CI avant build ; pas de `concurrency`, pas de `permissions:` explicite pour le push du tag ; input `hotfix` déclaré mais jamais lu (`release.yml:11-14`) ; signal de succès = `echo` (`release.yml:32`) ; `-Pversion` écrasé par `build.gradle:9` qui relit `VERSION` (`release.yml:23`) → jar et image ne portent pas la même version ; aucun rollback.
- **Doit devenir** : job `publish` (validation regex `x.y.z` + `git ls-remote --tags` vide, `./gradlew test`, bootJar, image, tag, `gh release create --generate-notes`) puis job `deploy-prod` sous `environment: production` à approbation obligatoire ; input `dry_run` qui s'arrête après le plan ; `concurrency: release-prod` ; `permissions: contents: write` ; outputs structurés (version, image, URL) ; suppression du `echo SUCCESS` et de l'input `hotfix` inutilisé ; `VERSION` committé en amont par la CLI plutôt que `-Pversion`.
- **Critère de vérification** : dispatch `dry_run=true` → aucun push registry, aucun SSH ; dispatch réel → `deploy-prod` en attente d'approbation ; `version=abc` ou tag existant → échec avant le build ; `ls build/libs` dans le job montre la version taguée.

### [BLOCK] [P1] Ancien déploiement manuel — `scripts/old-deploy.sh`
- **Fait aujourd'hui** : `docker build`, `docker push` et `ssh deploy@prod.acme.io "docker pull … && docker compose up -d"` depuis le poste de l'appelant, pour n'importe quelle chaîne passée en `$1`.
- **Problème** : script mort de l'aveu du fichier (preuve : `old-deploy.sh:2`) mais toujours exécutable : il déploie en prod sans tests, sans tag, sans pipeline, avec les identifiants locaux (`old-deploy.sh:5-7`) ; aucun hook ni `settings.json` n'interdit à un agent de le lancer, par exemple quand `release.yml` échoue à l'étape SSH (`CLAUDE.md:108`).
- **Doit devenir** : supprimé ; le job `deploy-prod` de `release.yml` est l'unique chemin vers `prod.acme.io`.
- **Critère de vérification** : fichier absent ; `grep -r prod.acme.io` ne renvoie que `release.yml`. Suppression soumise à approbation humaine.

### [MERGE] [P2] Script de hotfix — `scripts/hotfix.mjs`
- **Fait aujourd'hui** : vérifie `hotfix/*`, lit `VERSION`, incrémente le patch, lance `gh workflow run release.yml … -f hotfix=true`.
- **Problème** : duplique `release.mjs` à la variation près (preuve : `hotfix.mjs:11-13`, `hotfix.mjs:16` vs `release.mjs:7-8`, `release.mjs:23`) — CLI implicite en deux exemplaires non testés ; `hotfix=true` n'est lu nulle part dans le workflow (`release.yml:11-14` seulement), un hotfix est donc identique à une release ; mêmes absences de dry-run, de confirmation et de bump de `VERSION` ; aucune vérification que la branche part du tag de prod.
- **Doit devenir** : `release plan --type patch`, avec pré-condition « branche `hotfix/*` ou `release/*` » dans la CLI.
- **Critère de vérification** : `scripts/hotfix.mjs` supprimé ; `SKILL.md` ne le cite plus ; `release plan --type patch` hors `hotfix/*` sort en exit ≠ 0.

### [SPLIT] [P2] Fichier d'instructions repo — `CLAUDE.md`
- **Fait aujourd'hui** : 111 lignes chargées à chaque session : commandes, stack, architecture, conventions, exemple, style, tests, processus de release, troubleshooting.
- **Problème** : l'exemple de « service bien formé » utilise l'injection par champ interdite trois sections plus haut (preuve : `CLAUDE.md:51` vs `CLAUDE.md:74-75`) et le code réel la reproduit (`InvoiceService.java:10-11`) — une erreur d'exemple est copiée fidèlement ; la section Release (`CLAUDE.md:95-101`) duplique `SKILL.md` avec la même lecture de `SUCCESS` (`CLAUDE.md:98`) et une description inexacte du calcul de version (`CLAUDE.md:97`) ; 45 % de référence et 26 % de bruit pour 29 % d'instruction ; références mortes (`CLAUDE.md:9`, `CLAUDE.md:12`, `CLAUDE.md:33-37`, `CLAUDE.md:42`) ; deux règles obligatoires sans garde-fou (`CLAUDE.md:57`, `CLAUDE.md:63`) ; aucune clause de maintenance ni processus de travail.
- **Doit devenir** : ≈40 lignes — règles avec leur pourquoi et le garde-fou qui les porte, processus de travail (quand s'arrêter et demander, critère de fini, test flaky), une ligne vers `.claude/skills/release/SKILL.md` ; référence (Build, Stack, Troubleshooting, Packages) déportée dans `docs/dev.md` chargé à la demande ; exemple corrigé ; clause « une règle née d'un commentaire de review entre dans ce fichier dans la même PR ; une règle sans violation depuis six mois en sort ».
- **Critère de vérification** : l'exemple compile la règle qu'il illustre ; chaque commande et chemin cité existe dans le dépôt ; section Release = une ligne ; part de référence < 30 % ; clause de maintenance présente.

### [KEEP] Workflow CI — `.github/workflows/ci.yml`
Gate L4 saine (Checkstyle main+test puis suite complète dont ArchUnit, sur push `develop`/`main` et sur PR, `ci.yml:3-14`) ; elle devient la source lue par `release plan`.

### [KEEP] Checkstyle — `config/checkstyle/checkstyle.xml`
Porte quatre règles de `CLAUDE.md` (`checkstyle.xml:4-9`) ; en P3, ajouter `CustomImportOrder`, `TypeName`, `MemberName` pour que la section Code Style devienne un pointeur d'une ligne.

### [KEEP] ArchUnit — `src/test/java/com/acme/billing/ArchitectureTest.java`
Garde-fou exemplaire — la javadoc cite la règle CLAUDE.md qu'il porte (`ArchitectureTest.java:12-16`) ; c'est là que doivent atterrir « injection par constructeur » et « pas de `@MockBean` en test unitaire ».

### [KEEP] Build Gradle + VERSION — `build.gradle`
Câble Checkstyle et ArchUnit et fait de `VERSION` la source de vérité (`build.gradle:9`, `build.gradle:21-27`) ; l'écrasement de `-Pversion` se résout côté CLI/workflow (committer `VERSION`), pas ici.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | `scripts/old-deploy.sh` | Supprimer le script (au minimum retirer le bit exécutable et le sortir du dépôt). | — | Fichier absent ; `grep -r prod.acme.io` ne renvoie que `release.yml`. | Oui |
| 2 | P1 | SPLIT | `.github/workflows/release.yml` | Jobs `publish` + `deploy-prod` (`environment: production`, reviewers), input `dry_run`, validation regex + tag inexistant, step `./gradlew test`, `concurrency`, `permissions: contents: write`, outputs, suppression de `hotfix` et de `echo SUCCESS`, retrait de `-Pversion`. | — | `dry_run=true` : ni push ni SSH ; dispatch réel : en attente d'approbation ; version invalide ou taguée : échec avant build. | Oui |
| 3 | P1 | SPLIT | `scripts/release.mjs` → CLI `release` | Créer `release plan --type … [--dry-run]` (pré-conditions exit 1, plan JSON) et `release run --plan` (bump + commit VERSION, déclenchement, URL + conclusion), avec tests unitaires. | 2 | `plan --dry-run` ne déclenche rien et échoue sur develop rouge/en retard ; `run` refuse sans plan ; tests verts en CI. | Non |
| 4 | P2 | MERGE | `scripts/hotfix.mjs` | Supprimer `release.mjs` et `hotfix.mjs` ; le hotfix devient `plan --type patch` avec pré-condition de branche. | 3 | Les deux `.mjs` absents ; `plan --type patch` hors `hotfix/*` sort en exit ≠ 0. | Oui |
| 5 | P1 | PUSH_DOWN | `.claude/skills/release/SKILL.md` | Réécrire : `plan` → accord humain → `run` → lecture de `conclusion` ; conserver cas d'abandon et annonce ; retirer onglet Actions, dump prod, grep de log. | 3 | Aucune vérification manuelle ni lecture de log ; confirmation explicite avant `run`. | Non |
| 6 | P2 | PUSH_DOWN | `CLAUDE.md:51` (injection) | Règle ArchUnit `noFields().should().beAnnotatedWith(Autowired.class)` ; corriger `InvoiceService.java` et l'exemple `CLAUDE.md:70-81`. | — | Remettre un `@Autowired` sur champ fait échouer `ArchitectureTest`. | Non |
| 7 | P2 | PUSH_DOWN | `CLAUDE.md:57` (autorisation) | Test générique sur `RequestMappingHandlerMapping` (`@WithMockUser(roles="NONE")` → 401/403) + configuration Spring Security explicite ; la règle pointe vers le test. | — | Un nouvel endpoint sans règle de sécurité fait échouer la CI. | Non |
| 8 | P2 | PUSH_DOWN | `CLAUDE.md:63` (migrations) | Step CI « migrations immuables » (diff `db/migration/V*` M/D contre la branche cible → exit 1) ou test Testcontainers `migrate` + `validate`. | — | Une PR modifiant `V1__init.sql` est rouge. | Non |
| 9 | P2 | SPLIT | `CLAUDE.md` | Réduire à ≈40 lignes ; déporter la référence dans `docs/dev.md` ; supprimer les références mortes ; section Release = pointeur vers le skill ; clause de maintenance ; processus de travail. | 5, 6, 7, 8 | Chaque chemin/commande existe ; référence < 30 % ; clause présente. | Non |
| 10 | P3 | KEEP | `config/checkstyle/checkstyle.xml` | Ajouter `CustomImportOrder`, `TypeName`, `MemberName`, `ParameterName` ; retirer `CLAUDE.md:65-66, 85` au profit de « Checkstyle fait foi ». | — | `checkstyleMain` échoue sur un import mal groupé ou une classe mal nommée. | Non |
| 11 | P3 | KEEP | `.github/workflows/release.yml` | `gh release create v${version} --generate-notes` dans `publish` pour produire la liste des PRs (`SKILL.md:22`) en L4. | 2 | Chaque tag a une GitHub Release ; le skill renvoie à son URL. | Non |

## 6. Ce que l'audit n'a pas pu vérifier

- Fichiers référencés mais absents du dépôt : `gradlew` (`CLAUDE.md:6`, `ci.yml:13`), `Dockerfile` (`release.yml:24`, `old-deploy.sh:5`), fichier docker compose (`CLAUDE.md:12`), `gradle.properties` (`CLAUDE.md:109`). Ni Checkstyle, ni ArchUnit, ni les scripts n'ont été exécutés : analyse statique uniquement.
- Paramètres GitHub non lisibles depuis le dépôt : environnement `production` protégé, branch protection sur `develop`, permissions par défaut du `GITHUB_TOKEN` (le `git push origin v…` de `release.yml:27` peut échouer en lecture seule), présence des secrets `REGISTRY_PASSWORD` / `PROD_SSH_KEY`.
- L'écrasement de `-Pversion` par `build.gradle:9` est déduit de la sémantique Gradle, non exécuté.
- Les packages `customer` / `payment` / `config` / `security` et le dossier `dto/` (`CLAUDE.md:33-42`) n'existent pas dans `src/` : dérive documentaire ou fixture tronquée, non tranché.
- Testcontainers annoncé (`CLAUDE.md:17`) mais absent de `build.gradle` ; aucun test `*IT`.
- Aucun agent, `.claude/settings.json`, hook ou `.cursor/rules` trouvé : supposés inexistants (donc aucune restriction d'outil sur `ssh` ou `gh workflow run`).
- `README.md:3` renvoie vers `../traps.md`, hors périmètre : volontairement non consulté (évaluation en aveugle).

## 7. Données machine

```json
{
  "audit": {
    "process": "Release / déploiement production de billing-api + instrumentation IA (CLAUDE.md, skill release)",
    "scope": "fixtures/repos/java-back/repo (CLAUDE.md, .claude/skills, scripts/, .github/workflows, config/checkstyle, src/test ArchUnit)",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 4 }
  },
  "elements": [
    {
      "id": "release-skill",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["claude-md"],
      "calls": ["release-mjs", "hotfix-mjs", "release-yml", "ci-yml"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "Les trois pré-conditions de release (CI develop verte, migrations Flyway alignées avec la prod, develop à jour) et la détection du succès (grep SUCCESS/ERROR dans les logs) ne vivent que dans le prompt ; le déclenchement du deploy prod (étape 4) n'a aucun point d'arrêt humain ni dry-run.",
      "evidence": [".claude/skills/release/SKILL.md:9", ".claude/skills/release/SKILL.md:10", ".claude/skills/release/SKILL.md:11", ".claude/skills/release/SKILL.md:14", ".claude/skills/release/SKILL.md:15", ".claude/skills/release/SKILL.md:16"],
      "target": "Skill L2 pur : vocabulaire, séquence `release plan` → validation humaine → `release run`, lecture d'un retour JSON (url du run, conclusion), cas d'abandon ; les pré-conditions descendent dans la sous-commande CLI `release plan` (exit 1) et dans release.yml.",
      "check": "SKILL.md ne contient plus aucune vérification manuelle (onglet Actions, dump prod, grep de log) ; chaque étape pointe vers une sous-commande ou un workflow, et une étape « demander confirmation avant `release run` » est explicite."
    },
    {
      "id": "release-mjs",
      "path": "scripts/release.mjs",
      "declared_layer": "L3",
      "actual_layer": "MIXED",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["release-yml", "build-gradle"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "Mélange du jugement L1 codé en dur (type de version déduit du nom de branche : develop = toujours mineure, feat/breaking-* = majeure déployée en prod), de la logique L3 sans pré-condition ni test, et d'un déclenchement L4 immédiat sans dry-run ni confirmation ; VERSION n'est jamais incrémenté donc la release suivante recalcule la même version et le push du tag échoue après avoir écrasé l'image.",
      "evidence": ["scripts/release.mjs:11", "scripts/release.mjs:12", "scripts/release.mjs:15", "scripts/release.mjs:16", "scripts/release.mjs:23", "scripts/release.mjs:7", "VERSION:1", ".github/workflows/release.yml:27"],
      "target": "Une CLI testée `release` : `release plan --type major|minor|patch [--dry-run]` (vérifie CI verte, arbre propre et à jour, tag inexistant, calcule la version, sort du JSON) et `release run --plan <fichier>` (déclenche le workflow, commit VERSION, retourne l'URL du run) ; le type de version est choisi par l'humain/agent (L1), pas par le préfixe de branche.",
      "check": "`release plan --type minor --dry-run` sort un JSON sans rien déclencher et sort en code ≠ 0 si develop est rouge ou en retard ; tests unitaires sur le calcul de version et les pré-conditions ; `scripts/release.mjs` supprimé."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["release-mjs", "hotfix-mjs"],
      "calls": ["build-gradle"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "workflow_dispatch qui build, publie, tague et déploie en prod dans un seul job, sans `environment` protégé, sans input `dry_run`, sans validation du format de version ni du tag, sans concurrency, acceptant n'importe quel `ref` ; l'input `hotfix` est déclaré mais jamais utilisé ; le signal de succès est un `echo SUCCESS` ; `-Pversion` est écrasé par build.gradle qui relit VERSION.",
      "evidence": [".github/workflows/release.yml:3", ".github/workflows/release.yml:8", ".github/workflows/release.yml:11", ".github/workflows/release.yml:16", ".github/workflows/release.yml:23", ".github/workflows/release.yml:27", ".github/workflows/release.yml:28", ".github/workflows/release.yml:32", "build.gradle:9"],
      "target": "Deux jobs : `publish` (validation regex x.y.z + tag inexistant, tests, bootJar, image, tag) puis `deploy-prod` avec `environment: production` à reviewers obligatoires, input `dry_run` qui s'arrête après le plan, `concurrency` par environnement, `permissions: contents: write` explicite, outputs structurés (version, image, url du run) et suppression de l'input `hotfix` ou usage réel.",
      "check": "Un dispatch avec `dry_run=true` ne touche ni registry ni prod ; un dispatch réel reste en attente d'approbation sur l'environnement `production` ; un `version` non semver ou déjà tagué fait échouer le job avant le build."
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
      "finding": "Script mort (le commentaire le dit) mais toujours exécutable : il build, pousse et déploie en prod via SSH depuis un poste, en court-circuitant release.yml, les tests, le tag et tout point d'arrêt ; aucun hook ni settings.json n'empêche un agent de le lancer.",
      "evidence": ["scripts/old-deploy.sh:2", "scripts/old-deploy.sh:5", "scripts/old-deploy.sh:7"],
      "target": "Supprimé du dépôt ; le seul chemin vers la prod est le job `deploy-prod` de release.yml.",
      "check": "`scripts/old-deploy.sh` absent ; grep `ssh .*prod.acme.io` ne matche plus que release.yml."
    },
    {
      "id": "hotfix-mjs",
      "path": "scripts/hotfix.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-skill", "claude-md"],
      "calls": ["release-yml", "build-gradle"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Duplique release.mjs (lecture VERSION, parsing, calcul, `gh workflow run`) avec une seule variation (patch) ; l'input `hotfix=true` qu'il passe n'est lu nulle part dans release.yml, donc un hotfix est strictement identique à une release ; mêmes absences de dry-run et de confirmation.",
      "evidence": ["scripts/hotfix.mjs:11", "scripts/hotfix.mjs:12", "scripts/hotfix.mjs:13", "scripts/hotfix.mjs:16", ".github/workflows/release.yml:11"],
      "target": "Absorbé par `release plan --type patch` ; la vérification « part d'une branche hotfix/* » devient une pré-condition de la CLI quand `--type patch` est demandé hors tag de prod.",
      "check": "`scripts/hotfix.mjs` supprimé ; SKILL.md ne le mentionne plus ; `release plan --type patch` échoue (exit ≠ 0) hors branche hotfix/* ou release/*."
    },
    {
      "id": "claude-md",
      "path": "CLAUDE.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": [],
      "calls": ["release-skill", "release-mjs", "hotfix-mjs", "ci-yml", "release-yml", "checkstyle-xml", "architecture-test"],
      "verdict": "SPLIT",
      "priority": "P2",
      "finding": "Mélange instruction (29 %), référence (45 %) et bruit (26 %) ; l'exemple « service bien formé » utilise l'injection par champ que la règle juste au-dessus interdit (et le code réel la copie) ; la section « Release process » duplique SKILL.md avec le même grep de SUCCESS ; références mortes (InvoiceServiceTest, docker compose, packages customer/payment/config/security, dossier dto) ; aucune clause de maintenance.",
      "evidence": ["CLAUDE.md:51", "CLAUDE.md:74", "CLAUDE.md:75", "src/main/java/com/acme/billing/invoice/InvoiceService.java:10", "CLAUDE.md:95", "CLAUDE.md:98", "CLAUDE.md:9", "CLAUDE.md:12", "CLAUDE.md:34", "CLAUDE.md:42", "CLAUDE.md:103"],
      "target": "Un CLAUDE.md court (≈40 lignes) : règles avec leur pourquoi et le garde-fou qui les porte, processus de travail, un pointeur vers le skill release ; référence (commandes, troubleshooting, stack) déportée dans `docs/` chargée à la demande ; exemple corrigé en injection par constructeur ; clause « toute règle ajoutée en review va dans ce fichier dans la même PR, toute règle sans violation depuis 6 mois est retirée ».",
      "check": "Exemple de service compilant la règle qu'il illustre ; aucune commande ou chemin cité n'est absent du dépôt ; section Release réduite à une ligne vers `.claude/skills/release/SKILL.md` ; part de référence < 30 %."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["checkstyle-xml", "architecture-test", "build-gradle"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Gate L4 saine : Checkstyle main+test et suite de tests (dont ArchUnit) sur push develop/main et sur PR ; c'est le garde-fou de « run the full suite before a PR ».",
      "evidence": [".github/workflows/ci.yml:3", ".github/workflows/ci.yml:5", ".github/workflows/ci.yml:13", ".github/workflows/ci.yml:14"],
      "target": "Inchangé ; son résultat devient la source lue par `release plan` (conclusion du dernier run sur develop).",
      "check": "`release plan` lit la conclusion de ci.yml via `gh run list --workflow ci.yml --branch develop --json conclusion`."
    },
    {
      "id": "checkstyle-xml",
      "path": "config/checkstyle/checkstyle.xml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "build-gradle"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Porte quatre règles de CLAUDE.md (longueur 120, pas d'import *, une classe publique par fichier, nommage constantes/méthodes) ; extension P3 souhaitable : ImportOrder/CustomImportOrder, TypeName, MemberName pour couvrir le reste de la section Naming/Code Style.",
      "evidence": ["config/checkstyle/checkstyle.xml:4", "config/checkstyle/checkstyle.xml:6", "config/checkstyle/checkstyle.xml:7", "config/checkstyle/checkstyle.xml:8", "config/checkstyle/checkstyle.xml:9"],
      "target": "Inchangé dans son rôle ; ajout des modules manquants pour que la section Code Style de CLAUDE.md devienne un pointeur d'une ligne.",
      "check": "Un import non groupé java/javax/org/com ou une classe en camelCase fait échouer `./gradlew checkstyleMain`."
    },
    {
      "id": "architecture-test",
      "path": "src/test/java/com/acme/billing/ArchitectureTest.java",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Garde-fou exemplaire de « pas de repository dans les contrôleurs » : la javadoc cite la règle CLAUDE.md qu'il porte ; c'est le bon endroit pour accueillir la règle « injection par constructeur » et « pas de @MockBean en test unitaire ».",
      "evidence": ["src/test/java/com/acme/billing/ArchitectureTest.java:12", "src/test/java/com/acme/billing/ArchitectureTest.java:14"],
      "target": "Inchangé ; accueille les nouvelles règles ArchUnit issues du PUSH_DOWN de CLAUDE.md.",
      "check": "Chaque règle ArchUnit cite la ligne CLAUDE.md qu'elle garde, et chaque règle obligatoire de CLAUDE.md pointe vers son test."
    },
    {
      "id": "build-gradle",
      "path": "build.gradle",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "release-yml", "release-mjs", "hotfix-mjs"],
      "calls": ["checkstyle-xml"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Câble Checkstyle et ArchUnit et fait de VERSION la source de vérité de la version ; cette assignation écrase le `-Pversion` passé par release.yml, incohérence à résoudre côté workflow/CLI (committer VERSION) plutôt qu'ici.",
      "evidence": ["build.gradle:9", "build.gradle:21", "build.gradle:24", ".github/workflows/release.yml:23"],
      "target": "Inchangé ; la CLI `release run` commit VERSION sur le ref avant de déclencher le workflow, et release.yml cesse de passer `-Pversion`.",
      "check": "Le jar produit par release.yml porte la version taguée (`ls build/libs` dans le job)."
    }
  ],
  "process_leaks": [
    { "rule": "Ne jamais releaser si la CI de develop n'est pas verte", "told_in": ".claude/skills/release/SKILL.md:9 ; CLAUDE.md:96", "if_skipped": "Une image construite sur un develop rouge (tests ou Checkstyle KO) part en prod : release.yml ne relance pas les tests et ne lit pas le statut de ci.yml", "belongs_in": "L3", "guard_tool": "Sous-commande `release plan` : `gh run list --workflow ci.yml --branch develop --json conclusion` → exit 1 si ≠ success ; doublée d'un step `./gradlew test` dans le job publish de release.yml (L4)" },
    { "rule": "Vérifier qu'aucune migration Flyway n'est non appliquée en prod avant de releaser", "told_in": ".claude/skills/release/SKILL.md:10", "if_skipped": "Migration inattendue ou FlywayValidateException au démarrage du conteneur en prod, découverte après `docker compose up -d` ; l'étape demande en plus un dump de la base prod au propriétaire", "belongs_in": "L4", "guard_tool": "Step `flyway info`/`flyway validate` (ou `./gradlew flywayInfo`) contre la base prod dans le job deploy-prod, avant le `docker pull`, avec exit ≠ 0 si état inattendu" },
    { "rule": "Être sur develop à jour (checkout + pull) avant de lancer la release", "told_in": ".claude/skills/release/SKILL.md:11", "if_skipped": "release.mjs ne vérifie que le nom de la branche : un develop local en retard ou un arbre sale produit un `ref` et une VERSION qui ne correspondent pas à ce qui sera déployé", "belongs_in": "L3", "guard_tool": "`release plan` : `git fetch` puis exit 1 si `git status -sb` indique behind/ahead ou un arbre non propre" },
    { "rule": "La release est réussie quand la sortie du workflow contient SUCCESS ; en cas d'ERROR/FAILED prévenir et ne pas relancer", "told_in": ".claude/skills/release/SKILL.md:15 ; .claude/skills/release/SKILL.md:16 ; CLAUDE.md:98", "if_skipped": "Succès halluciné ou manqué : `gh workflow run` ne retourne pas d'id de run, le SUCCESS est un simple `echo` (release.yml:32) et un run partiellement échoué (image poussée, tag KO) n'est pas distinguable", "belongs_in": "L3", "guard_tool": "`release run` retourne l'URL du run et attend `gh run view <id> --json conclusion,jobs` ; release.yml expose des outputs (version, image, étape atteinte)" },
    { "rule": "Point d'arrêt humain entre le plan de release et le déploiement en production", "told_in": ".claude/skills/release/SKILL.md:14 (absent : l'étape 4 déclenche directement)", "if_skipped": "Un agent ou un `node scripts/release.mjs` lancé par erreur déploie en prod sans dry-run ni validation ; aucune protection côté workflow", "belongs_in": "L4", "guard_tool": "`environment: production` avec required reviewers sur le job deploy-prod + input `dry_run` ; côté L3, `release plan --dry-run` par défaut et `release run` qui exige le plan" },
    { "rule": "Injection par constructeur, jamais par champ", "told_in": "CLAUDE.md:51", "if_skipped": "Dépendances cachées, services non testables unitairement ; déjà violé par InvoiceService.java:10 et par l'exemple de CLAUDE.md:74", "belongs_in": "L3", "guard_tool": "Règle ArchUnit dans ArchitectureTest : `noFields().should().beAnnotatedWith(Autowired.class)` (+ `noMethods()` setters @Autowired)" },
    { "rule": "Chaque endpoint a un test d'autorisation (mauvais rôle → 403)", "told_in": "CLAUDE.md:57", "if_skipped": "Un endpoint de facturation exposé sans contrôle de rôle passe la CI ; InvoiceControllerTest.java:8 constate qu'aucun test 403 n'existe", "belongs_in": "L3", "guard_tool": "Test JUnit paramétré sur `RequestMappingHandlerMapping` : pour chaque mapping, requête avec `@WithMockUser(roles=\"NONE\")` doit répondre 401/403 ; échoue à l'ajout d'un endpoint sans règle de sécurité" },
    { "rule": "Ne jamais modifier une migration Flyway déjà appliquée", "told_in": "CLAUDE.md:63", "if_skipped": "Détecté seulement au démarrage en prod (FlywayValidateException, CLAUDE.md:104), c'est-à-dire après le déploiement", "belongs_in": "L3", "guard_tool": "Check CI en PR gate : script `migrations check` comparant les checksums de `src/main/resources/db/migration/V*` à la branche cible (`git diff --name-status origin/develop -- db/migration` → exit 1 sur M/D), ou test Testcontainers `flyway migrate` + `validate`" }
  ],
  "guarded_rules": [
    { "rule": "Pas de logique métier ni d'accès repository dans les contrôleurs", "told_in": "CLAUDE.md:27 ; CLAUDE.md:54", "guarded_by": "src/test/java/com/acme/billing/ArchitectureTest.java:14" },
    { "rule": "Longueur de ligne max 120", "told_in": "CLAUDE.md:84", "guarded_by": "config/checkstyle/checkstyle.xml:4" },
    { "rule": "Pas d'import wildcard", "told_in": "CLAUDE.md:85", "guarded_by": "config/checkstyle/checkstyle.xml:6" },
    { "rule": "Une classe publique par fichier", "told_in": "CLAUDE.md:68", "guarded_by": "config/checkstyle/checkstyle.xml:7" },
    { "rule": "Constantes en UPPER_SNAKE_CASE, méthodes en camelCase (partiel : pas de TypeName/MemberName)", "told_in": "CLAUDE.md:66", "guarded_by": "config/checkstyle/checkstyle.xml:8" },
    { "rule": "Suite complète + Checkstyle avant toute PR / à chaque push", "told_in": "CLAUDE.md:93 ; CLAUDE.md:45", "guarded_by": ".github/workflows/ci.yml:13" },
    { "rule": "Un hotfix part d'une branche hotfix/*", "told_in": ".claude/skills/release/SKILL.md:19", "guarded_by": "scripts/hotfix.mjs:7" },
    { "rule": "Une release part de develop, release/* ou feat/breaking-* (périmètre discutable)", "told_in": "CLAUDE.md:97", "guarded_by": "scripts/release.mjs:17" }
  ],
  "instruction_files": [
    { "path": "CLAUDE.md", "loaded_lines": 111, "instruction_pct": 29, "reference_pct": 45, "noise_pct": 26, "justified_rules": false, "maintenance_clause": false },
    { "path": ".claude/skills/release/SKILL.md", "loaded_lines": 22, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "old-deploy-sh", "action": "Supprimer scripts/old-deploy.sh (ou au minimum retirer le bit exécutable et le déplacer hors du dépôt) ; aucun autre chemin SSH vers prod.acme.io hors release.yml.", "depends_on": [], "check": "Le fichier est absent ; `grep -r prod.acme.io` ne renvoie que release.yml.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "SPLIT", "element": "release-yml", "action": "Refondre release.yml : jobs `publish` et `deploy-prod` (environment: production, reviewers requis), input `dry_run`, validation regex x.y.z + `git ls-remote --tags` vide, step `./gradlew test`, `concurrency: release-prod`, `permissions: contents: write`, outputs version/image/run, suppression de l'input `hotfix` inutilisé et du `echo SUCCESS`, retrait de `-Pversion` au profit du fichier VERSION committé.", "depends_on": [], "check": "Dispatch `dry_run=true` : aucun push registry, aucun ssh ; dispatch réel : job deploy-prod en attente d'approbation ; version `abc` ou déjà taguée : échec avant le build.", "needs_human_approval": true },
    { "order": 3, "priority": "P1", "verdict": "SPLIT", "element": "release-mjs", "action": "Créer une CLI testée (ex. `tools/release/` ou `npm run release -- plan|run`) : `plan --type major|minor|patch [--dry-run]` vérifie CI verte, arbre propre/à jour, tag inexistant, calcule la version et écrit un plan JSON ; `run --plan` bump + commit VERSION, déclenche release.yml et retourne l'URL du run + conclusion ; tests unitaires du calcul de version et des pré-conditions.", "depends_on": [2], "check": "`plan --dry-run` ne déclenche rien et sort en exit 1 sur develop rouge/en retard ; `run` refuse sans plan ; tests verts en CI.", "needs_human_approval": false },
    { "order": 4, "priority": "P2", "verdict": "MERGE", "element": "hotfix-mjs", "action": "Supprimer scripts/release.mjs et scripts/hotfix.mjs une fois la CLI en place ; le cas hotfix devient `plan --type patch` avec pré-condition « branche hotfix/* ou release/* ».", "depends_on": [3], "check": "Les deux .mjs sont absents ; `plan --type patch` hors hotfix/* sort en exit ≠ 0.", "needs_human_approval": true },
    { "order": 5, "priority": "P1", "verdict": "PUSH_DOWN", "element": "release-skill", "action": "Réécrire SKILL.md : séquence `plan` → montrer le plan JSON à l'humain et attendre son accord → `run` → lire `conclusion` ; conserver les cas d'abandon (échec = prévenir, ne pas relancer) et l'annonce #releases ; retirer onglet Actions, dump prod et grep SUCCESS/ERROR.", "depends_on": [3], "check": "Aucune vérification manuelle ni lecture de log dans SKILL.md ; une étape de confirmation explicite précède `run`.", "needs_human_approval": false },
    { "order": 6, "priority": "P2", "verdict": "PUSH_DOWN", "element": "claude-md", "action": "Ajouter dans ArchitectureTest la règle `noFields().should().beAnnotatedWith(Autowired.class)` et corriger InvoiceService.java en injection par constructeur ; corriger l'exemple CLAUDE.md:70-81.", "depends_on": [], "check": "`./gradlew test --tests ArchitectureTest` échoue si on remet un `@Autowired` sur un champ ; l'exemple de CLAUDE.md compile la règle.", "needs_human_approval": false },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "claude-md", "action": "Ajouter un test d'autorisation générique (itération sur RequestMappingHandlerMapping, `@WithMockUser(roles=\"NONE\")` → 401/403) et une configuration Spring Security explicite ; remplacer CLAUDE.md:57 par un pointeur vers ce test.", "depends_on": [], "check": "Ajouter un `@GetMapping` sans règle de sécurité fait échouer la CI.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "PUSH_DOWN", "element": "claude-md", "action": "Ajouter un step CI « migrations immuables » (diff des fichiers `db/migration/V*` modifiés/supprimés par rapport à la branche cible → exit 1) ou un test Testcontainers `flyway validate` ; CLAUDE.md:63 pointe vers ce gate.", "depends_on": [], "check": "Une PR qui modifie V1__init.sql est rouge en CI.", "needs_human_approval": false },
    { "order": 9, "priority": "P2", "verdict": "SPLIT", "element": "claude-md", "action": "Réduire CLAUDE.md à ≈40 lignes : règles + pourquoi + garde-fou, processus de travail (quand s'arrêter, critère de fini), une ligne vers le skill release ; déporter Build/Stack/Troubleshooting/Package structure dans `docs/dev.md` ; supprimer les références mortes (InvoiceServiceTest, docker compose, packages inexistants, dossier dto) ; ajouter la clause de maintenance.", "depends_on": [5, 6, 7, 8], "check": "Chaque commande et chemin cité existe ; part de référence < 30 % ; clause de maintenance présente ; section Release = 1 ligne.", "needs_human_approval": false },
    { "order": 10, "priority": "P3", "verdict": "KEEP", "element": "checkstyle-xml", "action": "Ajouter CustomImportOrder (java/javax/org/com), TypeName, MemberName, ParameterName ; supprimer de CLAUDE.md les lignes 65-66 et 85 au profit d'un pointeur « Checkstyle fait foi ».", "depends_on": [], "check": "`./gradlew checkstyleMain` échoue sur un import mal groupé ou une classe mal nommée.", "needs_human_approval": false },
    { "order": 11, "priority": "P3", "verdict": "KEEP", "element": "release-yml", "action": "Ajouter `gh release create v${version} --generate-notes` dans le job publish pour que la « liste des PRs incluses » (SKILL.md:22) soit produite par L4 et non reconstituée par l'agent.", "depends_on": [2], "check": "Chaque tag a une GitHub Release avec notes générées ; le skill renvoie à son URL pour l'annonce.", "needs_human_approval": false }
  ],
  "unverified": [
    "Fichiers référencés mais absents du dépôt : `gradlew` (CLAUDE.md:6, ci.yml:13), `Dockerfile` (release.yml:24, old-deploy.sh:5), fichier docker compose (CLAUDE.md:12), `gradle.properties` (CLAUDE.md:109) ; ni Checkstyle, ni ArchUnit, ni la CLI n'ont pu être exécutés — l'analyse est statique.",
    "Paramètres GitHub non lisibles depuis le dépôt : existence d'un environnement `production` protégé, branch protection sur develop, permissions par défaut du GITHUB_TOKEN (le `git push origin v…` de release.yml:27 peut échouer en lecture seule), secrets REGISTRY_PASSWORD / PROD_SSH_KEY.",
    "Comportement Gradle `-Pversion` écrasé par `build.gradle:9` déduit de la sémantique Gradle, non exécuté.",
    "Les packages customer/payment/config/security et le dossier dto décrits dans CLAUDE.md:33-42 n'existent pas dans src/ : dérive documentaire ou fixture tronquée, non tranché.",
    "Dépendance Testcontainers annoncée (CLAUDE.md:17) absente de build.gradle ; aucun test `*IT` dans le dépôt.",
    "Aucun agent, `.claude/settings.json`, hook ou `.cursor/rules` trouvé : supposé inexistant (donc aucune restriction d'outil sur `ssh` ou `gh workflow run`).",
    "README.md:3 renvoie vers `../traps.md`, hors périmètre : volontairement non consulté (évaluation en aveugle)."
  ]
}
```
