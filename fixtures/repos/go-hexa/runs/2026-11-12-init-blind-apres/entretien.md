# Entretien de go-hexa : 7 question(s)

- I6, que seul le propriétaire détient : demandé à la question 4

## 1
**Question** : 1. Mode : délégation (défaut : l'agent reçoit une tâche entière et revient avec une PR) ou assistance (vous relisez chaque diff en direct, aucun agent hors session) ?

**Réponse** (mode) : Délégation. On veut confier des tickets entiers et relire la PR à la fin.

## 2
**Question** : 2. Interdits : qu'est-ce qu'un agent ne doit jamais toucher ou faire (dossiers, secrets, base partagée, migrations prod, force push...) ?

**Réponse** (interdits) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## 3
**Question** : 3. Outils et CI : quels agents utilisez-vous (Claude Code seul, ou aussi Copilot, Cursor, Codex) ? Quelle CI, et quels checks bloquent la fusion aujourd'hui ?

**Réponse** (ci, outils) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
Claude Code et Copilot.

## 4
**Question** : 4. Qu'est-ce que vous redites à chaque revue, ou qu'un nouveau venu apprend en se trompant, et qu'aucun fichier ne dit ?

**Réponse** (oral) : Une chose qui n'est écrite nulle part, et qu'on redit à chaque revue : quand un endpoint rejoue une requête déjà traitée, sa réponse porte l'en-tête `Idempotency-Replayed: true`. L'application mobile s'en sert depuis juin 2026 pour ne pas afficher deux fois la confirmation. `POST /transfers` ne le fait pas encore, c'est au backlog ; tout nouvel endpoint d'écriture doit le faire.

## 5
**Question** : internal/app/fees.go calcule les frais avec float64, contraire à l'ADR 0002 ; le job lint qui porterait la règle ne bloque pas. Est-ce connu ? Un agent doit-il le corriger quand il passe par là, ou ne pas y toucher ?

**Réponse** (ci, interdits, lint) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.
Personne n'a pris le temps de solder la dette. Oui, on sait que ça affaiblit ce qui s'appuie dessus.

## 6
**Question** : Le README cite 'make e2e' mais le Makefile n'a pas de cible e2e. Ces scénarios existent-ils ailleurs, ou la ligne est-elle périmée ?

**Réponse** (e2e) : La cible `make e2e` a été retirée il y a un an avec l'ancien banc de tests ; le README n'a pas suivi.

## 7
**Question** : Pour l'interdit 'une base qui n'est pas la sienne' : faut-il comprendre que make reset-db et make migrate ne se lancent que sur une base locale à soi, jamais avec un DATABASE_URL de staging ou production ?

**Réponse** (interdits) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.
