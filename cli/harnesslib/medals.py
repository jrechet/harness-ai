"""Medals and achievements: the maturity level, told as a progression one wants to follow.

Nothing is graded here by a model. For a repository, the medal is the level that `harness status`
measures (bronze = level 1 … platinum = level 4) and each passed check is an unlocked achievement.
For a plugin marketplace, four ranks of checks read in its files. The result is kept in
`.harness/medals.json`, which can be committed: it keeps the date each achievement was unlocked, and
says when one of them was lost. `--page` turns it into a standalone HTML page.

Until 2026-11-16 the ids were French (`aucune`, `argent`, `or`, `platine`, `B.frais`…). A previous
file with those ids is still read: its dates are kept under the English ids."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from datetime import date
from typing import Any

from . import commands, facts, fresh, maturity, progress

SCHEMA = 1
FILE = "medals.json"
MEDALS = ({"id": "none", "name": "No medal"}, {"id": "bronze", "name": "Bronze"},
          {"id": "silver", "name": "Silver"}, {"id": "gold", "name": "Gold"}, {"id": "platinum", "name": "Platinum"})
# French ids written before 2026-11-16 (medals, tiers and achievements), read from a previous file.
LEGACY_IDS = {"aucune": "none", "argent": "silver", "or": "gold", "platine": "platinum",
              "B.frais": "B.fresh", "B.pourquoi": "B.why", "B.outils": "B.tools", "B.cibles": "B.targets",
              "B.commandes": "B.commands", "B.objectif": "B.target", "M1.manifeste": "M1.manifest",
              "M1.identite": "M1.identity", "M2.quand": "M2.when", "M2.quand-pas": "M2.when-not",
              "M4.aveugle": "M4.blind"}
KINDS = ("repo", "marketplace")
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medals_template.html")
MAX_SKILL_LINES = 500
NOT_MEASURED = "not measured: no instruction file"
# A skill description is written by its author, in French or in English: both are read.
_TRIGGER = re.compile(r"(?<!ne pas )(?<!pas )\butiliser (?:dès|quand|pour|si|lorsque)|\bà utiliser\b|"
                      r"(?<!not )(?<!n't )\buse (?:(?:this|it|the skill) )?(?:when|for|whenever)\b", re.IGNORECASE)
_NEGATIVE = re.compile(r"ne pas utiliser|do not use|don't use|not for\b|n'est pas pour", re.IGNORECASE)


def _success(ident: str, tier: str, title: str, passed: bool, evidence: str, action: str | None,
             waiting: bool = False) -> dict[str, Any]:
    return {"id": ident, "tier": tier, "title": title, "passed": bool(passed), "evidence": evidence,
            "next": None if passed else action, "waiting": bool(waiting and not passed)}


def _short(value: Any) -> str:
    """The measured value of a check, in one readable line."""
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_short(v)}" for k, v in value.items() if not isinstance(v, (dict, list)))[:160]
    if isinstance(value, (list, tuple)):
        return ", ".join(_short(v) for v in value)[:160] or "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return "" if value is None else str(value)[:160]


# --- A repository: the levels of harness status ----------------------------------------------------------

def evaluate_repo(repo: str, today: date | None = None) -> dict[str, Any]:
    state = maturity.evaluate(facts.collect(repo, today=today))
    tiers, successes = [], []
    for level in state["levels"][1:]:
        medal = MEDALS[level["level"]]
        tiers.append({"id": medal["id"], "name": medal["name"], "title": level["name"], "promise": level["summary"]})
        successes += [_success(c["id"], medal["id"], c["label"], c["passed"],
                               maturity.WITH_FILE if c.get("follows") else _short(c.get("value")),
                               c.get("next_action"), c.get("waits", False)) for c in level["checks"]]
    source = state["facts"]["instructions"]["source"]
    total = source.get("rules_total") or 0
    found = commands.collect(repo)
    unwritten = [c["command"] for c in found["candidates"] if c["ci"] and c["kind"] != "delivery" and not c["documented"]]
    target = state["target"]
    try:
        aged = fresh.collect(repo, today, fast=True)
    except Exception:  # freshness is a bonus: its failure does not deprive of a medal
        aged = {"git": False, "items": []}
    broken = [i for i in aged["items"] if i["state"] == "broken"]
    bonus = [
        ("B.fresh", "No skill or agent cites what has vanished", bool(source.get("path")) and aged["git"] and not broken,
         ", ".join(f"{i['path']}: {i['evidence']}" for i in broken[:2]) or ("nothing broken" if aged["git"] else "unmeasured: no git history"),
         "Run `harness fresh` and repair each broken reference."),
        ("B.dates", "Each rule carries its date", total > 0 and source.get("rules_dated") == total,
         f"{source.get('rules_dated', 0)} of {total}", "Date each rule [YYYY-MM]: the age of a rule is the input of the relevance review."),
        ("B.why", "Each rule says why", total > 0 and source.get("rules_justified") == total,
         f"{source.get('rules_justified', 0)} of {total}", "Add \"Why: …\" to the rules that do not say it, or \"no known incident\"."),
        ("B.tools", "Each rule is enforced by a tool", total > 0 and source.get("rules_guarded") == total,
         f"{source.get('rules_guarded', 0)} of {total}", "Push the narrated rules to a lint, an architecture test or a PR check."),
        ("B.targets", "No reference without a target", bool(source.get("path")) and not state["dangling"],
         f"{len(state['dangling'])} reference(s) without a target", "Remove or repair what `harness status` lists under \"References without a target\"."),
        ("B.commands", "The commands the CI runs are written", bool(source.get("path")) and not unwritten,
         ", ".join(unwritten[:3]) or "no departure from the obvious commands",
         "Run `harness commands`, confirm each candidate and write it in the AGENTS.md table."),
        ("B.target", "The target level is reached", bool(target.get("reached")),
         f"target: {target.get('name') or 'none'}", "Say where you stop with `harness target <level>`, then reach it."),
    ]
    if not source.get("path"):      # nothing to read: not measured, rather than measured and failed
        create = next(c["next_action"] for c in state["levels"][1]["checks"] if c["id"] == maturity.FOLLOWS_SOURCE)
        bonus = [row if row[0] == "B.target" else (row[0], row[1], False, NOT_MEASURED, create) for row in bonus]
    successes += [_success(i, "bonus", t, p, e, a) for i, t, p, e, a in bonus]
    return {"kind": "repo", "name": os.path.basename(os.path.abspath(repo)), "date": state["date"],
            "rank": state["level"]["reached"], "tiers": tiers, "successes": successes}


# --- A plugin marketplace -----------------------------------------------------------------------------

def _json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _front_matter(path: str) -> tuple[dict[str, str], int]:
    """The first-level keys of a SKILL.md header, multi-line values included (`description: >`), and
    the number of lines of the file. Without a YAML parser: standard library."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return {}, 0
    header: dict[str, str] = {}
    key = None
    if lines[:1] == ["---"]:
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line[:1] in (" ", "\t"):
                if key:
                    header[key] = (header[key] + " " + line.strip()).strip()
                continue
            name, sep, value = line.partition(":")
            key = name.strip() if sep and name.strip() else None
            if key:
                header[key] = "" if value.strip() in (">", "|", ">-", "|-", ">+", "|+") else value.strip().strip("'\"")
    return header, len(lines)


