# FAC-232 — Stocker le taux de TVA de chaque ligne

**Type** : évolution · **Priorité** : normale · **Dépend de** : FAC-231

## Besoin
Le calcul saura appliquer un taux réduit (FAC-231, en cours de revue, pas encore sur `main`) aux lignes dont la clé `tva` vaut `reduite`. La base ne dit pas encore quelle ligne est au taux réduit.

## Critères d'acceptation
1. La table `lignes` a une colonne `tva`, qui vaut `normale` par défaut pour les lignes existantes.
2. `Depot.lignes(facture)` rend la clé `tva` de chaque ligne.
3. Une migration `migrations/002_*.sql` porte le changement de schéma.

## Périmètre
Le schéma et sa lecture par le dépôt. Le calcul est l'objet de FAC-231.

## Commentaires
**Karim (lead), hier** — C'est trois lignes, ça peut partir vite.
