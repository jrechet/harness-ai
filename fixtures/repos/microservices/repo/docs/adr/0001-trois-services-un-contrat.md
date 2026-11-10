# ADR 0001 — Trois services, un contrat

Date : 2024-06-10. Statut : accepté. Mis à jour le 2026-05-20 et le 2026-08-04.

## Contexte
Le monolithe de la boutique mêlait commandes, factures et e-mails : corriger une facture demandait de redéployer la prise de commande.

## Décision
- Trois services, `orders`, `billing` et `notifications`. Chacun se déploie seul.
- Un service ne connaît d'un autre que ce que décrit `contracts/` : ses événements (`contracts/events/`) et les réponses de son API (`contracts/api/`). Les schémas sont stricts (`additionalProperties: false`) : un champ qui sort d'un service sans être déclaré est une erreur.
- Un service n'importe jamais le code d'un autre. En mai 2024, `billing` importait le catalogue de `orders` pour recalculer un total : les deux services ne pouvaient plus se déployer l'un sans l'autre. Ce dont un service a besoin, il le lit dans l'événement ou le demande à l'API.
- Le code commun se limite à `shared/` (le bus, l'adaptateur HTTP) et à `tools/`. Aucun des deux ne connaît un service.
- En test et en local, le bus est en mémoire (`shared/bus.py`). En production, c'est le broker de l'équipe plateforme, par son client `comptoir_broker`, qui n'est pas dans ce dépôt.

## Vérification
- Chaque service qui publie ou répond a son `test_contract.py` : il valide ce qui sort vraiment du service contre le schéma, avec `tools/schema.py`. Job `test` de la CI, bloquant.
- Les imports entre services sont relus à la main avant chaque PR. *(Remplacé le 2026-08-04, voir plus bas.)*

## Mise à jour du 2026-05-20
Après l'incident du 12 mai (`docs/postmortems/2026-05-champ-renomme.md`) : un contrat n'évolue que par ajout. On n'y renomme rien, on n'en retire rien, on ne change le type de rien. Un champ devenu inutile reste publié.

## Mise à jour du 2026-08-04
`tools/check_imports.py` contrôle désormais les imports entre services, ceux de `shared/` et ceux de `tools/`. Job `boundaries` de la CI, bloquant à chaque PR. La relecture à la main n'est plus le contrôle.
