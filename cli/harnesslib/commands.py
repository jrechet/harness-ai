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
ENV_RUNNERS = ("uv", "poetry", "pipenv", "pdm", "hatch", "rye")
VERBS = {"go": ("test", "vet", "build"), "cargo": ("test", "clippy", "build", "fmt", "check")}
PLAIN_FLAGS = {"-B", "--batch-mode", "-q", "--quiet", "-ntp", "--no-transfer-progress", "-v", "--verbose", "-V",
               "--no-daemon", "--stacktrace", "--info", "-e", "--errors", "--console=plain", "--locked"}
NODE_SETUP = {"install", "ci", "i", "add", "config", "cache", "set", "dlx", "publish", "login", "version"}
TARGETS = {"test", "tests", "it", "integration", "integration-test", "e2e", "lint", "check", "verify", "build",
           "format", "fmt", "typecheck", "types", "ci", "unit", "coverage"}
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
_RUN = re.compile(r"^(\s*)(?:-\s+)?[\"']?run[\"']?:\s*(.*)$")
_SCRIPT = re.compile(r"^(\s*)(?:before_script|script|after_script):\s*$")
_DELIVERY = re.compile(r"deploy|release|publish|deliver|livraison|rollout|promote|(?:^|[-_.])cd(?:[-_.]|$)", re.IGNORECASE)
_DELIVERY_CMD = re.compile(r"deploy|release|publish|rollout|kubectl\s+(?:apply|delete|rollout)|terraform\s+(?:apply|destroy)"
                           r"|docker\s+push|helm\s+(?:upgrade|install)|twine\s+upload|gh\s+release|git\s+push|\bscp\b",
                           re.IGNORECASE)
_TARGET = re.compile(r"^([A-Za-z0-9][^:=#\t]*?)\s*:(?![:=])")
_EXPR = re.compile(r"\$\{\{.*?\}\}")
_HEREDOC = re.compile(r"<<[-~]?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)")
_JOB = re.compile(r"^(\s+)([A-Za-z0-9_-]+):\s*$")
_PREFIXES = ("sudo", "time", "exec", "then", "do", "else", "!", "{", "(")


def _lines(repo: str, rel: str) -> list[str]:
    try:
        with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read(2_000_000).splitlines()
    except OSError:
        return []


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(value: str) -> str:
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"" else value


def _split(raw: str) -> list[str]:
    """Une ligne de shell en commandes simples : sans les variables posées devant, sans commentaire,
    sans ce qui suit un tube. Un `cd dossier` reste devant les commandes qui le suivent."""
    saved: list[str] = []

    def keep(match: re.Match[str]) -> str:
        saved.append(match[0])
        return f"\0{len(saved) - 1}\0"

    out, where = [], ""
    for part in re.split(r"&&|\|\||;", _EXPR.sub(keep, raw)):
        part = re.sub(r"\s#.*$", "", part.split("|")[0]).strip()
        tokens = part.split()
        while tokens and (_ASSIGN.match(tokens[0]) or tokens[0] in _PREFIXES or tokens[0].startswith("(")):
            tokens = [tokens[0].lstrip("(")] + tokens[1:] if tokens[0].lstrip("(") and tokens[0][0] == "(" else tokens[1:]
        if tokens and tokens[-1].endswith(")") and "$(" not in part:
            tokens[-1] = tokens[-1].rstrip(")")
        tokens = [t for t in tokens if t]
        if not tokens or tokens[0].startswith("#"):
            continue
        command = re.sub(r"\0(\d+)\0", lambda m: saved[int(m[1])], " ".join(tokens))
        if tokens[0] == "cd" and len(tokens) == 2:
            where = f"cd {tokens[1]} && "
            continue
        out.append(where + command)
    return out


def _logical(block: list[tuple[int, str]], folded: bool) -> list[tuple[int, str]]:
    """Les lignes d'un bloc de script, rejointes : continuation par `\\`, bloc replié, corps de heredoc sauté."""
    if folded:
        text = " ".join(line.strip() for _, line in block if line.strip())
        return [(block[0][0], text)] if block and text else []
    out, pending, start, heredoc = [], "", 0, None
    for number, line in block:
        if heredoc:
            heredoc = None if line.strip() == heredoc else heredoc
            continue
        if not pending:
            start = number
        if line.rstrip().endswith("\\"):
            pending += line.rstrip()[:-1] + " "
            continue
        full, pending = pending + line, ""
        match = _HEREDOC.search(full)
        heredoc = match[1] if match else None
        out.append((start, full))
    return out + ([(start, pending)] if pending else [])


