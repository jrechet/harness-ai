# Audit du harness — shopfront : ajout de composant et traduction automatisée

**Périmètre** : `fixtures/repos/node-front/repo/` (AGENTS.md, CLAUDE.md, `.cursor/rules`, `.github/copilot-instructions.md`, `.claude/skills/`, `scripts/`, `tools/`, `.github/workflows/`, eslint/stylelint/husky/vitest, `package.json`) · **Date** : 2026-11-09 · **Éléments inventoriés** : 17

## 1. Synthèse

- **Score de santé** : 0 — l'agent n'est pas un accélérateur mais un pilier : trois règles obligatoires (chaînes traduites, story + test par composant, couverture) et une interdiction de sécurité (module PCI) ne vivent que dans des prompts, deux des trois mentions « Vérifiée par » d'AGENTS.md sont fausses, et un workflow laisse un agent écrire puis fusionner seul dans `main`. Déduction brute : 102 points (2 × P1, 6 × P2, 2 × P3), bornée à 0 ; le test « coupe l'agent » en échec plafonnait de toute façon à 60.
- **Résultat du test « coupe l'agent »** : ÉCHEC — 7 étape(s) du processus n'existent que dans des prompts.
- **Points bloquants (P1)** : 2
- **Les trois actions qui changent le plus les choses** :
  1. Neutraliser `agent-fix-i18n.yml` (`.github/workflows/agent-fix-i18n.yml:18-23`) : retirer l'auto-merge, restreindre `Edit` à `src/locales/en.json`, ajouter un input `dry_run`, cibler la PR réellement créée au lieu de `.[0]`.
  2. Rendre vraie la phrase « Vérifiée par `scripts/check-i18n.mjs` » (`AGENTS.md:18`) : ajouter `@intlify/eslint-plugin-vue-i18n` (`vue-i18n/no-raw-text`) dans `eslint.config.js` — aujourd'hui `src/components/NewBadge.vue:6` livre « Nouveau » en dur et passe tous les jobs CI.
  3. Mettre `src/payment/` et `src/styles/tokens.css` sous `.github/CODEOWNERS` + revue obligatoire : les deux interdits (`AGENTS.md:27`, `AGENTS.md:29`) n'ont aujourd'hui aucun garde-fou, et l'agent du workflow ci-dessus peut les éditer.

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md | `AGENTS.md` | L2 | L2 | CLAUDE.md (include), sessions agent | skill add-component, scripts npm, eslint-plugin-design-tokens, stylelint, check-i18n, ci.yml |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2 | Claude Code | AGENTS.md (`@AGENTS.md`) |
| 3 | Règles Cursor | `.cursor/rules/vue.mdc` | L2 | L2 | Cursor (`alwaysApply: true`) | — |
| 4 | Instructions Copilot | `.github/copilot-instructions.md` | L2 | L2 | Copilot | `npm test` (script inexistant) |
| 5 | Skill add-component | `.claude/skills/add-component/SKILL.md` | L2 | MIXED (procédure + vérification manuelle de couverture) | AGENTS.md:37, Claude Code | scripts npm (`check:i18n`, `lint`, `test:unit`), rapport de couverture |
| 6 | check-i18n | `scripts/check-i18n.mjs` | L3 | L3 | `package.json:12`, `ci.yml:25` | — |
| 7 | i18n-report | `scripts/i18n-report.mjs` | L3 | L3 | `agent-fix-i18n.yml:15` | — |
| 8 | legacy-theme-migrate | `scripts/legacy-theme-migrate.js` | L3 | L3 (mort) | personne | — |
| 9 | eslint-plugin-design-tokens | `tools/eslint-plugin-design-tokens/index.js` | L3 | L3 (périmètre réel : `<script>` seulement) | `eslint.config.js:2,8` | — |
| 10 | Config eslint | `eslint.config.js` | L3 | L3 | `npm run lint` (`package.json:8`), husky, ci.yml:11 | eslint-plugin-design-tokens, eslint-plugin-vue |
| 11 | Config stylelint | `.stylelintrc.json` | L3 | L3 | `npm run lint:style` (`package.json:9`), ci.yml:12 | stylelint-config-standard (absent des devDependencies) |
| 12 | Hook pre-commit | `.husky/pre-commit` | L3 | L3 (mort : husky non installé) | personne | `npm run lint` |
| 13 | Scripts npm (CLI du repo) | `package.json:5-16` | L3 | L3 | AGENTS.md, skill, ci.yml, deploy-preview.yml, copilot | eslint, stylelint, vitest, playwright, check-i18n, size-limit |
| 14 | Config vitest | `vitest.config.ts` | L3 | L3 | `npm run test:unit` | — |
| 15 | Workflow ci | `.github/workflows/ci.yml` | L4 | L4 | push / pull_request | scripts npm, check-i18n, size-limit |
| 16 | Workflow agent-fix-i18n | `.github/workflows/agent-fix-i18n.yml` | L4 | MIXED (L1 agent + L3 script + L4 merge) | cron quotidien, `workflow_dispatch` | i18n-report, `@anthropic-ai/claude-code`, `gh pr merge --auto` |
| 17 | Workflow deploy-preview | `.github/workflows/deploy-preview.yml` | L4 | L4 | pull_request | `npm run build`, netlify, `gh pr comment` |

Processus nominal A — ajouter un composant :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| Créer `src/components/<Nom>.vue` en `<script setup lang="ts">` | L2 (`SKILL.md:8`, `AGENTS.md:32`) | Oui — `vue/component-api-style: script-setup` (`eslint.config.js:11`), job lint (`ci.yml:11`) | n/a |
| Pas de couleur en dur | L2 (`AGENTS.md:17`) | Partiel — eslint `no-raw-color` ne voit que les littéraux du `<script>` (`tools/eslint-plugin-design-tokens/index.js:11`) ; stylelint couvre `<style>` si la config tourne (`.stylelintrc.json:1`) ; le template n'est pas couvert | n/a |
| Ajouter la story `<Nom>.stories.ts` | L2 seulement (`SKILL.md:9`, contredit par `AGENTS.md:33`, `vue.mdc:7`, `copilot-instructions.md:5`) | Non — `NewBadge.vue` sans story passe la CI | n/a |
| Ajouter le test `<Nom>.spec.ts` | L2 seulement (`SKILL.md:10`, `AGENTS.md:20`) | Non — `NewBadge.vue` sans spec passe la CI | n/a |
| Clés i18n dans les deux locales | L2 + L3 (`SKILL.md:11`, `scripts/check-i18n.mjs`) | Parité fr/en oui (`check-i18n.mjs:13-15`, `ci.yml:25`) ; usage de `t()` non (`check-i18n.mjs:2`) | n/a |
| `npm run lint && npm run test:unit` | L3/L4 (`package.json:8,10`, `ci.yml:11,20`) | Oui | n/a |
| La couverture ne baisse pas | L2 seulement, à l'œil (`SKILL.md:13`, `AGENTS.md:21`) | Non — pas de `thresholds` (`vitest.config.ts:3`), pas de diff en CI | n/a |
| Bundle < 250 kB gzip | L3/L4 (`package.json:16`, `ci.yml:33`) | Oui — `size-limit` | n/a |
| PR avec capture de la story | L2 (`SKILL.md:14`) | Non (pas de template de PR) | n/a |
| Preview déployée et commentée sur la PR | L4 (`deploy-preview.yml:13-15`) | Oui — sortie `--json`, `environment: preview` | Environnement protégé, pas de dry-run (acceptable : preview) |

