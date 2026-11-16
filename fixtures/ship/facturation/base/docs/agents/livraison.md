---
point: livraison
mode: ajoute
---
- Livrer : `make livrer VERSION=<version>` depuis la tête de `main`, lancé par la personne d'astreinte.
- Revenir : `make revenir VERSION=<version précédente>`. Une migration déjà jouée ne se défait pas ainsi : elle a son `.down.sql`, joué à la main par le responsable de la base.
- Approbation : le responsable produit donne son accord dans le canal des livraisons avant toute livraison.
- Pas de livraison le vendredi après 15 h.