def _jobs(lines: list[str]) -> list[dict[str, Any]]:
    """Par ligne d'un workflow GitHub : le job auquel elle appartient, et s'il livre (son nom, ou un
    `environment:`). Sans parseur YAML : les jobs sont les clés du premier niveau sous `jobs:`."""
    info: list[dict[str, Any]] = [{"job": "", "delivery": False} for _ in lines]
    level, current, start = None, "", 0
    inside = False
    for index, line in enumerate(lines):
        if re.match(r"^jobs:\s*$", line):
            inside, level = True, None
            continue
        if inside and line.strip() and not line.startswith((" ", "\t", "#")):
            inside = False
        match = _JOB.match(line) if inside else None
        if match and (level is None or len(match[1]) == level):
            level, current, start = len(match[1]), match[2], index
        if not inside:
            current = ""
        info[index]["job"] = current
        if current and (_DELIVERY.search(current) or re.match(r"^\s+environment:", line)):
            for back in range(start, len(lines)):
                if back > index and info[back]["job"] not in ("", current):
                    break
                info[back]["delivery"] = True
                info[back]["job"] = info[back]["job"] or current
    return info


def _workdir(lines: list[str], index: int) -> str:
    """Le `working-directory:` de l'étape qui porte la ligne `run:` donnée, s'il y en a un."""
    limit = _indent(lines[index]) if lines[index].lstrip().startswith("- ") else _indent(lines[index]) - 2
    start = index
    while start > 0 and not (lines[start].lstrip().startswith("- ") and _indent(lines[start]) <= limit):
        start -= 1
    end = index + 1
    while end < len(lines) and not (lines[end].strip() and _indent(lines[end]) <= limit):
        end += 1
    for line in lines[start:end]:
        match = re.match(r"^\s*(?:-\s+)?working-directory:\s*(\S+)", line)
        if match:
            return _unquote(match[1])
    return ""


def _github(repo: str, rel: str) -> list[dict[str, Any]]:
    found, lines, index = [], _lines(repo, rel), 0
    jobs = _jobs(lines)
    by_name = bool(_DELIVERY.search(os.path.basename(rel)))
    while index < len(lines):
        match = _RUN.match(lines[index])
        index += 1
        if not match:
            continue
        key, value, base = index - 1, match[2].strip(), _indent(lines[index - 1])
        if value and value[0] not in "|>":
            block, folded = [(index, _unquote(value))], False
        else:
            block, folded = [], value.startswith(">")
            while index < len(lines) and (not lines[index].strip() or _indent(lines[index]) > base):
                block.append((index + 1, lines[index]))
                index += 1
        where = _workdir(lines, key)
        for number, text in _logical(block, folded):
            for command in _split(text):
                if where and not command.startswith("cd "):
                    command = f"cd {where} && {command}"
                found.append({"command": command, "path": rel, "line": number,
                              "delivery": by_name or jobs[key]["delivery"]})
    return found


def _gitlab(repo: str, rel: str) -> list[dict[str, Any]]:
    found, lines, index = [], _lines(repo, rel), 0
    job = ""
    while index < len(lines):
        top = re.match(r"^([A-Za-z0-9_.-]+):\s*$", lines[index])
        job = top[1] if top else job
        match = _SCRIPT.match(lines[index])
        index += 1
        if not match:
            continue
        base = len(match[1])
        while index < len(lines) and lines[index].strip().startswith("-") and _indent(lines[index]) >= base:
            item, item_indent = lines[index].strip()[1:].strip(), _indent(lines[index])
            index += 1
            if item[:1] in ("|", ">"):
                block = []
                while index < len(lines) and (not lines[index].strip() or _indent(lines[index]) > item_indent):
                    block.append((index + 1, lines[index]))
                    index += 1
            else:
                block = [(index, _unquote(item))]
            for number, text in _logical(block, item.startswith(">")):
                found += [{"command": c, "path": rel, "line": number, "delivery": bool(_DELIVERY.search(job))}
                          for c in _split(text)]
    return found