def _inside(repo: str, path: str) -> bool:
    """The path, links followed, stays inside the repository."""
    root = os.path.realpath(repo)
    return os.path.commonpath([root, os.path.realpath(path)]) == root


CODE_DIRS = ("cli", "scripts", "src", "bin", "lib", "hooks")
CODE_EXT = (".py", ".js", ".mjs", ".ts", ".sh")
_TEST_NAME = re.compile(r"^test_.*\.py$|\.(?:test|spec)\.(?:js|mjs|ts)$")
_TEST_BODY = re.compile(r"def test_|unittest|\b(?:it|test|describe)\(")


def _code_and_tests(root: str) -> tuple[bool, bool]:
    """Does the plugin carry code, and does this code have at least one test that asserts something?"""
    code = tests = False
    for folder in CODE_DIRS:
        for base, dirs, names in os.walk(os.path.join(root, folder)):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "__pycache__", ".git")]
            for name in names:
                if _TEST_NAME.search(name):
                    try:
                        with open(os.path.join(base, name), encoding="utf-8", errors="replace") as fh:
                            tests = tests or bool(_TEST_BODY.search(fh.read(200_000)))
                    except OSError:
                        pass
                elif name.endswith(CODE_EXT) and name != "__init__.py":
                    code = True
    return code, tests


