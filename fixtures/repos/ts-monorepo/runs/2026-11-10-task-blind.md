# Campagne du 2026-11-10 — tâche `escalated` sur ses trois bras

Première mesure avant et après du banc. Trois agents neufs, la même consigne au mot près, un bras chacun. Sorties dans `2026-11-10-task-blind-<bras>/` : `diff.patch`, `compte-rendu.md`, `note.md`.

| Bras | Instructions du dépôt | Note | Tokens | Appels d'outil | Durée |
|---|---|---|---|---|---|
| `bare` | aucune | 7/7 | 126 000 | 33 | 232 s |
| `asis` | `CLAUDE.md` généré, 104 lignes, et la note du web | 7/7 | 113 000 | 18 | 148 s |
| `harness` | `AGENTS.md` du pas 1, 23 lignes | 7/7 | 116 000 | 27 | 143 s |

Coût : 355 000 tokens, pour 270 000 annoncés. L'estimation par exécution était trop basse ; elle est corrigée dans `cli/harnesslib/bench.py`.

## Ce que la mesure dit
**Aucun écart de note.** Sur cette tâche, avec ce modèle, le harness ne change pas le résultat, et le fichier généré jamais relu ne l'abîme pas. Un tirage par bras : ce n'est pas une preuve, ni dans un sens ni dans l'autre.

Le seul écart visible est d'effort : sans instructions, l'agent a mis plus de temps et plus d'appels pour retrouver seul l'ADR et le post-mortem. Sur un tirage, c'est un indice.

Ce que les comptes rendus montrent :
- `bare` a lu `README.md`, l'ADR 0001 et le post-mortem de lui-même, et a appliqué la consigne du post-mortem.
- `asis` a écarté de lui-même trois consignes du fichier généré, en le disant : la confirmation avant chaque commande, les commandes `lint` et `build` qui n'existent pas, l'import du web vers l'API.
- `harness` cite `AGENTS.md` pour avoir lancé tous les tests. Son compte rendu est le plus court.

## Pourquoi elle ne départage rien
1. **La tâche est rattrapée par le projet.** La solution tentée échoue aux tests et au contrôle de types du dépôt : un agent qui lance `npm test` la corrige seul. La tâche mesure « l'agent lance-t-il les tests », pas ce que les instructions lui apprennent. `bench selftest` le signale désormais par un avertissement.
2. **Le fait planté est découvrable.** L'incident est dans `docs/postmortems/`, et un agent soigneux lit `docs/`.
3. **Le bras nu ne l'était pas.** Les agents ont été lancés depuis la session de campagne et en ont hérité les consignes : leurs comptes rendus portent la section « Questions » et les « Hypothèses prises sans question » de cette session, et l'un d'eux s'est servi d'un outil de la session pour déposer une suggestion de tâche. Les trois bras avaient donc un harness commun par-dessus le leur.

## Défaut du projet trouvé par un agent
Le bras `bare` a relevé que le trou de CI est plus étroit que ne le dit le post-mortem : le job `api` lance le contrôle de types de tout le dépôt quand `packages/shared` change, donc un libellé manquant y serait attrapé. Seuls les tests du web ne tournent pas. Le fait I1 de cette fixture est à resserrer, ou le job `api` à limiter à son workspace.
