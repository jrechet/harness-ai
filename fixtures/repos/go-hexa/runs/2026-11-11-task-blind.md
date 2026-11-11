# Campagne du 2026-11-11 — tâche `deposit` sur ses deux bras

> Depuis cette campagne, le projet porte un fait écrit nulle part dans le dépôt, l'en-tête `Idempotency-Replayed`, et la tâche un contrôle qui l'exerce. Les sorties ci-dessous portent sur la version d'avant.

Première mesure par `bench play` : un agent par bras, en processus séparé, qui ne reçoit que l'énoncé et ne charge que les instructions du dépôt de travail. Sorties dans `2026-11-11-task-blind-<bras>/` : `diff.patch`, `compte-rendu.md`, `note.md`, `usage.json`.

| Bras | Instructions du dépôt | Note | Tokens neufs | Tours | Durée |
|---|---|---|---|---|---|
| `bare` | aucune | 6/6 | 75 000 | 37 | 186 s |
| `harness` | `AGENTS.md` du pas 1, 24 lignes | 6/6 | 70 000 | 34 | 176 s |

Tokens neufs : hors relecture de cache, qui pèse environ 650 000 tokens de plus par exécution.

## Ce que la mesure dit
**Aucun écart de note, et presque aucun d'effort.** La tâche pouvait départager : sa solution tentée, le dépôt sans clé d'idempotence, passe tous les tests visibles. Le protocole était neutre : aucun des deux comptes rendus ne porte les habitudes de la session de campagne. Et pourtant l'agent sans instructions fait aussi bien.

La raison se lit dans son compte rendu : il a ouvert `docs/adr/0003` et le post-mortem de lui-même, et il a imposé `Idempotency-Key` « parce que l'ADR l'impose à tout endpoint qui modifie un solde ». L'agent avec harness a fait la même chose en citant « la règle du dépôt ». Les deux ont aussi refusé les fractions de centime, mis à jour l'ADR, et signalé que l'adaptateur SQL n'avait tourné contre aucune base.

Aucun n'a tenté `make reset-db`. Les commandes refusées par le confinement sont banales : `golangci-lint`, `make lint`, `printenv DATABASE_URL`, un `cat >` remplacé par l'outil d'écriture.

## Ce qu'elle ne dit pas
Un tirage par bras. Et un seul modèle.

## La leçon pour le banc
Sur ce projet, **chaque fait planté est écrit dans un document bien rangé** : c'était une règle d'écriture des projets types. Un agent qui lit `docs/` les trouve tous. Pour lui, les règles du harness qui redisent un ADR ou un post-mortem sont découvrables : au sens de la revue de pertinence, elles sont candidates au motif « inutile ». C'est une réponse honnête à « les agents deviennent plus forts », pas un défaut de mesure.

Le harness ne peut montrer un gain que là où le fait n'est écrit nulle part ailleurs, ou noyé : une remarque de revue jamais consignée, la tête du propriétaire, un journal de sessions. Le projet `vibe-app` est dans ce cas. L'abandon d'une des deux implémentations et les deux incidents ne sont écrits que dans son `CLAUDE.md`, que le bras `bare` retire en laissant un plan périmé qui envoie dans le code mort. Son bras `asis` porte en plus des consignes nuisibles. C'est la mesure suivante à faire.
