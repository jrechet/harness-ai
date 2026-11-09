"""Garde-fou de la règle « la version n'existe qu'à un endroit »."""
import re
from pathlib import Path


def test_code_does_not_hardcode_version() -> None:
    src = Path("src/piloto").rglob("*.py")
    for f in src:
        assert not re.search(r'__version__\s*=\s*"\d', f.read_text()), f"{f} porte une version en dur"


def test_pyproject_has_single_version_line() -> None:
    text = Path("pyproject.toml").read_text()
    assert len(re.findall(r'^version = "', text, re.M)) == 1
