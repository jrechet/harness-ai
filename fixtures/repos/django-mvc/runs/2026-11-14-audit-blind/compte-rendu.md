# Audit du harness — Contribution assistée par IA à Cursus

**Périmètre** : dépôt Cursus (AGENTS.md, CLAUDE.md, `.github/workflows/ci.yml`, tests qui servent de garde-fous, `docs/`) · **Date** : 2026-11-14 · **Éléments inventoriés** : 12

## 1. Synthèse

- **Score de santé** : 49 — l'agent reste un accélérateur pour les listes et les migrations oubliées, mais trois règles nées d'incidents ne tiennent que par le texte, et l'une d'elles cite un garde-fou qui n'existe pas.
- **Résultat du test « coupe l'agent »** : ÉCHEC — 4 règles ou étapes du processus n'existent que dans des prompts.
- **Points bloquants (P1)** : 1
- **Les trois actions qui changent le plus les choses** :
  1. Créer le job CI `frozen-migrations`. AGENTS.md:58 et CLAUDE.md:20 le présentent comme existant, mais `ci.yml` n'a qu'un job, `test`.
  2. Fermer les moyens de contourner `services.enroll()` (formulaire d'ajout de l'admin, écritures directes) et ajouter un paramètre `notify` pour les traitements en masse.
  3. Réduire CLAUDE.md à `@AGENTS.md`. Aujourd'hui, Claude ne voit ni les incidents ni la règle des envois en masse, et CLAUDE.md:18 la contredit.

