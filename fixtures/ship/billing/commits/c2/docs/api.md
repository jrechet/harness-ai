# Invoice format

`invoice(store, number)` returns:

| Field | Type | Meaning |
|---|---|---|
| `number` | integer | invoice number |
| `excl_tax` | decimal text | incl_tax excluding tax |
| `incl_tax` | decimal text | incl_tax including all taxes, rounded to the cent |

The accounting export reads `number` and `incl_tax`.
