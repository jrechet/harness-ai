# Compte rendu — harness-init sur shopfront

Branche `develop`, commit `4cfe037` (auteur owner). Date : 2026-11-09.

## Palier atteint selon `harness status`

**Palier 1 « Cadré » : 5/5.** Palier 2 : 2/4, palier 3 : 2/4, palier 4 : 3/5.

Vérifications restantes :
- L2 : aucun harvest depuis moins de 45 jours (marqueur du 2026-07-12, PR 231, sans `harvest.json` en face) ; aucun signal S1–S4 connu. harness-harvest n'est pas installé dans ce repo : la collecte des `rule:` est manuelle jusque-là.
- L3 : 30 % de règles « Vérifiée par » selon le CLI (il compte les 4 Interdits parmi les règles : 3/10 ; sur la section Règles seule, 3/6) ; l'audit a 2 P1 ouverts.
- L4 : le test « coupe l'agent » échoue (5 fuites) ; pas de harvest pour juger les PR d'agent.

## Fichiers créés ou modifiés

| Fichier | Action | Lignes |
|---|---|---|
| `AGENTS.md` | fusionné (44 → 51) | 51 |
| `CLAUDE.md` | inchangé (déjà le stub `@AGENTS.md`) | 1 |
| `.github/copilot-instructions.md` | remplacé par le stub du template (8 → 1) | 1 |
| `.cursor/rules/vue.mdc` → `.cursor/rules/agents.mdc` | renommé, contenu remplacé par le stub du template (8 → 5) | 5 |
| `.claude/skills/add-component/SKILL.md` | complété (14 → 24) | 24 |
| `.harness/state.json` | créé par `harness status` | 353 |
| `.harness/audit.json` | créé (gate) | 70 |
| Non touchés volontairement | `agent-fix-i18n.yml`, `scripts/legacy-theme-migrate.js`, `NewBadge.vue` : constats de fond → prochaines étapes et Questions | — |

Rapport d'audit complet : `/tmp/claude-0/-home-user/c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b/scratchpad/init-merge-eval/audit.md`.

### Ce qui a été gardé, déplacé, retiré, fichier par fichier

**AGENTS.md** (44 lignes, mode assistance)
- Gardé : la table commandes → CI (complétée d'une ligne `build && size`, et la ligne locale dit ce que `check:i18n` vérifie vraiment) ; les règles couleurs (#212), `t()` (#198), story + test, couverture (#240), bundle 250 kB ; les trois Interdits ; la section Maintenance ; le marqueur harvest existant (non modifié : le remettre à aujourd'hui aurait simulé un harvest).
- Modifié : mode → **délégation** ; règle `t()` requalifiée **(non vérifiée)** — l'ancien fichier l'attribuait à `check-i18n.mjs`, qui ne compare que les clés fr/en (`scripts/check-i18n.mjs:2`) et `NewBadge.vue:6` la viole avec une CI verte ; règle `<script setup>` marquée **Vérifiée par** `eslint.config.js:11` (`vue/component-api-style`), ce que le fichier ne disait pas ; les deux autres règles non vérifiées nomment leur cible.
- Retiré : « PascalCase / useXxx » et « préfère const » (bruit : le modèle le fait seul) ; la stack dans « Ce que fait ce repo » (découvrable) ; la section « Ajouter un composant » (dupliquait le skill et le contredisait : story « optionnelle » ici, « obligatoire » dans le skill — tranché pour obligatoire, cohérent avec la règle et sa raison).
- Ajouté : Interdit « pas de PR d'agent fusionnée sans relecture humaine » (demande du propriétaire) ; section « Processus de travail » (obligatoire en délégation) ; section « Tâches déléguées » (`add-component`, et l'état du workflow i18n) ; clause de maintenance complétée (six mois, ligne Mode = sévérité).

**CLAUDE.md** — gardé tel quel.

