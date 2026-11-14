# Audit du harness — comptoir (livraison d'un ticket délégué jusqu'à la PR)

**Périmètre** : repo (AGENTS.md, CLAUDE.md, services/billing/AGENTS.md, .github/, tools/, shared/, contracts/, services/*/test_*.py, docs/, README.md) · **Date** : 2026-11-14 · **Éléments inventoriés** : 22

## 1. Synthèse

- **Score de santé** : 27 — dans l'ensemble l'agent ne fait qu'accélérer le travail : 5 des 12 règles ont un vrai garde-fou dans la CI. Mais la règle née du dernier incident se dit vérifiée alors qu'elle ne l'est pas.
- **Résultat du test « coupe l'agent »** : ÉCHEC — 6 règles n'existent que dans AGENTS.md, et la CI ne bloque aucune d'entre elles.
- **Points bloquants (P1)** : 1
- **Les trois actions qui changent le plus les choses** :
  1. Créer `tools/check_contracts.py` et un job CI `contracts` bloquant, qui compare chaque schéma à sa version sur la branche de base. Ce même outil peut contrôler `contracts/CHANGES.md`.
  2. Corriger AGENTS.md:17, 21 et 22. Deux affirmations sont fausses, et une procédure manuelle est moins bonne que le contrôle déjà en CI.
  3. Valider contre `contracts/` les événements que les tests de `notifications` et `billing` construisent à la main. C'est la cause directe de l'incident du 12 mai.

Calcul : 100 − 25 (1 P1) − 40 (5 P2) − 8 (4 P3) = 27. Le plafond de 60 dû au test en échec ne joue pas ici.

## 2. Carte du harness

| # | Élément | Chemin | Couche déclarée | Couche réelle | Appelé par | Appelle |
|---|---|---|---|---|---|---|
| 1 | claude-md | CLAUDE.md | L2 | L2 | session | agents-md |
| 2 | agents-md | AGENTS.md | L2 | L2 | claude-md | ci-test, ci-boundaries, check-imports, billing-agents-md |
| 3 | billing-agents-md | services/billing/AGENTS.md | L2 | L2 | agents-md | billing-test-ledger |
| 4 | contract-additivity | AGENTS.md:17 | L3 (se dit vérifiée) | L2 | agents-md | orders-test-contract (à tort) |
| 5 | agents-md-imports-lines | AGENTS.md:21-22 | L2 | L2 | agents-md | — |
| 6 | contracts-changelog | AGENTS.md:19 | L2 | L2 | agents-md | — |
| 7 | consumer-test-fixtures | services/notifications/test_app.py:9-26, services/billing/test_app.py:12 | L3 | L3 | ci-test | bus-py |
| 8 | guard-weakening | AGENTS.md:27 | L3 (via CODEOWNERS) | L2 | agents-md | codeowners |
| 9 | broker-url-guard | shared/bus.py:58-65 | L3 | L2 | services | — |
| 10 | readme-replay | README.md:14 | L2 | L2 | — | tools/replay.py (absent) |
| 11 | event-size-rule | AGENTS.md:23 | L2 | L2 | agents-md | — |
| 12 | notifications-api-contract | services/notifications/app.py:56-58 | L3 | L3 | — | — |
| 13 | ci-test | .github/workflows/ci.yml:8-19 | L4 | L4 | PR, push main | toute la suite unittest |
| 14 | ci-boundaries | .github/workflows/ci.yml:21-27 | L4 | L4 | PR, push main | check-imports |
| 15 | check-imports | tools/check_imports.py | L3 | L3 | ci-boundaries, agents-md | — |
| 16 | schema-py | tools/schema.py | L3 | L3 | test_contract × 2 | — |
| 17 | bus-py | shared/bus.py:33-55 | L3 | L3 | tous les tests | — |
| 18 | orders-test-contract | services/orders/test_contract.py | L3 | L3 | ci-test | schema-py |
| 19 | billing-test-contract | services/billing/test_contract.py | L3 | L3 | ci-test | schema-py |
| 20 | billing-test-ledger | services/billing/test_ledger.py | L3 | L3 | ci-test | — |
| 21 | codeowners | .github/CODEOWNERS | L4 | L4 | GitHub | — |
| 22 | contributing-md | CONTRIBUTING.md | L2 | L2 | humains | — |

Processus nominal pour un ticket délégué :

| Étape du processus | Portée par | Vérifiée par du code ? | Dry-run ? |
|---|---|---|---|
| Modifier un service, lancer ses tests | AGENTS.md:11 → ci-test | Oui (suite complète en CI) | s.o. |
| Respecter les frontières d'import | check_imports.py → ci-boundaries | Oui | s.o. (lecture seule) |
| Contrat strict côté fournisseur | test_contract.py × 2 | Oui pour orders et billing, non pour notifications /outbox | s.o. |
| Changement de contrat additif | AGENTS.md:17 uniquement | **Non** (le test cité ne le voit pas) | — |
| Champ remplacé marqué `deprecated` | AGENTS.md:18 | Non (le choix relève du jugement) | — |
| Ligne dans contracts/CHANGES.md | AGENTS.md:19 | **Non** | — |
| Consommateur idempotent | bus-py (deliveries=2) | Oui | s.o. |
| Taille d'événement < 64 Ko | AGENTS.md:23 | Non | — |
| BROKER_URL jamais vers préprod ou prod | AGENTS.md:26 | **Non** | — |
| Ne pas affaiblir un garde-fou | AGENTS.md:27 + CODEOWNERS | Partiel (services/ n'est pas couvert) | — |
| Déploiement | équipe plateforme, hors dépôt (docs/exploitation.md:10) | hors périmètre | hors périmètre |

## 3. Fuites : règles et étapes racontées sans vérification

1. **Changement de contrat additif** — AGENTS.md:17. La ligne affirme « Vérifiée par : services/orders/test_contract.py ». Or le post-mortem dit le contraire : ce test reste vert quand le schéma et le fournisseur changent dans la même PR (docs/postmortems/2026-05-champ-renomme.md:11, :22-26). Si l'agent saute la règle, un renommage passe la CI au vert et casse notifications et comptoir-export en production, comme le 12 mai. **À placer en L3** : `tools/check_contracts.py`, qui compare chaque schéma à celui de la base de la PR, avec un job CI `contracts`.
2. **Ligne datée dans contracts/CHANGES.md** — AGENTS.md:19. Si l'agent l'oublie, les consommateurs extérieurs ne voient pas le changement. **À placer en L3** : le même outil sort en erreur quand un `contracts/**/*.json` a changé sans nouvelle ligne en tête de CHANGES.md.
3. **Champ remplacé : `"deprecated": true`** — AGENTS.md:18. Le retrait d'un champ sera attrapé par le point 1. L'oubli de l'annotation, lui, ne se vérifie pas, parce que savoir quel champ en remplace un autre est une affaire de jugement (L1). Garde-fou partiel, à garder tel quel.
4. **BROKER_URL vers préprod ou prod** — AGENTS.md:26. `connect()` accepte n'importe quelle URL (shared/bus.py:58-65). Si la consigne est ignorée, des événements réels partent d'un poste, comme les 3 100 e-mails du 9 janvier 2026 (docs/exploitation.md:29). **À placer en L3** : un refus dans `connect()`, doublé en L4 d'identifiants que seule la plateforme détient.
5. **Affaiblir un garde-fou** — AGENTS.md:27. CODEOWNERS (lignes 2-5) ne couvre pas `services/`, or c'est là qu'un `deliveries=1` se glisserait. Si ça arrive, un consommateur non idempotent passe la CI. **À placer en L3** : un test qui refuse `InMemoryBus(deliveries=` sous `services/`.
6. **Taille d'événement < 64 Ko** — AGENTS.md:23. Aucun contrôle, et la justification est datée (voir 3c). **À placer en L3** : un contrôle de taille dans `InMemoryBus.publish`, une fois la limite réelle confirmée.

Règles qui ont leur garde-fou :
- Contrats stricts côté fournisseur (AGENTS.md:16) : `services/{orders,billing}/test_contract.py` et `tools/schema.py`. Partiel, car `/outbox` n'a pas de contrat.
- Idempotence (AGENTS.md:20) : `shared/bus.py`, qui livre deux fois par défaut.
- Pas d'import entre services (AGENTS.md:21) : `tools/check_imports.py`, job `boundaries`. Bloquant, alors que la ligne dit « non vérifiée ».
- Factures numérotées sans trou et facture figée (services/billing/AGENTS.md:5-6) : `services/billing/test_ledger.py`.

## 3b. Coût de contexte

| Fichier | Lignes chargées (avec includes) | Part instruction / référence / bruit | Chargé quand |
|---|---|---|---|
| CLAUDE.md → @AGENTS.md | 28 | 70 % / 30 % / 0 % | chaque session |
| services/billing/AGENTS.md | 7 | 85 % / 15 % / 0 % | travail dans services/billing |

Toutes les règles sont datées et justifiées par un incident ou un ADR, ce qui est le vrai point fort de ce harness. Il manque une clause de maintenance. Il manque aussi, alors que le mode déclaré est la délégation, une indication de quand s'arrêter et demander (AGENTS.md:3).

## 3c. Lignes à retirer

| Fichier:ligne | Texte | Motif | Preuve | Question au propriétaire ? |
|---|---|---|---|---|
| AGENTS.md:22 | « Avant d'ouvrir une PR, lance `grep -rnE …` et relis chaque ligne à la main … c'est le seul contrôle » | harmful | Contredit ADR 0001:23 (« La relecture à la main n'est plus le contrôle ») et ci.yml:21-27. Le grep rate `from services import orders`, les imports relatifs et les imports indentés (tools/test_check_imports.py:39-46). | Non |
| AGENTS.md:21 | « (non vérifiée) » | harmful | Vérifiée par check_imports.py, job boundaries, depuis le 2026-08-04. À remplacer par « Vérifiée par : tools/check_imports.py, job boundaries ». | Non |
| AGENTS.md:17 | « Vérifiée par : `services/orders/test_contract.py`. » | harmful | Post-mortem 2026-05:11 et :22-26. À remplacer par « (non vérifiée) » jusqu'à l'arrivée du job contracts. | Non |
| README.md:14 | `python3 tools/replay.py order.created` | harmful | Le script n'existe pas, et rejouer une file d'un poste est réservé à la plateforme (exploitation.md:28-29). | Oui (Q2) |
| AGENTS.md:23 | « Pourquoi : … le plan mutualisé du broker coupe la connexion … » | outdated | Le broker est un cluster dédié depuis mars 2025 (exploitation.md:13). | Oui (Q1) |

**Questions au propriétaire**
1. AGENTS.md:23 — le cluster dédié a-t-il encore une limite de taille, et laquelle ? *Défaut proposé* : garder la règle « pas de fichier dans un événement », réécrire le pourquoi avec la limite réelle, ajouter le contrôle dans `InMemoryBus.publish`.
2. README.md:14 — `tools/replay.py` a-t-il été retiré après le 9 janvier 2026 ? *Défaut proposé* : retirer la ligne et renvoyer vers docs/exploitation.md, section « Rejouer des événements ».
3. `GET /outbox` est-il lu hors du service notifications ? *Défaut proposé* : oui, par prudence. Ajouter `contracts/api/outbox.json` et `services/notifications/test_contract.py`.
4. La protection de `main` exige-t-elle les jobs `test` et `boundaries` ainsi que la revue des CODEOWNERS ? *Défaut proposé* : supposer que non tant que ce n'est pas confirmé, et ajouter le test anti-`deliveries=`.
5. Un poste ou une session d'agent peut-il obtenir des identifiants pour comptoir-preprod ou comptoir-prod ? *Défaut proposé* : ajouter le refus dans `connect()`, avec un marqueur de déploiement à convenir avec la plateforme.
6. Pour la règle additive, faut-il comparer à `origin/main` ou à la version déployée ? *Défaut proposé* : la base de la PR.

AGENTS.md passe de 28 à 27 lignes. On retire la ligne 22 et on corrige deux fragments. Les lignes 16 à 20 et 26 à 27 sont à garder absolument : chacune porte un incident.

## 4. Constats par élément

### [PUSH_DOWN] [P1] contract-additivity — AGENTS.md:17
- **Fait aujourd'hui** : la règle se dit vérifiée par `services/orders/test_contract.py`.
- **Problème** : ce test valide le fournisseur contre le schéma, pas le schéma contre sa version précédente. Il était vert le 12 mai (preuve : docs/postmortems/2026-05-champ-renomme.md:11, :22-26). L'agent se fie donc à la CI pour un contrôle qu'elle ne fait pas.
- **Doit devenir** : `tools/check_contracts.py`, testé, avec `--json` et une sortie en erreur quand une propriété est retirée, un type changé, un champ rendu requis ou `additionalProperties` assoupli. Un job CI `contracts` bloquant le lance.
- **Critère de vérification** : une PR qui renomme `customer_email` en `email` fait échouer le job `contracts`.

### [REMOVE] [P2] agents-md-imports-lines — AGENTS.md:21-22
- **Fait aujourd'hui** : la ligne 21 dit la règle non vérifiée, la ligne 22 impose un grep manuel présenté comme « seul contrôle ».
- **Problème** : c'est faux depuis le 2026-08-04 (preuve : docs/adr/0001-trois-services-un-contrat.md:23, .github/workflows/ci.yml:21-27). Le grep laisse passer trois graphies d'import (tools/test_check_imports.py:39-46).
- **Doit devenir** : la ligne 22 est retirée, la ligne 21 dit « Vérifiée par : tools/check_imports.py, job boundaries ».
- **Critère de vérification** : `harness rules` montre AGENTS.md:21 avec son garde-fou.

### [PUSH_DOWN] [P2] contracts-changelog — AGENTS.md:19
- **Fait aujourd'hui** : la règle est seulement écrite, et `contracts/CHANGES.md` n'existe pas.
- **Problème** : les consommateurs extérieurs dépendent de ce fichier (preuve : AGENTS.md:19, docs/exploitation.md:17-23).
- **Doit devenir** : une vérification dans `check_contracts.py` (contrat modifié sans ligne CHANGES.md → exit 1).
- **Critère de vérification** : un ajout de champ sans ligne CHANGES.md fait échouer la CI.

### [PUSH_DOWN] [P2] consumer-test-fixtures — services/notifications/test_app.py:9-26
- **Fait aujourd'hui** : les tests de notifications et de billing (services/billing/test_app.py:12) construisent leurs événements à la main.
- **Problème** : ces événements ne sont jamais validés contre `contracts/`, et c'est la cause directe du 12 mai (preuve : post-mortem 2026-05:6, :24).
- **Doit devenir** : chaque fixture est validée par `tools.schema.validate` contre son contrat.
- **Critère de vérification** : retirer `customer_email` du schéma fait échouer les tests des deux consommateurs.

### [PUSH_DOWN] [P2] guard-weakening — AGENTS.md:27
- **Fait aujourd'hui** : la règle repose sur CODEOWNERS.
- **Problème** : CODEOWNERS ne couvre pas `services/` (preuve : .github/CODEOWNERS:2-5), et la protection de branche n'est pas visible depuis le dépôt.
- **Doit devenir** : un test qui refuse `InMemoryBus(deliveries=` sous `services/`.
- **Critère de vérification** : `deliveries=1` dans un test de service fait échouer le job `test`.

### [PUSH_DOWN] [P2] broker-url-guard — shared/bus.py:58-65
- **Fait aujourd'hui** : `connect()` se branche sur toute URL fournie dans `BROKER_URL`.
- **Problème** : l'interdit n'existe que dans AGENTS.md:26, et l'incident du 9 janvier montre ce que coûte son contournement (preuve : docs/exploitation.md:29).
- **Doit devenir** : un refus des hôtes `comptoir-preprod` et `comptoir-prod` sans marqueur de déploiement, et des identifiants tenus en L4 par la plateforme.
- **Critère de vérification** : un test de `shared/test_bus.py` prouve le refus, et la préproduction démarre toujours.

### [REMOVE] [P3] readme-replay — README.md:14
- **Fait aujourd'hui** : le README documente un script `tools/replay.py`.
- **Problème** : ce script est absent, et l'opération qu'il décrit est interdite depuis un poste (preuve : docs/exploitation.md:28-29).
- **Doit devenir** : la ligne est retirée, ou remplacée par un renvoi vers docs/exploitation.md (Q2).
- **Critère de vérification** : plus aucune mention de `replay.py`.

### [PUSH_DOWN] [P3] event-size-rule — AGENTS.md:23
- **Fait aujourd'hui** : la limite de 64 Ko est écrite sans contrôle.
- **Problème** : la justification renvoie au plan mutualisé, abandonné en mars 2025 (preuve : docs/exploitation.md:13).
- **Doit devenir** : après la réponse à Q1, un contrôle de taille dans `InMemoryBus.publish`.
- **Critère de vérification** : publier un événement au-delà de la limite fait échouer un test.

### [PUSH_DOWN] [P3] notifications-api-contract — services/notifications/app.py:56-58
- **Fait aujourd'hui** : `/outbox` répond sans schéma ni `test_contract.py`.
- **Problème** : la règle AGENTS.md:16 couvre tout ce qu'un service répond, et rien n'oblige un service à avoir son test de contrat.
- **Doit devenir** : un schéma et un test pour `/outbox`, ou une exception écrite dans la règle (Q3).
- **Critère de vérification** : les réponses de `/outbox` sont validées contre un schéma.

### [KEEP] [P3] agents-md — AGENTS.md
- **Fait aujourd'hui** : un fichier court, daté et justifié.
- **Problème** : pas de clause de maintenance, et pas d'indication de quand s'arrêter et demander, alors que le mode est la délégation (preuve : AGENTS.md:3).
- **Doit devenir** : deux lignes de plus, une pour la maintenance et une pour l'arrêt.
- **Critère de vérification** : les deux clauses sont présentes.

### [KEEP] claude-md — CLAUDE.md
Une seule ligne, `@AGENTS.md` : il n'y a qu'une source d'instructions.

### [KEEP] billing-agents-md — services/billing/AGENTS.md
Deux règles légales, justifiées et gardées par `test_ledger.py`.

### [KEEP] ci-test — .github/workflows/ci.yml:8-19
Toute la suite tourne sur chaque PR, sans filtre de chemins ni `continue-on-error`.

### [KEEP] ci-boundaries — .github/workflows/ci.yml:21-27
Bloquant à chaque PR.

### [KEEP] check-imports — tools/check_imports.py
CLI testé, avec code de sortie et `--json`. 0 violation aujourd'hui.

### [KEEP] schema-py — tools/schema.py
Refuse tout mot-clé inconnu au lieu de le laisser passer en silence.

### [KEEP] bus-py — shared/bus.py:33-55
Livre deux fois par défaut, donc l'idempotence est testée sans qu'on y pense.

### [KEEP] orders-test-contract — services/orders/test_contract.py
Le test est bon. C'est la ligne AGENTS.md:17 qui le cite à tort.

### [KEEP] billing-test-contract — services/billing/test_contract.py
Même rôle que celui d'orders.

### [KEEP] billing-test-ledger — services/billing/test_ledger.py
Numérotation sans trou et facture figée, testées.

### [KEEP] codeowners — .github/CODEOWNERS
Relecture à deux des garde-fous. Son angle mort est traité dans guard-weakening.

### [KEEP] contributing-md — CONTRIBUTING.md
Conventions de style destinées aux humains, non chargées par l'agent. Ce n'est pas une fuite.

## 5. Plan de remédiation

| Ordre | Priorité | Verdict | Élément | Action | Dépend de | Vérification | Approbation humaine requise |
|---|---|---|---|---|---|---|---|
| 1 | P1 | PUSH_DOWN | contract-additivity | Créer `tools/check_contracts.py` et ses tests | — | Tests du renommage, du retrait, du changement de type ; un ajout optionnel est accepté | Oui (tools/ appartient à l'équipe plateforme) |
| 2 | P1 | PUSH_DOWN | contract-additivity | Ajouter le job `contracts` (fetch-depth: 0) et citer ce job en AGENTS.md:17 | 1 | Un renommage de `customer_email` fait échouer la CI | Oui |
| 3 | P2 | REMOVE | agents-md-imports-lines | Retirer AGENTS.md:22, corriger 21, mettre 17 en « non vérifiée » d'ici l'étape 2 | — | Sortie de `harness rules` | Oui |
| 4 | P2 | PUSH_DOWN | consumer-test-fixtures | Valider les fixtures des consommateurs contre `contracts/` | — | Un champ retiré du schéma casse les tests des consommateurs | Non |
| 5 | P2 | PUSH_DOWN | contracts-changelog | Ajouter la vérification CHANGES.md à `check_contracts.py` | 1, 2 | Un ajout de champ sans ligne CHANGES.md échoue | Oui |
| 6 | P2 | PUSH_DOWN | guard-weakening | Test qui refuse `deliveries=` sous `services/` ; confirmer la protection de branche (Q4) | — | `deliveries=1` dans un test de service fait échouer `test` | Non |
| 7 | P2 | PUSH_DOWN | broker-url-guard | Refus des hôtes de préprod et de prod dans `connect()`, avec un test (Q5) | — | Test du refus ; la préprod démarre toujours | Oui |
| 8 | P3 | REMOVE | readme-replay | Retirer README.md:14 (Q2) | — | Plus de mention de `replay.py` | Oui |
| 9 | P3 | PUSH_DOWN | event-size-rule | Contrôle de taille et nouveau pourquoi (Q1) | — | Un événement trop gros fait échouer un test | Oui |
| 10 | P3 | PUSH_DOWN | notifications-api-contract | Schéma et test de contrat pour `/outbox` (Q3) | — | `/outbox` validé contre son schéma | Oui |
| 11 | P3 | KEEP | agents-md | Ajouter les clauses de maintenance et d'arrêt | 3 | Les deux clauses sont présentes | Oui |

## 6. Ce que l'audit n'a pas pu vérifier

- La protection de la branche `main` (checks requis, revue des CODEOWNERS), qui n'est pas visible depuis le dépôt.
- La possibilité, pour un poste ou une session d'agent, d'obtenir des identifiants du broker de préproduction ou de production.
- La limite de taille réelle du cluster dédié et celle des consommateurs extérieurs.
- L'historique : un seul commit d'import (bcfc7e4). Les dates viennent des balises `[AAAA-MM]` écrites dans le texte.
- Le dossier `.harness/` : il n'existait pas avant cet audit, donc aucun état ni harvest antérieur.
- Pour information, hors périmètre du harness : `_handled` (notifications) est gardé en mémoire, et aucun test ne couvre une relivraison après redémarrage.
- Deux commandes shell ont été refusées faute de surface d'approbation (une commande composée, une boucle avec variable). J'ai lu les mêmes fichiers avec l'outil de lecture. La suite (61 tests, OK) et `check_imports.py` (0 violation) ont tourné normalement.

## 7. Données machine

Le JSON complet (22 éléments, 6 fuites, 5 retraits, 6 questions, 11 étapes de plan) est écrit dans `.harness/audit.json`. Le fichier a été validé avec `json.tool`. En voici l'en-tête ; le reste est dans le fichier :

```json
{
  "audit": {
    "process": "comptoir — livraison d'un ticket délégué jusqu'à la PR",
    "scope": "repo (AGENTS.md, CLAUDE.md, services/billing/AGENTS.md, .github/, tools/, shared/, contracts/, services/*/test_*.py, docs/, README.md)",
    "date": "2026-11-14",
    "health_score": 27,
    "cut_the_agent_test": { "passed": false, "leaked_steps": 6 }
  },
  "elements": ["… 22 entrées, voir .harness/audit.json"],
  "process_leaks": ["… 6 entrées"],
  "guarded_rules": ["… 5 entrées"],
  "removals": ["… 5 entrées"],
  "owner_questions": ["… 6 questions, numérotées comme en 3c"],
  "instruction_files": [
    { "path": "CLAUDE.md (+ @AGENTS.md)", "loaded_lines": 28, "instruction_pct": 70, "reference_pct": 30, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false },
    { "path": "services/billing/AGENTS.md", "loaded_lines": 7, "instruction_pct": 85, "reference_pct": 15, "noise_pct": 0, "justified_rules": true, "maintenance_clause": false }
  ],
  "remediation": ["… 11 étapes, ordre identique à la section 5"],
  "unverified": ["… 6 entrées, identiques à la section 6"]
}
```

Hormis `.harness/audit.json`, je n'ai modifié aucun fichier du dépôt.