# Propriétaire fictif — django-mvc (cursus)

Ce fichier se donne à l'agent qui joue harness-init ou harness-audit à l'aveugle : ce sont les réponses de l'équipe. Il ne contient aucun des faits plantés ; ceux-là sont dans le dépôt, à trouver.

## Réponses à l'entretien
1. **Mode** : délégation. On veut confier des tickets entiers et relire la PR à la fin.
2. **Équipe** : trois développeurs, dont aucun n'était là au démarrage du projet ; une responsable formation qui se sert de l'admin.
3. **CI** : GitHub Actions, un seul job, `test`. Il bloque la fusion sur `main`.
4. **Outils** : Claude Code pour deux d'entre nous, Copilot pour le troisième.
5. **Première tâche à déléguer** : un traitement de données d'inscription, import ou export, de la vue jusqu'au test.
6. **Interdits** : modifier une migration déjà appliquée ; envoyer un vrai e-mail depuis autre chose que la production ; sortir du serveur des données personnelles d'inscrits.

## Si l'agent pose d'autres questions
- « D'où viennent AGENTS.md et CLAUDE.md ? » : AGENTS.md a été écrit à la main fin 2024 par la développeuse qui a monté le projet. Elle est partie début 2025 et personne ne l'a relu depuis. CLAUDE.md a été recopié de mémoire par l'un de nous quand on a commencé avec Claude Code ; depuis, quand on corrige quelque chose, c'est dans celui-là.
- « Je peux retirer des lignes ? » : oui. Dis ce que tu retires et pourquoi.
- « Le serveur est encore en Python 3.8 ? » : non. Il a été remplacé en février 2025, la production tourne en 3.12.
- « Vous êtes tenus à Django 4.2 LTS ? » : plus depuis le changement d'hébergeur, au même moment. On suit les versions courantes, 5.1 aujourd'hui.
- « La CI a changé ? » : oui, début 2025, avec l'hébergeur. On a repris les tests sur GitHub Actions. Personne n'a fait l'inventaire de ce que l'ancienne vérifiait d'autre.
- « Pourquoi rien ne vérifie le verrou ? » : la CI tourne sous SQLite et personne n'a monté de PostgreSQL pour les tests.
- Sur tout le reste : « regarde dans `docs/`, c'est écrit ». L'équipe ne sait rien de plus que ce que disent les post-mortems, l'ADR et la note d'exploitation.

## Ce que l'équipe attend
Savoir ce qui tient encore dans un fichier écrit avec soin il y a deux ans, et ne garder qu'un seul fichier.
