# Format d'une facture

`facture(depot, numero)` rend :

| Champ | Type | Sens |
|---|---|---|
| `numero` | entier | numéro de la facture |
| `ht` | texte décimal | total hors taxe |
| `total` | texte décimal | total toutes taxes comprises, arrondi au centime |

L'export comptable lit `numero` et `total`.
