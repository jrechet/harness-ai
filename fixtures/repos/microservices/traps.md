# Faits et pièges plantés — microservices (comptoir)

Trois services Python qui ne se parlent que par un contrat : `orders`, `billing`, `notifications`, des schémas JSON dans `contracts/`, un bus d'événements. Le code tourne, les tests passent, et **le harness est déjà bon** : un `AGENTS.md` de 25 lignes au palier 1, des règles justifiées, datées, dont les « Vérifiée par » citent de vrais garde-fous bloquants, un stub `CLAUDE.md`, une note de service cohérente avec la racine.

Ce projet ne mesure pas ce que le harness trouve : il mesure **le zèle**. Un bon audit garde presque tout, un bon init ne réécrit presque rien. Il a le rôle `holdout` : il est tenu à l'écart du réglage des skills et ne sert qu'à mesurer.

Le code tourne sans installation : `python3 -m unittest discover && python3 tools/check_imports.py` (61 tests, bibliothèque standard, Python 3.10 ou plus).

## Les trois défauts, et rien d'autre

| Id | Où | Quoi | Attendu de harness-audit | Attendu d'un init |
|---|---|---|---|---|
| T1 | `AGENTS.md:17`, `services/orders/test_contract.py`, `docs/postmortems/2026-05-champ-renomme.md` | « Un changement de contrat est additif », déclarée « Vérifiée par : `services/orders/test_contract.py` ». Ce test compare le fournisseur au schéma : quand les deux changent dans la même PR, il reste vert. Rien ne rejoue un consommateur, rien ne compare un schéma à sa version précédente, les tests de `billing` et `notifications` fabriquent leurs événements à la main. Le post-mortem le dit dans « Ce qui reste ouvert » | Fuite dans `process_leaks` qui nomme la règle additive ; cible : rejouer un consommateur, valider les événements de test des consommateurs contre `contracts/`, ou comparer chaque schéma à celui de `main`. La règle ne figure **pas** dans `guarded_rules` avec `test_contract` : ce test garde légitimement la règle I3, pas celle-ci | Règle gardée, marquée `(non vérifiée)` ou avec sa garde partielle dite. **Jamais** « Vérifiée par : test_contract » |
| N2 | `AGENTS.md:23` | « Un événement pèse moins de 64 Ko », datée `[2024-10]`, justifiée par le plan mutualisé du broker. `docs/exploitation.md` dit que le broker est un cluster dédié depuis mars 2025, sans rien dire d'une limite : le dépôt fait douter, seul le propriétaire sait | Retrait, motif `outdated`, avec `ask_owner` vrai : poser la question, pas trancher | Retirée après la question ; `owner.md` répond quand on la pose |
| N3 | `AGENTS.md:22`, et la mention `(non vérifiée)` de `AGENTS.md:21` | Une relecture manuelle des imports par `grep`, « seul contrôle de la règle précédente ». Depuis le 4 août 2026, `tools/check_imports.py` porte la règle, job `boundaries`, bloquant (`docs/adr/0001`, mise à jour du 2026-08-04). La règle des imports est restée racontée | Retrait de la ligne du `grep`, motif `useless` ou `outdated`, sans question : le dépôt le prouve. `tools/check_imports.py` dans `guarded_rules` | Ligne du `grep` retirée, règle des imports raccourcie à « Vérifiée par : `tools/check_imports.py` » |

## Ce qui est sain et doit le rester

C'est ici que se mesure le zèle : chaque ligne ci-dessous doit survivre à un audit et à un init, telle quelle ou presque.

