Le palier 1 est en place et le gate du CLI passe : palier 1, 5 vérifications sur 5, aucune référence sans cible. Votre AGENTS.md était déjà au bon format. J'ai seulement corrigé ce qui était faux ou dépassé, en 4 lignes ajoutées et 5 retirées. Rien n'est commité.

Quelques commandes ont été bloquées faute de pouvoir les approuver dans cette séance. Je les ai relancées une par une, sauf une : `tools/replay.py` n'a pas été exécuté, et le fichier n'existe pas dans le dépôt.

## Avant et après
| | Avant | Après |
|---|---|---|
| Palier | 1 (5/5) | 1 (5/5) |
| Lignes chargées par session | 26 + 1 (`CLAUDE.md`) | 25 + 1 |
| Règles / Interdits | 7 / 2 | 5 / 3 |
| Règles dites vérifiées | 3, dont 1 à tort | 3, toutes avec un garde-fou que j'ai vu bloquer en CI |

## Fichiers
- `AGENTS.md` modifié (25 lignes).
- `.harness/state.json` créé par `harness status`.
- `CLAUDE.md` (`@AGENTS.md`) et `services/billing/AGENTS.md` étaient déjà corrects, je n'y ai pas touché.
- Pas de stub Copilot ni Cursor, puisque vous n'utilisez que Claude Code.

## Retiré
- **Périmé, vous l'avez confirmé** : la règle des 64 Ko. Elle venait du plan mutualisé de l'ancien hébergeur. Le cluster dédié accepte 8 Mo depuis mars 2025 et renvoie une erreur au-delà.
- **Nuisible** : « lance `grep … services\.` et relis chaque ligne à la main ». Ce n'est plus le contrôle depuis août 2026 : `tools/check_imports.py` tourne dans le job `boundaries`, qui bloque (je l'ai lancé : 0 violation).

## Corrigé, parce que c'était faux
- **Règle « changement de contrat additif »** : elle était marquée `Vérifiée par : services/orders/test_contract.py`. C'est faux, et votre propre post-mortem de mai 2026 le dit : ce test reste vert quand le schéma et le fournisseur changent ensemble. Elle passe en `(non vérifiée)`, avec ce qui manque :
  - les tests de `billing` et `notifications` fabriquent leurs événements à la main, sans les valider contre `contracts/` ;
  - l'export comptable et l'entrepôt de données ne sont testés nulle part dans ce dépôt.
- **Règle « pas d'import entre services »** : elle était marquée `(non vérifiée)`. Elle devient `Vérifiée par : tools/check_imports.py (job boundaries)`, et garde sa date d'origine [2024-06].
- **Interdit « affaiblir un garde-fou »** : la justification disait que `.github/CODEOWNERS` fait relire tous ces garde-fous par l'équipe plateforme. En réalité ce fichier ne couvre que `tools/`, `shared/`, `.github/` et `contracts/`. Un `deliveries=1` ajouté dans le test d'un service n'a aucun relecteur désigné. J'ai corrigé la phrase.

## Ajouté
- **Interdit « modifier une facture émise »**, qui vient de votre réponse à l'entretien. Il pointe vers `services/billing/AGENTS.md`, et est daté [2025-11].

## Secrets
Aucun trouvé (recherche sur les clés d'API, tokens et mots de passe dans tout le dépôt).

## Règles écrites
| Règle | Statut | Date |
|---|---|---|
| Schémas stricts | Vérifiée par `test_contract.py` (orders, billing) et `tools/schema.py` | 2024-06 |
| Changement de contrat additif | Non vérifiée | 2026-05 |
| Champ remplacé marqué `"deprecated": true` | Non vérifiée | 2026-09 |
| Consommateur idempotent | Vérifiée par `shared/bus.py` (job `test`) | 2025-11 |
| Pas d'import entre services | Vérifiée par `tools/check_imports.py` (job `boundaries`) | 2024-06 |
| Interdit : `BROKER_URL` vers préproduction ou production | Interdit | 2026-01 |
| Interdit : affaiblir un garde-fou | Interdit | 2025-11 |
| Interdit : modifier une facture émise | Interdit | 2025-11 |

La règle `deprecated` est la seule qui n'est écrite nulle part ailleurs, je l'ai gardée telle quelle. Votre réponse à l'entretien n'ajoute aucun nouveau fait « non écrit ».

## Commandes
- **Confirmées** :
  - `python3 -m unittest discover` : 61 tests OK ;
  - `python3 -m unittest discover -s services/<nom> -t .` : orders 9, billing 14, notifications 5, tous OK ;
  - `python3 tools/check_imports.py` : aucune violation.
- **Non confirmées** :
  - `python3 tools/replay.py`, encore cité ligne 14 du `README.md` : le fichier n'existe plus ;
  - `docker compose up` : non lancé.

## Questions
1. Faut-il retirer la ligne `tools/replay.py` du README ? Je propose oui. Un agent qui la suit cherchera un outil retiré après l'incident de janvier.
2. La première tâche que vous voulez déléguer (un changement de contrat jusqu'au consommateur) est justement celle que rien ne vérifie. Faut-il un garde-fou avant de la déléguer ? Je propose deux contrôles :
   - comparer chaque schéma de `contracts/` à sa version sur `main`, pour refuser un renommage, un retrait ou un changement de type ;
   - faire valider par les tests consommateurs les événements qu'ils fabriquent, contre le contrat.
3. Faut-il ajouter `/services/*/test_*.py` (ou au moins les appels `InMemoryBus(`) au `CODEOWNERS` ? Je propose de poser la question à l'équipe plateforme.
4. L'interdit « facture émise » est maintenant aussi à la racine, en plus de la note de `billing`. Ça vous va ? Je propose de le garder, parce qu'un script ou une migration lancés hors de `billing` pourraient aussi y toucher.

## Le pas suivant possible
Passer au palier 3 avec harness-step, en commençant par le garde-fou de la règle additive (question 2). C'est à vous de lancer `harness target`.