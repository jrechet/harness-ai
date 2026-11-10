# Gabarits, pas par pas

Chaque pas ajoute son bloc, et seulement le sien. Les crochets `<…>` sont à remplir ; une section dont on n'a rien de non-découvrable à dire est **supprimée**, pas remplie.

Budget : AGENTS.md sous 60 lignes, tous pas confondus. Si une section déborde, son contenu devient un skill dans `.claude/skills/` ou un fichier dans `docs/agents/`, et AGENTS.md garde une ligne de pointeur.

---

## Pas 1 — Cadré (harness-init)

```markdown
# <nom du repo> — instructions pour les agents

Mode : **délégation**. Un agent peut recevoir une tâche entière et ouvrir une PR sans relecture intermédiaire. Ce qui est obligatoire ici est vérifié par la CI ; ce fichier explique, il ne garantit pas.

## Ce que fait ce repo
<Deux lignes max : quoi, pour qui, où sont les décisions et les incidents. Pas la stack, pas l'arborescence.>

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| <zone> | `<commande confirmée>` | <job qui bloque, ou « rien »> |

## Règles
- <Règle en une phrase.> Pourquoi : <incident ou raison, ou « pas d'incident connu »>. Vérifiée par : <chemin du garde-fou qui bloque> | (non vérifiée) [<AAAA-MM>]

## Interdits
- <Ce qu'un agent ne fait jamais, même si la tâche semble le demander.> Pourquoi : <…> [<AAAA-MM>]
```

Variante assistance, ligne de mode : `Mode : **assistance**. L'humain pilote et relit chaque diff ; ce fichier évite les allers-retours, il n'est pas un garde-fou.`

### Stubs

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

## Pas 2 — Bouclé (harness-step)

À la fin d'AGENTS.md :

```markdown
## Maintenance de ce fichier
- Un commentaire de review qui commence par `rule:` est une règle candidate. Elle est ajoutée ici dans la même PR, datée, avec le lien vers le commentaire, ou collectée par harness-harvest.
- Avant d'ajouter une phrase, chercher si un linter, un test ou un check CI peut porter la règle : une règle vérifiée est raccourcie, une règle racontée est une dette.
- Une règle sans incident depuis six mois, ou écrite pour une génération de modèles passée, est candidate au retrait à la prochaine revue de pertinence.

<!-- harvest: last=<AAAA-MM-JJ du pas> ref=init -->
```

Le marqueur `ref=init` ne se pose que sur un fichier qui n'en avait pas : remettre à aujourd'hui un marqueur périmé simulerait un harvest qui n'a pas eu lieu.

### La convention `rule:`

Dans un commentaire de review, sur une ligne ou sur la PR :

```
rule: <la règle en une phrase, au présent, vérifiable>
```

Exemples :
- `rule: les appels HTTP sortants passent par le client de src/http, jamais fetch direct`
- `rule: une migration ne supprime jamais une colonne dans la même release que le code qui cesse de la lire`

Ce qu'on en fait, dans l'ordre :
1. Chercher un garde-fou : règle de lint, test d'architecture, script de check en PR. Si possible, la règle entre en CI et AGENTS.md ne garde qu'une ligne « Vérifiée par ».
2. Sinon, l'ajouter dans « Règles » avec le lien du commentaire comme justification, la mention `(non vérifiée)` et la date.
3. Jamais sans justification : un `rule:` sans contexte est renvoyé à son auteur.

---

## Pas 4 — Délégué (harness-step)

Avant « Maintenance de ce fichier » :

```markdown
## Processus de travail
- Arrête-toi et pose la question quand : <ex. la tâche implique un choix d'architecture, touche à un interdit, ou la CI échoue pour une raison étrangère à la tâche>.
- Une tâche est finie quand : <ex. CI verte, un test couvre le changement, la PR explique le pourquoi, pas de TODO laissé>.
- CI rouge : <ex. corrige si la cause est dans ton diff ; sinon signale-le dans la PR et n'y touche pas>.
- Test flaky : <ex. relance une fois ; s'il reste instable, ouvre une issue, ne le désactive pas>.

## Tâches déléguées
- `<nom-du-skill>` (`.claude/skills/<nom-du-skill>`) — <une ligne>.
```

Une ligne de « Tâches déléguées » ne s'écrit que dans le pas qui crée le contrat : `harness status` signale un contrat cité sans `SKILL.md`.

En assistance, ces deux sections n'existent pas, sauf si une tâche précise est déjà déléguée.
