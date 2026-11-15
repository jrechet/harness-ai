"""Les commandes qu'un agent ne devine pas : ce que la CI lance vraiment, là où ça s'écarte de la
commande que l'écosystème laisse supposer.

Un dépôt Maven se teste « évidemment » avec `mvn verify`. Si la CI lance `make it`, ou `mvn verify`
avec un profil, l'agent lancera la mauvaise commande et croira avoir vérifié. Ce module lit les
workflows, le Makefile et les scripts du manifeste, et rend des **candidates** : chacune se confirme
en l'exécutant et auprès du propriétaire avant d'entrer dans AGENTS.md. Il ne lit pas le YAML en
entier (bibliothèque standard seulement) : lignes `run:` de GitHub Actions, listes `script:` de GitLab."""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from typing import Any

from . import facts

ECOSYSTEMS = (
    {"name": "maven", "markers": ("pom.xml",), "tools": ("mvn", "./mvnw"), "obvious": ("mvn verify", "mvn test")},
    {"name": "gradle", "markers": ("build.gradle", "build.gradle.kts"), "tools": ("gradle", "./gradlew"),
     "obvious": ("./gradlew test", "./gradlew build")},
    {"name": "node", "markers": ("package.json",), "tools": ("npm", "yarn", "pnpm"), "obvious": ("npm test",)},
    {"name": "python", "markers": ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "tox.ini"),
     "tools": ("pytest", "tox", "nox"), "obvious": ("pytest", "python -m unittest")},
    {"name": "go", "markers": ("go.mod",), "tools": ("go",), "obvious": ("go test ./...",)},
    {"name": "rust", "markers": ("Cargo.toml",), "tools": ("cargo",), "obvious": ("cargo test",)},
)
RUNNERS = ("make", "just", "task")
VERBS = {"go": ("test", "vet", "build"), "cargo": ("test", "clippy", "build", "fmt", "check")}
PLAIN_FLAGS = {"-B", "--batch-mode", "-q", "--quiet", "-ntp", "--no-transfer-progress", "-v", "--verbose", "-V",
               "--no-daemon", "--stacktrace", "--info", "-e", "--errors", "--console=plain", "--locked"}
NODE_SETUP = {"install", "ci", "i", "add", "config", "cache", "set", "dlx", "exec", "publish", "login", "version"}
TARGETS = {"test", "tests", "it", "integration", "integration-test", "e2e", "lint", "check", "verify", "build",
           "format", "fmt", "typecheck", "types", "ci", "unit", "coverage"}
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
_RUN = re.compile(r"^(\s*)(?:-\s+)?run:\s*(.*)$")
_SCRIPT = re.compile(r"^(\s*)(?:before_script|script|after_script):\s*$")
_DELIVERY = re.compile(r"deploy|release|publish|deliver|livraison|(?:^|[-_.])cd(?:[-_.]|$)", re.IGNORECASE)
_TARGET = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)")


def _lines(repo: str, rel: str) -> list[str]:
    try:
        with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(value: str) -> str:
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"" else value


def _split(raw: str) -> list[str]:
    """Une ligne de shell en commandes simples, sans les variables posées devant ni `sudo`."""
    out = []
    for part in re.split(r"&&|\|\||;", raw):
        tokens = part.strip().split()
        while tokens and (_ASSIGN.match(tokens[0]) or tokens[0] in ("sudo", "time", "exec")):
            tokens = tokens[1:]
        if tokens and not tokens[0].startswith("#"):
            out.append(" ".join(tokens))
    return out


def _github(repo: str, rel: str) -> list[dict[str, Any]]:
    found, lines, index = [], _lines(repo, rel), 0
    while index < len(lines):
        match = _RUN.match(lines[index])
        index += 1
        if not match:
            continue
        value, base = match[2].strip(), _indent(lines[index - 1])
        if value and value[0] not in "|>":
            found += [{"command": c, "path": rel, "line": index} for c in _split(_unquote(value))]
            continue
        while index < len(lines) and (not lines[index].strip() or _indent(lines[index]) > base):
            found += [{"command": c, "path": rel, "line": index + 1} for c in _split(lines[index])]
            index += 1
    return found


