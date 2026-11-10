# Pas 1 par l'auteur de la fixture — 2026-11-10

Ce que le pas 1 de harness doit poser sur ce dépôt, écrit par la session qui a planté les faits : le palier 1 et rien d'autre. Ni section Maintenance, ni marqueur de harvest, ni Processus de travail, ni contrat : ce sont les pas suivants.

C'est une **base de régression** pour le noteur (`fixture check django-mvc --init <ce dossier>`) et le bras `harness` par défaut du banc, pas une mesure du skill.

Les dates des règles sont celles de l'incident ou de la décision, pas celle du pas : une règle ne rajeunit pas parce qu'on la recopie. La règle des migrations porte la date de la mise en production (`docs/exploitation.md`), celle des services la date de l'ADR.

## Ce qui a été retiré, et pourquoi
`AGENTS.md` : 67 lignes avant, 26 après. `CLAUDE.md` : 23 lignes avant, 1 après.

| Retiré | Raison |
|---|---|
| « Le projet » et son arborescence | Découvrable en lisant le dépôt |
| `python manage.py test --settings=cursus.settings_ci` | Périmé : `cursus/settings_ci.py` n'existe plus, la commande échoue. Remplacée par celle de `CLAUDE.md`, vérifiée |
| « Réfléchis étape par étape », « N'invente pas d'API Django » | Écrit pour d'anciens modèles ; ne change plus rien |
| « Donne toujours le fichier complet, jamais un extrait » | Nuisible : fait réécrire des fichiers entiers pour contourner un défaut disparu |
| « Réponds en français » | Préférence de conversation, pas une règle du dépôt ; la langue des commits se lit dans l'historique |
| PEP 8, noms clairs, docstring, pas de code commenté, un test par changement | Générique : un modèle le fait sans qu'on le dise |
| Python 3.8 | Périmé, confirmé par le propriétaire : le serveur a été remplacé en février 2025. Le code et Django 5.1 le contredisaient déjà |
| Django 4.2 LTS, pas de `db_default` ni de `GeneratedField` | Périmé, confirmé par le propriétaire : l'hébergeur a changé. `requirements.txt` et une migration de 2025 le contredisaient déjà |
| « Vérifié par : le job `frozen-migrations` » | Faux par dérive : le job n'est pas dans `ci.yml`. La règle reste, marquée `(non vérifiée)` |
| « ouvre la page avec django-debug-toolbar et compte les requêtes » | Périmé : l'outil n'est plus installé, le test `catalog/tests/test_queries.py` a pris sa place |
| « Dates : `timezone.now()`, jamais `datetime.now()` » | Ce qu'un modèle fait dans un projet Django, et que Django signale par un avertissement. Le contrôle `no_naive_now` de la tâche dit si ce retrait coûte |
| « Git » | Découvrable : la CI ne tourne que sur les PR vers `main` |
| `CLAUDE.md`, « toute inscription créée envoie sa confirmation » | Nuisible : la copie contredit l'original pour un traitement en masse |
| `CLAUDE.md`, tout le reste | Doublon. Ses deux apports, la commande de test et le test de requêtes, sont reportés dans `AGENTS.md` |

## Ce qui a été gardé, et ce qui a changé
| Règle | Changement |
|---|---|
| E-mails | Gardée dans son fond, avec l'incident en « Pourquoi ». Ajout : `services.enroll()` envoie toujours, ce que dit le post-mortem et pas l'ancien fichier |
| Capacité | Gardée. Ajout : SQLite ignore le verrou, et l'admin n'est pas un modèle à suivre |
| Requêtes | Raccourcie : « Vérifiée par : `catalog/tests/test_queries.py` » remplace la vérification à la main |
| Migrations appliquées | Gardée, passée de « vérifiée » à `(non vérifiée)` ; reprise en Interdit |
| Migrations oubliées | Devenue une ligne de la table des commandes : la CI la porte |
| Services | Gardée, avec « pas d'incident connu » |

Les Interdits viennent de l'entretien (`owner.md`) et de `docs/exploitation.md`.
