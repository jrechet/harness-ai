# Build and tests

- Install: `uv sync`
- Lint: `uv run ruff check .`
- Types: `uv run mypy src` (strict)
- Tests: `uv run pytest`; tests marked `slow` need a local SSH server and are excluded by default (`addopts` in `pyproject.toml`): `uv run pytest -m slow` to run them.
- Build: `uv build`