def _gitlab(repo: str, rel: str) -> list[dict[str, Any]]:
    found, lines, index = [], _lines(repo, rel), 0
    while index < len(lines):
        match = _SCRIPT.match(lines[index])
        index += 1
        if not match:
            continue
        base = len(match[1])
        while index < len(lines) and lines[index].strip().startswith("- ") and _indent(lines[index]) >= base:
            item = _unquote(lines[index].strip()[2:].strip())
            found += [{"command": c, "path": rel, "line": index + 1} for c in _split(item)]
            index += 1
    return found


def ci_commands(repo: str) -> list[dict[str, Any]]:
    """Chaque commande que la CI lance, avec le fichier et la ligne où elle est écrite."""
    found: list[dict[str, Any]] = []
    workflows = os.path.join(repo, ".github", "workflows")
    if os.path.isdir(workflows):
        for name in sorted(os.listdir(workflows)):
            if name.endswith((".yml", ".yaml")):
                found += _github(repo, f".github/workflows/{name}")
    if os.path.isfile(os.path.join(repo, ".gitlab-ci.yml")):
        found += _gitlab(repo, ".gitlab-ci.yml")
    return found


def ecosystems(repo: str) -> list[dict[str, Any]]:
    return [eco for eco in ECOSYSTEMS if any(os.path.isfile(os.path.join(repo, m)) for m in eco["markers"])]


def classify(repo: str, command: str) -> tuple[str, str] | None:
    """(`enveloppe` | `options` | `evidente`, commande normalisée), ou None pour ce qui n'est pas une
    commande de vérification : installation, préparation, affichage."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return None
    tool, rest = tokens[0], tokens[1:]
    if tool in RUNNERS:
        return ("enveloppe", command) if rest else None
    if tool in ("bash", "sh") and rest:
        tool, rest = rest[0], rest[1:]
        if not os.path.isfile(os.path.join(repo, tool)):
            return None
        return "enveloppe", command
    if tool.startswith("./") and tool not in ("./mvnw", "./gradlew"):
        return ("enveloppe", command) if os.path.isfile(os.path.join(repo, tool)) else None
    if tool in ("python", "python3") and rest[:1] == ["-m"] and rest[1:2] and rest[1] in ("pytest", "unittest", "tox", "nox"):
        tool, rest = rest[1], rest[2:]
        if tool == "unittest":
            return "evidente", "python -m unittest"
    if tool in ("npm", "yarn", "pnpm"):
        if not rest or rest[0] in NODE_SETUP or rest[0].startswith("-"):
            return None
        return ("evidente", "npm test") if rest == ["test"] else ("enveloppe", command)
    known = {t for eco in ECOSYSTEMS for t in eco["tools"]}
    if tool not in known:
        return None
    words = [t for t in rest if not t.startswith("-")]
    if tool in VERBS and (not words or words[0] not in VERBS[tool]):
        return None
    if tool in ("mvn", "./mvnw") and not any(w in ("test", "verify", "package", "install", "integration-test") for w in words):
        return None
    flags = [t for t in rest if t.startswith("-") and t not in PLAIN_FLAGS]
    plain = " ".join([tool.replace("./mvnw", "mvn"), *words])
    return ("options", command) if flags else ("evidente", plain)


def _targets(repo: str) -> list[dict[str, Any]]:
    """Les cibles du Makefile et les scripts du manifeste dont le nom dit qu'ils vérifient quelque chose."""
    found = []
    for number, line in enumerate(_lines(repo, "Makefile"), 1):
        match = _TARGET.match(line)
        if match and match[1] in TARGETS:
            found.append({"command": f"make {match[1]}", "path": "Makefile", "line": number})
    try:
        with open(os.path.join(repo, "package.json"), encoding="utf-8") as fh:
            scripts = json.load(fh).get("scripts", {})
    except (OSError, ValueError, AttributeError):
        scripts = {}
    if isinstance(scripts, dict):
        found += [{"command": f"npm run {name}", "path": "package.json", "line": None}
                  for name in scripts if isinstance(name, str) and name != "test" and name.split(":")[0] in TARGETS]
    return found


