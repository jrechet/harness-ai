# Audit du harness — release de piloto (CLI Python publiée sur PyPI)

**Périmètre** : `fixtures/repos/python-cli/repo/` (AGENTS.md, CLAUDE.md, stub Copilot, `src/piloto/AGENTS.md`, skill `release` et ses scripts, `.github/workflows/`, ruff, mypy/pre-commit, pytest, `.harness/`) · **Date** : 2026-11-09 · **Éléments inventoriés** : 17

## 1. Synthèse

- **Score de santé** : 2 — l'agent est un pilier : la publication de secours, les pré-conditions de release, la cohérence tag/version et la vérification finale ne vivent que dans `SKILL.md`, et ce même fichier porte un jeton PyPI en clair.
- **Résultat du test « coupe l'agent »** : ÉCHEC — 4 étape(s) du processus n'existent que dans des prompts (main vert, CHANGELOG renseigné, tag cohérent avec `pyproject.toml`, vérification de la publication).
- **Points bloquants (P1)** : 2
- **Les trois actions qui changent le plus les choses** :
  1. Révoquer le jeton PyPI écrit dans `.claude/skills/release/SKILL.md:13`, supprimer la ligne et `.claude/skills/release/scripts/publish.sh` : le chemin de publication hors `release.yml` est interdit par `AGENTS.md:26` et le skill le contredit avec un secret.
  2. Ajouter à `release.yml` un job `verify` avant `publish` : lint, mypy, tests, `tag == version pyproject`, section `## <version>` non vide dans `CHANGELOG.md`. Aujourd'hui un tag poussé sur n'importe quel commit publie.
  3. Remplacer `bump_version.py` par une sous-commande testée (`piloto-release plan|bump`, ou `uv version`) avec `--dry-run`, arbre propre, tag absent ; faire pointer le skill dessus et corriger le chemin faux de `SKILL.md:12`.

Calcul : 100 − 2 × 25 (P1) − 6 × 8 (P2) − 0 × 2 (P3) = 2 ; le plafond de 60 du test « coupe l'agent » en échec est sans effet.

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md racine | `AGENTS.md` | L2 | L2 | CLAUDE.md (`@`), copilot-instructions | skill release, docs/agents, ci.yml, release.yml, pre-commit, test_version_single_source, ruff.toml |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2 | Claude Code (chargement auto) | AGENTS.md |
| 3 | Stub Copilot | `.github/copilot-instructions.md` | L2 | L2 | Copilot (chargement auto) | AGENTS.md |
| 4 | AGENTS.md de dossier | `src/piloto/AGENTS.md` | L2 | L2 | chargement auto dans `src/piloto/` | — |
| 5 | Référence build/test | `docs/agents/build-and-test.md` | L2 (référence) | L2 | AGENTS.md:6 (à la demande) | — |
| 6 | Skill release | `.claude/skills/release/SKILL.md` | L2 | MIXED (L1 + L2 + L3 + L4 + secret) | AGENTS.md:13, :36 | bump_version.py, publish.sh, release.yml (via tag), git, PyPI web |
| 7 | Script bump | `.claude/skills/release/scripts/bump_version.py` | L3 | L3 (+ `git commit -am`) | SKILL.md:10 (et :12 sous un faux chemin) | git |
| 8 | Script publication de secours | `.claude/skills/release/scripts/publish.sh` | L3 | L4 (publie sur PyPI avec un jeton) | SKILL.md:13 | build, twine → PyPI |
| 9 | Workflow CI | `.github/workflows/ci.yml` | L4 | L4 | push main, pull_request | ruff.toml, pytest (pyproject) |
| 10 | Workflow release | `.github/workflows/release.yml` | L4 | L4 | push de tag `v*` (SKILL.md:12) | uv build, pypa/gh-action-pypi-publish |
| 11 | pre-commit | `.pre-commit-config.yaml` | L3 | L3 local, opt-in | développeur (si installé) | ruff, mypy --strict |
| 12 | Config ruff | `ruff.toml` | L3 | L3 | ci.yml:12, pre-commit | — |
| 13 | pyproject (version, pytest, mypy) | `pyproject.toml` | L3 | L3 | ci.yml:18 (addopts), bump_version.py, test_version_single_source | — |
| 14 | Test version unique | `tests/test_version_single_source.py` | L3 | L3 | ci.yml:18 | pyproject.toml, src/ |
| 15 | Test net | `tests/test_net.py` | L3 | L3 | ci.yml:18 | net.py |
| 16 | Test E2E push | `tests/test_push_e2e.py` | L3 | L3 jamais exécuté | personne (désélectionné par pyproject.toml:17) | cli.py |
| 17 | Harvest | `.harness/harvest.json` | — (donnée) | — | harness-harvest | — |