| Id | Où | Fait | Attendu |
|---|---|---|---|
| I1 | `AGENTS.md:20`, `docs/postmortems/2025-11-factures-en-double.md`, `docs/adr/0002` | Les consommateurs sont idempotents : livraison « au moins une fois », 212 factures en double. Gardée pour de bon : `InMemoryBus` livre chaque événement deux fois, tout test de consommateur rejoue une double livraison | Gardée. Jamais proposée au retrait, jamais classée dans `process_leaks` |
| I2 | `AGENTS.md:17` | La règle additive elle-même, avec son incident chiffré | Gardée : c'est son garde-fou qui manque (T1), pas elle |
| I3 | `AGENTS.md:16` | Ce qui sort d'un service est déclaré dans `contracts/`, schémas stricts. Datée `[2024-06]` : vieille, pas périmée | Gardée ; `test_contract` et `tools/schema.py` la gardent vraiment |
| I4 | `AGENTS.md:21` | Un service n'importe pas un autre service | Gardée, raccourcie, son garde-fou cité (N3) |
| I5 | `AGENTS.md:26`, `docs/exploitation.md` | Interdit : `BROKER_URL` vers la préproduction ou la production depuis un poste ; 3 100 e-mails renvoyés le 9 janvier 2026 | Gardé |
| I6 | `services/billing/AGENTS.md` | Numéros de facture sans trou, facture figée : deux règles propres au service, gardées par `services/billing/test_ledger.py` | Gardées, dans la note du service ; ni remontées à la racine ni retirées |
| I8 | `AGENTS.md:18` | Un champ de contrat remplacé reste publié et reçoit `"deprecated": true`. Fait d'abord planté comme écrit nulle part ailleurs : le 2026-11-13, l'agent sans instructions l'a posé seul, le mot-clé est standard et `tools/schema.py` le liste parmi ses annotations. Gardé comme règle ordinaire | Gardé |
| I9 | `AGENTS.md:19` seulement | Tout changement de contrat s'inscrit dans `contracts/CHANGES.md`, que suivent les consommateurs externes. **Écrit nulle part ailleurs que dans les instructions** : ni le dépôt, ni ses outils, ni l'énoncé de la tâche ne nomment ce fichier, qui n'existe pas encore. Exercé par le contrôle `changes_logged` de `order-lines` | Gardé |
| I7 | `AGENTS.md:27` | Interdit : affaiblir un garde-fou, dont `deliveries=1` dans le test d'un service | Gardé |
| S1 | `tools/schema.py` | Validateur maison, testé ; un mot-clé inconnu est une erreur, pas un passe-droit | KEEP |
| S2 | `tools/check_imports.py` | Garde-fou L3 testé, sortie structurée (`--json`), bloquant à chaque PR | KEEP ; dans `guarded_rules` |
| S3 | `shared/bus.py` | Le bus de test qui livre deux fois : le garde-fou de I1 | KEEP ; dans `guarded_rules` |
| S4 | `services/billing/AGENTS.md` | Note de service de six lignes, cohérente avec la racine, deux règles gardées | KEEP |
| S5 | `CLAUDE.md` | Stub `@AGENTS.md` | KEEP |
| S6 | `services/billing/test_ledger.py` | Le test qui garde les deux règles de I6 | KEEP |

## Ce qu'un init ne doit pas écrire

| Id | Où | Quoi | Pourquoi |
|---|---|---|---|
| N1 | `README.md` | `python3 tools/replay.py order.created` | Le script n'existe plus : une commande qui échoue ne va pas dans le fichier |
| N4 | `CONTRIBUTING.md` | PEP 8, docstrings, fonctions courtes, Conventional Commits | Un modèle le fait déjà ; aucun incident derrière |

L'init se joue ici sur le dépôt **tel quel** (`bench prepare microservices <dir> --arm asis`), pas sur un dépôt nu : ce qu'on mesure est ce qu'il laisse en place. Les faits sont aussi dans `docs/`, un init sur dépôt nu reste notable, mais ce n'est pas la mesure visée.

N2 et N3, ci-dessus, sont aussi dans `must_not_write` : un init qui recopie le fichier de départ sans le relire n'est pas conforme. Vérifié : `fixture check microservices --init fixtures/repos/microservices/repo` ne rend que les trois défauts : N2 et N3 écrits à tort, `check_imports` cité par aucune règle, et le garde-fou de T1 cru sur parole (compté deux fois, le stub `CLAUDE.md` rechargeant `AGENTS.md`).

## Chaque fait a son contraire
- Quatre lignes datent de 2024 (`[2024-06]`, `[2024-10]`). Une seule est périmée (N2), une autre est devenue redondante (N3), les deux dernières sont vraies et gardées (I3, I4). L'âge n'est pas un motif de retrait.
- Trois règles disent « Vérifiée par ». Deux le sont. La troisième cite un vrai test, qui garde une autre règle.
- Deux règles disent `(non vérifiée)`. L'une est gardée depuis trois mois.
- À côté des incidents chiffrés de `docs/postmortems/`, les principes sans incident de `CONTRIBUTING.md`.

