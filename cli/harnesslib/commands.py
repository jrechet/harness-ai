"""The commands an agent does not guess: what the CI really runs, where it departs from the command
the ecosystem suggests.

A Maven repository is "obviously" tested with `mvn verify`. If the CI runs `make it`, or `mvn verify`
with a profile, the agent will run the wrong command and believe it has verified. This module reads the
workflows, the Makefile and the manifest scripts, and returns **candidates**: each one is confirmed by
running it and with the owner before it enters AGENTS.md. It does not parse the whole YAML (standard
library only): GitHub Actions `run:` lines, GitLab `script:` lists.

Kinds of candidate: `wrapper` (the CI runs this command, not the tool directly), `options` (the tool
with options that change what runs), `target` (offered by the repository, not run by the CI) and
`delivery` (it delivers or publishes). An `obvious` command is the one the ecosystem suggests."""
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
# A job, target or file name that delivers: in English, or in French ("livraison") in a team's repository.
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
    """A shell line split into simple commands: without the variables set in front, without comments,
    without what follows a pipe. A `cd folder` stays in front of the commands that follow it."""
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
    """The lines of a script block, joined: continuation by `\\`, folded block, heredoc body skipped."""
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
    """For each line of a GitHub workflow: the job it belongs to, and whether it delivers (its name, or an
    `environment:`). Without a YAML parser: the jobs are the first-level keys under `jobs:`."""
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
    """The `working-directory:` of the step that carries the given `run:` line, if there is one."""
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
    """Each command the CI runs, with the file and the line where it is written."""
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
    """(`wrapper` | `options` | `obvious`, normalized command), or None for what is not a
    verification command: installation, preparation, display."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return None
    tool, rest = tokens[0], tokens[1:]
    if tool == "cd" and "&&" in rest:  # `cd folder && command`: the command is classified, the whole is kept
        inner = classify(repo, " ".join(rest[rest.index("&&") + 1:]))
        return (("wrapper" if inner[0] == "obvious" else inner[0]), command) if inner else None
    if tool in ENV_RUNNERS and rest[:1] == ["run"] and len(rest) > 1:
        return "wrapper", command
    if tool in ("npx", "docker-compose") or (tool == "docker" and rest[:1] == ["compose"]) or \
            (tool in ("pnpm", "yarn") and rest[:1] == ["exec"]):
        return None if any(w in ("install", "up", "down", "pull", "build", "login") for w in rest) else ("wrapper", command)
    if tool in RUNNERS:
        return ("wrapper", command) if rest else None
    if tool in ("bash", "sh") and rest:
        tool, rest = rest[0], rest[1:]
        if not os.path.isfile(os.path.join(repo, tool)):
            return None
        return "wrapper", command
    if tool.startswith("./") and tool not in ("./mvnw", "./gradlew"):
        return ("wrapper", command) if os.path.isfile(os.path.join(repo, tool)) else None
    if tool in ("python", "python3") and rest[:1] == ["-m"] and rest[1:2] and rest[1] in ("pytest", "unittest", "tox", "nox"):
        tool, rest = rest[1], rest[2:]
        if tool == "unittest":
            return "obvious", "python -m unittest"
    if tool in ("npm", "yarn", "pnpm"):
        if not rest or rest[0] in NODE_SETUP or rest[0].startswith("-"):
            return None
        return ("obvious", "npm test") if rest == ["test"] else ("wrapper", command)
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
    return ("options", command) if flags else ("obvious", plain)


def _targets(repo: str) -> list[dict[str, Any]]:
    """The targets of the Makefile or justfile and the manifest scripts whose name says they verify
    or deliver something."""
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
    """The command is written as is in code of the instructions (between backticks or in a block),
    not as the start of another one nor as words of a sentence."""
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
        if kind[0] == "obvious":
            seen_obvious.setdefault(kind[1], {"command": kind[1], "source": source(item)})
            continue
        label = "delivery" if item["delivery"] or _DELIVERY_CMD.search(kind[1]) else kind[0]
        previous = candidates.get(kind[1])
        # a command that an ordinary job also runs is not a delivery: its job was
        if previous is None or (previous["kind"] == "delivery" and label != "delivery"):
            candidates[kind[1]] = {"command": kind[1], "kind": label, "source": source(item), "ci": True}
    for item in _targets(repo):
        label = "delivery" if item["delivery"] else "target"
        candidates.setdefault(item["command"], {"command": item["command"], "kind": label, "source": source(item),
                                                "ci": False})
    for candidate in candidates.values():
        candidate["obvious"] = obvious
        candidate["documented"] = _documented(candidate["command"], corpus)
    order = {"wrapper": 0, "options": 1, "target": 2, "delivery": 3}
    return {"ecosystems": [eco["name"] for eco in ecos],
            "candidates": sorted(candidates.values(), key=lambda c: (c["documented"], order[c["kind"]], c["command"])),
            "obvious_in_ci": sorted(seen_obvious.values(), key=lambda c: c["command"])}


WHY = {"wrapper": "the CI runs this command, not the tool directly",
       "options": "the CI runs the tool with options that change what runs",
       "target": "the repository offers it, the CI does not run it: to confirm",
       "delivery": "it delivers or publishes: candidate for a Forbidden rule, an agent does not run it from its machine"}


def render_md(result: dict[str, Any]) -> str:
    todo = [c for c in result["candidates"] if not c["documented"]]
    out = [f"Commands an agent does not guess: {len(todo)} to confirm, "
           f"{len(result['candidates']) - len(todo)} already in the instructions."]
    if result["ecosystems"]:
        out.append("Ecosystem seen: " + ", ".join(result["ecosystems"]) + ".")
    for item in result["candidates"]:
        line = f"- `{item['command']}` — {WHY[item['kind']]} ({item['source']})."
        if item["obvious"] and item["kind"] != "delivery":
            line += " What an agent would run without knowing: " + ", ".join(f"`{o}`" for o in item["obvious"]) + "."
        out.append(line + (" Already written." if item["documented"] else ""))
    if result["obvious_in_ci"]:
        out.append("Obvious commands the CI runs as is (nothing to write): "
                   + ", ".join(f"`{c['command']}`" for c in result["obvious_in_ci"]) + ".")
    if not result["candidates"]:
        out.append("No candidate: the CI and the repository show no departure from the obvious commands.")
    out.append("A candidate is not a rule. Read what it runs before running it, never run a delivery command nor a command that writes outside the repository, then ask the owner whether the departure is intended.")
    return "\n".join(out) + "\n"


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--format", choices=["md", "json"], default="md")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    if not os.path.isdir(args.repo):
        print(f"harness commands: {args.repo} is not a directory", file=sys.stderr)
        return 2
    result = collect(args.repo)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(result))
    return 0