def ci_commands(repo: str) -> list[dict[str, Any]]:
    """Chaque commande que la CI lance, avec le fichier et la ligne où elle est écrite."""
    found: list[dict[str, Any]] = []
    for folder, deep in ((".github/workflows", False), (".github/actions", True)):
        try:
            for root, dirs, names in os.walk(os.path.join(repo, folder)):
                dirs[:] = sorted(dirs) if deep else []
                for name in sorted(names):
                    if name.endswith((".yml", ".yaml")):
                        rel = os.path.relpath(os.path.join(root, name), repo).replace(os.sep, "/")
                        found += _github(repo, rel)
        except OSError:
            continue
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
    if tool == "cd" and "&&" in rest:  # `cd dossier && commande` : on classe la commande, on garde le tout
        inner = classify(repo, " ".join(rest[rest.index("&&") + 1:]))
        return (("enveloppe" if inner[0] == "evidente" else inner[0]), command) if inner else None
    if tool in ENV_RUNNERS and rest[:1] == ["run"] and len(rest) > 1:
        return "enveloppe", command
    if tool in ("npx", "docker-compose") or (tool == "docker" and rest[:1] == ["compose"]) or \
            (tool in ("pnpm", "yarn") and rest[:1] == ["exec"]):
        return None if any(w in ("install", "up", "down", "pull", "build", "login") for w in rest) else ("enveloppe", command)
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
    """Les cibles du Makefile ou du justfile et les scripts du manifeste dont le nom dit qu'ils vérifient
    ou qu'ils livrent quelque chose."""
    found = []
    for rel, runner in (("Makefile", "make"), ("justfile", "just"), ("Justfile", "just")):
        for number, line in enumerate(_lines(repo, rel), 1):
            match = _TARGET.match(line)
            for name in (match[1].split() if match else []):
                if name in TARGETS or (_DELIVERY.search(name) and re.fullmatch(r"[A-Za-z0-9_.-]+", name)):
                    found.append({"command": f"{runner} {name}", "path": rel, "line": number,
                                  "delivery": bool(_DELIVERY.search(name))})
    manifest = _lines(repo, "package.json")
    try:
        scripts = json.loads("\n".join(manifest)).get("scripts", {})
    except (ValueError, AttributeError):
        scripts = {}
    for name in scripts if isinstance(scripts, dict) else []:
        if not isinstance(name, str) or name == "test":
            continue
        if name.split(":")[0] in TARGETS or _DELIVERY.search(name):
            line = next((n for n, text in enumerate(manifest, 1) if re.search(rf'"{re.escape(name)}"\s*:', text)), None)
            found.append({"command": f"npm run {name}", "path": "package.json", "line": line,
                          "delivery": bool(_DELIVERY.search(name))})
    return found


def _documented(command: str, corpus: str) -> bool:
    """La commande est écrite telle quelle dans du code des instructions (entre accents graves ou dans
    un bloc), pas comme le début d'une autre ni comme des mots d'une phrase."""
    code = "\n".join(re.findall(r"```.*?```|`[^`\n]+`", corpus, re.DOTALL))
    return bool(re.search(r"(?<![\w./-])" + re.escape(command) + r"(?![\w:./-])", code))


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
            continue
        label = "livraison" if item["delivery"] or _DELIVERY_CMD.search(kind[1]) else kind[0]
        previous = candidates.get(kind[1])
        # une commande qu'un job ordinaire lance aussi n'est pas une livraison : c'est son job qui l'était
        if previous is None or (previous["kind"] == "livraison" and label != "livraison"):
            candidates[kind[1]] = {"command": kind[1], "kind": label, "source": source(item), "ci": True}
    for item in _targets(repo):
        label = "livraison" if item["delivery"] else "cible"
        candidates.setdefault(item["command"], {"command": item["command"], "kind": label, "source": source(item),
                                                "ci": False})
    for candidate in candidates.values():
        candidate["obvious"] = obvious
        candidate["documented"] = _documented(candidate["command"], corpus)
    order = {"enveloppe": 0, "options": 1, "cible": 2, "livraison": 3}
    return {"ecosystems": [eco["name"] for eco in ecos],
            "candidates": sorted(candidates.values(), key=lambda c: (c["documented"], order[c["kind"]], c["command"])),
            "obvious_in_ci": sorted(seen_obvious.values(), key=lambda c: c["command"])}


WHY = {"enveloppe": "la CI lance cette commande, pas l'outil directement",
       "options": "la CI lance l'outil avec des options qui changent ce qui tourne",
       "cible": "le dépôt l'offre, la CI ne la lance pas : à confirmer",
       "livraison": "elle livre ou publie : candidate pour un Interdit, un agent ne la lance pas de son poste"}


def render_md(result: dict[str, Any]) -> str:
    todo = [c for c in result["candidates"] if not c["documented"]]
    out = [f"Commandes qu'un agent ne devine pas : {len(todo)} à confirmer, "
           f"{len(result['candidates']) - len(todo)} déjà dans les instructions."]
    if result["ecosystems"]:
        out.append("Écosystème vu : " + ", ".join(result["ecosystems"]) + ".")
    for item in result["candidates"]:
        line = f"- `{item['command']}` — {WHY[item['kind']]} ({item['source']})."
        if item["obvious"] and item["kind"] != "livraison":
            line += " Ce qu'un agent lancerait sans le savoir : " + ", ".join(f"`{o}`" for o in item["obvious"]) + "."
        out.append(line + (" Déjà écrite." if item["documented"] else ""))
    if result["obvious_in_ci"]:
        out.append("Commandes évidentes que la CI lance telles quelles (rien à écrire) : "
                   + ", ".join(f"`{c['command']}`" for c in result["obvious_in_ci"]) + ".")
    if not result["candidates"]:
        out.append("Aucune candidate : la CI et le dépôt ne montrent pas d'écart avec les commandes évidentes.")
    out.append("Une candidate n'est pas une règle. Lis ce qu'elle lance avant de l'exécuter, n'exécute jamais une commande de livraison ni une commande qui écrit hors du dépôt, puis demande au propriétaire si l'écart est voulu.")
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
