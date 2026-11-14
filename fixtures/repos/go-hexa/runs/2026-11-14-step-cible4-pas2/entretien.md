# Entretien de go-hexa : 2 question(s)

- I6, que seul le propriétaire détient : jamais demandé

## 1
**Question** : Le prochain pas est d'écrire le contrat de la première tâche répétitive que vous confiez à un agent (.claude/skills/<tâche>/SKILL.md : étapes, vérifications, critère de fini). Quelle est cette tâche ? Défaut si vous n'avez pas d'idée : aucun, je ne l'invente pas.

**Réponse** (premiere-tache, fini) : Ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test.
Une tâche est finie quand `make test` et `make arch` passent, qu'un test couvre le changement, et que la PR dit pourquoi en deux lignes.

## 2
**Question** : Pour cette tâche, y a-t-il une étape, une vérification ou un point d'arrêt propre à elle que l'agent ne peut pas deviner (au-delà de make test / make arch) ?

**Réponse** (par défaut) : Regardez dans `docs/`, c'est écrit. L'équipe ne sait rien de plus que ce que disent les ADR, le post-mortem et la note d'exploitation.
