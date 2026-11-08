# Templates écrits par harness-init

Trois blocs : le AGENTS.md jour 1, les stubs, et la convention `rule:`. Les crochets `<…>` sont à remplir ; une section dont on n'a rien de non-découvrable à dire est **supprimée**, pas remplie.

Budget : AGENTS.md sous 60 lignes. Si une section déborde, son contenu devient un skill dans `.claude/skills/` ou un fichier dans `docs/agents/` et AGENTS.md garde une ligne de pointeur.

---

## 1. AGENTS.md — mode délégation (défaut)

```markdown
# <nom du repo> — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
<Deux lignes max : quoi, pour qui. Pas la stack, pas l'arborescence.>

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| <zone> | `<commande confirmée>` | <job / check, ou « rien » > |

## Règles
Chaque règle dit pourquoi et par quoi elle est vérifiée. Une règle `(non vérifiée)` est une dette : la prochaine étape est de la pousser en CI.
- <Règle en une phrase.> Pourquoi : <incident ou raison>. Vérifiée par : <chemin du linter / test / check> | (non vérifiée)

## Interdits
<Ce qu'un agent ne fait jamais, même si la tâche semble le demander : dossiers, secrets, migrations prod, force push, suppression de tests…>

## Processus de travail
- Arrête-toi et pose la question quand : <ex. la tâche implique un choix d'architecture, touche à un interdit, ou la CI échoue pour une raison étrangère à la tâche>.
- Une tâche est finie quand : <ex. CI verte, PR sous N fichiers, description qui explique le pourquoi, pas de TODO laissé>.
- CI rouge : <ex. corrige si la cause est dans ton diff ; sinon signale-le dans la PR et n'y touche pas>.
- Test flaky : <ex. relance une fois ; s'il reste instable, ouvre une issue, ne le désactive pas>.

## Tâches déléguées
Chaque tâche récurrente a son contrat dans `.claude/skills/` :
- `<nom-du-skill>` — <une ligne>.

## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate. Elle est ajoutée ici dans la même PR, avec le lien vers le commentaire, ou collectée par harness-harvest.
- Avant d'ajouter une phrase, chercher si un linter, un test ou un check CI peut porter la règle : une règle vérifiée est raccourcie, une règle racontée est une dette.
- Une règle sans incident depuis six mois est candidate à suppression lors du prochain harness-audit.
- Ce fichier est relu par `harness-audit` ; la ligne « Mode » fixe la sévérité.
- `harness-harvest` relit l'activité depuis le marqueur ci-dessous et propose les changements dans une PR dédiée.

<!-- harvest: last=<AAAA-MM-JJ de l'init> ref=init -->
```

## 1b. Variante assistance

Même squelette, avec ces différences :
- Ligne de mode : `Mode : **assistance**. L'humain pilote et relit chaque diff ; ce fichier évite les allers-retours, il n'est pas un garde-fou.`
- Section « Processus de travail » supprimée.
- Section « Tâches déléguées » supprimée, sauf si une tâche précise est déjà déléguée.
- La mention `(non vérifiée)` reste, mais elle n'est pas une dette prioritaire.

---

## 2. Stubs

`CLAUDE.md` (une seule ligne) :
```
@AGENTS.md
```

`.github/copilot-instructions.md` (Copilot ne sait pas inclure un fichier) :
```markdown
Les instructions de ce dépôt vivent dans `AGENTS.md` à la racine. Lis-le avant toute modification et applique-le ; aucune règle n'est définie ici.
```

`.cursor/rules/agents.mdc` :
```markdown
---
description: Instructions du dépôt
alwaysApply: true
---
Les instructions de ce dépôt vivent dans `AGENTS.md` à la racine. Lis-le et applique-le ; aucune règle n'est définie ici.
```

---

## 3. Convention `rule:`

Dans un commentaire de review, sur une ligne ou sur la PR :

```
rule: <la règle en une phrase, au présent, vérifiable>
```

Exemples :
- `rule: les appels HTTP sortants passent par le client de src/http, jamais fetch direct`
- `rule: une migration ne supprime jamais une colonne dans la même release que le code qui cesse de la lire`

Ce qu'on en fait, dans l'ordre :
1. Chercher un garde-fou : règle eslint, test d'architecture, script de check en PR gate. Si possible, la règle entre en CI et AGENTS.md ne garde qu'une ligne « Vérifiée par ».
2. Sinon, l'ajouter dans « Règles » avec le lien du commentaire comme justification et la mention `(non vérifiée)`.
3. Jamais sans justification : un `rule:` sans contexte est renvoyé à son auteur.