Processus nominal de release, tel que raconté dans `SKILL.md` :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| 1. `main` est vert | SKILL.md:8 (prompt, lecture de l'onglet Actions) | Non | — |
| 2. Choisir patch / minor / major avec l'utilisateur | SKILL.md:9 (L1, légitime) | — | — |
| 3. Monter la version et commiter | bump_version.py (L3) | Partiel : regex trouvée ou `exit`, mais ni arbre propre, ni branche, ni tag absent ; non testé | Non |
| 4. Renseigner `CHANGELOG.md` et amender | SKILL.md:11 (à la main) | Non | — |
| 5. Tag `v<version>` et `git push --tags` | SKILL.md:12 (commande git, chemin de script inexistant) | Non : rien ne vérifie `tag == version` | Non, aucun point d'arrêt entre tag et publication |
| 6. Publication PyPI | release.yml (L4, OIDC) | Oui pour la publication ; aucune pré-condition (tests, cohérence) avant `publish` | Non |
| 6 bis. Publication de secours depuis le poste | SKILL.md:13 + publish.sh (jeton en clair) | Non, contourne release.yml | Non |
| 7. Vérifier que la version apparaît sur pypi.org | SKILL.md:14 (page web, lecture humaine) | Non | — |

## 3. Fuites : règles et étapes racontées sans vérification

| Règle ou étape | Racontée en | Si l'agent la saute | Doit vivre en | Outil cible |
|---|---|---|---|---|
| `main` doit être vert avant de releaser | `.claude/skills/release/SKILL.md:8` | un tag sur un commit rouge publie sur PyPI, irréversible | L4 | job `verify` dans `release.yml` (ruff, mypy, pytest) avant `publish` |
| Le tag `v<x>` correspond à la version de `pyproject.toml` | `.claude/skills/release/SKILL.md:12` (et le chemin `scripts/bump_version.py` n'existe pas : `$(…)` vide → `git tag v`) | tag `v` ou tag décalé d'une version ; `release.yml` publie quand même (`v*`) | L3 + L4 | sous-commande `release tag` qui lit la version ; step `verify` dans `release.yml` comparant `${GITHUB_REF_NAME#v}` à `uv version --short` |
| `CHANGELOG.md` a une section non vide pour la version publiée | `AGENTS.md:20`, `SKILL.md:11` ; `CHANGELOG.md:9` montre `## 1.4.0` encore vide | nouvelle « release 1.4 » avec changelog vide (incident cité) | L4 | job `verify` (section `## <version>` non vide) ; PR gate `changelog-touched` dans `ci.yml` avec label d'exemption |
| Publier sur PyPI uniquement par `release.yml` | `AGENTS.md:26` — contredit par `SKILL.md:13` et `publish.sh` | publication depuis un poste, avec un jeton long-vécu, hors audit, sans environnement protégé | L4 | supprimer `publish.sh` ; côté PyPI, trusted publisher seul, aucun jeton d'API actif ; environnement `pypi` avec relecteurs requis |
| La version publiée est constatée | `SKILL.md:14` (lecture de pypi.org) | succès halluciné si la publication a échoué | L3/L4 | step final de `release.yml` : `pip index versions piloto` / appel JSON `pypi.org/pypi/piloto/<v>/json` avec `exit 1` ; URL du run comme retour structuré |
| Tout code passe mypy en strict (incident #23) | `AGENTS.md:18` prétend « Vérifiée par : mypy dans `.pre-commit-config.yaml` » | le hook est local et opt-in ; `ci.yml:7-18` ne lance jamais mypy : une PR sans hook passe verte | L4 | job `types` dans `ci.yml` : `uv run mypy src` |
| Les appels réseau passent par `piloto.net`, jamais `subprocess` (incident #38) | `AGENTS.md:23` ; contredite par `src/piloto/AGENTS.md:5` ; violée par `src/piloto/cli.py:36` (`ssh` sans timeout) | CI ou poste bloqué sur un `ssh` sans timeout, comme #38 | L3 | ruff `flake8-tidy-imports` `banned-api` (TID251) interdisant `subprocess` hors `src/piloto/net.py`, ou test miroir de `test_version_single_source.py` |
| Pousser sur `main` sans PR est interdit | `AGENTS.md:28` ; `SKILL.md:10-12` crée un commit local sur `main` et ne pousse que les tags | tag pointant sur un commit absent de `main` ; `main` ne porte pas le bump | L4 | protection de branche (non visible dans le dépôt) ; le bump passe par une PR, le tag se pose sur le commit fusionné |
| Les tests E2E « manuels de la release » couvrent `cli.py` | `src/piloto/AGENTS.md:6` ; `tests/test_push_e2e.py:8` dit lui-même « jamais exécuté en CI » ; `pyproject.toml:17` désélectionne `slow` | `cli.py` n'a aucun test exécuté nulle part | L4 | job `e2e` dans `ci.yml` avec un service `sshd`, `pytest -m slow` |

Règles **avec** garde-fou (partie saine, raccourcissable dans `AGENTS.md`) :
- Style ruff (`AGENTS.md:17`) — `ruff.toml` exécuté par `ci.yml:12` sur PR et `main`.
- Version à un seul endroit (`AGENTS.md:19`) — `tests/test_version_single_source.py:6-14`, lancé par `ci.yml:18`.
- « Finie quand pytest passe » (`AGENTS.md:21`) — `ci.yml:18` (avec la réserve que `pyproject.toml:17` exclut `slow` et s'arrête à la première erreur).
- Publication par OIDC sans secret stocké, dans un `environment` — `release.yml:5-7, 11` (les règles de protection de l'environnement ne sont pas visibles).
- Micro-garde sur le timeout par défaut — `tests/test_net.py:4-5` borne `DEFAULT_TIMEOUT` (ne couvre pas le `subprocess` de `cli.py:36`).

## 3b. Coût de contexte

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| `CLAUDE.md` → `AGENTS.md` | 43 (1 + 42) | ~70 % / ~20 % / ~10 % | chaque session Claude Code |
| `.github/copilot-instructions.md` | 1 (pointeur vers AGENTS.md, non résolu automatiquement par Copilot) | 100 % / 0 / 0 | chaque session Copilot |
| `src/piloto/AGENTS.md` | 6 | 0 / 0 / 100 % (trois lignes qui contredisent la racine) | travail dans `src/piloto/` |
| `docs/agents/build-and-test.md` | 7 | 0 / 100 % / 0 | à la demande (`AGENTS.md:6`) |

Les règles de `AGENTS.md` sont justifiées : six sur sept citent un pourquoi, quatre un incident (#23, #31, #38, release 1.4), et le fichier dit honnêtement « (non vérifiée) » pour deux d'entre elles. Le bruit tient en deux lignes : `AGENTS.md:22` (docstring + annotations, sans pourquoi, sans garde-fou — ruff `D` n'est pas sélectionné dans `ruff.toml:3`) et le doublon de la définition de « fini » (`AGENTS.md:21` contre `:32`, qui ne disent pas la même chose). La clause de maintenance existe (`AGENTS.md:38-40`) et un marqueur de harvest est posé (`AGENTS.md:42`). Deux incohérences internes : `AGENTS.md:13` donne un skill, pas une commande, comme « ce qu'on lance » pour la release ; `SKILL.md:10` et `:12` appellent le même script par deux chemins, dont un inexistant.

## 4. Constats par élément

### [SPLIT] [P1] Skill release — `.claude/skills/release/SKILL.md`
- **Fait aujourd'hui** : une séquence de sept étapes qui mélange jugement (choix du type de version, :9), procédure (:8, :11, :14), logique locale (chemins de scripts, :10, :12), exécution distante (`git push --tags` déclenche la publication, :12) et un contournement de L4 avec un jeton PyPI écrit en clair (:13).
- **Problème** : (a) secret en clair dans un fichier versionné et chargé en contexte (`SKILL.md:13`, valeur non recopiée ici) ; (b) `SKILL.md:13` contredit l'Interdit `AGENTS.md:26` ; (c) pré-condition « main vert » racontée (`:8`) ; (d) `scripts/bump_version.py --show` (`:12`) n'existe pas — le vrai chemin est `.claude/skills/release/scripts/bump_version.py` (`:10`) — donc `git tag v$(…)` produit un tag `v` que `release.yml:4` accepte ; (e) aucun point d'arrêt ni dry-run entre le tag et la publication ; (f) retour final non structuré (`:14`, lecture de pypi.org) ; (g) le commit de release reste local sur `main` (`:10-12` ne poussent que les tags) alors que `AGENTS.md:28` interdit de pousser `main` sans PR : le processus ne dit pas comment le bump atteint `main`.
- **Doit devenir** : un SKILL.md de procédure pure : « `release plan <kind>` (dry-run, affiche version, tag, section changelog), ouvrir la PR de bump, après fusion `release tag` sur le commit fusionné, lire l'URL du run `release.yml` et son exit code ». Le choix patch/minor/major reste à l'agent (L1). Les étapes 6 et 7 disparaissent au profit du job `verify` et du step de constat dans `release.yml`.
- **Critère de vérification** : `grep -c "PYPI_TOKEN\|pypi-" .claude/skills/release/SKILL.md` renvoie 0 ; chaque commande du skill existe (`test -f` sur chaque chemin cité) ; un essai à blanc `release plan patch` s'exécute sans agent et sans écrire.

### [BLOCK] [P1] Publication de secours — `.claude/skills/release/scripts/publish.sh`
- **Fait aujourd'hui** : build local puis `twine upload` avec `PYPI_TOKEN` (`publish.sh:4-6`), appelé par `SKILL.md:13` avec le jeton fourni dans la commande.
- **Problème** : action L4 irréversible exécutée depuis un poste, sans `environment` protégé, sans OIDC, sans trace de run ; viole `AGENTS.md:26` ; le script n'a aucun appelant légitime et sert de porte dérobée à la règle « publier uniquement par `release.yml` » (preuve : `publish.sh:2` le dit lui-même « quand release.yml ne passe pas »).
- **Doit devenir** : supprimé. Le cas « `release.yml` échoue » devient : corriger, re-déclencher (`workflow_dispatch` avec input `tag` et `environment: pypi` à relecteurs requis), jamais publier à la main. Côté PyPI : trusted publisher seul, jetons d'API révoqués.
- **Critère de vérification** : fichier absent ; `grep -rn twine .claude/ AGENTS.md` vide ; sur pypi.org, aucun jeton d'API actif pour le projet (constat humain).

### [PUSH_DOWN] [P2] AGENTS.md racine — `AGENTS.md`
- **Fait aujourd'hui** : fichier court, justifié, avec clause de maintenance (`:38-40`), mais deux règles à incident déclarées « (non vérifiée) » (`:20` CHANGELOG, `:23` réseau), une règle dont le garde-fou annoncé ne tourne pas dans le pipeline (`:18`, mypy en pre-commit seulement), une règle de bruit (`:22`), deux définitions de « fini » (`:21`, `:32`) et une entrée « Lance… » qui désigne un skill et non une commande (`:13`).
- **Problème** : trois fuites de processus racontées (preuves : `AGENTS.md:18`, `:20`, `:23`) et un garde-fou revendiqué à tort (`ci.yml:7-18` ne contient pas mypy). Le fichier de dossier `src/piloto/AGENTS.md:5-6` le contredit sans que rien l'empêche.
- **Doit devenir** : `:18` → « Vérifiée par : `ci.yml` job types » après ajout du job ; `:20` → PR gate changelog + `verify` dans `release.yml` ; `:23` → règle ruff TID251 ; `:22` supprimée ou réduite à « ruff `D` » si on l'active ; `:21` fusionnée dans `:32` ; `:13` → la commande CLI de release.
- **Critère de vérification** : plus aucune mention « (non vérifiée) » dans le fichier, chaque « Vérifiée par » cite un fichier qui tourne dans `ci.yml` ou `release.yml` ; `harness status` (quand `.harness/audit.json` sera écrit) ne liste plus ces trois règles en fuite.

### [BLOCK] [P2] AGENTS.md de dossier — `src/piloto/AGENTS.md`
- **Fait aujourd'hui** : trois « conventions » : `print()` pour déboguer (`:4`), `subprocess.run(["ssh", …])` acceptable dans `cli.py` (`:5`), tests obligatoires seulement pour `net.py`, `cli.py` « couvert par les tests manuels de la release » (`:6`).
- **Problème** : `:5` contredit frontalement `AGENTS.md:23` (règle née de l'incident #38) et légitime `src/piloto/cli.py:36`, un `ssh` sans timeout ; `:6` repose sur `tests/test_push_e2e.py`, désélectionné par `pyproject.toml:17` et jamais exécuté (`test_push_e2e.py:8`). Le fichier est chargé précisément là où l'agent écrit le code réseau : c'est une autorisation de violer la règle, pas une convention.
- **Doit devenir** : supprimé (ou réduit à un pointeur vers `AGENTS.md`) ; la règle réseau devient une règle ruff `banned-api` sur `subprocess` hors `net.py` ; `cli.py:36` passe par `piloto.net` (hors périmètre harness, à ouvrir en tâche séparée).
- **Critère de vérification** : fichier absent ou sans règle contradictoire ; `ruff check .` échoue sur `import subprocess` dans `cli.py` tant que la ligne 36 n'est pas migrée.

### [PUSH_DOWN] [P2] Script bump — `.claude/skills/release/scripts/bump_version.py`
- **Fait aujourd'hui** : lit la version par regex (`:9`, `:13`), calcule la suivante (`:25-31`), réécrit `pyproject.toml` et fait `git commit -am` (`:32-33`), `--show` imprime la version (`:22-24`).
- **Problème** : logique L3 obligatoire sans test (rien dans `tests/` ne l'importe ; mypy ne le voit pas, `docs/agents/build-and-test.md:5` limite mypy à `src`) ; `git commit -am` embarque toute modification suivie en cours (`:33`) ; ni vérification d'arbre propre, ni de branche, ni de tag existant, ni dry-run ; la connaissance « où est la version » est dupliquée avec `tests/test_version_single_source.py:13-14` (deux regex) ; appelé sous un chemin inexistant à `SKILL.md:12`.
- **Doit devenir** : une sous-commande testée (`piloto-release` dans `src/`, ou `uv version --bump <kind>` + script de garde) qui expose `plan` (dry-run JSON : version actuelle, version cible, tag, section changelog présente) et `bump` (échoue si arbre sale, si pas sur `main`, si le tag existe, si la section changelog manque) ; `tomllib` au lieu de la regex.
- **Critère de vérification** : tests unitaires dans `tests/` couvrant plan/bump/échecs, exécutés par `ci.yml` ; `release plan patch` n'écrit rien et sort 0 ; `.claude/skills/release/scripts/bump_version.py` supprimé.

### [PUSH_DOWN] [P2] Workflow release — `.github/workflows/release.yml`
- **Fait aujourd'hui** : sur tag `v*` (`:3-4`), build puis publication OIDC dans l'environnement `pypi` (`:5-7`, `:11`, `:15-16`). C'est la bonne couche et le bon mécanisme de secret.
- **Problème** : aucune pré-condition avant `publish` : ni tests ni lint (un tag sur un commit rouge publie), ni comparaison `tag == version` (un tag `v` ou `v1.4.9` publierait 1.4.2), ni section changelog ; aucun constat structuré de fin ; pas de `workflow_dispatch` pour rejouer une publication échouée, ce qui pousse vers `publish.sh`. Les pré-conditions racontées dans `SKILL.md:8` et `:11-12` doivent descendre ici.
- **Doit devenir** : job `verify` (`needs` de `publish`) : `uv run ruff check .`, `uv run mypy src`, `uv run pytest`, `test "${GITHUB_REF_NAME#v}" = "$(uv version --short)"`, section `## <version>` non vide ; step final qui interroge `https://pypi.org/pypi/piloto/<version>/json` et échoue sinon ; `workflow_dispatch` avec input `tag` (et `dry_run` qui s'arrête après `verify` + `uv build`) ; `environment: pypi` avec relecteurs requis (à confirmer côté GitHub).
- **Critère de vérification** : un tag `v9.9.9` posé sur un commit dont `pyproject.toml` dit 1.4.2 fait échouer `verify` sans atteindre `publish` ; le run publie l'URL et la version en sortie de job.

### [PUSH_DOWN] [P2] pre-commit — `.pre-commit-config.yaml`
- **Fait aujourd'hui** : hooks ruff et `mypy --strict` (`:2-7`), à installer par chaque développeur.
- **Problème** : présenté par `AGENTS.md:18` comme le garde-fou de la règle « mypy strict » (incident #23), alors qu'il est local et opt-in ; `ci.yml:7-18` n'exécute pas mypy. Un agent en délégation (mode annoncé `AGENTS.md:3`) n'installe pas pre-commit : la règle n'est vérifiée par rien dans le pipeline.
- **Doit devenir** : le hook reste (miroir local utile), mais la garantie descend dans `ci.yml` : job `types` = `uv run mypy src`. La config mypy de `pyproject.toml:20-21` est déjà en place.
- **Critère de vérification** : une PR qui ajoute `def f(x): return x` dans `src/piloto/` est rouge en CI sans que pre-commit soit installé.

### [PUSH_DOWN] [P2] Test E2E push — `tests/test_push_e2e.py`
- **Fait aujourd'hui** : seul test qui exerce `cli.py` (`:7-11`), marqué `slow`, désélectionné par défaut (`pyproject.toml:17`), et dont le commentaire admet qu'il n'est « jamais exécuté en CI » (`:8`).
- **Problème** : test mort : aucun appelant (ni `ci.yml`, ni `release.yml`, ni le skill ne lance `pytest -m slow`), pourtant `src/piloto/AGENTS.md:6` s'appuie dessus pour dispenser `cli.py` de tests. Par ailleurs `pyproject.toml:17` met `-x --maxfail=1` : la CI s'arrête à la première erreur et masque les suivantes (hygiène, P3, inclus ici).
- **Doit devenir** : job `e2e` dans `ci.yml` avec un conteneur `sshd` de service et `uv run pytest -m slow`, ou suppression du test avec le commentaire daté exigé par le mode délégation ; retirer `-x --maxfail=1` des `addopts`.
- **Critère de vérification** : le log d'un run `ci.yml` affiche « 1 passed » pour `test_push_against_local_sshd`, ou le fichier n'existe plus ; `addopts` ne contient plus `-x`.

### [KEEP] CLAUDE.md — `CLAUDE.md`
Une ligne `@AGENTS.md` : la bonne manière de charger les instructions sans dupliquer.

### [KEEP] Stub Copilot — `.github/copilot-instructions.md`
Pointeur vers `AGENTS.md` sans règle propre ; Copilot ne résout pas l'`@include`, mais la phrase suffit à envoyer un agent lire le bon fichier.

### [KEEP] Référence build/test — `docs/agents/build-and-test.md`
Sept lignes de commandes chargées à la demande, cohérentes avec `pyproject.toml` (marqueur `slow`, `uv`) : c'est la référence au bon endroit, hors du contexte permanent.

### [KEEP] Workflow CI — `.github/workflows/ci.yml`
Lint et tests sur PR et `main`, en L4 : c'est là que doivent atterrir les jobs `types` et `e2e` recommandés plus haut, sans en changer la structure.

### [KEEP] Config ruff — `ruff.toml`
Sélection `E, F, I, B` exécutée en CI ; c'est aussi le point d'accueil naturel de la règle `banned-api` sur `subprocess` (TID251) et, si on garde la règle docstring, du jeu `D`.

### [KEEP] pyproject — `pyproject.toml`
Source unique de la version (`:3`), scripts, `[tool.mypy] strict` (`:20-21`) : bon étage ; seul le bloc `addopts` (`:17`) est à alléger, traité avec le test E2E.

### [KEEP] Test version unique — `tests/test_version_single_source.py`
Garde-fou réel d'une règle à incident (#31), exécuté par `ci.yml:18` ; bon modèle pour la future règle réseau.

### [KEEP] Test net — `tests/test_net.py`
Borne `DEFAULT_TIMEOUT` (`:4-5`) : faible mais exécuté ; il ne couvre pas le `subprocess` de `cli.py:36`, ce que la règle ruff couvrira.

### [KEEP] Harvest — `.harness/harvest.json`
Donnée utile : le signal S1 du 2026-10-28 (`:11-23`, « timeout explicite, jamais un subprocess ssh nu ») a bien donné la règle `AGENTS.md:23` (marqueur `AGENTS.md:42`), mais `related_rule` est resté `null`, aucun garde-fou n'a suivi, `cli.py:36` viole toujours la règle et `src/piloto/AGENTS.md:5` l'autorise : un signal collecté sans suite complète. Les six S5 (`:24-29`) marquent des règles sans incident dans les PR ; la règle docstring (`:29`) est la candidate à suppression.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | publish.sh + SKILL.md:13 | Révoquer le jeton PyPI côté pypi.org, supprimer `SKILL.md:13` et `.claude/skills/release/scripts/publish.sh`, vérifier que le projet PyPI n'a que le trusted publisher | — | `grep -rn "pypi-\|twine" .claude AGENTS.md` vide ; aucun jeton actif sur PyPI | Oui (révocation + suppression) |
| 2 | P2 | PUSH_DOWN | release.yml | Ajouter le job `verify` (ruff, mypy, pytest, `tag == version`, section changelog) en `needs` de `publish`, un step de constat sur l'API JSON de PyPI, `workflow_dispatch` (`tag`, `dry_run`) ; confirmer les relecteurs requis sur l'environnement `pypi` | 1 | tag incohérent → run rouge avant `publish` ; sortie de job avec version et URL | Oui (modifie le pipeline de publication) |
| 3 | P2 | PUSH_DOWN | pre-commit-config | Ajouter le job `types` (`uv run mypy src`) dans `ci.yml` ; garder le hook local | — | PR non typée rouge en CI sans pre-commit | Non |
| 4 | P2 | PUSH_DOWN | bump_version.py | Créer la sous-commande testée `release plan|bump|tag` (tomllib, arbre propre, tag absent, section changelog, `--dry-run`) avec ses tests dans `tests/`, puis supprimer le script | — | tests verts dans `ci.yml` ; `release plan patch` n'écrit rien ; script absent | Oui pour la suppression |
| 5 | P2 | BLOCK | src/piloto/AGENTS.md | Supprimer le fichier (ou le réduire à un pointeur) ; ajouter dans `ruff.toml` `[lint.flake8-tidy-imports.banned-api]` sur `subprocess` avec exemption `per-file-ignores` pour `net.py` ; ouvrir une tâche pour migrer `cli.py:36` vers `piloto.net` | — | `ruff check .` signale `cli.py:5` tant que la migration n'est pas faite ; fichier absent | Oui (suppression d'instructions) |
| 6 | P2 | PUSH_DOWN | test_push_e2e.py | Job `e2e` dans `ci.yml` avec service `sshd` et `pytest -m slow`, ou suppression datée ; retirer `-x --maxfail=1` de `pyproject.toml:17` | 3 | log CI « 1 passed » pour le test, ou fichier absent ; `addopts` sans `-x` | Oui si suppression |
| 7 | P2 | PUSH_DOWN | AGENTS.md | Job `changelog` dans `ci.yml` (PR gate avec label d'exemption) ; réécrire `:13` (commande CLI), `:18` (ci.yml job types), `:20` et `:23` (garde-fous nommés), fusionner `:21` dans `:32`, supprimer ou réduire `:22` | 2, 3, 4, 5 | plus aucun « (non vérifiée) » ; chaque « Vérifiée par » cite un job de `ci.yml`/`release.yml` | Non |
| 8 | P1 | SPLIT | SKILL.md | Réécrire le skill en procédure pure autour de `release plan` / PR de bump / `release tag` / lecture du run ; corriger tous les chemins ; supprimer les étapes 6 et 7 | 1, 2, 4 | chaque commande citée existe ; essai à blanc sans agent ; aucun secret | Non (après 1) |
| 9 | P3 | KEEP | harvest.json | Lier le signal S1 à la règle `AGENTS.md:23` (`related_rule`) et le clore quand la règle ruff existe ; écrire `.harness/audit.json` à partir de ce rapport | 5 | `harness status` montre la règle comme gardée | Non |

## 6. Ce que l'audit n'a pas pu vérifier

- Les règles de protection de l'environnement GitHub `pypi` (relecteurs requis, branches/tags autorisés) et la protection de branche de `main` (`AGENTS.md:28`) : hors dépôt, non lisibles ici.
- Côté PyPI : si le projet a d'autres jetons d'API actifs que le trusted publisher, et si le jeton de `SKILL.md:13` est valide (non testé, valeur non recopiée).
- L'historique git n'a pas été consulté (consigne de l'audit) : impossible de dire depuis quand le jeton est versionné ni s'il faut purger l'historique ; à traiter dans la remédiation 1.
- Aucun test ni workflow n'a été exécuté ; `uv run ruff check .` lint vraisemblablement `.claude/` (pas d'exclusion dans `ruff.toml`), non confirmé.
- `.harness/audit.json` n'existe pas : premier audit, pas de comparaison possible. Le JSON ci-dessous n'a pas été écrit dans le dépôt (consigne « ne rien modifier ») ; il est fourni à part.
- `CHANGELOG.md:9` (`## 1.4.0` vide) est lu comme la trace de l'incident cité à `AGENTS.md:20`, hypothèse non confirmée.

## 7. Données machine

Voir le fichier JSON joint (`blind-python-cli.json`), reproduit à l'identique ci-dessous.

```json
{
  "audit": {
    "process": "release de piloto (CLI Python publiée sur PyPI)",
    "scope": "fixtures/repos/python-cli/repo/ : AGENTS.md, CLAUDE.md, .github/copilot-instructions.md, src/piloto/AGENTS.md, .claude/skills/release, .github/workflows, ruff.toml, .pre-commit-config.yaml, pyproject.toml, tests/, .harness/",
    "date": "2026-11-09",
    "health_score": 2,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 4 }
  },
  "elements": [
    {
      "id": "release-skill",
      "path": ".claude/skills/release/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["agents-md"],
      "calls": ["bump-version-script", "publish-sh", "release-yml"],
      "verdict": "SPLIT",
      "priority": "P1",
      "finding": "Le skill mêle jugement, procédure, chemins de scripts (dont un inexistant), déclenchement L4 par git push --tags sans point d'arrêt, et un jeton PyPI en clair qui contredit l'interdit de publier hors release.yml.",
      "evidence": [".claude/skills/release/SKILL.md:8", ".claude/skills/release/SKILL.md:10", ".claude/skills/release/SKILL.md:12", ".claude/skills/release/SKILL.md:13", ".claude/skills/release/SKILL.md:14", "AGENTS.md:26", "AGENTS.md:28"],
      "target": "Procédure pure : release plan (dry-run), PR de bump, release tag sur le commit fusionné, lecture de l'URL et du code de sortie du run release.yml ; étapes 6 et 7 supprimées.",
      "check": "Aucune occurrence de PYPI_TOKEN ou pypi- dans le skill ; chaque chemin cité existe ; release plan patch s'exécute sans agent et sans écrire."
    },
    {
      "id": "publish-sh",
      "path": ".claude/skills/release/scripts/publish.sh",
      "declared_layer": "L3",
      "actual_layer": "L4",
      "called_by": ["release-skill"],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "Publication PyPI depuis un poste avec un jeton long-vécu, sans environnement protégé ni OIDC : porte dérobée à la règle « publier uniquement par release.yml ».",
      "evidence": [".claude/skills/release/scripts/publish.sh:2", ".claude/skills/release/scripts/publish.sh:4", ".claude/skills/release/scripts/publish.sh:6", "AGENTS.md:26"],
      "target": "Supprimé ; l'échec de release.yml se traite par correction et workflow_dispatch dans l'environnement pypi, jamais par publication manuelle ; jetons d'API PyPI révoqués.",
      "check": "Fichier absent ; grep twine sur .claude et AGENTS.md vide ; aucun jeton d'API actif sur le projet PyPI."
    },
    {
      "id": "agents-md",
      "path": "AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["claude-md", "copilot-instructions"],
      "calls": ["release-skill", "docs-build-and-test", "ci-yml", "release-yml", "pre-commit-config", "test-version-single-source", "ruff-toml"],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Deux règles à incident racontées sans garde-fou (CHANGELOG, réseau), un garde-fou revendiqué qui ne tourne pas en pipeline (mypy en pre-commit), une règle de bruit (docstring), deux définitions de « fini » et une entrée « Lance » qui désigne un skill au lieu d'une commande.",
      "evidence": ["AGENTS.md:13", "AGENTS.md:18", "AGENTS.md:20", "AGENTS.md:21", "AGENTS.md:22", "AGENTS.md:23", "AGENTS.md:32", ".github/workflows/ci.yml:7"],
      "target": "Chaque « Vérifiée par » cite un job de ci.yml ou release.yml : job types (mypy), PR gate changelog, règle ruff banned-api sur subprocess ; ligne 22 supprimée, lignes 21 et 32 fusionnées, ligne 13 pointant sur la commande CLI.",
      "check": "Plus aucun « (non vérifiée) » dans le fichier et chaque garde-fou cité est exécuté par ci.yml ou release.yml."
    },
    {
      "id": "src-piloto-agents-md",
      "path": "src/piloto/AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P2",
      "finding": "Le fichier de dossier autorise le subprocess ssh direct que la racine interdit (incident #38) et dispense cli.py de tests en s'appuyant sur un test E2E jamais exécuté ; cli.py:36 viole déjà la règle.",
      "evidence": ["src/piloto/AGENTS.md:5", "src/piloto/AGENTS.md:6", "AGENTS.md:23", "src/piloto/cli.py:36", "tests/test_push_e2e.py:8", "pyproject.toml:17"],
      "target": "Supprimé ou réduit à un pointeur vers AGENTS.md ; la règle réseau devient une règle ruff banned-api (TID251) sur subprocess hors net.py ; cli.py:36 migré vers piloto.net en tâche séparée.",
      "check": "Fichier absent ou sans règle contradictoire ; ruff check . échoue sur import subprocess dans cli.py tant que la migration n'est pas faite."
    },
    {
      "id": "bump-version-script",
      "path": ".claude/skills/release/scripts/bump_version.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["release-skill"],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Logique L3 obligatoire (calcul et écriture de version, commit) sans test, sans dry-run, sans vérification d'arbre propre ni de tag existant ; git commit -am embarque tout ; regex dupliquée avec test_version_single_source ; appelé sous un faux chemin.",
      "evidence": [".claude/skills/release/scripts/bump_version.py:9", ".claude/skills/release/scripts/bump_version.py:13", ".claude/skills/release/scripts/bump_version.py:33", "tests/test_version_single_source.py:14", ".claude/skills/release/SKILL.md:12", "docs/agents/build-and-test.md:5"],
      "target": "Sous-commande testée release plan|bump|tag (tomllib, arbre propre, sur main, tag absent, section changelog présente, --dry-run) dans src/ avec tests dans tests/, puis suppression du script.",
      "check": "Tests de plan/bump/échecs verts dans ci.yml ; release plan patch n'écrit rien et sort 0 ; script supprimé."
    },
    {
      "id": "release-yml",
      "path": ".github/workflows/release.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": ["release-skill"],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Publication OIDC correcte mais sans aucune pré-condition : ni tests, ni cohérence tag/version, ni changelog, ni constat structuré, ni workflow_dispatch pour rejouer ; les pré-conditions racontées dans SKILL.md doivent descendre ici.",
      "evidence": [".github/workflows/release.yml:4", ".github/workflows/release.yml:9", ".github/workflows/release.yml:15", ".github/workflows/release.yml:16", ".claude/skills/release/SKILL.md:8", ".claude/skills/release/SKILL.md:12"],
      "target": "Job verify (ruff, mypy, pytest, tag == version pyproject, section ## <version> non vide) en needs de publish ; step de constat sur l'API JSON de PyPI ; workflow_dispatch avec tag et dry_run ; environnement pypi à relecteurs requis.",
      "check": "Un tag v9.9.9 sur un commit en 1.4.2 fait échouer verify sans atteindre publish ; le run expose version et URL en sortie."
    },
    {
      "id": "pre-commit-config",
      "path": ".pre-commit-config.yaml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": ["ruff-toml"],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Présenté comme le garde-fou de la règle mypy strict (incident #23), le hook est local et opt-in ; ci.yml ne lance jamais mypy, donc la règle n'est vérifiée par rien dans le pipeline.",
      "evidence": [".pre-commit-config.yaml:5", ".pre-commit-config.yaml:7", "AGENTS.md:18", ".github/workflows/ci.yml:7", ".github/workflows/ci.yml:18"],
      "target": "Garder le hook, ajouter le job types (uv run mypy src) dans ci.yml.",
      "check": "Une PR non typée dans src/piloto/ est rouge en CI sans pre-commit installé."
    },
    {
      "id": "test-push-e2e",
      "path": "tests/test_push_e2e.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Seul test de cli.py, désélectionné par addopts et exécuté nulle part (ni CI, ni release, ni skill), alors que src/piloto/AGENTS.md s'appuie dessus ; addopts -x --maxfail=1 masque en plus les échecs suivants.",
      "evidence": ["tests/test_push_e2e.py:6", "tests/test_push_e2e.py:8", "pyproject.toml:17", "src/piloto/AGENTS.md:6"],
      "target": "Job e2e dans ci.yml avec service sshd et pytest -m slow, ou suppression datée ; retirer -x --maxfail=1 des addopts.",
      "check": "Le log CI affiche 1 passed pour test_push_against_local_sshd, ou le fichier est absent ; addopts sans -x."
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
      "finding": "Une ligne @AGENTS.md, sans duplication.",
      "evidence": ["CLAUDE.md:1"],
      "target": "Inchangé.",
      "check": "Le fichier reste une seule ligne d'inclusion."
    },
    {
      "id": "copilot-instructions",
      "path": ".github/copilot-instructions.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["agents-md"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Pointeur vers AGENTS.md sans règle propre.",
      "evidence": [".github/copilot-instructions.md:1"],
      "target": "Inchangé.",
      "check": "Aucune règle n'y est ajoutée."
    },
    {
      "id": "docs-build-and-test",
      "path": "docs/agents/build-and-test.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["agents-md"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Référence de commandes chargée à la demande, cohérente avec pyproject.toml.",
      "evidence": ["docs/agents/build-and-test.md:3", "docs/agents/build-and-test.md:6", "AGENTS.md:6"],
      "target": "Inchangé.",
      "check": "Les commandes citées existent toujours."
    },
    {
      "id": "ci-yml",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["ruff-toml", "pyproject-toml", "test-version-single-source", "test-net"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Lint et tests sur PR et main ; point d'accueil des jobs types, e2e et changelog recommandés ailleurs.",
      "evidence": [".github/workflows/ci.yml:3", ".github/workflows/ci.yml:12", ".github/workflows/ci.yml:18"],
      "target": "Structure inchangée, jobs ajoutés par les remédiations 2, 3, 6, 7.",
      "check": "Les jobs lint et tests restent requis sur PR."
    },
    {
      "id": "ruff-toml",
      "path": "ruff.toml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "pre-commit-config"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Sélection E, F, I, B exécutée en CI ; accueillera la règle banned-api sur subprocess.",
      "evidence": ["ruff.toml:3", ".github/workflows/ci.yml:12"],
      "target": "Ajout de [lint.flake8-tidy-imports.banned-api] par la remédiation 5.",
      "check": "ruff check . reste exécuté par ci.yml."
    },
    {
      "id": "pyproject-toml",
      "path": "pyproject.toml",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml", "bump-version-script", "test-version-single-source"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Source unique de la version et config mypy strict ; seul addopts est à alléger, traité avec test-push-e2e.",
      "evidence": ["pyproject.toml:3", "pyproject.toml:17", "pyproject.toml:21"],
      "target": "Inchangé hormis addopts.",
      "check": "Une seule ligne version ; [tool.mypy] strict conservé."
    },
    {
      "id": "test-version-single-source",
      "path": "tests/test_version_single_source.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": ["pyproject-toml"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Garde-fou réel d'une règle à incident (#31), exécuté en CI.",
      "evidence": ["tests/test_version_single_source.py:6", "tests/test_version_single_source.py:12", ".github/workflows/ci.yml:18"],
      "target": "Inchangé ; modèle pour la règle réseau.",
      "check": "Toujours collecté par uv run pytest."
    },
    {
      "id": "test-net",
      "path": "tests/test_net.py",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["ci-yml"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Borne DEFAULT_TIMEOUT, exécuté en CI ; ne couvre pas le subprocess de cli.py.",
      "evidence": ["tests/test_net.py:4", "tests/test_net.py:5"],
      "target": "Inchangé.",
      "check": "Toujours collecté par uv run pytest."
    },
    {
      "id": "harness-harvest",
      "path": ".harness/harvest.json",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Le signal S1 (timeout explicite, jamais subprocess ssh nu) a produit la règle AGENTS.md:23 mais related_rule est resté null, aucun garde-fou n'a suivi et cli.py:36 viole toujours la règle ; six S5 marquent des règles sans incident, dont la règle docstring.",
      "evidence": [".harness/harvest.json:20", ".harness/harvest.json:21", ".harness/harvest.json:29", "AGENTS.md:23", "AGENTS.md:42", "src/piloto/cli.py:36"],
      "target": "Lier S1 à la règle, le clore quand la règle ruff existe ; écrire .harness/audit.json depuis ce rapport.",
      "check": "harness status montre la règle réseau comme gardée."
    }
  ],
  "process_leaks": [
    { "rule": "main doit être vert avant de releaser", "told_in": ".claude/skills/release/SKILL.md:8", "if_skipped": "Un tag posé sur un commit rouge publie sur PyPI, irréversible.", "belongs_in": "L4", "guard_tool": "job verify (ruff, mypy, pytest) en needs de publish dans release.yml" },
    { "rule": "Le tag v<x> correspond à la version de pyproject.toml", "told_in": ".claude/skills/release/SKILL.md:12", "if_skipped": "Le chemin scripts/bump_version.py n'existe pas : git tag v (vide) ou tag décalé ; release.yml publie quand même (v*).", "belongs_in": "L4", "guard_tool": "step verify dans release.yml comparant GITHUB_REF_NAME à la version pyproject ; sous-commande release tag" },
    { "rule": "CHANGELOG.md a une section non vide pour la version publiée", "told_in": "AGENTS.md:20", "if_skipped": "Nouvelle release avec changelog vide, comme la 1.4 (CHANGELOG.md:9 encore vide).", "belongs_in": "L4", "guard_tool": "job verify dans release.yml (section ## <version> non vide) et PR gate changelog dans ci.yml avec label d'exemption" },
    { "rule": "Publier sur PyPI uniquement par release.yml sur un tag", "told_in": "AGENTS.md:26", "if_skipped": "SKILL.md:13 et publish.sh publient depuis un poste avec un jeton long-vécu, hors audit et hors environnement protégé.", "belongs_in": "L4", "guard_tool": "suppression de publish.sh ; trusted publisher seul côté PyPI ; environnement pypi à relecteurs requis" },
    { "rule": "La version publiée est constatée sur PyPI", "told_in": ".claude/skills/release/SKILL.md:14", "if_skipped": "Succès halluciné si la publication a échoué : lecture humaine d'une page web.", "belongs_in": "L4", "guard_tool": "step final de release.yml interrogeant https://pypi.org/pypi/piloto/<version>/json avec exit 1" },
    { "rule": "Tout code est typé et passe mypy en strict", "told_in": "AGENTS.md:18", "if_skipped": "Le hook pre-commit est local et opt-in ; ci.yml ne lance pas mypy : une PR non typée passe verte (incident #23 reproductible).", "belongs_in": "L4", "guard_tool": "job types (uv run mypy src) dans ci.yml" },
    { "rule": "Les appels réseau passent par piloto.net, jamais par subprocess direct", "told_in": "AGENTS.md:23", "if_skipped": "ssh sans timeout bloque la CI ou le poste (#38) ; cli.py:36 le fait déjà et src/piloto/AGENTS.md:5 l'autorise.", "belongs_in": "L3", "guard_tool": "ruff flake8-tidy-imports banned-api (TID251) sur subprocess avec per-file-ignores pour src/piloto/net.py, ou test miroir de test_version_single_source.py" },
    { "rule": "Pousser sur main sans PR est interdit ; le commit de release doit atteindre main", "told_in": "AGENTS.md:28", "if_skipped": "SKILL.md:10-12 commite localement sur main et ne pousse que les tags : tag sur un commit absent de main, main sans le bump.", "belongs_in": "L4", "guard_tool": "protection de branche main ; bump par PR ; tag posé sur le commit fusionné par release tag" },
    { "rule": "cli.py est couvert par les tests E2E de la release", "told_in": "src/piloto/AGENTS.md:6", "if_skipped": "tests/test_push_e2e.py est désélectionné par pyproject.toml:17 et exécuté nulle part : cli.py n'a aucun test.", "belongs_in": "L4", "guard_tool": "job e2e dans ci.yml avec service sshd et pytest -m slow" }
  ],
  "guarded_rules": [
    { "rule": "Le style suit ruff", "told_in": "AGENTS.md:17", "guarded_by": "ruff.toml via .github/workflows/ci.yml:12" },
    { "rule": "La version n'existe qu'à un endroit, pyproject.toml", "told_in": "AGENTS.md:19", "guarded_by": "tests/test_version_single_source.py via .github/workflows/ci.yml:18" },
    { "rule": "Une tâche est finie quand pytest passe", "told_in": "AGENTS.md:21", "guarded_by": ".github/workflows/ci.yml:18 (avec -k 'not slow' et -x de pyproject.toml:17)" },
    { "rule": "La publication se fait par OIDC dans un environnement, sans secret stocké", "told_in": "AGENTS.md:26", "guarded_by": ".github/workflows/release.yml:5-7,11 (règles de protection de l'environnement non visibles)" },
    { "rule": "Le timeout réseau par défaut est borné", "told_in": "src/piloto/net.py:1", "guarded_by": "tests/test_net.py:4-5 via .github/workflows/ci.yml:18" }
  ],
  "instruction_files": [
    { "path": "AGENTS.md", "loaded_lines": 43, "instruction_pct": 70, "reference_pct": 20, "noise_pct": 10, "justified_rules": true, "maintenance_clause": true },
    { "path": "CLAUDE.md", "loaded_lines": 43, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": ".github/copilot-instructions.md", "loaded_lines": 1, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false },
    { "path": "src/piloto/AGENTS.md", "loaded_lines": 6, "instruction_pct": 0, "reference_pct": 0, "noise_pct": 100, "justified_rules": false, "maintenance_clause": false },
    { "path": "docs/agents/build-and-test.md", "loaded_lines": 7, "instruction_pct": 0, "reference_pct": 100, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "publish-sh", "action": "Révoquer le jeton PyPI côté pypi.org, supprimer la ligne 13 de SKILL.md et .claude/skills/release/scripts/publish.sh, vérifier que le projet PyPI n'a que le trusted publisher.", "depends_on": [], "check": "grep de pypi- et twine sur .claude et AGENTS.md vide ; aucun jeton d'API actif sur PyPI.", "needs_human_approval": true },
    { "order": 2, "priority": "P2", "verdict": "PUSH_DOWN", "element": "release-yml", "action": "Ajouter le job verify (ruff, mypy, pytest, tag == version, section changelog) en needs de publish, un step de constat sur l'API JSON de PyPI, workflow_dispatch avec tag et dry_run ; confirmer les relecteurs requis sur l'environnement pypi.", "depends_on": [1], "check": "Un tag incohérent rend le run rouge avant publish ; la sortie du job porte version et URL.", "needs_human_approval": true },
    { "order": 3, "priority": "P2", "verdict": "PUSH_DOWN", "element": "pre-commit-config", "action": "Ajouter le job types (uv run mypy src) dans ci.yml en gardant le hook local.", "depends_on": [], "check": "Une PR non typée est rouge en CI sans pre-commit installé.", "needs_human_approval": false },
    { "order": 4, "priority": "P2", "verdict": "PUSH_DOWN", "element": "bump-version-script", "action": "Créer la sous-commande testée release plan|bump|tag (tomllib, arbre propre, tag absent, section changelog, --dry-run) avec ses tests dans tests/, puis supprimer le script.", "depends_on": [], "check": "Tests verts dans ci.yml ; release plan patch n'écrit rien ; script absent.", "needs_human_approval": true },
    { "order": 5, "priority": "P2", "verdict": "BLOCK", "element": "src-piloto-agents-md", "action": "Supprimer le fichier ou le réduire à un pointeur ; ajouter dans ruff.toml la règle banned-api sur subprocess avec exemption pour net.py ; ouvrir une tâche pour migrer cli.py:36 vers piloto.net.", "depends_on": [], "check": "ruff check . signale cli.py:5 tant que la migration n'est pas faite ; fichier absent.", "needs_human_approval": true },
    { "order": 6, "priority": "P2", "verdict": "PUSH_DOWN", "element": "test-push-e2e", "action": "Ajouter le job e2e dans ci.yml avec un service sshd et pytest -m slow, ou supprimer le test avec commentaire daté ; retirer -x --maxfail=1 de pyproject.toml.", "depends_on": [3], "check": "Log CI avec 1 passed pour le test, ou fichier absent ; addopts sans -x.", "needs_human_approval": true },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Ajouter le job changelog (PR gate avec label d'exemption) dans ci.yml ; réécrire les lignes 13, 18, 20, 23, fusionner 21 dans 32, supprimer ou réduire 22.", "depends_on": [2, 3, 4, 5], "check": "Plus aucun « (non vérifiée) » ; chaque « Vérifiée par » cite un job de ci.yml ou release.yml.", "needs_human_approval": false },
    { "order": 8, "priority": "P1", "verdict": "SPLIT", "element": "release-skill", "action": "Réécrire le skill en procédure pure autour de release plan, PR de bump, release tag et lecture du run ; corriger tous les chemins ; supprimer les étapes 6 et 7.", "depends_on": [1, 2, 4], "check": "Chaque commande citée existe ; essai à blanc sans agent ; aucun secret.", "needs_human_approval": false },
    { "order": 9, "priority": "P3", "verdict": "KEEP", "element": "harness-harvest", "action": "Lier le signal S1 à la règle AGENTS.md:23 et le clore quand la règle ruff existe ; écrire .harness/audit.json à partir de ce rapport.", "depends_on": [5], "check": "harness status montre la règle réseau comme gardée.", "needs_human_approval": false }
  ],
  "unverified": [
    "Règles de protection de l'environnement GitHub pypi (relecteurs requis) et protection de branche de main : hors dépôt.",
    "Côté PyPI : existence d'autres jetons d'API actifs et validité du jeton écrit à .claude/skills/release/SKILL.md:13 (valeur non recopiée, non testée).",
    "Historique git non consulté : ancienneté du jeton dans l'historique et besoin de purge non établis.",
    "Aucun test ni workflow exécuté ; uv run ruff check . lint vraisemblablement .claude/ (pas d'exclusion dans ruff.toml), non confirmé.",
    ".harness/audit.json absent : premier audit, pas de comparaison ; le JSON n'a pas été écrit dans le dépôt (consigne de ne rien modifier).",
    "CHANGELOG.md:9 (## 1.4.0 vide) lu comme la trace de l'incident cité à AGENTS.md:20, hypothèse non confirmée."
  ]
}
```