Calcul : 100 − 25 (1 P1) − 24 (3 P2) − 2 (1 P3) = 49. Le plafond de 60 lié au test en échec ne change rien.

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | AGENTS.md | `AGENTS.md` | L2 | L2 (instruction + référence) | Copilot, Cursor (chargement auto) | règles 3–6, docs/ |
| 2 | CLAUDE.md | `CLAUDE.md` | L2 | L2, copie qui dérive | Claude Code (chargement auto) | rien (pas d'`@AGENTS.md`) |
| 3 | Règle migrations appliquées | `AGENTS.md:58`, `CLAUDE.md:20` | L4 (« job frozen-migrations ») | L2 seulement | 1, 2 | — |
| 4 | Règle e-mails en masse | `AGENTS.md:56` | L2 | L2 (la partie signal est en L3) | 1 | 9 |
| 5 | Règle capacité | `AGENTS.md:57`, `CLAUDE.md:19` | L2 | L2 | 1, 2 | — |
| 6 | Règle dates | `AGENTS.md:61`, `CLAUDE.md:22` | L2 | L2 | 1, 2 | — |
| 7 | Workflow CI | `.github/workflows/ci.yml` | L4 | L4 | PR et push sur `main` | 8, 9 |
| 8 | Test du nombre de requêtes | `catalog/tests/test_queries.py` | L3 | L3 | 7 | — |
| 9 | Test « save n'envoie rien » | `enrollments/tests/test_services.py:106` | L3 | L3 | 7 | — |
| 10 | Postmortems et ADR | `docs/postmortems/`, `docs/adr/` | L2 (référence) | L2 | 1 | — |
| 11 | Exploitation | `docs/exploitation.md` | L2 (référence) | L2 | — | — |
| 12 | README | `README.md` | L2 (référence) | L2 | — | — |

Aucun agent, skill, script, hook, règle Cursor ou dossier `.harness/` n'existait avant l'audit.

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| Branche, puis PR vers `main` | AGENTS.md:66, ci.yml:3-4 | En partie (la CI ne se déclenche que vers `main`) | — |
| Modèle modifié → migration commitée | ci.yml:18-19 | Oui | Oui (`--check --dry-run`) |
| Ne pas modifier une migration appliquée | AGENTS.md:58 | **Non** | — |
| Tests | ci.yml:21 | Oui | — |
| Pas de requête par ligne dans les listes | test_queries.py | Oui | — |
| Pas d'e-mail dans un signal ou dans `save()` | test_services.py:106 | Oui | — |
| Pas d'e-mail par ligne dans un traitement en masse | AGENTS.md:56 | **Non**, et la règle est déjà violée | — |
| Inscription uniquement par `enroll()` | AGENTS.md:57 | **Non** (admin ouvert, verrou jamais testé) | — |
| Dates avec `timezone.now()` | AGENTS.md:61 | **Non** | — |
| Compatibilité Python 3.8 / Django 4.2 | AGENTS.md:51-52 | Non, et contredite par le code (Q1, Q2) | — |
| Revue puis fusion | humain, protection de branche | Non vérifiable dans le dépôt | — |
| Déploiement : `migrate` automatique à la fusion | hébergeur (docs/exploitation.md:13) | Hors dépôt | Non, et pas de retour arrière |

## 3. Fuites : règles et étapes racontées sans vérification

1. **Migrations appliquées** (AGENTS.md:58, CLAUDE.md:20). Les deux fichiers disent « Vérifié par le job `frozen-migrations` ». Ce job n'existe pas : ci.yml:8-21 ne contient qu'un job, `test`, ce que confirme docs/exploitation.md:27. **Si l'agent saute la règle**, la migration modifiée passe la CI, est fusionnée, puis `migrate` ne la rejoue pas : la production garde l'ancien schéma sans aucune erreur (docs/exploitation.md:16-17). L'agent croit pourtant qu'un filet existe. **Cible** : L4, un job CI (`git diff --diff-filter=MDR origin/main...HEAD -- '*/migrations/0*.py'` non vide → `exit 1`).
2. **E-mails en masse** (AGENTS.md:56, deuxième phrase). Rien ne la vérifie, et elle est déjà violée : l'action d'admin `cancel_selected` (enrollments/admin.py:18-19) appelle `services.cancel()`, qui envoie un e-mail de promotion par ligne (services.py:66). De plus, `enroll()` envoie toujours, ce qui est un point ouvert depuis le postmortem 2024-03:21. **Si l'agent saute la règle**, on revit l'incident de mars 2024 : un compte SMTP suspendu. **Cible** : L3, un paramètre `notify` sur les services et un test de l'action d'admin sur `mail.outbox`.
3. **Capacité** (AGENTS.md:57). Le formulaire d'ajout de `EnrollmentAdmin` permet de créer une inscription confirmée sans passer par `enroll()` (enrollments/admin.py:7-8, déjà signalé dans le postmortem 2024-09:19). Le verrou n'est jamais testé, car SQLite ignore `select_for_update` (2024-09:18, settings.py:51-63). **Si l'agent saute la règle**, on revit l'incident de septembre 2024 : une session surréservée. **Cible** : L3, avec `has_add_permission=False`, un test qui scanne les sources et un job PostgreSQL.
4. **Dates** (AGENTS.md:61). Aucun garde-fou. Une date naïve fausse `has_started` (catalog/models.py:58-59). **Cible** : L3, avec ruff DTZ en CI.

Règles qui ont leur garde-fou :
- Pas d'e-mail dans un signal ou dans `save()` (AGENTS.md:56) : vérifiée par `enrollments/tests/test_services.py:106-112`.
- Migration commitée avec le modèle (AGENTS.md:59) : vérifiée par `ci.yml:18-19`. La règle peut se réduire à sa ligne « Vérifiée par ».
- Pas de requête par ligne (AGENTS.md:60) : vérifiée par `catalog/tests/test_queries.py`. Elle peut se réduire, CLAUDE.md:21 donne déjà la bonne formulation.
- La règle « services » (AGENTS.md:62) est une convention de revue assumée par l'ADR 0001:15. Ce n'est pas une fuite.

## 3b. Coût de contexte

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| AGENTS.md | 67 | ~55 % / ~35 % / ~10 % | Chaque session Copilot ou Cursor (Claude Code ne le charge pas) |
| CLAUDE.md | 24 | ~60 % / ~30 % / ~10 % | Chaque session Claude Code |

Le volume est raisonnable. Les deux règles nées d'incidents (AGENTS.md:56-57) expliquent leur pourquoi et citent leur postmortem, c'est un vrai point fort. CLAUDE.md supprime tous ces pourquoi. Aucun des deux fichiers ne dit comment il évolue.

## 3c. Lignes à retirer

| Fichier:ligne | Texte | Motif | Preuve | Question au propriétaire ? |
|---|---|---|---|---|
| AGENTS.md:30 | `test --settings=cursus.settings_ci` | nuisible | `cursus/settings_ci.py` n'existe pas ; la CI lance `manage.py test` (ci.yml:21) | Non |
| AGENTS.md:58 | « Vérifié par : le job `frozen-migrations` » | nuisible | Job absent (ci.yml:8-21). La règle reste, seule la mention du garde-fou part tant que le job n'existe pas | Non |
| CLAUDE.md:20 | « la CI le refuse (job `frozen-migrations`) » | nuisible | Même preuve | Non |
| AGENTS.md:60 | « ouvre la page avec django-debug-toolbar… » | nuisible | Outil retiré (postmortem 2025-06:14), remplacé par test_queries.py | Non |
| CLAUDE.md:18 | « toute inscription créée envoie sa confirmation » | nuisible | Contredit AGENTS.md:56 et le postmortem 2024-03:17, alors que CLAUDE.md ne contient pas la règle des envois en masse | Non |
| AGENTS.md:3, 36, 37, 44, 46 ; CLAUDE.md:16 | « Lis-le en entier », « étape par étape », « n'invente pas d'API », « noms clairs », « pas de print » | inutile | Comportements par défaut ou chargement automatique | Non |
| AGENTS.md:7, 9-24 | Présentation et arborescence | inutile | Déjà dans README.md:3 et :35-41, et visible dans le dépôt | Non |
| AGENTS.md:51 ; CLAUDE.md:17 | Python 3.8 | périmée ? | `match` (notifications.py:17) et `X \| None` (services.py:47) ne s'importent pas sous 3.8 ; la CI tourne en 3.12 | **Q1** |
| AGENTS.md:52 | Django 4.2 LTS | périmée ? | requirements.txt:1 demande 5.1 ; models.py:48 utilise `condition=`, une API de la 5.1 | **Q2** |
| AGENTS.md:38 | « Donne toujours le fichier complet… » | périmée ? | Contournement d'un usage en chat copié-collé | **Q3** |
| AGENTS.md:43 | « lignes de 100 caractères au plus » | périmée ? | Aucun linter ; des lignes dépassent déjà 100 caractères (services.py:39, views.py:26 et :36, catalog/models.py:38) | **Q6** |

**Questions au propriétaire**
1. Le serveur de production est-il encore en Python 3.8 ? Le code actuel ne s'y importe pas. *Défaut proposé : non.* On retire AGENTS.md:51 et CLAUDE.md:17, on indique la version réelle et on aligne `ci.yml` dessus. Si la réponse est oui, c'est un P1 : la production ne peut pas démarrer ce code.
2. L'hébergeur exige-t-il toujours une version LTS de Django ? La 5.1 n'en est pas une. *Défaut proposé : on retire AGENTS.md:52 et requirements.txt fait foi.* Si l'exigence tient, on passe en 5.2 LTS.
3. Quelqu'un colle-t-il encore des réponses d'assistant depuis un chat ? *Défaut proposé : non, on retire AGENTS.md:38.*
4. L'e-mail de promotion envoyé pour chaque ligne par `cancel_selected` est-il une exception voulue à la décision de 2024-03 ? *Défaut proposé : non.* L'action enregistre sans prévenir, et le service formation prévient lui-même.
5. Le staff doit-il pouvoir ajouter une inscription depuis l'admin ? *Défaut proposé : non, on met `has_add_permission=False`.* Sinon, l'ajout doit passer par `enroll()`.
6. La limite de 100 caractères est-elle toujours voulue ? *Défaut proposé : oui, avec ruff `line-length = 100` en CI.*
7. La protection de branche de `main` exige-t-elle bien le job `test` ? *Défaut proposé : oui. Il faut le confirmer, puis y ajouter `frozen-migrations`.*

AGENTS.md compte 67 lignes et en garderait environ 40 après nettoyage. Deux lignes sont à garder absolument et à ne pas raccourcir : **AGENTS.md:56 et :57** (incidents de mars et septembre 2024).

## 4. Constats par élément

### [PUSH_DOWN] [P1] Règle « migrations appliquées » — AGENTS.md:58
- **Fait aujourd'hui** : elle annonce un garde-fou CI.
- **Problème** : le job n'existe pas (ci.yml:8-21, exploitation.md:27). Comme le déploiement applique `migrate` à chaque fusion, une modification passe sans bruit (exploitation.md:13-17). `harness rules` compte même cette règle comme « avec garde-fou », sur la seule foi du texte.
- **Doit devenir** : un job `frozen-migrations` dans ci.yml, exigé par la protection de branche.
- **Critère de vérification** : une PR qui modifie `catalog/migrations/0001_initial.py` est rouge, une PR qui ajoute `0003_*.py` est verte.

### [PUSH_DOWN] [P2] Règle « e-mails en masse » — AGENTS.md:56
- **Fait aujourd'hui** : un test garde la partie « signal / `save()` ». La partie « en masse » n'est que racontée.
- **Problème** : l'action `cancel_selected` envoie déjà un e-mail par ligne (enrollments/admin.py:18-19, services.py:66), et `enroll()` n'a aucun moyen de ne pas envoyer (postmortem 2024-03:21).
- **Doit devenir** : un paramètre `notify` (mot-clé, `True` par défaut) sur `enroll()` et `cancel()`, que l'admin et les imports passent à `False`, avec un test.
- **Critère de vérification** : le test de l'action d'admin sur plusieurs lignes laisse `mail.outbox` vide.

### [PUSH_DOWN] [P2] Règle « capacité » — AGENTS.md:57
- **Fait aujourd'hui** : elle est racontée, avec son pourquoi.
- **Problème** : on peut ajouter une inscription par l'admin (enrollments/admin.py:7-8), et le verrou n'est testé que sous SQLite (postmortem 2024-09:18-19).
- **Doit devenir** : `has_add_permission=False`, un test qui scanne les sources pour trouver `Enrollment.objects.create`/`bulk_create` hors des services et des tests, et un job CI PostgreSQL avec un test de concurrence.
- **Critère de vérification** : la page d'ajout renvoie 403 en test, et le scan échoue sur une écriture directe ajoutée volontairement.

### [MERGE] [P2] CLAUDE.md — CLAUDE.md
- **Fait aujourd'hui** : il résume AGENTS.md sans l'inclure (CLAUDE.md:3).
- **Problème** : Claude ne voit ni les pourquoi ni la règle des envois en masse. La ligne 18 la contredit et la ligne 20 répète le faux garde-fou.
- **Doit devenir** : `@AGENTS.md`, plus les seules lignes propres à Claude. La formulation de CLAUDE.md:21 remonte dans AGENTS.md:60.
- **Critère de vérification** : aucune règle n'existe dans un seul des deux fichiers, et CLAUDE.md fait moins de 10 lignes.

### [PUSH_DOWN] [P3] Règle « dates » — AGENTS.md:61
- **Fait aujourd'hui** : elle est racontée, sans garde-fou.
- **Problème** : un `datetime.now()` passerait la CI et fausserait `has_started` (catalog/models.py:58-59).
- **Doit devenir** : ruff avec les règles DTZ en CI.
- **Critère de vérification** : un `datetime.now()` ajouté fait échouer la CI.

### [KEEP] AGENTS.md — AGENTS.md
C'est le bon fichier, avec le bon périmètre et des règles d'incident exemplaires. Il est à nettoyer ligne par ligne selon la section 3c.

### [KEEP] Workflow CI — .github/workflows/ci.yml
Un job bloquant qui garde les migrations oubliées et lance les tests. Les nouveaux garde-fous s'ajoutent ici.

### [KEEP] Test du nombre de requêtes — catalog/tests/test_queries.py
C'est le modèle à suivre : né d'un incident qu'il cite, il dit aussi ce qu'il ne faut pas faire.

### [KEEP] Test « save n'envoie rien » — enrollments/tests/test_services.py:106
Il garde l'absence d'envoi dans un signal ou dans `save()`.

### [KEEP] Postmortems et ADR — docs/postmortems/, docs/adr/
Ils portent les pourquoi et listent honnêtement ce qui reste ouvert.

### [KEEP] Exploitation — docs/exploitation.md
Il décrit fidèlement la CI réelle, et c'est lui qui révèle le faux garde-fou.

### [KEEP] README — README.md
Ses commandes sont exactes et alignées sur la CI.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | PUSH_DOWN | Migrations appliquées | Job `frozen-migrations` dans ci.yml et dans la protection de branche | — | PR modifiant 0001 rouge, PR ajoutant 0003 verte | Oui |
| 2 | P2 | PUSH_DOWN | Capacité | Fermer l'ajout dans l'admin, test de scan des sources, job PostgreSQL | Q5 | 403 en test, scan rouge sur une écriture directe | Oui |
| 3 | P2 | PUSH_DOWN | E-mails en masse | Paramètre `notify` et test de l'action d'admin | Q4 | `mail.outbox` vide | Oui |
| 4 | P2 | REMOVE | AGENTS.md | Lignes nuisibles :30 et :60 (2ᵉ phrase), et la mention du job à :58 si l'ordre 1 est refusé | 1 | Toutes les commandes citées s'exécutent | Oui |
| 5 | P2 | MERGE | CLAUDE.md | Réduire à `@AGENTS.md` et retirer :18 | 4 | Plus aucun doublon | Oui |
| 6 | P3 | PUSH_DOWN | Dates | ruff DTZ (et E501 à 100 selon Q6) | Q6 | `datetime.now()` rouge en CI | Oui |
| 7 | P3 | REMOVE | AGENTS.md | Lignes inutiles 3, 7, 9-24, 36, 37, 44, 46 ; raccourcir 59-60 | 5 | ~40 lignes, 56-57 intactes | Oui |
| 8 | P3 | REMOVE | AGENTS.md / CLAUDE.md | Lignes périmées 38, 43, 51, 52 et CLAUDE.md:17 selon les réponses | Q1, Q2, Q3, Q6 | Versions alignées sur requirements.txt et ci.yml | Oui |
| 9 | P3 | KEEP | AGENTS.md | Ajouter une clause de maintenance | 7 | Clause présente | Non |

## 6. Ce que l'audit n'a pas pu vérifier

- Les tests n'ont pas été exécutés, car Django n'est pas installé dans l'environnement.
- La protection de branche de `main` (Q7).
- Le pipeline de déploiement de l'hébergeur, hors dépôt : ni dry-run ni point d'arrêt vérifiables, et pas de retour arrière (docs/exploitation.md:13).
- Les versions réelles de Python et de Django en production (Q1, Q2).
- L'âge des règles : l'historique git se réduit à un commit d'import (3719e0e), donc les âges donnés par `harness rules` ne signifient rien.

## 7. Données machine

Le bloc JSON complet, conforme au schéma du gabarit (12 éléments, 4 fuites, 3 règles gardées, 18 retraits, 7 questions, 9 actions de remédiation), est écrit dans `.harness/audit.json` ; la syntaxe a été validée. Son résumé :

```json
{
  "audit": {
    "process": "Contribution assistée par IA à Cursus (PR vers main, CI, déploiement automatique)",
    "scope": "repo Cursus : AGENTS.md, CLAUDE.md, .github/workflows/ci.yml, tests garde-fous, docs/",
    "date": "2026-11-14",
    "health_score": 49,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 4 }
  }
}
```

Le fichier complet est ici : /tmp/claude-0/-home-user/c9c9c05e-e8c6-5b39-9449-fc2d7f51c43b/scratchpad/banc/w-98numf2m/repo/.harness/audit.json

---

Je n'ai rien modifié d'autre dans le dépôt : `.harness/audit.json` est le seul fichier écrit, comme le skill le demande, et il n'est pas commité.