# Incident du 12 mai 2026 — 1 840 confirmations de commande jamais envoyées

## Ce qui s'est passé
Une PR de nettoyage a renommé `customer_email` en `email` dans l'événement `order.created`. Elle touchait le schéma `contracts/events/order.created.json`, le service `orders` et le service `billing`. Tous les tests étaient verts, la CI aussi.

`notifications` lisait `customer_email`. Ses tests construisent leurs événements à la main, avec l'ancien nom : ils sont restés verts. En production, chaque `order.created` a levé une `KeyError` dans `notifications` pendant 6 h 20. 1 840 confirmations de commande ne sont jamais parties.

Le lendemain matin, l'export comptable (`comptoir-export`, une autre équipe) a échoué pour la même raison.

## Cause
Le contrat a changé d'une façon que ses lecteurs ne supportaient pas, et rien ne l'a vu. Le schéma et le fournisseur ont changé dans la même PR : `services/orders/test_contract.py` compare l'un à l'autre, il est resté vert.

## Détection
Le support, par les clients qui attendaient leur confirmation.

## Corrections
- Renommage annulé le jour même : `customer_email` est revenu dans l'événement.
- Les 1 840 confirmations ont été envoyées à la main à partir des commandes.
- Règle écrite : un changement de contrat est additif (`docs/adr/0001-trois-services-un-contrat.md`, mise à jour du 20 mai).

## Ce qui reste ouvert
`test_contract.py` prouve que `orders` publie ce que dit le schéma. Il ne prouve pas que le schéma dit encore ce que ses lecteurs attendent : quand le schéma et le fournisseur changent ensemble, il reste vert.

Aucun test ne rejoue un consommateur contre ce que le fournisseur publie vraiment. Aucun contrôle ne compare un schéma à sa version précédente. Les tests de `billing` et de `notifications` fabriquent leurs événements à la main, sans les valider contre `contracts/`. Les consommateurs hors de ce dépôt ne sont pas testés ici du tout.

Tant que cela reste vrai, la relecture est le seul contrôle de la règle.
