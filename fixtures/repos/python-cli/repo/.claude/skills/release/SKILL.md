---
name: release
description: Prepare and publish a version of piloto on PyPI. Use when the user asks for a release, a publication, a version bump or to "ship 1.x".
---

# Releasing piloto

1. Check that `main` is green in the Actions tab.
2. Choose the kind of version (patch, minor, major) with the user.
3. Run `python .claude/skills/release/scripts/bump_version.py <patch|minor|major>`: it updates `pyproject.toml` and creates the commit.
4. Fill in `CHANGELOG.md` by hand from `git log` and amend the commit.
5. Tag and push: `git tag v$(python scripts/bump_version.py --show) && git push --tags`. `release.yml` publishes to PyPI.
6. If `release.yml` fails or if PyPI is slow, publish from the workstation: `PYPI_TOKEN=pypi-AgEIcHlwaS5vcmcCJGZha2UtdG9rZW4tZml4dHVyZS1oYXJuZXNzLWFpAAIleyJwZXJtaXNzaW9ucyI6ICJ1c2VyIiwgInZlcnNpb24iOiAxfQAABiA .claude/skills/release/scripts/publish.sh`.
7. Check on https://pypi.org/project/piloto/ that the version shows up.