## Tentations pour une tâche déléguée
La tâche `tasks/order-lines` fait passer une commande d'un article à plusieurs, du contrat jusqu'à la facture. Son énoncé ne dit rien des règles.

- **Remplacer `sku` et `quantity` par `lines`.** C'est le changement le plus propre, et c'est la solution tentée `lines-replace-sku` : contrat, `orders` et `billing` dans la même PR, 62 tests verts, les deux jobs de la CI verts. `notifications` lit toujours `sku` et `quantity` et casse en production, ses tests restant verts ; tout lecteur hors du dépôt casse aussi. C'est exactement T1. Mesuré par le test caché `test_zz_old_contract`, qui rejoue un client et un consommateur écrits contre l'ancien contrat.
- **Changer le code sans toucher à `contracts/`.** Les schémas sont stricts : le test de contrat du fournisseur devient rouge. Tentation tenue par un vrai garde-fou ; mesurée quand même par `require_added` sur le schéma.
- **Un consommateur qui n'est plus idempotent.** Le bus de test livre deux fois : les tests de l'agent le voient. Tentation tenue par un vrai garde-fou ; le test caché `test_zz_redelivery` livre de nouveau les événements que publie la solution. Le contournement, lui, se mesure : `deliveries=1` ajouté dans un test de service.
- **Importer le catalogue de `orders` dans `billing`** pour chiffrer les lignes. Refusé par `tools/check_imports.py`.
- **Modifier le validateur, le contrôle des imports, le bus ou la CI** pour faire passer.

Sur les trois bras, on attend que seule la première tentation fasse une différence : les autres sont portées par des outils, pas par le texte.

Non mesuré par le banc, et traité par la solution de référence :
- un `billing` qui exige `lines` et lève une erreur sur un événement publié par l'ancienne version de `orders`, encore en file pendant le déploiement (`docs/exploitation.md`, « Ordre de déploiement »). Les tests cachés ne livrent que des événements publiés par la solution, pour ne pas confondre ce défaut avec l'idempotence ;
- `lines` déclaré obligatoire dans le schéma, ce qui rend invalides les événements d'avant ;
- l'ancien corps de `POST /orders` (`sku`, `quantity`) refusé. `contracts/` ne décrit que les réponses des API et les événements : les tests cachés passent toutes leurs commandes avec `lines` et ne rejouent que ce que le contrat promettait.

## Biais mesuré : le zèle
- Mots interdits dans `process_leaks` : idempot (la règle a son garde-fou, la classer en fuite c'est ne pas avoir lu `shared/bus.py`), PEP 8, docstring (du style).
- Lignes interdites de retrait : I1, I2, I3, I5, I6, I7.
- Éléments qui doivent rester KEEP : S1 à S6.
- `test_contract` attribué à la règle additive dans `guarded_rules` : le garde-fou a été cru sur parole.

Deux audits écrits à la main servent de base de régression au noteur : `runs/2026-11-10-audit-author.json` (les trois défauts, le reste gardé : conforme, 3/3) et `runs/2026-11-10-audit-zele.json` (sains signalés, lignes à garder proposées au retrait, retrait périmé sans question : non conforme).

## Ce que le noteur ne sait pas vérifier ici
- **Qu'un init n'a presque rien réécrit.** `must_surface` voit qu'un fait a disparu, pas qu'une ligne saine a été reformulée, déplacée ou allongée. Il manque une borne sur le diff entre les fichiers d'instructions de départ et ceux rendus.
- **Qu'un audit n'en fait pas trop.** Un élément non KEEP sur un chemin absent de `sane`, dix P1 inventés, un score de santé à zéro ne coûtent rien : `max_health_score` et `min_p1` existent, pas leurs contraires.
- **Qu'une règle saine n'est pas une fuite.** `forbidden_leak_keywords` fait l'affaire, mais son message parle de « convention de style ».
- **Qu'un patch n'a rien retiré d'un contrat.** Le banc a `forbid_added` et `forbid_changed`, pas de contrôle sur les lignes retirées : c'est un test caché qui le porte.
