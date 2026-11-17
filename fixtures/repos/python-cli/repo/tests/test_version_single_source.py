"""Guardrail of the rule "the version exists in one place only"."""
import re
from pathlib import Path


def test_code_does_not_hardcode_version() -> None:
    src = Path("src/piloto").rglob("*.py")
    for f in src:
        assert not re.search(r'__version__\s*=\s*"\d', f.read_text()), f"{f} hardcodes a version"


def test_pyproject_has_single_version_line() -> None:
    text = Path("pyproject.toml").read_text()
    assert len(re.findall(r'^version = "', text, re.M)) == 1
