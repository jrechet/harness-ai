# Propriétaire fictif — go-hexa (ledger)

Ce fichier se donne à l'agent qui joue harness-init à l'aveugle : ce sont les réponses de l'équipe à l'entretien. Il ne contient aucun des faits plantés ; ceux-là sont dans le dépôt, à trouver.

## Réponses à l'entretien
1. **Mode** : délégation. On veut confier des tickets entiers et relire la PR à la fin.
2. **Équipe** : quatre développeurs, une personne QA qui utilise la base de staging.
3. **CI** : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas, « il y a trop d'avertissements hérités ».
4. **Outils** : Claude Code et Copilot.
5. **Première tâche à déléguer** : ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test.
6. **Interdits** : toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## Si l'agent pose d'autres questions
- « Pourquoi le lint ne bloque pas ? » : personne n'a pris le temps de solder la dette. Oui, on sait que ça affaiblit ce qui s'appuie dessus.
- « `POST /accounts` n'a pas de clé d'idempotence ? » : exact, c'est au backlog, pas prioritaire.
- « `make e2e` ? » : la cible a été retirée il y a un an avec l'ancien banc de tests, le README n'a pas suivi.
- Sur tout le reste : « regarde dans `docs/`, c'est écrit ». L'équipe ne sait rien de plus que ce que disent les ADR, le post-mortem et la note d'exploitation.

## Ce que l'équipe attend
Un fichier court. Elle a déjà un CONTRIBUTING que personne ne lit et ne veut pas d'un second.