Processus nominal B — traduction automatisée (`agent-fix-i18n.yml`) :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| Détecter les clés fr absentes d'en | L3 (`scripts/i18n-report.mjs`, `agent-fix-i18n.yml:15`) | Oui — sortie JSON structurée | n/a |
| Traduire les clés | L1 (agent, `agent-fix-i18n.yml:18`) | Non, et c'est normal (jugement) — mais aucun contrôle qualité en aval | Non |
| Modifier uniquement `src/locales/en.json` | L2 (le prompt, `agent-fix-i18n.yml:18`) | Non — `--allowedTools "Edit,Bash(git *)"` sans restriction de chemin (`:19`) | Non |
| Ouvrir une PR | L1 via `gh pr create` (`agent-fix-i18n.yml:19`) | Non | Non |
| Revue humaine | absente | Non — contredit `AGENTS.md:3` (« l'humain relit chaque diff ») | — |
| Fusion dans `main` | L4 `gh pr merge --auto --squash` sur `gh pr list --author app/acme-bot … .[0]` (`agent-fix-i18n.yml:22`) | Non — la seule CI pertinente (parité de clés) passe par construction après l'ajout des clés ; la PR ciblée n'est pas forcément celle qui vient d'être créée | Non — `workflow_dispatch` sans input (`agent-fix-i18n.yml:5`) |

## 3. Fuites : règles et étapes racontées sans vérification

| Règle / étape | Racontée en | Si l'agent la saute | Doit vivre en | Outil cible |
|---|---|---|---|---|
| Toute chaîne visible passe par `t()`, jamais de texte en dur dans un template | `AGENTS.md:18` (prétend « Vérifiée par `scripts/check-i18n.mjs` », faux : `scripts/check-i18n.mjs:2` « Ne regarde pas les templates ») ; contredit par `.github/copilot-instructions.md:6` | Texte non traduit en production — incident #198 déjà arrivé ; preuve vivante : `src/components/NewBadge.vue:6` (« Nouveau » en dur) passe tous les jobs de `ci.yml` | L3 | `@intlify/eslint-plugin-vue-i18n` règles `vue-i18n/no-raw-text` et `vue-i18n/no-missing-keys` dans `eslint.config.js`, job lint existant |
| Un composant a une story Storybook | `AGENTS.md:20` (obligatoire), `SKILL.md:9` (obligatoire même sans UI), mais `AGENTS.md:33` (optionnel sans UI), `.cursor/rules/vue.mdc:7` (facultative), `.github/copilot-instructions.md:5` (optional) — quatre réponses | Composant jamais relu visuellement ; `src/components/NewBadge.vue` n'a pas de story | L3 | Script `scripts/check-components.mjs` (glob `src/components/*.vue` → exige `.stories.ts` et `.spec.ts`, `exit 1`) ou test vitest équivalent, branché dans `ci.yml` |
| Un composant a un test unitaire | `AGENTS.md:20`, `SKILL.md:10`, `vue.mdc:7`, `copilot-instructions.md:5` | Composant non testé ; `NewBadge.vue` n'a pas de spec et la CI est verte | L3 | Même script que ci-dessus |
| La couverture unitaire ne baisse pas | `AGENTS.md:21` ; vérification manuelle à l'œil `SKILL.md:13` (« ouvre `coverage/index.html` ») | Perte silencieuse de tests — incident #240 ; `vitest.config.ts:3` n'a ni `thresholds` ni reporter `json-summary`, `ci.yml:20` ne compare rien | L3/L4 | `coverage.thresholds` (+ `thresholds.autoUpdate`) dans `vitest.config.ts`, ou action de diff de couverture vs `main` en PR gate |
| Ne jamais toucher `src/payment/` (module PCI) | `AGENTS.md:29`, `.cursor/rules/vue.mdc:8`, `.github/copilot-instructions.md:6` | Modification d'un module PCI sans revue propriétaire ; l'agent de `agent-fix-i18n.yml:19` a `Edit` sans restriction de chemin et auto-merge | L4 | `.github/CODEOWNERS` (`src/payment/ @owners`) + revue requise par la protection de branche ; `Edit(src/locales/en.json)` dans le workflow |
| Ne jamais modifier `src/styles/tokens.css` sans ticket design | `AGENTS.md:27` | Dérive du thème sans validation design | L4 | `.github/CODEOWNERS` (`src/styles/tokens.css @design`) + template de PR demandant le ticket |
| Pas de couleur en dur dans le template (attribut `style`, `:style`, classes inline) | `AGENTS.md:17` (prétend couverte par `no-raw-color`), `tools/eslint-plugin-design-tokens/index.js:1-2` (prétend « templates et styles inline ») | Hex oublié dans un template → thème sombre cassé (incident #212, trois fois) ; le visiteur `Literal` (`index.js:11`) n'est appelé que sur le `<script>`, pas sur l'AST template de vue-eslint-parser | L3 | Réécrire la règle avec `context.parserServices.defineTemplateBodyVisitor` (nœuds `VLiteral`/`Literal` du template) + `RuleTester` ; stylelint avec `customSyntax: postcss-html` pour `<style>` et attributs `style` |
| Pas d'`eslint-disable` sans justification datée | `AGENTS.md:28` | Règles contournées silencieusement (hygiène, P3) | L3 | `@eslint-community/eslint-plugin-eslint-comments` règle `require-description` |
| Revue humaine de chaque diff | `AGENTS.md:3` | Traductions hallucinées fusionnées dans `main` sans relecture (`agent-fix-i18n.yml:21-23`) | L4 | Supprimer l'étape auto-merge ; `environment:` protégé avec reviewers requis ; protection de branche |

Règles qui **ont** leur garde-fou (partie saine, raccourcissable dans AGENTS.md) :

- Composition API `<script setup>` uniquement (`AGENTS.md:19`) — `vue/component-api-style: ["error", ["script-setup"]]` (`eslint.config.js:11`), job lint `ci.yml:11`. Le « Pourquoi » peut rester, le reste devient un pointeur vers le linter.
- Bundle initial < 250 kB (`AGENTS.md:22`) — `size-limit` `package.json:16` + `npx size-limit` `ci.yml:33`. Claim exact.
- Parité des clés fr/en (`AGENTS.md:13`, `SKILL.md:11`) — `scripts/check-i18n.mjs:13-15` (`exit 1`, message typé) + `ci.yml:25`. C'est la seule partie vraie du « Vérifiée par » de la ligne 18.
- Pas de couleur en dur dans le `<script>` et les fichiers `.css` (`AGENTS.md:17`) — `design-tokens/no-raw-color` (`eslint.config.js:10`, `tools/eslint-plugin-design-tokens/index.js:11-13`) et `color-no-hex` + `function-disallowed-list` (`.stylelintrc.json:1`). Garde partielle, voir fuite ci-dessus et constat sur `.stylelintrc.json`.
- Table « Si tu touches… → Vérifié en CI par » (`AGENTS.md:9-14`) — exacte : jobs `lint` (`ci.yml:4-12`), `unit` (`:13-20`), `i18n` (`:21-25`), `e2e` (`:34-41`).

## 3b. Coût de contexte

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| `CLAUDE.md` → `AGENTS.md` | 45 (1 + 44) | ~45 % instruction (l.16-29, 39-42) / ~45 % référence (l.5-14 table des commandes, l.31-37 procédure dupliquée du skill, l.44 marqueur) / ~10 % bruit (l.23-24 : PascalCase, `const`) | Chaque session Claude Code |
| `.cursor/rules/vue.mdc` | 8 | 100 % instruction, dont 3 lignes contredisent AGENTS.md et le linter (l.5-7) | Chaque session Cursor (`alwaysApply: true`, l.3) |
| `.github/copilot-instructions.md` | 8 | ~85 % instruction / ~15 % référence (l.7, commande `npm test` inexistante) ; 4 lignes contredisent AGENTS.md (l.3-6) | Chaque session Copilot |
| `.claude/skills/add-component/SKILL.md` | 14 | 100 % procédure (sa place), dont l'étape 6 est une vérification à l'œil qui devrait être du code | À la demande (déclencheur de la description) |

Justification : point fort net d'`AGENTS.md` — six règles sur huit expliquent *pourquoi* et quatre citent l'incident ou l'issue (#212 l.17, #198 l.18, #240 l.21, PR #231 l.44) ; `vue.mdc` et `copilot-instructions.md` ne justifient rien. Clause de maintenance présente et précise (`AGENTS.md:39-42` : commentaires `rule:`, « chercher un garde-fou avant d'ajouter une phrase », marqueur harvest l.44) ; absente des deux autres fichiers, qui ont donc dérivé.

## 4. Constats par élément

### [BLOCK] [P1] Workflow agent-fix-i18n — `.github/workflows/agent-fix-i18n.yml`
- **Fait aujourd'hui** : chaque jour ouvré à 6h (l.3-4) ou à la main (l.5), liste les clés manquantes (l.15), lance `claude-code -p` pour les traduire et ouvrir une PR avec `--allowedTools "Edit,Bash(git *),Bash(gh pr create*)"` (l.18-19), puis `gh pr merge --auto --squash` sur la première PR de `app/acme-bot` (l.22).
- **Problème** : (1) l'agent fusionne seul dans `main` sans relecture humaine, ce qui contredit `AGENTS.md:3` ; la seule CI qui regarde les locales (`ci.yml:25`) vérifie la parité des clés, satisfaite par construction dès que l'agent ajoute les clés — une traduction hallucinée est verte. (2) `Edit` et `Bash(git *)` ne sont pas restreints (l.19) : l'agent peut toucher `src/payment/`, `tokens.css`, les workflows, et `git push --force`. (3) `gh pr list … --jq '.[0].number'` (l.22) cible la PR la plus récente du bot, pas celle qui vient d'être créée ; si aucune n'existe, la commande échoue ou fusionne une PR sans rapport. (4) Aucun input `dry_run`, aucun `environment:` protégé sur le `workflow_dispatch` (l.5) alors que deux secrets sont exposés (l.20, l.23). (5) Le script tourne même si `missing.json` est `[]` : l'agent est appelé pour rien. (6) Incohérence de processus : `ci.yml:25` bloque déjà toute PR qui introduit des clés manquantes, donc l'état que ce workflow répare ne devrait pas pouvoir exister sur `main` — soit la CI est contournée, soit le workflow est inutile.
- **Doit devenir** : L4 prépare (`i18n report --json`, court-circuit si vide) ; L1 traduit et ouvre une PR **brouillon** avec `--allowedTools "Edit(src/locales/en.json),Bash(gh pr create*)"` ; la fusion repasse par un humain (reviewers requis, pas d'auto-merge) ; input `dry_run` qui s'arrête à l'artefact `missing.json` ; la PR est identifiée par l'URL retournée par `gh pr create`, pas par `.[0]`.
- **Critère de vérification** : plus aucune occurrence de `pr merge --auto` dans le workflow ; `allowedTools` restreint au fichier cible ; un `workflow_dispatch` avec `dry_run=true` produit l'artefact et aucune PR ; un run réel produit une PR en brouillon non fusionnable sans approbation.

### [PUSH_DOWN] [P1] AGENTS.md — `AGENTS.md`
- **Fait aujourd'hui** : 44 lignes, bien justifiées (incidents cités), avec table des commandes par type de changement (l.9-14), huit règles (l.17-24), trois interdits (l.27-29), une procédure d'ajout de composant (l.31-37) et une clause de maintenance (l.39-42).
- **Problème** : deux des trois « Vérifiée par » sont inexacts : l.18 attribue la règle « toute chaîne passe par `t()` » à `scripts/check-i18n.mjs`, qui ne lit que les deux JSON (`scripts/check-i18n.mjs:2,9-10`) — `src/components/NewBadge.vue:6` le prouve ; l.17 attribue « pas de couleur en dur » à `no-raw-color`, qui ne visite pas le template (`tools/eslint-plugin-design-tokens/index.js:11`). Les règles l.20 (story + test), l.21 (couverture), l.27 (`tokens.css`), l.28 (`eslint-disable`) et l.29 (`src/payment/`, PCI) n'ont aucun garde-fou. Contradiction interne : l.20 rend la story obligatoire, l.33 la rend optionnelle, et `SKILL.md:9` la rend obligatoire « même sans UI ». L.31-37 duplique la procédure du skill vers lequel l.37 renvoie. L.3 affirme un mode « assistance, l'humain relit chaque diff » alors que `agent-fix-i18n.yml:22` fusionne sans humain. L.23-24 sont du bruit qu'un modèle récent applique seul.
- **Doit devenir** : chaque règle obligatoire pointe vers un garde-fou réel (voir §3) et la phrase « Vérifiée par » n'est écrite que quand c'est vrai ; l.31-37 remplacées par le seul pointeur vers le skill ; une seule position sur la story, tranchée et alignée avec le script de vérification ; l.23-24 supprimées ; l.3 mentionne le workflow autonome et son périmètre.
- **Critère de vérification** : pour chaque « Vérifiée par », un test rouge volontaire (texte en dur dans un template, composant sans story, hex dans un `:style`) fait échouer `ci.yml` ; `grep -c "story" AGENTS.md .claude/skills/add-component/SKILL.md .cursor/rules/vue.mdc .github/copilot-instructions.md` renvoie une seule formulation.

### [MERGE] [P2] Règles Cursor — `.cursor/rules/vue.mdc`
- **Fait aujourd'hui** : 4 règles chargées à chaque session Cursor (`alwaysApply: true`, l.3).
- **Problème** : trois contredisent AGENTS.md et le code : l.5 autorise l'Options API sous 50 lignes alors que `eslint.config.js:11` la refuse partout (`vue/component-api-style: script-setup`) — l'agent Cursor produit du code que le job lint rejette ; l.6 tolère un hex « avec `// TODO token` » alors que `AGENTS.md:17` l'interdit et que stylelint le refuse ; l.7 rend la story facultative contre `AGENTS.md:20` et `SKILL.md:9`. Aucun « pourquoi », pas de clause de maintenance.
- **Doit devenir** : un fichier réduit à un pointeur vers `AGENTS.md` (ou généré depuis lui), sans règle propre.
- **Critère de vérification** : `vue.mdc` ne contient plus de règle contredisant une règle eslint/stylelint active ; une seule source de vérité pour story, Options API et couleurs.

### [MERGE] [P2] Instructions Copilot — `.github/copilot-instructions.md`
- **Fait aujourd'hui** : 6 consignes en anglais chargées par Copilot.
- **Problème** : l.3 (Options API « fine ») contredit `eslint.config.js:11` ; l.4 (hex « acceptable in one-off overrides ») contredit `AGENTS.md:17` et `.stylelintrc.json:1` ; l.5 (story optionnelle) contredit `AGENTS.md:20` ; l.6 (« hardcoded strings acceptable in admin pages ») ouvre une exception à la règle i18n (`AGENTS.md:18`) qui n'existe nulle part ailleurs ; l.7 fait lancer `npm test`, script absent de `package.json:5-14` (seuls `test:unit` et `test:e2e` existent) — l'agent copiera fidèlement une commande qui échoue.
- **Doit devenir** : pointeur vers `AGENTS.md` (ou contenu généré), commandes reprises de la table `AGENTS.md:9-14`.
- **Critère de vérification** : toute commande citée existe dans `package.json` ; plus aucune exception à une règle d'AGENTS.md.

### [PUSH_DOWN] [P2] Skill add-component — `.claude/skills/add-component/SKILL.md`
- **Fait aujourd'hui** : 7 étapes de procédure pour ajouter un composant (l.8-14), bon déclencheur, bonne couche pour les étapes 1-5 et 7.
- **Problème** : l'étape 6 (l.13) demande à l'agent d'ouvrir `coverage/index.html` et de comparer à l'œil le pourcentage avec `main` — pré-condition racontée, retour non structuré, non reproductible hors agent (`vitest.config.ts:3` n'a ni seuil ni `json-summary`). L.9 impose la story « même pour un composant sans UI » alors que `AGENTS.md:33` l'exempte : l'agent reçoit les deux dans la même session. Les étapes 1-5 dupliquent `AGENTS.md:32-36`. La capture d'écran (l.14) n'est demandée par aucun template de PR.
- **Doit devenir** : l'étape 6 devient « lance `npm run test:unit` » une fois `coverage.thresholds` en place ; la règle story est tranchée une fois et vérifiée par le script de complétude ; `AGENTS.md:31-37` ne garde que le pointeur.
- **Critère de vérification** : le skill ne contient plus de vérification manuelle d'un chiffre ; `npm run test:unit` échoue localement et en CI quand la couverture passe sous le seuil.

### [MERGE] [P2] i18n-report — `scripts/i18n-report.mjs`
- **Fait aujourd'hui** : liste en JSON les clés fr absentes d'en pour le workflow agent (l.2, l.13-14).
- **Problème** : duplique mot pour mot `flatten` et la lecture des deux locales de `scripts/check-i18n.mjs:5-10` (`i18n-report.mjs:5-10`) ; deux scripts, deux évolutions divergentes possibles (ex. : seul `check-i18n` regarde le sens en→fr, `:12`), aucun test pour l'un ni l'autre, et le rapport ne sait pas s'arrêter proprement quand la liste est vide.
- **Doit devenir** : une seule commande `scripts/i18n.mjs` avec `check` (exit 1, actuel) et `report --json` (exit 0, liste), ou `check-i18n.mjs --json` ; le workflow appelle cette sous-commande.
- **Critère de vérification** : un seul `flatten` dans `scripts/` ; `agent-fix-i18n.yml` n'appelle plus `i18n-report.mjs` ; un test vitest couvre la parité et le rapport sur deux fixtures.

### [PUSH_DOWN] [P2] eslint-plugin-design-tokens — `tools/eslint-plugin-design-tokens/index.js`
- **Fait aujourd'hui** : règle `no-raw-color` qui signale tout littéral chaîne contenant `#hex`, `rgb(`, `hsl(` (l.3, l.11-13) ; activée en `error` sur `src/**` (`eslint.config.js:7-10`).
- **Problème** : le commentaire d'en-tête promet « templates et styles inline » (l.1), mais un visiteur `Literal` nu (l.11) n'est appelé par vue-eslint-parser que sur le `<script>` ; les littéraux du `<template>` (`:style="{ color: '#fff' }"`, `style="color:#fff"`) vivent dans `templateBody` et exigent `defineTemplateBodyVisitor`. Le bloc `<style>` n'est jamais vu par ESLint. La règle n'a pas de test (`RuleTester`), et la regex `#(?:[0-9a-f]{3}){1,2}\b` produit des faux positifs sur des ancres comme `"#add"`. Incident #212 cité trois fois : la garde est là où le bug n'est pas.
- **Doit devenir** : règle réécrite avec `defineTemplateBodyVisitor` (nœuds `VLiteral`, `Literal` et `TemplateElement` du template) en plus du `<script>`, regex ancrée sur une valeur CSS, fichier `index.test.js` avec `RuleTester` (cas valides/invalides, template inclus).
- **Critère de vérification** : un composant avec `<span style="color:#fff">` fait échouer `npm run lint` ; `router.push("#add")` ne le fait pas ; les tests de la règle tournent dans `npm run test:unit`.

### [SPLIT] [P2] Config stylelint — `.stylelintrc.json`
- **Fait aujourd'hui** : `extends: stylelint-config-standard`, `color-no-hex: true`, `function-disallowed-list` rgb/rgba/hsl/hsla (l.1), lancé sur `src/**/*.{css,vue}` (`package.json:9`, `ci.yml:12`).
- **Problème** : (1) la règle et sa seule exception légitime partagent le même périmètre — `src/styles/tokens.css:2-5` ne contient que des hex et est couvert par le glob : soit `lint:style` est rouge en permanence, soit quelqu'un a contourné (le contournement n'est pas dans le repo). (2) `stylelint-config-standard` n'est pas dans `package.json:17-28` : la commande échoue au chargement de la config. (3) Aucun `customSyntax`/`overrides` `postcss-html` pour les `.vue` (absent aussi des devDependencies) : stylelint 16 ne parse pas les SFC sans lui. En l'état, la garde « `<style>` sans hex » déclarée en `AGENTS.md:17` ne tourne pas.
- **Doit devenir** : `ignoreFiles: ["src/styles/tokens.css"]` (la source de vérité est le seul endroit où les hex sont légitimes), `overrides` `postcss-html` pour `*.vue`, dépendances déclarées.
- **Critère de vérification** : `npm run lint:style` passe sur le repo tel quel, échoue sur un `.vue` avec `color: #fff` dans `<style>`, et ne signale rien dans `tokens.css`.

### [BLOCK] [P3] legacy-theme-migrate — `scripts/legacy-theme-migrate.js`
- **Fait aujourd'hui** : migration one-shot SCSS → tokens « faite en 2024, plus appelée » (l.1) ; `require` CommonJS (l.2).
- **Problème** : aucun appelant dans le repo ; incompatible avec `"type": "module"` (`package.json:4`) — `require` n'est pas défini dans un `.js` ESM, le script ne peut même plus s'exécuter ; écrase les fichiers passés en argument sans dry-run (l.7).
- **Doit devenir** : supprimé (l'historique git garde la trace).
- **Critère de vérification** : fichier absent ; `grep -r legacy-theme-migrate` vide. Approbation humaine : suppression.

### [BLOCK] [P3] Hook pre-commit — `.husky/pre-commit`
- **Fait aujourd'hui** : `npm run lint` (l.1).
- **Problème** : hook mort — `husky` n'est pas dans `package.json:17-28` et il n'y a pas de script `prepare` (`package.json:5-14`), donc `.husky/` n'est jamais installé dans `.git/hooks`. Un développeur croit protégé ce qui ne l'est pas ; la CI fait le vrai travail (`ci.yml:11`).
- **Doit devenir** : soit branché (`husky` en devDependency + `"prepare": "husky"`) et étendu à `lint:style` et `check:i18n` ; soit supprimé pour ne pas afficher une garde fictive.
- **Critère de vérification** : après `npm ci`, un commit avec un hex en dur est refusé localement ; ou le dossier `.husky/` n'existe plus. Approbation humaine : suppression.

### [KEEP] CLAUDE.md — `CLAUDE.md`
Un seul include `@AGENTS.md` (l.1) : pas de duplication, source unique pour Claude Code — c'est ce que `vue.mdc` et `copilot-instructions.md` devraient aussi être.

### [KEEP] check-i18n — `scripts/check-i18n.mjs`
Fait exactement ce qu'il dit (l.2), avec `exit 1` et message typé (l.13-15), appelé par le CLI et par la CI (`package.json:12`, `ci.yml:25`) ; le seul défaut est la promesse excessive faite à son sujet dans `AGENTS.md:18`.

### [KEEP] Config eslint — `eslint.config.js`
Porte deux garde-fous réels (`no-raw-color` l.10, `component-api-style` l.11) sur le bon périmètre `src/**` (l.7) ; c'est ici qu'atterrit `vue-i18n/no-raw-text`.

### [KEEP] Scripts npm — `package.json:5-16`
CLI du repo correctement exposée (`lint`, `lint:style`, `test:unit`, `test:e2e`, `check:i18n`, `size`) et cohérente avec la table `AGENTS.md:9-14` ; les dépendances manquantes qui empêchent certains scripts de tourner sont listées en §6.

### [KEEP] Config vitest — `vitest.config.ts`
Bonne couche ; recevra `coverage.thresholds` et le reporter `json-summary` (fuite « couverture », §3).

### [KEEP] Workflow ci — `.github/workflows/ci.yml`
Cinq jobs indépendants, un par règle de la table d'AGENTS.md ; recevra le job de complétude des composants et la garde de couverture.

### [KEEP] Workflow deploy-preview — `.github/workflows/deploy-preview.yml`
Modèle L4 sain : `environment: preview` (l.7), secret tenu en L4 (l.14), sortie `--json` relue par `jq` (l.13, l.15) plutôt qu'un log.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | BLOCK | `agent-fix-i18n.yml` | Retirer l'étape auto-merge (l.21-23), restreindre `--allowedTools` à `Edit(src/locales/en.json),Bash(gh pr create*)`, ajouter `inputs.dry_run` qui s'arrête après l'artefact `missing.json`, court-circuiter si la liste est vide, ouvrir la PR en brouillon et la cibler par l'URL de `gh pr create` | — | Run `dry_run=true` : artefact, aucune PR ; run réel : PR brouillon non fusionnable sans revue | Oui |
| 2 | P1 | PUSH_DOWN | AGENTS.md:18 (règle i18n) | Ajouter `@intlify/eslint-plugin-vue-i18n` avec `vue-i18n/no-raw-text` et `vue-i18n/no-missing-keys` dans `eslint.config.js` ; corriger `NewBadge.vue:6` | — | `npm run lint` échoue sur `NewBadge.vue` avant correction, passe après ; `ci.yml` job lint rouge sur un template avec texte en dur | Non |
| 3 | P1 | PUSH_DOWN | AGENTS.md:27, :29 (interdits) | Créer `.github/CODEOWNERS` (`src/payment/`, `src/styles/tokens.css`), activer revue requise par la protection de branche ; template de PR avec champ « ticket design » | 1 | Une PR touchant `src/payment/` exige l'approbation du propriétaire ; un run du workflow agent ne peut pas y écrire | Oui (paramètres du dépôt) |
| 4 | P2 | PUSH_DOWN | `tools/eslint-plugin-design-tokens` | Réécrire `no-raw-color` avec `defineTemplateBodyVisitor`, regex ancrée, ajouter `RuleTester` | — | Test rouge sur `style="color:#fff"` dans un template ; vert sur `"#add"` | Non |
| 5 | P2 | SPLIT | `.stylelintrc.json` | Déclarer `stylelint-config-standard` et `postcss-html`, `overrides` pour `*.vue`, `ignoreFiles: src/styles/tokens.css` | — | `npm run lint:style` vert sur le repo, rouge sur un `<style>` avec hex | Non |
| 6 | P2 | PUSH_DOWN | AGENTS.md:20 / SKILL.md:9-10 (story + spec) | Trancher la règle (recommandé : story obligatoire, conformément à `AGENTS.md:20` et au « pourquoi »), créer `scripts/check-components.mjs` (`exit 1` si un `src/components/*.vue` n'a pas `.stories.ts` + `.spec.ts`), job `components` dans `ci.yml` ; compléter `NewBadge` | — | CI rouge sur le repo tel quel, verte après ajout des deux fichiers de `NewBadge` | Oui (choix de la règle) |
| 7 | P2 | PUSH_DOWN | AGENTS.md:21 / SKILL.md:13 (couverture) | `coverage.thresholds` (+ `autoUpdate`) et reporter `json-summary` dans `vitest.config.ts` ; l'étape 6 du skill devient « lance `npm run test:unit` » | — | `npm run test:unit` échoue quand on supprime `AppButton.spec.ts` | Non |
| 8 | P2 | MERGE | `scripts/i18n-report.mjs` | Fusionner dans `check-i18n.mjs` (`--json`) ou `scripts/i18n.mjs check|report`, avec un test vitest ; mettre à jour le workflow | 1 | Un seul `flatten` dans `scripts/` ; le workflow appelle la sous-commande | Oui (suppression de fichier) |
| 9 | P2 | PUSH_DOWN | `.claude/skills/add-component/SKILL.md` | Supprimer la vérification manuelle (l.13), aligner l.9 sur la règle tranchée, référencer `check:components` | 6, 7 | Le skill ne demande plus d'ouvrir `coverage/index.html` | Non |
| 10 | P2 | MERGE | `.cursor/rules/vue.mdc` | Remplacer par un pointeur vers `AGENTS.md` (ou générer le contenu depuis lui) | 6 | Aucune règle propre ; zéro contradiction avec eslint/stylelint | Non |
| 11 | P2 | MERGE | `.github/copilot-instructions.md` | Idem ; remplacer `npm test` par les commandes de `AGENTS.md:9-14` | 6 | Toute commande citée existe dans `package.json` | Non |
| 12 | P1 | PUSH_DOWN | `AGENTS.md` (fichier) | Réécrire les « Vérifiée par » (l.17-18) pour refléter les garde-fous réels, ajouter ceux des l.20-21, 27-29 ; remplacer l.31-37 par le pointeur ; supprimer l.23-24 ; mentionner le workflow autonome en l.3 | 2, 3, 4, 5, 6, 7 | Chaque « Vérifiée par » a un test rouge reproductible ; une seule formulation de la règle story dans le repo | Non |
| 13 | P3 | PUSH_DOWN | AGENTS.md:28 (`eslint-disable`) | Ajouter `@eslint-community/eslint-plugin-eslint-comments` règle `require-description` | — | `// eslint-disable-next-line x` sans description fait échouer `npm run lint` | Non |
| 14 | P3 | BLOCK | `scripts/legacy-theme-migrate.js` | Supprimer | — | Fichier absent, `grep` vide | Oui |
| 15 | P3 | BLOCK | `.husky/pre-commit` | Brancher (`husky` + `prepare`, ajouter `lint:style` et `check:i18n`) ou supprimer | 5 | Commit local refusé sur un hex en dur, ou dossier absent | Oui si suppression |

## 6. Ce que l'audit n'a pas pu vérifier

- Aucun script n'a été exécuté (pas de `node_modules`, interdiction de modifier le dépôt) : le comportement de stylelint sur les `.vue` et sur `tokens.css`, et l'échec de `lint:style`, sont déduits de `.stylelintrc.json:1`, `package.json:9,17-28` et de la documentation de stylelint 16, pas observés.
- Dépendances absentes de `package.json:17-28` alors que des fichiers les importent ou que des commandes les supposent : `stylelint-config-standard`, `postcss-html`, `@testing-library/vue` (`src/components/AppButton.spec.ts:1`), `jsdom` (`vitest.config.ts:3`), `@playwright/test` (`tests/e2e/cart.spec.ts:1`), `husky`, `@storybook/vue3-vite`. Si c'est volontaire dans la fixture, les jobs `lint`, `unit` et `e2e` de `ci.yml` ne peuvent pas être verts aujourd'hui ; je n'ai pas pu le confirmer.
- `src/payment/` n'existe pas dans le dépôt : l'interdit `AGENTS.md:29` est audité comme règle, pas contre du code.
- Paramètres du dépôt distant non lisibles : protection de branche, reviewers requis, existence et règles de l'environnement `preview` (`deploy-preview.yml:7`), configuration de `app/acme-bot`, secrets `BOT_TOKEN`/`ANTHROPIC_API_KEY`/`NETLIFY_AUTH_TOKEN`.
- Issues #212, #198, #240 et PR #231 citées dans `AGENTS.md` non consultables (dépôt `acme/shopfront` synthétique, cf. `README.md:3`).
- Comportement réel de `gh pr list --author app/acme-bot … .[0]` (`agent-fix-i18n.yml:22`) quand aucune PR n'est ouverte : supposé échouer sur un argument vide.
- Historique git non consulté (consigne de l'audit) : impossible de dater la dérive entre `AGENTS.md`, `vue.mdc` et `copilot-instructions.md`.

## 7. Données machine

Le bloc JSON est écrit dans `blind-node-front.json` (même dossier) et reproduit ci-dessous.

```json
{
  "audit": {
    "process": "shopfront — ajout de composant et traduction automatisée",
    "scope": "fixtures/repos/node-front/repo (AGENTS.md, CLAUDE.md, .cursor/rules, .github/copilot-instructions.md, .claude/skills, scripts, tools, .github/workflows, eslint/stylelint/husky/vitest, package.json)",
    "date": "2026-11-09",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 7 }
  },
  "elements": [
    {
      "id": "wf-agent-fix-i18n",
      "path": ".github/workflows/agent-fix-i18n.yml",
      "declared_layer": "L4",
      "actual_layer": "MIXED",
      "called_by": [],
      "calls": ["script-i18n-report"],
      "verdict": "BLOCK",
      "priority": "P1",
      "finding": "Un agent traduit avec Edit et Bash(git *) sans restriction de chemin puis gh pr merge --auto fusionne dans main la première PR du bot sans relecture humaine, sans dry_run ni environnement protégé, alors que la seule CI pertinente (parité de clés) passe par construction.",
      "evidence": [".github/workflows/agent-fix-i18n.yml:5", ".github/workflows/agent-fix-i18n.yml:18-19", ".github/workflows/agent-fix-i18n.yml:22", ".github/workflows/ci.yml:25", "AGENTS.md:3"],
      "target": "L4 prépare (report JSON, court-circuit si vide, input dry_run), L1 traduit et ouvre une PR brouillon avec Edit(src/locales/en.json) seulement, la fusion repasse par un humain ; plus d'auto-merge.",
      "check": "Un run dry_run=true produit l'artefact missing.json et aucune PR ; un run réel produit une PR brouillon non fusionnable sans approbation ; aucune occurrence de 'pr merge --auto'."
    },
    {
      "id": "agents-md",
      "path": "AGENTS.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": ["claude-md"],
      "calls": ["skill-add-component", "package-json-scripts", "eslint-plugin-design-tokens", "stylelintrc", "script-check-i18n", "wf-ci"],
      "verdict": "PUSH_DOWN",
      "priority": "P1",
      "finding": "Deux des trois « Vérifiée par » sont faux (check-i18n ne lit pas les templates, no-raw-color ne visite pas le template), cinq règles obligatoires n'ont aucun garde-fou (story+test, couverture, tokens.css, eslint-disable, src/payment PCI), et la règle story se contredit entre l.20 et l.33.",
      "evidence": ["AGENTS.md:17", "AGENTS.md:18", "AGENTS.md:20", "AGENTS.md:21", "AGENTS.md:27", "AGENTS.md:28", "AGENTS.md:29", "AGENTS.md:33", "scripts/check-i18n.mjs:2", "tools/eslint-plugin-design-tokens/index.js:11", "src/components/NewBadge.vue:6"],
      "target": "Chaque règle obligatoire pointe vers un garde-fou L3/L4 réel (eslint vue-i18n/no-raw-text, check-components, coverage thresholds, CODEOWNERS), 'Vérifiée par' n'est écrit que quand c'est vrai, l.31-37 remplacées par le pointeur vers le skill, l.23-24 supprimées, l.3 mentionne le workflow autonome.",
      "check": "Pour chaque 'Vérifiée par', un test rouge volontaire (texte en dur dans un template, composant sans story, hex dans :style) fait échouer ci.yml ; une seule formulation de la règle story dans le dépôt."
    },
    {
      "id": "cursor-vue-mdc",
      "path": ".cursor/rules/vue.mdc",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": [],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Trois des quatre règles contredisent AGENTS.md et le linter : Options API tolérée sous 50 lignes (eslint la refuse partout), hex toléré avec TODO, story facultative.",
      "evidence": [".cursor/rules/vue.mdc:5", ".cursor/rules/vue.mdc:6", ".cursor/rules/vue.mdc:7", "eslint.config.js:11", "AGENTS.md:17", "AGENTS.md:20"],
      "target": "Fichier réduit à un pointeur vers AGENTS.md ou généré depuis lui, sans règle propre.",
      "check": "Aucune règle de vue.mdc ne contredit une règle eslint/stylelint active ni AGENTS.md."
    },
    {
      "id": "copilot-instructions",
      "path": ".github/copilot-instructions.md",
      "declared_layer": "L2",
      "actual_layer": "L2",
      "called_by": [],
      "calls": ["package-json-scripts"],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Quatre consignes contredisent AGENTS.md (Options API, hex en override, story optionnelle, chaînes en dur acceptées en admin) et la commande 'npm test' n'existe pas dans package.json.",
      "evidence": [".github/copilot-instructions.md:3", ".github/copilot-instructions.md:4", ".github/copilot-instructions.md:5", ".github/copilot-instructions.md:6", ".github/copilot-instructions.md:7", "package.json:5-14"],
      "target": "Pointeur vers AGENTS.md ou contenu généré ; commandes reprises de la table AGENTS.md:9-14.",
      "check": "Toute commande citée existe dans package.json ; aucune exception à une règle d'AGENTS.md."
    },
    {
      "id": "skill-add-component",
      "path": ".claude/skills/add-component/SKILL.md",
      "declared_layer": "L2",
      "actual_layer": "MIXED",
      "called_by": ["agents-md"],
      "calls": ["package-json-scripts", "vitest-config"],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "L'étape 6 fait comparer à l'œil le pourcentage de couverture avec main (retour non structuré, non reproductible), l.9 impose la story 'même sans UI' alors qu'AGENTS.md:33 l'exempte, et les étapes 1-5 dupliquent AGENTS.md:32-36.",
      "evidence": [".claude/skills/add-component/SKILL.md:9", ".claude/skills/add-component/SKILL.md:13", "AGENTS.md:33", "vitest.config.ts:3"],
      "target": "L'étape 6 devient 'lance npm run test:unit' une fois coverage.thresholds en place ; règle story tranchée et vérifiée par check-components ; AGENTS.md ne garde que le pointeur.",
      "check": "Le skill ne contient plus de vérification manuelle d'un chiffre ; npm run test:unit échoue quand la couverture passe sous le seuil."
    },
    {
      "id": "script-i18n-report",
      "path": "scripts/i18n-report.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["wf-agent-fix-i18n"],
      "calls": [],
      "verdict": "MERGE",
      "priority": "P2",
      "finding": "Duplique mot pour mot flatten et la lecture des locales de check-i18n.mjs, sans test, avec un seul sens (fr→en) et sans sortie courte quand la liste est vide.",
      "evidence": ["scripts/i18n-report.mjs:5-10", "scripts/check-i18n.mjs:5-10"],
      "target": "Une seule commande (check-i18n.mjs --json ou scripts/i18n.mjs check|report) avec un test vitest ; le workflow appelle la sous-commande.",
      "check": "Un seul flatten dans scripts/ ; agent-fix-i18n.yml n'appelle plus i18n-report.mjs."
    },
    {
      "id": "eslint-plugin-design-tokens",
      "path": "tools/eslint-plugin-design-tokens/index.js",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["eslint-config"],
      "calls": [],
      "verdict": "PUSH_DOWN",
      "priority": "P2",
      "finding": "Le visiteur Literal nu n'est appelé que sur le <script> : les littéraux du <template> (:style, style=\"\") ne sont pas vus malgré l'en-tête qui promet 'templates et styles inline' ; pas de RuleTester ; faux positifs sur des ancres comme '#add'.",
      "evidence": ["tools/eslint-plugin-design-tokens/index.js:1", "tools/eslint-plugin-design-tokens/index.js:3", "tools/eslint-plugin-design-tokens/index.js:11"],
      "target": "Règle réécrite avec defineTemplateBodyVisitor (VLiteral/Literal/TemplateElement du template) en plus du script, regex ancrée sur une valeur CSS, tests RuleTester.",
      "check": "Un composant avec <span style=\"color:#fff\"> fait échouer npm run lint ; router.push('#add') ne le fait pas ; les tests de la règle tournent dans test:unit."
    },
    {
      "id": "stylelintrc",
      "path": ".stylelintrc.json",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts"],
      "calls": [],
      "verdict": "SPLIT",
      "priority": "P2",
      "finding": "color-no-hex couvre src/styles/tokens.css, seul endroit légitime pour des hex, donc la règle et son exception partagent le même périmètre ; stylelint-config-standard et postcss-html (pour les .vue) ne sont pas déclarés : la garde '<style> sans hex' ne tourne pas telle quelle.",
      "evidence": [".stylelintrc.json:1", "package.json:9", "package.json:17-28", "src/styles/tokens.css:2-5"],
      "target": "ignoreFiles pour tokens.css, overrides postcss-html pour *.vue, dépendances déclarées.",
      "check": "npm run lint:style passe sur le dépôt tel quel, échoue sur un .vue avec color:#fff dans <style>, ne signale rien dans tokens.css."
    },
    {
      "id": "script-legacy-theme-migrate",
      "path": "scripts/legacy-theme-migrate.js",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": [],
      "verdict": "BLOCK",
      "priority": "P3",
      "finding": "Script mort (aucun appelant, 'plus appelée' en l.1), inexécutable en ESM (require avec type: module) et destructif sans dry-run.",
      "evidence": ["scripts/legacy-theme-migrate.js:1", "scripts/legacy-theme-migrate.js:2", "scripts/legacy-theme-migrate.js:7", "package.json:4"],
      "target": "Supprimé.",
      "check": "Fichier absent ; grep -r legacy-theme-migrate vide."
    },
    {
      "id": "husky-pre-commit",
      "path": ".husky/pre-commit",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": [],
      "calls": ["package-json-scripts"],
      "verdict": "BLOCK",
      "priority": "P3",
      "finding": "Hook jamais installé : husky absent des devDependencies et pas de script prepare ; garde fictive.",
      "evidence": [".husky/pre-commit:1", "package.json:5-14", "package.json:17-28"],
      "target": "Brancher (husky + prepare, ajouter lint:style et check:i18n) ou supprimer.",
      "check": "Après npm ci, un commit avec un hex en dur est refusé localement ; ou .husky/ n'existe plus."
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
      "finding": "Un seul include @AGENTS.md : source unique, pas de duplication.",
      "evidence": ["CLAUDE.md:1"],
      "target": "Inchangé ; modèle pour vue.mdc et copilot-instructions.md.",
      "check": "Le fichier reste un include seul."
    },
    {
      "id": "script-check-i18n",
      "path": "scripts/check-i18n.mjs",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts", "wf-ci"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Vérifie la parité des clés fr/en avec exit 1 et message typé, appelé par le CLI et la CI ; seul défaut : la promesse excessive faite à son sujet dans AGENTS.md:18.",
      "evidence": ["scripts/check-i18n.mjs:2", "scripts/check-i18n.mjs:13-15", "package.json:12", ".github/workflows/ci.yml:25"],
      "target": "Inchangé ; accueille le mode --json issu de la fusion avec i18n-report.",
      "check": "Un test vitest couvre la parité sur deux fixtures."
    },
    {
      "id": "eslint-config",
      "path": "eslint.config.js",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts", "husky-pre-commit", "wf-ci"],
      "calls": ["eslint-plugin-design-tokens"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Porte deux garde-fous réels (no-raw-color, component-api-style script-setup) sur src/** ; c'est ici qu'atterrit vue-i18n/no-raw-text.",
      "evidence": ["eslint.config.js:7", "eslint.config.js:10", "eslint.config.js:11"],
      "target": "Inchangé dans sa structure ; ajout des règles vue-i18n et eslint-comments.",
      "check": "npm run lint reste la commande unique du job lint."
    },
    {
      "id": "package-json-scripts",
      "path": "package.json",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["agents-md", "skill-add-component", "wf-ci", "wf-deploy-preview", "husky-pre-commit", "copilot-instructions"],
      "calls": ["eslint-config", "stylelintrc", "vitest-config", "script-check-i18n"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "CLI du dépôt correctement exposée et cohérente avec la table AGENTS.md:9-14 ; les dépendances manquantes qui empêchent certains scripts de tourner sont listées dans unverified.",
      "evidence": ["package.json:5-16"],
      "target": "Inchangé ; ajout de check:components et des devDependencies manquantes.",
      "check": "Chaque script cité par un fichier d'instructions existe."
    },
    {
      "id": "vitest-config",
      "path": "vitest.config.ts",
      "declared_layer": "L3",
      "actual_layer": "L3",
      "called_by": ["package-json-scripts"],
      "calls": [],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Bonne couche ; recevra coverage.thresholds et le reporter json-summary pour porter la règle 'la couverture ne baisse pas'.",
      "evidence": ["vitest.config.ts:3"],
      "target": "Ajout de coverage.thresholds (+ autoUpdate) et json-summary.",
      "check": "npm run test:unit échoue quand on supprime AppButton.spec.ts."
    },
    {
      "id": "wf-ci",
      "path": ".github/workflows/ci.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["package-json-scripts", "script-check-i18n"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Cinq jobs indépendants, un par ligne de la table AGENTS.md ; recevra le job de complétude des composants et la garde de couverture.",
      "evidence": [".github/workflows/ci.yml:4-41"],
      "target": "Ajout d'un job components (check-components) ; la couverture est portée par vitest.",
      "check": "Un composant sans story ou sans spec rend la CI rouge."
    },
    {
      "id": "wf-deploy-preview",
      "path": ".github/workflows/deploy-preview.yml",
      "declared_layer": "L4",
      "actual_layer": "L4",
      "called_by": [],
      "calls": ["package-json-scripts"],
      "verdict": "KEEP",
      "priority": null,
      "finding": "Modèle L4 sain : environment protégé, secret tenu en L4, sortie --json relue par jq plutôt qu'un log.",
      "evidence": [".github/workflows/deploy-preview.yml:7", ".github/workflows/deploy-preview.yml:13", ".github/workflows/deploy-preview.yml:15"],
      "target": "Inchangé.",
      "check": "Le commentaire de PR contient l'URL issue de deploy.json."
    }
  ],
  "process_leaks": [
    { "rule": "Toute chaîne visible passe par t(), jamais de texte en dur dans un template", "told_in": "AGENTS.md:18", "if_skipped": "Texte non traduit livré en production (incident #198) ; NewBadge.vue:6 livre « Nouveau » en dur et passe toute la CI, car check-i18n.mjs ne lit que les JSON (scripts/check-i18n.mjs:2)", "belongs_in": "L3", "guard_tool": "@intlify/eslint-plugin-vue-i18n règles vue-i18n/no-raw-text et vue-i18n/no-missing-keys dans eslint.config.js (job lint de ci.yml)" },
    { "rule": "Un composant a une story Storybook", "told_in": "AGENTS.md:20", "if_skipped": "Composant jamais relu visuellement ; NewBadge.vue n'a pas de story et la CI est verte ; quatre formulations contradictoires (AGENTS.md:33, SKILL.md:9, vue.mdc:7, copilot-instructions.md:5)", "belongs_in": "L3", "guard_tool": "scripts/check-components.mjs (glob src/components/*.vue → exige .stories.ts, exit 1) branché dans ci.yml" },
    { "rule": "Un composant a un test unitaire", "told_in": "AGENTS.md:20", "if_skipped": "Composant non testé ; NewBadge.vue n'a pas de spec et la CI est verte", "belongs_in": "L3", "guard_tool": "scripts/check-components.mjs (exige .spec.ts) branché dans ci.yml" },
    { "rule": "La couverture unitaire ne baisse pas", "told_in": "AGENTS.md:21", "if_skipped": "Perte silencieuse de tests (incident #240) ; la seule vérification est à l'œil dans SKILL.md:13, vitest.config.ts:3 n'a pas de thresholds", "belongs_in": "L3", "guard_tool": "coverage.thresholds (+ autoUpdate) et reporter json-summary dans vitest.config.ts, ou diff de couverture vs main en PR gate" },
    { "rule": "Ne jamais toucher src/payment/ (module PCI)", "told_in": "AGENTS.md:29", "if_skipped": "Modification d'un module PCI sans revue propriétaire ; l'agent de agent-fix-i18n.yml:19 a Edit sans restriction et auto-merge", "belongs_in": "L4", "guard_tool": ".github/CODEOWNERS + revue requise par la protection de branche ; Edit(src/locales/en.json) dans le workflow" },
    { "rule": "Ne jamais modifier src/styles/tokens.css sans ticket design", "told_in": "AGENTS.md:27", "if_skipped": "Dérive du thème sans validation design", "belongs_in": "L4", "guard_tool": ".github/CODEOWNERS (équipe design) + template de PR avec champ ticket" },
    { "rule": "Pas de couleur en dur dans le template (attribut style, :style)", "told_in": "AGENTS.md:17", "if_skipped": "Hex oublié dans un template → thème sombre cassé (incident #212) ; no-raw-color ne visite que le <script> (tools/eslint-plugin-design-tokens/index.js:11)", "belongs_in": "L3", "guard_tool": "Règle no-raw-color réécrite avec defineTemplateBodyVisitor + RuleTester ; stylelint avec customSyntax postcss-html" },
    { "rule": "Pas d'eslint-disable sans justification datée", "told_in": "AGENTS.md:28", "if_skipped": "Règles contournées silencieusement (hygiène)", "belongs_in": "L3", "guard_tool": "@eslint-community/eslint-plugin-eslint-comments règle require-description" },
    { "rule": "L'humain relit chaque diff avant fusion", "told_in": "AGENTS.md:3", "if_skipped": "Traductions hallucinées fusionnées dans main sans relecture (agent-fix-i18n.yml:21-23)", "belongs_in": "L4", "guard_tool": "Suppression de l'auto-merge, environment protégé avec reviewers requis, protection de branche" }
  ],
  "guarded_rules": [
    { "rule": "Composition API <script setup> uniquement", "told_in": "AGENTS.md:19", "guarded_by": "eslint.config.js:11 (vue/component-api-style script-setup), .github/workflows/ci.yml:11" },
    { "rule": "Bundle initial sous 250 kB gzip", "told_in": "AGENTS.md:22", "guarded_by": "package.json:16 (size-limit), .github/workflows/ci.yml:33" },
    { "rule": "Parité des clés fr/en dans les locales", "told_in": "AGENTS.md:13", "guarded_by": "scripts/check-i18n.mjs:13-15, .github/workflows/ci.yml:25" },
    { "rule": "Pas de couleur en dur dans le <script> et les fichiers .css (garde partielle)", "told_in": "AGENTS.md:17", "guarded_by": "eslint.config.js:10 + tools/eslint-plugin-design-tokens/index.js:11-13 ; .stylelintrc.json:1 (si la config tourne)" },
    { "rule": "Table « si tu touches X, lance Y, vérifié en CI par ci.yml job Z »", "told_in": "AGENTS.md:9-14", "guarded_by": ".github/workflows/ci.yml:4-41 (jobs lint, unit, i18n, size, e2e)" }
  ],
  "instruction_files": [
    { "path": "AGENTS.md", "loaded_lines": 45, "instruction_pct": 45, "reference_pct": 45, "noise_pct": 10, "justified_rules": true, "maintenance_clause": true },
    { "path": "CLAUDE.md", "loaded_lines": 45, "instruction_pct": 0, "reference_pct": 100, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true },
    { "path": ".cursor/rules/vue.mdc", "loaded_lines": 8, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false },
    { "path": ".github/copilot-instructions.md", "loaded_lines": 8, "instruction_pct": 85, "reference_pct": 15, "noise_pct": 0, "justified_rules": false, "maintenance_clause": false },
    { "path": ".claude/skills/add-component/SKILL.md", "loaded_lines": 14, "instruction_pct": 100, "reference_pct": 0, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false }
  ],
  "remediation": [
    { "order": 1, "priority": "P1", "verdict": "BLOCK", "element": "wf-agent-fix-i18n", "action": "Retirer l'auto-merge, restreindre allowedTools à Edit(src/locales/en.json) et gh pr create, ajouter inputs.dry_run, court-circuiter si missing.json est vide, ouvrir la PR en brouillon et la cibler par l'URL de gh pr create.", "depends_on": [], "check": "Run dry_run=true : artefact et aucune PR ; run réel : PR brouillon non fusionnable sans revue ; aucune occurrence de 'pr merge --auto'.", "needs_human_approval": true },
    { "order": 2, "priority": "P1", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Ajouter @intlify/eslint-plugin-vue-i18n (no-raw-text, no-missing-keys) dans eslint.config.js et corriger NewBadge.vue:6.", "depends_on": [], "check": "npm run lint échoue sur NewBadge.vue avant correction et passe après ; le job lint est rouge sur un template avec texte en dur.", "needs_human_approval": false },
    { "order": 3, "priority": "P1", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Créer .github/CODEOWNERS pour src/payment/ et src/styles/tokens.css, activer la revue requise par la protection de branche, ajouter un template de PR avec champ ticket design.", "depends_on": [1], "check": "Une PR touchant src/payment/ exige l'approbation du propriétaire ; le workflow agent ne peut pas y écrire.", "needs_human_approval": true },
    { "order": 4, "priority": "P2", "verdict": "PUSH_DOWN", "element": "eslint-plugin-design-tokens", "action": "Réécrire no-raw-color avec defineTemplateBodyVisitor, regex ancrée, ajouter des tests RuleTester.", "depends_on": [], "check": "Test rouge sur style=\"color:#fff\" dans un template ; vert sur '#add'.", "needs_human_approval": false },
    { "order": 5, "priority": "P2", "verdict": "SPLIT", "element": "stylelintrc", "action": "Déclarer stylelint-config-standard et postcss-html, overrides pour *.vue, ignoreFiles src/styles/tokens.css.", "depends_on": [], "check": "npm run lint:style vert sur le dépôt, rouge sur un <style> avec hex, silencieux sur tokens.css.", "needs_human_approval": false },
    { "order": 6, "priority": "P2", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Trancher la règle story (recommandé : obligatoire), créer scripts/check-components.mjs exigeant .stories.ts et .spec.ts par composant, job components dans ci.yml, compléter NewBadge.", "depends_on": [], "check": "CI rouge sur le dépôt tel quel, verte après ajout des deux fichiers de NewBadge.", "needs_human_approval": true },
    { "order": 7, "priority": "P2", "verdict": "PUSH_DOWN", "element": "vitest-config", "action": "Ajouter coverage.thresholds (+ autoUpdate) et le reporter json-summary dans vitest.config.ts.", "depends_on": [], "check": "npm run test:unit échoue quand on supprime AppButton.spec.ts.", "needs_human_approval": false },
    { "order": 8, "priority": "P2", "verdict": "MERGE", "element": "script-i18n-report", "action": "Fusionner dans check-i18n.mjs (--json) ou scripts/i18n.mjs check|report avec un test vitest, mettre à jour le workflow.", "depends_on": [1], "check": "Un seul flatten dans scripts/ ; le workflow appelle la sous-commande.", "needs_human_approval": true },
    { "order": 9, "priority": "P2", "verdict": "PUSH_DOWN", "element": "skill-add-component", "action": "Supprimer la vérification manuelle de couverture (l.13), aligner l.9 sur la règle story tranchée, référencer check:components.", "depends_on": [6, 7], "check": "Le skill ne demande plus d'ouvrir coverage/index.html.", "needs_human_approval": false },
    { "order": 10, "priority": "P2", "verdict": "MERGE", "element": "cursor-vue-mdc", "action": "Remplacer par un pointeur vers AGENTS.md ou un contenu généré depuis lui.", "depends_on": [6], "check": "Aucune règle propre ; zéro contradiction avec eslint/stylelint.", "needs_human_approval": false },
    { "order": 11, "priority": "P2", "verdict": "MERGE", "element": "copilot-instructions", "action": "Remplacer par un pointeur vers AGENTS.md ; remplacer npm test par les commandes de AGENTS.md:9-14.", "depends_on": [6], "check": "Toute commande citée existe dans package.json.", "needs_human_approval": false },
    { "order": 12, "priority": "P1", "verdict": "PUSH_DOWN", "element": "agents-md", "action": "Réécrire les 'Vérifiée par' (l.17-18) selon les garde-fous réels, ajouter ceux des l.20-21 et 27-29, remplacer l.31-37 par le pointeur vers le skill, supprimer l.23-24, mentionner le workflow autonome en l.3.", "depends_on": [2, 3, 4, 5, 6, 7], "check": "Chaque 'Vérifiée par' a un test rouge reproductible ; une seule formulation de la règle story dans le dépôt.", "needs_human_approval": false },
    { "order": 13, "priority": "P3", "verdict": "PUSH_DOWN", "element": "eslint-config", "action": "Ajouter @eslint-community/eslint-plugin-eslint-comments règle require-description.", "depends_on": [], "check": "Un eslint-disable sans description fait échouer npm run lint.", "needs_human_approval": false },
    { "order": 14, "priority": "P3", "verdict": "BLOCK", "element": "script-legacy-theme-migrate", "action": "Supprimer scripts/legacy-theme-migrate.js.", "depends_on": [], "check": "Fichier absent, grep vide.", "needs_human_approval": true },
    { "order": 15, "priority": "P3", "verdict": "BLOCK", "element": "husky-pre-commit", "action": "Brancher husky (devDependency + prepare, ajouter lint:style et check:i18n) ou supprimer .husky/.", "depends_on": [5], "check": "Commit local refusé sur un hex en dur, ou dossier absent.", "needs_human_approval": true }
  ],
  "unverified": [
    "Aucun script exécuté (pas de node_modules, dépôt non modifiable) : le comportement de stylelint sur les .vue et tokens.css est déduit de .stylelintrc.json:1, package.json:9,17-28 et de la documentation stylelint 16, pas observé.",
    "Dépendances absentes de package.json:17-28 mais importées ou supposées : stylelint-config-standard, postcss-html, @testing-library/vue (AppButton.spec.ts:1), jsdom (vitest.config.ts:3), @playwright/test (tests/e2e/cart.spec.ts:1), husky, @storybook/vue3-vite ; si c'est l'état réel, les jobs lint, unit et e2e de ci.yml ne peuvent pas être verts.",
    "src/payment/ n'existe pas dans le dépôt : l'interdit AGENTS.md:29 est audité comme règle, pas contre du code.",
    "Paramètres du dépôt distant non lisibles : protection de branche, reviewers requis, règles de l'environnement preview (deploy-preview.yml:7), configuration de app/acme-bot, secrets BOT_TOKEN / ANTHROPIC_API_KEY / NETLIFY_AUTH_TOKEN.",
    "Issues #212, #198, #240 et PR #231 citées dans AGENTS.md non consultables (dépôt synthétique, README.md:3).",
    "Comportement de gh pr list --author app/acme-bot … .[0] (agent-fix-i18n.yml:22) sans PR ouverte : supposé échouer sur un argument vide.",
    "Historique git non consulté (consigne) : impossible de dater la dérive entre AGENTS.md, vue.mdc et copilot-instructions.md."
  ]
}
```
