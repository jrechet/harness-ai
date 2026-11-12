# Entretien de go-hexa : 6 question(s)

- I6, que seul le propriétaire détient : jamais demandé

## 1
**Question** : Mode : délégation (défaut proposé : l'agent reçoit une tâche entière et revient avec une PR) ou assistance (l'humain pilote et relit chaque diff en direct) ?

**Réponse** (mode) : Délégation. On veut confier des tickets entiers et relire la PR à la fin.

## 2
**Question** : Interdits : qu'est-ce qu'un agent ne doit jamais toucher ou faire (dossiers, secrets, base partagée, migrations prod, force push...) ?

**Réponse** (interdits) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## 3
**Question** : Outils et CI : quels agents utilisez-vous (Claude Code seul, ou aussi Copilot, Cursor, Codex) ? Quelle CI, et quels checks bloquent la fusion aujourd'hui ?

**Réponse** (ci, outils) : GitHub Actions. Les jobs `test` et `arch` bloquent la fusion. Le job `lint` tourne mais ne bloque pas : il y a trop d'avertissements hérités.
Claude Code et Copilot.

## 4
**Question** : internal/app/fees.go calcule les frais avec un float64 (feeRate = 0.015, math.Round), alors que l'ADR 0002 interdit tout flottant dans internal/app. Est-ce une exception assumée, ou une violation à corriger ? (défaut proposé : violation connue, à ne pas imiter)

**Réponse** (interdits) : Toucher à une base qui n'est pas la sienne, modifier une migration déjà appliquée, lancer `deploy.yml` sans `dry_run`.

## 5
**Question** : Le README cite 'make e2e' (scénarios de bout en bout), mais le Makefile n'a pas de cible e2e. Est-ce que cette commande existe ailleurs ou a été abandonnée ? (défaut : je ne la mets pas dans AGENTS.md)

**Réponse** (e2e) : La cible `make e2e` a été retirée il y a un an avec l'ancien banc de tests ; le README n'a pas suivi.

## 6
**Question** : Un nouvel endpoint qui modifie un solde doit exiger Idempotency-Key (ADR 0003) ; POST /accounts en est exempté et sa reprise est au backlog. Un agent doit-il laisser POST /accounts tel quel tant que le ticket de reprise ne lui est pas confié ? (défaut : oui)

**Réponse** (premiere-tache, accounts) : Ajouter un endpoint à partir d'un cas d'usage, du handler jusqu'au test.
Exact, `POST /accounts` n'a pas de clé d'idempotence. C'est au backlog, pas prioritaire.
