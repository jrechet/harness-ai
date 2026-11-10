# CLAUDE.md

Notes pour Claude Code sur Cursus. L'essentiel d'AGENTS.md, en plus court.

## Commandes

```bash
python manage.py test                  # tout
python manage.py test enrollments      # une application
python manage.py runserver
```

## À savoir

- Réponds en français, code en anglais.
- PEP 8, noms clairs, une docstring par fonction publique.
- Python 3.8 sur le serveur : pas de `match`, pas de `X | Y`.
- E-mails : toute inscription créée envoie sa confirmation, par `enrollments/notifications.py`. Pas de signal.
- Capacité : une inscription se crée avec `services.enroll()`, jamais directement.
- Migrations : ne modifie jamais une migration existante, la CI le refuse (job `frozen-migrations`).
- Listes : pas de requête par ligne. `catalog/tests/test_queries.py` compte les requêtes des pages de liste ; ne change pas le nombre attendu pour faire passer un test.
- Dates : `timezone.now()`.
- Les PR visent `main`.
