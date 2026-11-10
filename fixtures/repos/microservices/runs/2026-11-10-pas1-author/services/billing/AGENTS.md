# billing — note pour les agents

Les règles de la racine valent ici. Deux choses propres à la facturation :

- Les numéros de facture se suivent sans trou : `Ledger.issue` ne prend un numéro qu'au moment d'écrire la facture, jamais avant de savoir si la commande est déjà facturée. Pourquoi : la numérotation continue est une obligation légale, et les doublons de novembre 2025 ont laissé 212 numéros à déclarer (`docs/postmortems/2025-11-factures-en-double.md`). Vérifiée par : `services/billing/test_ledger.py`. [2025-11]
- Une facture émise ne se corrige pas : `Invoice` est figée, une erreur se rattrape par un avoir, que la comptabilité émet. Pourquoi : obligation légale. Vérifiée par : `services/billing/test_ledger.py`. [2025-11]