**.github/copilot-instructions.md** (8 lignes) — tout retiré, remplacé par le stub. Les six lignes contredisaient AGENTS.md : Options API « fine », hex « acceptable », stories « optional », texte en dur « acceptable in admin pages » (le contraire de l'incident #198), `npm test` (script inexistant). Le seul point compatible (« do not touch payment ») est déjà dans AGENTS.md.

**.cursor/rules/vue.mdc** (8 lignes) — tout retiré, fichier renommé `agents.mdc` avec le stub. Mêmes contradictions : Options API tolérée sous 50 lignes, hex toléré avec `// TODO token`, story facultative.

**.claude/skills/add-component/SKILL.md** (14 lignes)
- Gardé : les sept étapes, la story obligatoire et sa raison, les deux locales, `check:i18n`.
- Modifié : étape 6 (« ouvre `coverage/index.html` », infaisable par un agent) → comparer la ligne « All files » du rapport texte à `develop` ; étape 4 dit que `check:i18n` ne lit pas le template ; étape 5 ajoute `lint:style` ; étape 7 cible `develop`, sans auto-merge, et remplace « capture de la story » par les états couverts.
- Ajouté : cas d'arrêt (nouveau token → ticket design ; `src/payment/`) ; « Fini quand » (cinq jobs verts, story + test, locales, couverture, approbation humaine).

## Secrets trouvés

Aucun. Les seules occurrences de `token`/`secret` sont des `${{ secrets.* }}` dans les workflows, tenus en L4. Rien à régénérer.

## Mode retenu et pourquoi

**Délégation**, choisi par le propriétaire : « on a déjà un workflow qui fait tourner un agent la nuit pour les traductions, autant l'assumer ». Conséquence : les règles racontées sans garde-fou sont des P1 à l'audit, la section « Processus de travail » et un contrat par tâche sont obligatoires.

## Règles écrites et leur statut

| Règle | Statut |
|---|---|
| Pas de couleur en dur, tokens seulement (#212) | vérifiée par `tools/eslint-plugin-design-tokens` (`no-raw-color`) + stylelint `color-no-hex` |
| `<script setup>` uniquement | vérifiée par eslint `vue/component-api-style` (`eslint.config.js`) |
| Bundle initial < 250 kB gzip | vérifiée par `size-limit` (`package.json`, job `size`) |
| Toute chaîne visible passe par `t()` (#198) | **non vérifiée** — cible : eslint `vue/no-bare-strings-in-template` |
| Un composant a une story et un test | **non vérifiée** — cible : script de check des paires dans le job lint |
| La couverture unitaire ne baisse pas (#240) | **non vérifiée** — cible : `coverage.thresholds` dans `vitest.config.ts` |

Interdits (4) : `src/payment/` ; `tokens.css` sans ticket ; PR d'agent sans relecture humaine ; `eslint-disable` sans justification datée. Aucun n'a de garde-fou L4 (pas de CODEOWNERS, pas de protection de branche connue).

## Commandes

Confirmées (exécutées ici) : `node scripts/check-i18n.mjs` → « i18n OK (3 clés) », exit 0 ; `node scripts/i18n-report.mjs` → `[]`, exit 0 ; `python3 harness.py status`.

**Non confirmées** (pas de `node_modules`, npm impossible) : `npm run lint`, `npm run lint:style`, `npm run test:unit`, `npm run test:e2e`, `npm run build`, `npm run size`. Hypothèse prise sans question : elles restent dans AGENTS.md parce qu'elles existent dans `package.json` et que `ci.yml` lance exactement celles-là.

## Résultat du gate (harness-audit)

- Score de santé **16/100**, test « coupe l'agent » **ÉCHEC** (5 fuites), **2 P1**, 4 P2, 1 P3. 22 éléments inventoriés. JSON dans `.harness/audit.json`, pris en compte par `harness status` (vue par couche : L2 9 dont 4 mal placés, L3 10 dont 2, L4 2, MIXED 1).
- Constats structurels corrigés pendant l'init : longueur (51 < 60), bruit retiré, doublon du skill retiré, stubs cohérents, clause de maintenance, chaque règle non vérifiée nomme sa cible.
- P1 restants, non corrigeables dans l'init :
  1. `agent-fix-i18n.yml:21-22` fusionne automatiquement la PR du bot (`gh pr merge --auto`), en contradiction directe avec l'Interdit du propriétaire ; de plus il cible `.[0]` des PR du bot (pas forcément la sienne) et donne `Edit` sans restriction (`:19`).
  2. La règle `t()` n'a aucun garde-fou et `NewBadge.vue` la viole aujourd'hui.

## Trois prochaines étapes

1. **Pousser la première règle non vérifiée en CI** : activer `vue/no-bare-strings-in-template` dans `eslint.config.js` et corriger `NewBadge.vue` (« Nouveau » → `t()`), puis raccourcir `AGENTS.md:22` en « Vérifiée par ».
2. **Retirer l'étape « Auto-merge when green »** d'`agent-fix-i18n.yml` et poser `.github/CODEOWNERS` (`src/payment/`, `src/styles/tokens.css`) avec revue requise sur `develop` ; sortir le prompt inline dans `.claude/skills/fix-i18n/SKILL.md`. Si la branche par défaut GitHub n'est pas `develop`, le workflow planifié doit aussi y arriver, sinon il est inerte.
3. **Seuils de couverture** dans `vitest.config.ts` au niveau mesuré par un premier `npm run test:unit`, puis supprimer l'étape 6 du skill ; dans la foulée, `scripts/check-components.mjs` dans le job lint pour la règle story + test.

## Questions

1. Retirer dès maintenant l'étape auto-merge d'`agent-fix-i18n.yml` (lignes 21-23) ? Je ne l'ai pas fait : le skill réserve les changements de workflow à une étape de remédiation approuvée. Défaut proposé : oui, dans la PR suivante, c'est la conséquence directe de votre Interdit.
2. Supprimer `scripts/legacy-theme-migrate.js` (aucun appelant, CommonJS dans un paquet ESM) ? Défaut proposé : oui.
3. Quelle est la branche par défaut sur GitHub ? Si ce n'est pas `develop`, le workflow nocturne et ce commit doivent être portés sur elle. Défaut proposé : je suppose `develop` tant que vous ne dites pas le contraire.
