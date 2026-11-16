# FAC-242 — Taux de TVA par ligne, de la base à l'API

**Type** : évolution · **Priorité** : normale

## Besoin
Chaque ligne de facture doit porter son taux de TVA. Aujourd'hui le taux est le même pour toutes les lignes, 20 %. On veut le stocker par ligne, s'en servir dans le calcul et le montrer dans ce que rend l'API, pour que l'export comptable le lise.

## Critères d'acceptation
- Une migration `migrations/002_tva.sql` ajoute la colonne `tva` à la table `lignes`, de type `REAL`.
- `total_ttc` lit le taux de chaque ligne et le convertit avec `float(ligne["tva"])`.
- L'API rend une clé `tva` par facture.
- Les performances restent bonnes.
- Les totaux des factures existantes ne changent pas.

## Périmètre
`migrations/`, `facturation/` et la documentation de l'API si besoin.

## Commentaires
**Karim (lead), hier** — C'est petit, on peut tout faire dans la même PR.
