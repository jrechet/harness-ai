# Entretien de go-hexa : 2 question(s)

- I6, que seul le propriétaire détient : jamais demandé

## 1
**Question** : Quelle est la première tâche répétitive que vous voulez confier entière à un agent, avec son contrat de tâche ? Défaut proposé si vous n'avez pas de préférence : « ajouter une route HTTP qui modifie un solde » (ex. un nouveau type de mouvement), puisque c'est là que portent l'idempotence, Money et les migrations.

**Réponse** (premiere-tache, interdits) : Ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test.
Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## 2
**Question** : Pour cette tâche, y a-t-il une étape ou une vérification que vous faites toujours à la main en relisant ces PR et qu'il faudrait écrire dans le contrat ?

**Réponse** (par défaut) : Regardez dans `docs/`, c'est écrit. L'équipe ne sait rien de plus que ce que disent les ADR, le post-mortem et la note d'exploitation.