def collect(repo: str) -> dict[str, Any]:
    ecos = ecosystems(repo)
    obvious = [command for eco in ecos for command in eco["obvious"]]
    corpus = "\n".join(facts.instruction_corpus(repo).values())
    candidates: dict[str, dict[str, Any]] = {}
    seen_obvious: dict[str, dict[str, Any]] = {}

    def source(item: dict[str, Any]) -> str:
        return f"{item['path']}:{item['line']}" if item["line"] else item["path"]

    for item in ci_commands(repo):
        kind = classify(repo, item["command"])
        if kind is None:
            continue
        if kind[0] == "evidente":
            seen_obvious.setdefault(kind[1], {"command": kind[1], "source": source(item)})
        else:
            label = "livraison" if _DELIVERY.search(os.path.basename(item["path"])) else kind[0]
            candidates.setdefault(kind[1], {"command": kind[1], "kind": label, "source": source(item), "ci": True})
    for item in _targets(repo):
        candidates.setdefault(item["command"], {"command": item["command"], "kind": "cible", "source": source(item),
                                                "ci": False})
    for candidate in candidates.values():
        candidate["obvious"] = obvious
        candidate["documented"] = candidate["command"] in corpus
    order = {"enveloppe": 0, "options": 1, "cible": 2, "livraison": 3}
    return {"ecosystems": [eco["name"] for eco in ecos],
            "candidates": sorted(candidates.values(), key=lambda c: (c["documented"], order[c["kind"]], c["command"])),
            "obvious_in_ci": sorted(seen_obvious.values(), key=lambda c: c["command"])}


WHY = {"enveloppe": "la CI lance cette commande, pas l'outil directement",
       "options": "la CI lance l'outil avec des options qui changent ce qui tourne",
       "cible": "le dépôt l'offre, la CI ne la lance pas : à confirmer",
       "livraison": "un workflow de livraison la lance : candidate pour un Interdit, un agent ne la lance pas de son poste"}


def render_md(result: dict[str, Any]) -> str:
    todo = [c for c in result["candidates"] if not c["documented"]]
    out = [f"Commandes qu'un agent ne devine pas : {len(todo)} à confirmer, "
           f"{len(result['candidates']) - len(todo)} déjà dans les instructions."]
    if result["ecosystems"]:
        out.append("Écosystème vu : " + ", ".join(result["ecosystems"]) + ".")
    for item in result["candidates"]:
        line = f"- `{item['command']}` — {WHY[item['kind']]} ({item['source']})."
        if item["obvious"] and item["kind"] in ("enveloppe", "options"):
            line += " Ce qu'un agent lancerait sans le savoir : " + ", ".join(f"`{o}`" for o in item["obvious"]) + "."
        out.append(line + (" Déjà écrite." if item["documented"] else ""))
    if result["obvious_in_ci"]:
        out.append("Commandes évidentes que la CI lance telles quelles (rien à écrire) : "
                   + ", ".join(f"`{c['command']}`" for c in result["obvious_in_ci"]) + ".")
    if not result["candidates"]:
        out.append("Aucune candidate : la CI et le dépôt ne montrent pas d'écart avec les commandes évidentes.")
    out.append("Une candidate n'est pas une règle : exécute-la (jamais une commande de livraison), puis demande au propriétaire si l'écart est voulu.")
    return "\n".join(out) + "\n"


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--format", choices=["md", "json"], default="md")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    if not os.path.isdir(args.repo):
        print(f"harness commands : {args.repo} n'est pas un dossier", file=sys.stderr)
        return 2
    result = collect(args.repo)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(result))
    return 0
