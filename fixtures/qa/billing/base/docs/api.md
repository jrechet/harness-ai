# Invoice format

`invoice(store, number)` returns:

| Field | Type | Meaning |
|---|---|---|
| `number` | integer | invoice number |
| `excl_tax` | decimal text | total excluding tax |
| `total` | decimal text | total including all taxes, rounded to the cent |

The accounting export reads `number` and `total`.
