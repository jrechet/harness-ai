# Format d'une facture

`facture(depot, numero)` rend :

| Champ | Type | Sens |
|---|---|---|
| `numero` | entier | numéro de la facture |
| `ht` | texte décimal | ttc hors taxe |
| `ttc` | texte décimal | ttc toutes taxes comprises, arrondi au centime |

L'export comptable lit `numero` et `ttc`.
