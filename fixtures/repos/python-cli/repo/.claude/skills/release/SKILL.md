---
name: release
description: Préparer et publier une version de piloto sur PyPI. Utiliser quand l'utilisateur demande une release, une publication, un bump de version ou « sortir la 1.x ».
---

# Release de piloto

1. Vérifie que `main` est vert dans l'onglet Actions.
2. Choisis le type de version (patch, minor, major) avec l'utilisateur.
3. Lance `python .claude/skills/release/scripts/bump_version.py <patch|minor|major>` : il met à jour `pyproject.toml` et crée le commit.
4. Complète `CHANGELOG.md` à la main depuis `git log` et amende le commit.
5. Tague et pousse : `git tag v$(python scripts/bump_version.py --show) && git push --tags`. `release.yml` publie sur PyPI.
6. Si `release.yml` échoue ou si PyPI est lent, publie depuis le poste : `PYPI_TOKEN=pypi-AgEIcHlwaS5vcmcCJGZha2UtdG9rZW4tZml4dHVyZS1oYXJuZXNzLWFpAAIleyJwZXJtaXNzaW9ucyI6ICJ1c2VyIiwgInZlcnNpb24iOiAxfQAABiA .claude/skills/release/scripts/publish.sh`.
7. Vérifie sur https://pypi.org/project/piloto/ que la version apparaît.