def _plugins(repo: str) -> tuple[Any, list[dict[str, Any]]]:
    manifest = _json(os.path.join(repo, ".claude-plugin", "marketplace.json"))
    plugins = []
    entries = manifest.get("plugins") if isinstance(manifest, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        source = entry.get("source") if isinstance(entry, dict) else None
        if (not isinstance(source, str) or source.startswith("/") or "://" in source or ".." in source.split("/")
                or not _inside(repo, os.path.join(repo, source))):
            plugins.append({"name": str((entry or {}).get("name") if isinstance(entry, dict) else entry), "root": None})
            continue
        root = os.path.normpath(os.path.join(repo, source))
        info = _json(os.path.join(root, ".claude-plugin", "plugin.json"))
        skills_dir = os.path.join(root, "skills")
        skills = sorted(os.path.join(skills_dir, d, "SKILL.md") for d in (os.listdir(skills_dir) if os.path.isdir(skills_dir) else [])
                        if os.path.isfile(os.path.join(skills_dir, d, "SKILL.md")) and _inside(repo, os.path.join(skills_dir, d, "SKILL.md")))
        has_code, has_tests = _code_and_tests(root)
        plugins.append({"name": entry.get("name") or source, "root": root, "info": info if isinstance(info, dict) else None,
                        "skills": [{"path": os.path.relpath(p, repo).replace(os.sep, "/"), "front": _front_matter(p)} for p in skills],
                        "has_code": has_code, "has_tests": has_tests})
    return manifest, plugins


def evaluate_marketplace(repo: str, today: date | None = None) -> dict[str, Any]:
    manifest, plugins = _plugins(repo)
    skills = [s for p in plugins if p["root"] for s in p["skills"]]

    def lacking(test: Any, items: list[dict[str, Any]], key: str) -> list[str]:
        return [str(i[key]) for i in items if not test(i)]

    def row(ident: str, tier: str, title: str, missing: list[str], total: int, action: str,
            vacuous: bool = False) -> dict[str, Any]:
        evidence = f"{total - len(missing)} of {total}" + (f"; missing: {', '.join(missing[:3])}" if missing else "")
        if vacuous and not total:
            evidence = "no plugin carries code: nothing to test"
        return _success(ident, tier, title, (total > 0 or vacuous) and not missing, evidence, action)

    valid = isinstance(manifest, dict) and isinstance(manifest.get("name"), str) and bool(plugins)
    blind = [os.path.join(r, d) for r, ds, _ in os.walk(os.path.join(repo, "fixtures")) for d in ds
             if os.path.basename(r) == "runs" and "blind" in d
             and any(names for _, _, names in os.walk(os.path.join(r, d)))]
    plan = progress.default_doc(repo)
    try:
        with open(os.path.join(repo, plan), encoding="utf-8") as fh:
            plan_errors = progress.parse(fh.read())[1]
    except OSError:
        plan_errors = [f"{plan} missing"]
    successes = [
        _success("M1.manifest", "bronze", "The marketplace manifest reads and lists plugins", valid,
                 f"{len(plugins)} plugin(s)", "Write `.claude-plugin/marketplace.json` with a name and at least one plugin."),
        row("M1.sources", "bronze", "Each plugin has its source in the repository, with its `plugin.json`",
            lacking(lambda p: p["root"] and p.get("info"), plugins, "name"), len(plugins),
            "Give each plugin a relative source and a `.claude-plugin/plugin.json`."),
        row("M1.identity", "bronze", "Each plugin has a name, a version and a description",
            lacking(lambda p: p.get("info") and all(isinstance(p["info"].get(k), str) and p["info"][k] for k in ("name", "version", "description")),
                    plugins, "name"), len(plugins), "Fill in `name`, `version` and `description` in each `plugin.json`."),
        row("M2.skills", "silver", "Each skill has a name and a description",
            lacking(lambda s: s["front"][0].get("name") and s["front"][0].get("description"), skills, "path"), len(skills),
            "Give each SKILL.md a `name` and `description` header."),
        row("M2.when", "silver", "Each description says when to use the skill",
            lacking(lambda s: _TRIGGER.search(s["front"][0].get("description", "")), skills, "path"), len(skills),
            "Write in the description the requests that must trigger the skill (\"Use when…\")."),
        row("M2.when-not", "silver", "Each description says when not to use it",
            lacking(lambda s: _NEGATIVE.search(s["front"][0].get("description", "")), skills, "path"), len(skills),
            "Add \"Do not use for…\": it is what separates two neighbouring skills."),
        row("M3.budget", "gold", f"No SKILL.md exceeds {MAX_SKILL_LINES} lines",
            lacking(lambda s: 0 < s["front"][1] <= MAX_SKILL_LINES, skills, "path"), len(skills),
            "Move the reference material to files loaded on demand."),
        row("M3.tests", "gold", "Each plugin that carries code has its tests",
            lacking(lambda p: p["has_tests"], [p for p in plugins if p.get("has_code")], "name"),
            len([p for p in plugins if p.get("has_code")]), "Test the plugin's CLI: what is guaranteed lives in tested code.",
            vacuous=valid),
        _success("M4.blind", "platinum", "At least one blind run is stored in the repository", bool(blind),
                 f"{len(blind)} run(s) under fixtures/", "Play a skill on a fixture with a fresh agent, and store its result in `runs/`."),
        _success("M4.plan", "platinum", "The progress plan exists and is well formed", not plan_errors,
                 "; ".join(plan_errors[:2]) or plan, f"Keep {plan} with `harness progress check`."),
    ]
    order = [m["id"] for m in MEDALS[1:]]
    rank = 0
    for index, tier in enumerate(order, 1):
        if not all(s["passed"] for s in successes if s["tier"] == tier):
            break
        rank = index
    tiers = [{"id": "bronze", "name": "Bronze", "title": "Installable", "promise": "The marketplace reads, each plugin installs."},
             {"id": "silver", "name": "Silver", "title": "Described", "promise": "Each skill says when it serves, and when it does not."},
             {"id": "gold", "name": "Gold", "title": "Maintained", "promise": "What is guaranteed is in tested code, the skills stay short."},
             {"id": "platinum", "name": "Platinum", "title": "Measured", "promise": "The skills are tested blind, the progress is kept."}]
    name = manifest.get("name") if isinstance(manifest, dict) and isinstance(manifest.get("name"), str) else os.path.basename(os.path.abspath(repo))
    return {"kind": "marketplace", "name": name, "date": (today or date.today()).isoformat(), "rank": rank,
            "tiers": tiers, "successes": successes}


# --- The repository file: what is kept from one run to the next ------------------------------------------

def build(evaluated: dict[str, Any], previous: Any = None) -> dict[str, Any]:
    """The content of medals.json: today's evaluation, plus the date each achievement was unlocked
    (kept from the previous time) and the date it was lost. French ids of a previous file are read
    under their English names (`LEGACY_IDS`)."""
    today = evaluated["date"]
    same = isinstance(previous, dict) and previous.get("schema") == SCHEMA and previous.get("kind") == evaluated["kind"]
    raw = previous.get("successes") if same else None
    before = {LEGACY_IDS.get(s["id"], s["id"]): s for s in raw
              if isinstance(s, dict) and isinstance(s.get("id"), str)} if isinstance(raw, list) else {}

    def day(value: Any) -> str | None:
        """A date taken from the previous file: a real date, not in the future."""
        try:
            return value if isinstance(value, str) and date.fromisoformat(value).isoformat() == value and value <= today else None
        except ValueError:
            return None

    successes = []
    for item in evaluated["successes"]:
        old = before.get(item["id"], {})
        unlocked = (day(old.get("unlocked")) or today) if item["passed"] else None
        lost = None if item["passed"] else (day(old.get("lost")) or (today if day(old.get("unlocked")) else None))
        successes.append({"id": item["id"], "tier": item["tier"], "title": item["title"], "unlocked": unlocked, "lost": lost,
                          "evidence": item["evidence"], "next": item["next"], "waiting": item["waiting"]})
    rank = evaluated["rank"]
    medal = {**MEDALS[rank], "rank": rank, "of": len(MEDALS) - 1}
    tiers = []
    for index, tier in enumerate(evaluated["tiers"], 1):
        mine = [s for s in successes if s["tier"] == tier["id"]]
        tiers.append({**tier, "done": sum(bool(s["unlocked"]) for s in mine), "total": len(mine), "earned": index <= rank})
    upcoming = evaluated["tiers"][rank]["id"] if rank < len(evaluated["tiers"]) else None
    missing = [s for s in successes if s["tier"] == upcoming and not s["unlocked"]]
    # An achievement that comes with another one (no action of its own) is missing, but is not a step.
    steps = [{"id": s["id"], "title": s["title"], "action": s["next"], "waiting": s["waiting"]} for s in missing if s["next"]]
    if rank and tiers:
        why = f"{medal['name']}: the {tiers[rank - 1]['total']} achievements of the \"{tiers[rank - 1]['title']}\" rank are unlocked"
        why += f", and {len(missing)} missing for {MEDALS[rank + 1]['name'].lower()}." if upcoming else ". It is the last rank."
    else:
        why = f"No medal yet: {len(missing)} achievement(s) missing for bronze."
    past = previous.get("history") if same else None
    history = [{"date": h["date"], "medal": LEGACY_IDS.get(h["medal"], h["medal"])} for h in (past if isinstance(past, list) else [])
               if isinstance(h, dict) and day(h.get("date")) and isinstance(h.get("medal"), str)]
    if not history or history[-1].get("medal") != medal["id"]:
        history.append({"date": today, "medal": medal["id"]})
    return {"schema": SCHEMA, "kind": evaluated["kind"], "name": evaluated["name"], "date": today, "medal": medal,
            "why": why, "tiers": tiers, "successes": successes, "next": steps, "history": history[-50:]}


def render_md(data: dict[str, Any]) -> str:
    done = [s for s in data["successes"] if s["unlocked"]]
    out = [f"# {data['medal']['name']} — {data['name']}", "", data["why"],
           f"Achievements unlocked: {len(done)} of {len(data['successes'])}. Measured on {data['date']}.", ""]
    for tier in data["tiers"]:
        out.append(f"## {'✓' if tier['earned'] else '·'} {tier['name']} — {tier['title']} ({tier['done']}/{tier['total']})")
        out.append(f"_{tier['promise']}_")
        for s in (s for s in data["successes"] if s["tier"] == tier["id"]):
            mark = f"[x] {s['title']} (since {s['unlocked']})" if s["unlocked"] else f"[ ] {s['title']}"
            out.append(f"- {mark}" + (f" — lost on {s['lost']}" if s["lost"] else ""))
        out.append("")
    extra = [s for s in data["successes"] if s["tier"] == "bonus"]
    if extra:
        out.append(f"## Outside the ranks ({sum(bool(s['unlocked']) for s in extra)}/{len(extra)})")
        out += [f"- [{'x' if s['unlocked'] else ' '}] {s['title']} ({s['evidence']})" for s in extra] + [""]
    if data["next"]:
        out.append("## Next steps")
        out += [f"{n}. {s['action'] or s['title']}" + (" (waiting: it does not depend on you alone)" if s["waiting"] else "")
                for n, s in enumerate(data["next"], 1)]
    return "\n".join(out).rstrip() + "\n"


# --- The page ---------------------------------------------------------------------------------------------

def csp(template: str) -> str:
    def digest(tag: str) -> str:
        body = re.search(rf"<{tag}>(.*?)</{tag}>", template, re.DOTALL)[1]
        return base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
    return (f"default-src 'none'; style-src 'sha256-{digest('style')}'; script-src 'sha256-{digest('script')}'; "
            "img-src data:; base-uri 'none'; form-action 'none'")


def render_html(data: dict[str, Any]) -> str:
    """A standalone page: the data is in the file, the script only shows it."""
    with open(TEMPLATE_FILE, encoding="utf-8") as fh:
        template = fh.read()
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = f"{data['medal']['name']} · {data['name']}".replace("&", "&amp;").replace("<", "&lt;")
    fields = {"csp": csp(template), "title": title, "data": raw}  # a single pass: a value is never read again
    return re.sub(r"\{\{(csp|title|data)\}\}", lambda m: fields[m[1]], template)


def write_file(path: str, text: str) -> None:
    """Writes in one go: a half-written file would restart the dates from zero."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--kind", choices=KINDS, help="what is measured (default: repo)")
    p.add_argument("--write", action="store_true", help=f"updates .harness/{FILE}, keeping the dates already earned")
    p.add_argument("--page", metavar="FILE", help="writes the interactive HTML page")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--name", help="the displayed name (default: the one of the medals file if it exists, otherwise of the folder or the marketplace)")
    p.add_argument("--today", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    if not os.path.isdir(args.repo):
        print(f"harness medals: {args.repo} is not a directory", file=sys.stderr)
        return 2
    try:
        today = date.fromisoformat(args.today) if args.today else None
    except ValueError:
        print(f"harness medals: --today {args.today!r} is not a YYYY-MM-DD date", file=sys.stderr)
        return 2
    kind = args.kind or "repo"
    path = os.path.join(args.repo, ".harness", FILE if kind == "repo" else f"medals-{kind}.json")
    previous = _json(path)
    usable = isinstance(previous, dict) and previous.get("schema") == SCHEMA and previous.get("kind") == kind
    if os.path.exists(path) and not usable:
        print(f"harness medals: {path} is unreadable or of another format, it is not reused: "
              "the unlock dates restart from today", file=sys.stderr)
    evaluated = evaluate_repo(args.repo, today) if kind == "repo" else evaluate_marketplace(args.repo, today)
    if args.name:
        evaluated["name"] = args.name
    elif usable and isinstance(previous.get("name"), str) and previous["name"]:
        evaluated["name"] = previous["name"]
    data = build(evaluated, previous)
    try:
        if args.page:
            write_file(args.page, render_html(data))
        # same measure, another day: the file does not move, its date is that of the last change
        if args.write and not (usable and {**previous, "date": None} == {**data, "date": None}):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_file(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"harness medals: cannot write ({exc})", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(data))
    return 0
