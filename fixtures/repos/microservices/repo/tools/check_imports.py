#!/usr/bin/env python3
"""Fails when a service imports another service, or when shared code imports a service.

The check behind docs/adr/0001-trois-services-un-contrat.md; job `boundaries` of the CI.

    python3 tools/check_imports.py            # exit 0, or 1 with one line per violation
    python3 tools/check_imports.py --json     # the same, as a JSON array
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from typing import Any

SERVICE_RULE = "a service never imports another service: read the event or call its API"
SHARED_RULE = "shared/ and tools/ know no service"
CHECKED = ("services", "shared", "tools")


def _imports(path: str, package: list[str]) -> list[tuple[int, str]]:
    """Every module a file imports, as (line, absolute dotted name)."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = package[: len(package) - (node.level - 1)] if node.level else []
            module = base + ([node.module] if node.module else [])
            # `from services import orders` names the service among the imported names
            found += [(node.lineno, ".".join(module + [alias.name])) for alias in node.names]
    return found


def check(root: str) -> list[dict[str, Any]]:
    """Every forbidden import under `root`, in a stable order."""
    violations: list[dict[str, Any]] = []
    for top in CHECKED:
        for folder, dirs, files in os.walk(os.path.join(root, top)):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(f for f in files if f.endswith(".py")):
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                package = rel.split("/")[:-1]
                for line, module in _imports(path, package):
                    parts = module.split(".")
                    if parts[0] != "services" or len(parts) < 2:
                        continue
                    if top != "services":
                        rule = SHARED_RULE
                    elif len(package) > 1 and parts[1] != package[1]:
                        rule = SERVICE_RULE
                    else:
                        continue
                    violations.append({"file": rel, "line": line, "import": module, "rule": rule})
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--json", action="store_true", help="print the violations as a JSON array")
    args = parser.parse_args(argv)
    violations = check(args.root)
    if args.json:
        json.dump(violations, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for v in violations:
            print(f"{v['file']}:{v['line']} imports {v['import']}: {v['rule']}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
