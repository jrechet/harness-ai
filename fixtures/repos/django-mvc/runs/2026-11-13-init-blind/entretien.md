# Entretien de django-mvc : 9 question(s)

- I5, que seul le propriétaire détient : demandé à la question 4

## 1
**Question** : 1. Mode : délégation (défaut : l'agent reçoit une tâche entière et revient avec une PR, personne ne relit en route) ou assistance (l'humain relit chaque diff en direct) ?

**Réponse** (mode) : Délégation. On veut confier des tickets entiers et relire la PR à la fin.

## 2
**Question** : 2. Interdits : qu'est-ce qu'un agent ne doit jamais toucher ou faire (dossiers, secrets, base partagée, migrations prod, force push...) ?

**Réponse** (interdits) : Modifier une migration déjà appliquée ; envoyer un vrai e-mail depuis autre chose que la production ; sortir du serveur des données personnelles d'inscrits.

## 3
**Question** : 3. Outils et CI : quels agents utilisez-vous (Claude Code seul, ou aussi Copilot, Cursor, Codex) ? Quelle CI, et quels checks bloquent la fusion aujourd'hui ?

**Réponse** (ci, outils) : GitHub Actions, un seul job, `test`. Il bloque la fusion sur `main`.
Claude Code pour deux d'entre nous, Copilot pour le troisième.

## 4
**Question** : 4. Qu'est-ce que vous redites à chaque revue, ou qu'un nouveau venu apprend en se trompant, et qu'aucun fichier du dépôt ne dit ?

**Réponse** (oral) : Une chose qui n'est écrite nulle part : l'hébergeur coupe toute requête à trente secondes. On a convenu avec lui, en février 2025, qu'un traitement lancé depuis une page ne dépasse pas 500 lignes, et que ce plafond se lit dans le réglage Django `CURSUS_IMPORT_MAX_ROWS`, pour qu'il puisse le baisser sans nous. Le réglage n'existe pas encore : aucun traitement de ce genre n'a été écrit. Au-delà du plafond, on refuse le fichier entier.

## 5
**Question** : AGENTS.md et CLAUDE.md exigent Python 3.8 sur le serveur. Or requirements.txt fixe Django 5.1 (qui demande Python 3.10 au moins), la CI tourne en 3.12, et le code utilise déjà match (enrollments/notifications.py) et 'Enrollment | None' (enrollments/services.py). Quelle version de Python tourne aujourd'hui en production ? La règle 3.8 est-elle périmée ?

**Réponse** (ci, python, django) : GitHub Actions, un seul job, `test`. Il bloque la fusion sur `main`.
Non, plus en 3.8. Le serveur a été remplacé en février 2025, la production tourne en 3.12.
Plus depuis le changement d'hébergeur, en février 2025. On suit les versions courantes, 5.1 aujourd'hui.

## 6
**Question** : AGENTS.md dit de rester sur Django 4.2 LTS parce que l'hébergeur ne valide que les LTS ; requirements.txt fixe Django>=5.1,<5.2. Cette règle est-elle périmée, ou la dépendance est-elle une erreur ?

**Réponse** (django, oral) : Plus depuis le changement d'hébergeur, en février 2025. On suit les versions courantes, 5.1 aujourd'hui.
Une chose qui n'est écrite nulle part : l'hébergeur coupe toute requête à trente secondes. On a convenu avec lui, en février 2025, qu'un traitement lancé depuis une page ne dépasse pas 500 lignes, et que ce plafond se lit dans le réglage Django `CURSUS_IMPORT_MAX_ROWS`, pour qu'il puisse le baisser sans nous. Le réglage n'existe pas encore : aucun traitement de ce genre n'a été écrit. Au-delà du plafond, on refuse le fichier entier.

## 7
**Question** : AGENTS.md et CLAUDE.md citent un job CI 'frozen-migrations' et une commande 'test --settings=cursus.settings_ci'. Ni ce job ni ce fichier de réglages n'existent dans le dépôt. Ont-ils existé, faut-il les retirer des instructions ?

**Réponse** (ci, interdits, retirer) : GitHub Actions, un seul job, `test`. Il bloque la fusion sur `main`.
Modifier une migration déjà appliquée ; envoyer un vrai e-mail depuis autre chose que la production ; sortir du serveur des données personnelles d'inscrits.
Oui. Dis ce que tu retires et pourquoi.

## 8
**Question** : Le post-mortem de mars 2024 dit qu'un traitement en masse n'envoie jamais un e-mail par ligne, mais services.enroll() envoie toujours. CLAUDE.md dit « toute inscription créée envoie sa confirmation ». Pour un futur import (par exemple celui de 500 lignes plafonné par CURSUS_IMPORT_MAX_ROWS), quelle règle l'agent doit-il suivre ?

**Réponse** (interdits, oral) : Modifier une migration déjà appliquée ; envoyer un vrai e-mail depuis autre chose que la production ; sortir du serveur des données personnelles d'inscrits.
Une chose qui n'est écrite nulle part : l'hébergeur coupe toute requête à trente secondes. On a convenu avec lui, en février 2025, qu'un traitement lancé depuis une page ne dépasse pas 500 lignes, et que ce plafond se lit dans le réglage Django `CURSUS_IMPORT_MAX_ROWS`, pour qu'il puisse le baisser sans nous. Le réglage n'existe pas encore : aucun traitement de ce genre n'a été écrit. Au-delà du plafond, on refuse le fichier entier.

## 9
**Question** : Les messages de commit en français à l'impératif, et les lignes de 100 caractères au plus : toujours d'actualité ? (Aucun linter ne les vérifie.)

**Réponse** (par défaut) : Regardez dans `docs/`, c'est écrit. L'équipe ne sait rien de plus que ce que disent les post-mortems, l'ADR et la note d'exploitation.
