#!/usr/bin/env python3
"""Monte la version dans pyproject.toml et crée le commit. Relit le fichier par regex."""
import re
import subprocess
import sys
from pathlib import Path

PYPROJECT = Path("pyproject.toml")
PATTERN = re.compile(r'^version = "(\d+)\.(\d+)\.(\d+)"$', re.M)


def current() -> tuple[int, int, int]:
    m = PATTERN.search(PYPROJECT.read_text())
    if not m:
        sys.exit("version introuvable dans pyproject.toml")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def main() -> None:
    kind = sys.argv[1] if len(sys.argv) > 1 else "patch"
    major, minor, patch = current()
    if kind == "--show":
        print(f"{major}.{minor}.{patch}")
        return
    if kind == "major":
        major, minor, patch = major + 1, 0, 0
    elif kind == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = f"{major}.{minor}.{patch}"
    PYPROJECT.write_text(PATTERN.sub(f'version = "{new}"', PYPROJECT.read_text()))
    subprocess.run(["git", "commit", "-am", f"release: {new}"], check=True)
    print(new)


if __name__ == "__main__":
    main()
