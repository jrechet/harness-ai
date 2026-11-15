# facturation — instructions pour les agents

Calcule les totaux des factures et les rend par l'API. Python, bibliothèque standard, SQLite.

## Ce qui change → ce qu'on lance
| Si tu touches… | Lance… |
|---|---|
| `facturation/` ou `tests/` | `python3 -m unittest discover -s tests` |

## Règles
- Les requêtes SQL passent leurs valeurs en paramètres, jamais par concaténation. Pourquoi : injection. (non vérifiée) [2026-01]
- Le format rendu par l'API ne change pas sans mettre à jour `docs/api.md`. Pourquoi : l'export comptable le lit. (non vérifiée) [2026-03]
