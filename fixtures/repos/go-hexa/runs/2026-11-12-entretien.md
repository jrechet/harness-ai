# L'entretien du pas 1, avant et après — 2026-11-12

Ce qui a été mesuré : le pas 1 joué à l'aveugle par `bench init`, avec un propriétaire qui ne répond qu'à ce qu'on lui demande (`owner.json`). Deux exécutions, même jour, même modèle, même propriétaire ; seul le texte du skill change.

| | Avant | Après |
|---|---|---|
| Skill | `main`, trois questions | branche `stress/2026-11-12`, une quatrième question |
| Questions posées | 6 | 7 |
| Le fait que seul le propriétaire détient | jamais demandé | demandé à la question 4 |
| Note du pas 1 | 5/6 | 6/6, conforme |
| Tokens neufs | 83 911 | 47 769 |

Pour mémoire, le même pas avec les réponses données d'avance, le même jour : 6/6 (`2026-11-12-init-blind`). Le propriétaire qui dit tout de lui-même masquait le défaut.

## Ce que chaque agent a demandé
- **Avant** : les trois questions du skill, puis trois sur ce qu'il a vu dans le dépôt : le flottant de `fees.go`, la cible `make e2e` absente, `POST /accounts` sans clé d'idempotence. Rien sur ce que l'équipe sait sans l'avoir écrit.
- **Après** : les quatre questions du skill, la quatrième mot pour mot, puis trois sur le dépôt. La réponse devient une règle datée de juin 2026, « dit par l'équipe », avec le contre-exemple `POST /transfers` signalé.

## Le propriétaire simulé, retouché après les deux mesures
Pendant les deux mesures, `owner.json` était le même. Lu ensuite, il était trop littéral : trois façons plausibles sur huit de demander ce qui n'est écrit nulle part obtenaient la réponse, et deux réponses tombaient hors sujet. Ses déclencheurs ont été élargis : sept sur huit, et un test fige les deux côtés. Rejoués contre les nouveaux déclencheurs, les deux entretiens gardent leur verdict : avant, jamais demandé ; après, à la question 4.

## Ce que ça ne prouve pas
- **Biais d'auteur.** La question du skill et les déclencheurs du propriétaire ont été écrits par la même session, et l'agent a posé la question mot pour mot. Le test des formulations voisines réduit ce biais sans l'effacer. Un vrai propriétaire reste la référence.
- **Un tirage par bras**, un seul modèle.
- **Avant, la question 6 portait sur l'idempotence.** Un vrai propriétaire aurait peut-être cité l'en-tête à cette occasion ; le simulé ne le fait pas.
- **Rien hors du banc de réglage.** Le projet tenu à l'écart porte son fait dans ses propres instructions : il ne peut pas mesurer cette question. Aucun autre projet n'a de propriétaire simulé.
