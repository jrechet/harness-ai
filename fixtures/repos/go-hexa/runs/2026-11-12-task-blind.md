# Campagne du 2026-11-12 — tâche `deposit` rejouée sur ses deux bras

Le projet porte depuis le 2026-11-11 un fait écrit nulle part dans le dépôt : une réponse rejouée le dit dans l'en-tête `Idempotency-Replayed`, dont dépend l'application mobile. Agents neutres et confinés, un tirage par bras.

| Bras | Instructions du dépôt | Note | Contrôle manqué | Tokens neufs | Tours | Durée |
|---|---|---|---|---|---|---|
| `bare` | aucune | 6/7 | `replay_header` | 102 000 | 31 | 161 s |
| `harness` | `AGENTS.md` du pas 1, 25 lignes | 7/7 | aucun | 106 000 | 32 | 177 s |

## Ce que la mesure dit
**Même résultat que sur le monorepo.** Tout ce qui est écrit dans le dépôt, les deux bras le font : la clé d'idempotence exigée, un seul crédit par clé, les fractions de centime refusées, l'architecture tenue. Le seul contrôle qui les sépare est celui du fait que le dépôt ne dit pas. Le bras qui le tient de son harness pose l'en-tête ; l'autre n'en parle pas, et ne pouvait pas.

Ici le harness ne fait gagner ni temps ni tokens : les deux exécutions se valent. Son apport est le fait, pas l'effort.

## Mise en regard avec le 2026-11-11
La veille, sur le même projet sans ce fait, les deux bras rendaient 6/6. La différence d'aujourd'hui vient entièrement de ce que le dépôt ne dit pas. C'est la confirmation de la règle d'écriture : sur un dépôt bien documenté, un harness ne sert qu'à porter ce que la documentation ne porte pas.

## Ce qu'elle ne dit pas
Un tirage par bras, un seul modèle. Et le résultat est celui que la construction du banc annonce : il montre qu'un fait posé dans le harness arrive jusqu'au travail rendu, pas comment il y est entré.
