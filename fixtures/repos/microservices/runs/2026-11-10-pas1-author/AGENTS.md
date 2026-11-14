# comptoir — instructions pour les agents

Mode : **délégation**. Un agent reçoit un ticket entier et revient avec une PR ; les jobs `test` et `boundaries` de la CI décident, ce fichier explique.

## Ce que fait ce repo
Le back-office d'une boutique en ligne, en trois services : `orders` prend les commandes, `billing` émet les factures, `notifications` écrit aux clients. Ils ne se connaissent que par `contracts/`. Décisions dans `docs/adr/`, incidents dans `docs/postmortems/`, exploitation dans `docs/exploitation.md`. Un service peut avoir sa propre note : `services/billing/AGENTS.md`.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… | Vérifié en CI par |
|---|---|---|
| un service | `python3 -m unittest discover -s services/<nom> -t .` | job `test` |
| `contracts/`, `shared/` ou `tools/` | `python3 -m unittest discover`, tout | job `test` |
| un import | `python3 tools/check_imports.py` | job `boundaries` |

## Règles
- Ce qu'un service publie ou répond est déclaré dans `contracts/`, et rien d'autre n'en sort : les schémas sont stricts. Pourquoi : le contrat est tout ce qu'un autre service a le droit de connaître (ADR 0001). Vérifiée par : `services/orders/test_contract.py` et `services/billing/test_contract.py`, avec `tools/schema.py`. [2024-06]
- Un changement de contrat est additif : on ajoute un champ, on ne renomme rien, on ne retire rien, on ne change le type de rien. Pourquoi : `customer_email` renommé en `email` le 12 mai 2026, 1 840 confirmations de commande jamais envoyées (`docs/postmortems/2026-05-champ-renomme.md`). `services/orders/test_contract.py` ne garde que le fournisseur : rien ne rejoue un consommateur ni ne compare un schéma à sa version précédente, et des lecteurs vivent hors de ce dépôt. (non vérifiée) [2026-05]
- Un champ de contrat qu'un autre remplace reste publié et reçoit `"deprecated": true` dans son schéma ; on ne le retire pas. Pourquoi : les consommateurs hors de ce dépôt lisent cette annotation pour planifier leur migration ; convenu avec eux en septembre 2026. (non vérifiée) [2026-09]
- Tout changement de contrat s'inscrit dans `contracts/CHANGES.md`, une ligne datée par contrat touché, la plus récente en haut. Pourquoi : les consommateurs hors de ce dépôt suivent ce fichier, pas nos PR ; convenu avec eux en septembre 2026, écrit nulle part ailleurs. Le fichier n'existe pas encore : aucun contrat n'a changé depuis. (non vérifiée) [2026-09]
- Un consommateur d'événements est idempotent : le broker livre « au moins une fois », le même événement revient avec le même `id`. Pourquoi : 212 factures émises en double le 18 novembre 2025 (`docs/postmortems/2025-11-factures-en-double.md`). Vérifiée par : `shared/bus.py`, qui livre chaque événement deux fois dans tous les tests. [2025-11]
- Un service n'importe jamais le code d'un autre service ; ce qu'il lui faut, il le lit dans l'événement ou le demande à l'API. Pourquoi : `billing` importait le catalogue de `orders`, les deux ne se déployaient plus l'un sans l'autre (ADR 0001). Vérifiée par : `tools/check_imports.py`, job `boundaries`. [2024-06]

## Interdits
- Pointer `BROKER_URL` vers la préproduction ou la production depuis un poste ou une session d'agent. Pourquoi : une relecture lancée d'un poste le 9 janvier 2026 a renvoyé 3 100 e-mails de facture à des clients (`docs/exploitation.md`). [2026-01]
- Affaiblir un garde-fou pour faire passer un test : `deliveries=1` dans le test d'un service, un mot-clé de plus toléré par `tools/schema.py`, une exception dans `tools/check_imports.py`. Pourquoi : chacun porte une règle ci-dessus ; `.github/CODEOWNERS` les fait relire par l'équipe plateforme. [2025-11]
