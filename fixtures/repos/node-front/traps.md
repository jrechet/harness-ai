# Pièges plantés — node-front (shopfront)

Un front Vue 3 dont l'équipe est allée plus loin que java-back : AGENTS.md court avec mode, règles justifiées et « Vérifiée par », stub CLAUDE.md, section Maintenance, convention `rule:`, un contrat de tâche, eslint custom, stylelint, size-limit, husky. Il est au **palier 1**. Les pièges sont ceux d'un harness qui a l'air sain : contradictions entre ce qui est déclaré et ce qui tourne.

| Id | Où | Quoi | Attendu de harness-audit | Attendu de `harness status` |
|---|---|---|---|---|
| T1 | `AGENTS.md:3` vs `.github/workflows/agent-fix-i18n.yml` | Mode déclaré **assistance** alors qu'un agent tourne seul chaque matin, ouvre une PR et la fusionne en auto-merge sans relecture : c'est de la délégation de fait | Relever la contradiction et appliquer le barème délégation ; P1 | `L4.mode` échoue (assistance) |
| T2 | `.github/workflows/agent-fix-i18n.yml:22-24` | `gh pr merge --auto` sur la PR de l'agent : action L4 sans point d'arrêt humain, avec un token de bot | BLOCK, P1 | — |
| T3 | `AGENTS.md:17` | « Toute chaîne visible passe par `t()` », déclarée « Vérifiée par : scripts/check-i18n.mjs ». **Faux** : le script ne compare que les clés des deux locales, il ne lit aucun template. `NewBadge.vue:6` viole la règle sans que rien ne le voie | Garde-fou mensonger à démasquer : PUSH_DOWN vers une règle eslint (`@intlify/vue-i18n/no-raw-text`), P2 en assistance, P1 si le barème délégation est retenu (T1) ; ne doit **pas** figurer dans `guarded_rules` | `L3.guarded` compte 3 règles vérifiées : la mesure est aveugle à ce mensonge, c'est le rôle de l'audit |
| T4 | `scripts/check-i18n.mjs` + `scripts/i18n-report.mjs` | Même `flatten`, même lecture des locales, deux scripts | MERGE, P2 ou P3 | — |
| T5 | `AGENTS.md:19` (story optionnelle) vs `.claude/skills/add-component/SKILL.md:9` (story obligatoire) | La procédure « Ajouter un composant » est dupliquée dans AGENTS.md et **diverge** du contrat | Cohérence interne : P2 ; AGENTS.md ne garde qu'un pointeur (INLINE de la procédure) | — |
| T6 | `.github/copilot-instructions.md`, `.cursor/rules/vue.mdc` | Deux fichiers d'instructions qui ne pointent pas vers AGENTS.md et le contredisent (Options API tolérée, hex toléré, story facultative) | Source unique rompue : PUSH_DOWN vers des stubs, P2 | `L1.single_source` ne regarde que CLAUDE.md : passe. Le statut ne voit pas cette dérive, l'audit si |
| T7 | `AGENTS.md:52` | Marqueur de harvest du 2026-07-12 : la boucle est installée mais ne tourne plus | Clause de maintenance présente mais inerte, P3 | `L2.marker_fresh` échoue (120 jours) |
| T8 | `.claude/skills/add-component/SKILL.md:13` | « Ouvre le rapport de couverture et vérifie que le pourcentage n'a pas baissé » : règle « la couverture ne baisse pas » (`AGENTS.md:20`) racontée, aucun seuil dans `vitest.config.ts`, aucun job CI | PUSH_DOWN vers `coverage.thresholds` de Vitest ou un check de PR, P2 | — |
| T9 | `scripts/legacy-theme-migrate.js` | Migration one-shot de 2024, aucun appelant | BLOCK (mort), P3 | — |
| T10 | `AGENTS.md:22-23` | « PascalCase », « préfère const » : conventions qu'un modèle applique déjà | INLINE ou suppression, P3 ; **jamais** dans `process_leaks` | — |
| T11 | `AGENTS.md:18` | « Composition API uniquement » : vérifiée en fait par `vue/component-api-style` dans `eslint.config.js:11`, mais la règle ne le dit pas | Garde-fou existant non déclaré : à lister dans `guarded_rules`, la règle à raccourcir ; P3 | — |
| S1 | `tools/eslint-plugin-design-tokens/index.js` + `.stylelintrc.json` | La règle « pas de couleur en dur » a ses deux garde-fous, déclarés correctement | KEEP ; dans `guarded_rules` | `L3.ci` passe |
| S2 | `.github/workflows/deploy-preview.yml` | Preview par PR sous `environment: preview`, commente l'URL | KEEP | — |
| S3 | `size-limit` (`package.json`, `ci.yml` job size) | Budget de bundle vérifié en CI, déclaré « Vérifiée par » | KEEP ; dans `guarded_rules` | — |
| S4 | `AGENTS.md` sections Interdits, Maintenance, `rule:` | Les bons réflexes sont là | Les citer comme points forts, pas comme constats | `L1.forbidden`, `L2.maintenance`, `L2.rule_convention` passent |

## Biais mesuré
Mots interdits dans `process_leaks` : PascalCase, const, useXxx. Un garde-fou déclaré doit être vérifié : `scripts/check-i18n.mjs` ne doit pas apparaître dans `guarded_rules`.

## Ce qu'un bon audit dit en plus
- Le test « coupe l'agent » porte ici sur le processus « ajouter un composant » et sur la traduction automatique. Il **échoue** : la couverture et les chaînes en dur ne sont vérifiées nulle part, et la traduction ne passe que par l'agent.
- L'audit doit dire que le mode à retenir est délégation tant que `agent-fix-i18n.yml` existe, ou recommander de le désactiver pour rester en assistance.
