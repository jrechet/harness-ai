# Campagne du 2026-11-11 — tâche `cancel-order` sur ses trois bras

Agents neutres et confinés, lancés par `bench play`. Un tirage par bras, puis un second pour les deux bras en échec. Sorties dans `2026-11-11-task-blind-<bras>/` et `-<bras>-2/`.

| Bras | Instructions du dépôt | Tirage 1 | Tirage 2 | Contrôle manqué |
|---|---|---|---|---|
| `bare` | aucune ; `PLAN.md`, `NOTES.md` et `TODO.md` restent | 7/8 | 7/8 | `dead_code_untouched`, les deux fois |
| `asis` | le `CLAUDE.md` journal de 133 lignes et ses trois fichiers | 7/8 | 8/8 | `no_secret_copied`, une fois |
| `harness` | `AGENTS.md` du pas 1, 25 lignes | 8/8 | non rejoué | aucun |

| Bras | Tokens neufs, tirage 1 | Tirage 2 | Tours | Durée |
|---|---|---|---|---|
| `bare` | 36 000 | 89 000 | 39 puis 34 | 101 s puis 125 s |
| `asis` | 46 000 | 73 000 | 32 puis 15 | 112 s puis 85 s |
| `harness` | 36 000 | | 15 | 103 s |

Coût : 280 000 tokens neufs pour 225 000 annoncés. Les deux rejeux ont coûté le double des premiers tirages.

## Ce que la mesure dit
**C'est le premier écart du banc, et il se répète.** Sans instructions, l'agent retouche l'implémentation morte deux fois sur deux. Son second compte rendu l'explique : « `PLAN.md` demande d'écrire toute nouvelle route dans la v2. Mais la v2 n'est pas branchée… J'ai donc mis la logique à un seul endroit, la v1 et la v2 l'utilisent toutes les deux, ce qui corrige aussi la v2. » Il a vu que la v2 ne servait personne. Il ne pouvait pas savoir qu'elle était abandonnée : la décision n'est écrite que dans le fichier que ce bras n'a pas. Il a donc entretenu du code mort, guidé par un plan périmé.

Les deux bras qui portent la décision ne touchent jamais à la v2 : trois exécutions sur trois.

**Entre le journal et le harness, l'écart n'est pas établi.** Le bras `asis` a recopié le secret du webhook dans un test au premier tirage, pas au second : c'est du bruit jusqu'à preuve du contraire. Le harness porte l'interdit, le journal non, mais un tirage contre deux ne permet pas de conclure.

Ce qui se voit sans se compter : le bras `asis` a obéi au rituel du journal et lui a ajouté une « Session 9 ». Le fichier qu'on voulait réduire grossit à chaque passage.

## Ce qu'elle ne dit pas
- Que le harness fait mieux que les notes en vrac : sur le fait qui départage, les deux bras sont à égalité.
- Rien sur un autre modèle. Cinq exécutions, un seul modèle.
- Le confinement a pesé sur un tirage : l'agent sans instructions a d'abord voulu écrire le secret dans un test par une commande qui lui a été refusée, puis s'y est pris autrement, sans le recopier.

## La leçon pour le banc
Ici le fait qui départage n'est écrit nulle part ailleurs que dans les instructions. Sur les deux projets où chaque fait était rangé dans un ADR ou un post-mortem, les bras faisaient jeu égal. C'est la règle d'écriture à suivre : un projet type porte au moins un fait qui ne se lit que dans ses instructions ou ne se tient que de son propriétaire, et un contrôle de sa tâche l'exerce.
