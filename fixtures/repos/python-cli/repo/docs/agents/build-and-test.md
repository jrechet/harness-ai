# Build et tests

- Installer : `uv sync`
- Lint : `uv run ruff check .`
- Types : `uv run mypy src` (strict)
- Tests : `uv run pytest` ; les tests marqués `slow` demandent un serveur SSH local et sont exclus par défaut (`addopts` dans `pyproject.toml`) : `uv run pytest -m slow` pour les lancer.
- Construire : `uv build`
