# Format du rapport d'audit

Reproduis ces sections dans cet ordre, avec ces titres. Une section sans contenu contient le mot « Aucun ». Le bloc JSON final suit exactement le schéma donné.

---

# Audit du harness — <nom du processus>

**Périmètre** : <repo / dossiers audités> · **Date** : <AAAA-MM-JJ> · **Éléments inventoriés** : <n>

## 1. Synthèse

- **Score de santé** : <0–100> — <une phrase : l'agent est-il un accélérateur ou un pilier ?>
- **Résultat du test « coupe l'agent »** : RÉUSSI / ÉCHEC — <n> étape(s) du processus n'existent que dans des prompts.
- **Points bloquants (P1)** : <n>
- **Les trois actions qui changent le plus les choses** :
  1. …
  2. …
  3. …

Le score se calcule ainsi : 100, moins 25 par P1, moins 8 par P2, moins 2 par P3, borné à 0. Le test « coupe l'agent » en échec plafonne le score à 60.

## 2. Carte du harness

Tableau de tous les éléments inventoriés :

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|

Puis le processus nominal, étape par étape, avec la couche qui porte chaque étape :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|

## 3. Fuites : règles et étapes racontées sans vérification

Étapes de processus ou règles obligatoires qui ne vivent que dans un prompt, un SKILL.md ou un AGENTS.md, sans garde-fou en code ni en pipeline. Pour chacune : la règle ou l'étape, où elle est racontée (chemin:ligne), ce qui se passe si l'agent la saute, où elle devrait vivre et avec quel outil (sous-commande CLI, règle eslint, test ArchUnit, PR gate…).

Mentionne aussi, en une ligne chacune, les règles qui **ont** leur garde-fou : c'est la partie saine du harness et elle guide ce qui peut être raccourci dans les fichiers d'instructions.

## 3b. Coût de contexte (si des fichiers d'instructions sont dans le périmètre)

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|

Suivi d'une phrase sur la justification des règles (pourquoi + incidents cités ?) et sur la présence d'une clause de maintenance.

## 4. Constats par élément

Un bloc par élément, dans l'ordre P1 → P2 → P3 puis KEEP en fin :

### [<VERDICT>] [<P1|P2|P3|—>] <élément> — <chemin>
- **Fait aujourd'hui** : …
- **Problème** : … (preuve : chemin:ligne)
- **Doit devenir** : …
- **Critère de vérification** : …

Les éléments KEEP ont une ligne : `### [KEEP] <élément> — <chemin>` suivie d'une phrase.

## 5. Plan de remédiation

Ordonné par priorité puis par dépendance.

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|

## 6. Ce que l'audit n'a pas pu vérifier

Fichiers manquants, workflows non lisibles, tests non exécutables, hypothèses faites. Vide = « Aucun ».

## 7. Données machine

```json
{
  "audit": {
    "process": "<nom>",
    "scope": "<repo/dossiers>",
    "date": "<AAAA-MM-JJ>",
    "health_score": 0,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 0 }
  },
  "elements": [
    {
      "id": "<slug>",
      "path": "<chemin>",
      "declared_layer": "L1|L2|L3|L4",
      "actual_layer": "L1|L2|L3|L4|MIXED",
      "called_by": ["<id>"],
      "calls": ["<id>"],
      "verdict": "KEEP|INLINE|PUSH_DOWN|PROMOTE|MERGE|SPLIT|BLOCK",
      "priority": "P1|P2|P3|null",
      "finding": "<une phrase>",
      "evidence": ["<chemin:ligne>"],
      "target": "<une phrase>",
      "check": "<une phrase>"
    }
  ],
  "process_leaks": [
    { "rule": "<règle ou étape>", "told_in": "<chemin:ligne>", "if_skipped": "<conséquence>", "belongs_in": "L3|L4", "guard_tool": "<outil cible>" }
  ],
  "guarded_rules": [
    { "rule": "<règle>", "told_in": "<chemin:ligne>", "guarded_by": "<chemin du linter/test/gate>" }
  ],
  "instruction_files": [
    { "path": "<chemin>", "loaded_lines": 0, "instruction_pct": 0, "reference_pct": 0, "noise_pct": 0, "justified_rules": true, "maintenance_clause": true }
  ],
  "remediation": [
    {
      "order": 1,
      "priority": "P1",
      "verdict": "PUSH_DOWN",
      "element": "<id>",
      "action": "<une phrase>",
      "depends_on": [],
      "check": "<une phrase>",
      "needs_human_approval": true
    }
  ],
  "unverified": ["<texte>"]
}
```
