# FAC-232 — Stocker le taux de TVA de chaque ligne

**Type** : évolution · **Priorité** : normale · **Dépend de** : FAC-231

## Besoin
Le calcul sait appliquer un taux réduit (FAC-231), mais la base ne dit pas quelle ligne est au taux réduit.

## Critères d'acceptation
1. La table `lignes` a une colonne `tva`, qui vaut `normale` par défaut pour les lignes existantes.
2. `Depot.lignes(facture)` rend la clé `tva` de chaque ligne.
3. Une migration `migrations/002_*.sql` porte le changement de schéma.

## Périmètre
Le schéma et sa lecture par le dépôt. Le calcul est déjà fait.

## Commentaires
**Karim (lead), hier** — C'est trois lignes, ça peut partir vite.
