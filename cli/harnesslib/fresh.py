"""Ce qui a vieilli dans le harness d'un dépôt : la boucle contre l'obsolescence, sans modèle.

Les règles d'AGENTS.md avaient déjà leurs signaux (date, harvest, références sans cible). Un skill ou
un agent n'en avait aucun : il continue de citer un fichier renommé, une cible supprimée, un modèle
remplacé, et personne ne le voit. Ce module lit les skills et les agents du dépôt et les confronte à
l'historique git :
- **cassé** : il cite un chemin que le dépôt a eu et n'a plus, ou une cible `make` / un script `npm`
  disparus ; une règle cite un garde-fou qui n'existe plus ;
- **à revoir** : ce qu'il cite a changé depuis sa dernière relecture, il n'a pas bougé depuis
  longtemps, il nomme un modèle, le harvest ou l'audit datent, une règle a plus d'un an sans garde-fou.

Un chemin jamais vu par git n'est pas jugé : un skill parle souvent des fichiers d'un autre dépôt.
Sans git, seuls les signaux des règles sont rendus. Branché en hook de début de session (`--hook`),
il ne dit rien tant que rien n'est cassé ni en retard."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from typing import Any

from . import facts, maturity, rules

LAG_DAYS = 30          # ce qu'un skill cite a changé depuis plus longtemps que ça sans qu'il soit relu
IDLE_DAYS = 180        # un skill ou un agent que personne n'a touché depuis
AUDIT_DAYS = 180       # un audit plus vieux ne décrit plus le dépôt
RULE_DAYS = 365        # une règle sans garde-fou de plus d'un an repasse en revue de pertinence
STATES = ("cassé", "à revoir")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
_SKIP_TOKEN = re.compile(r"[<>*${}|=…]|^-|^~|://|^@")
_MODEL = re.compile(r"\bclaude-(?:\d|opus|sonnet|haiku|fable|instant)[\w.-]*|\b(?:opus|sonnet|haiku)[ -]?\d(?:\.\d)?\b"
                    r"|\bgpt-\d[\w.-]*|\bgemini-\d[\w.-]*", re.IGNORECASE)
_MAKE = re.compile(r"\bmake\s+(?:-C\s+\S+\s+)?([A-Za-z0-9][\w.-]*)")
_NPM = re.compile(r"\b(?:npm|pnpm|yarn)\s+run\s+([\w:.-]+)")
_TARGET = re.compile(r"^([A-Za-z0-9][^:=#\t]*?)\s*:(?![:=])", re.MULTILINE)


def _git(repo: str, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def history(repo: str) -> dict[str, str] | None:
    """Pour chaque chemin que git a connu, la date de son dernier changement. None hors d'un dépôt git.
    Les chemins sont relatifs au dossier donné, même s'il est un sous-dossier du dépôt."""
    log = _git(repo, "log", "--no-renames", "--name-only", "--relative", "--format=%x01%cs", "--max-count=20000")
    if log is None:
        return None
    last: dict[str, str] = {}
    day = ""
    for line in log.splitlines():
        if line.startswith("\x01"):
            day = line[1:].strip()
        elif line.strip():
            last.setdefault(line.strip(), day)
    return last


def tools(repo: str) -> list[dict[str, str]]:
    """Les skills et les agents du dépôt, hors données de test."""
    found = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in facts.SKIP_DIRS)
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        for name in sorted(names):
            rel = name if rel_root == "." else f"{rel_root}/{name}"
            if name == "SKILL.md":
                found.append({"path": rel, "kind": "skill"})
            elif name.endswith(".md") and os.path.basename(root) == "agents" and (
                    ".claude" in rel_root.split("/") or os.path.isdir(os.path.join(os.path.dirname(root), "skills"))
                    or os.path.isdir(os.path.join(os.path.dirname(root), ".claude-plugin"))):
                found.append({"path": rel, "kind": "agent"})
    return found


def _read(repo: str, rel: str) -> str:
    try:
        with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read(1_000_000)
    except OSError:
        return ""


def cited_paths(text: str) -> list[str]:
    """Ce qui, dans le code d'un texte, a la forme d'un chemin relatif : au moins un `/`, pas de variable."""
    seen: list[str] = []
    for span in _CODE.findall(text):
        for token in span.strip("`").split():
            token = re.sub(r":\d+(?:-\d+)?$", "", token.strip("'\"`(),;")).rstrip(".:").removeprefix("./")
            if "/" in token.strip("/") and not _SKIP_TOKEN.search(token) and not token.startswith("/") and token not in seen:
                seen.append(token)
    return seen


def _bases(rel: str) -> list[str]:
    """D'où un chemin cité peut partir : la racine, le dossier de l'outil, la racine de son plugin."""
    folder = os.path.dirname(rel)
    plugin = os.path.dirname(os.path.dirname(folder)) if os.path.basename(rel) == "SKILL.md" else os.path.dirname(folder)
    out = []
    for base in ("", folder, plugin):
        if base not in out:
            out.append(base)
    return out


def _join(base: str, token: str) -> str:
    return os.path.normpath(os.path.join(base, token)).replace(os.sep, "/")


def _days(day: str | None, today: date) -> int | None:
    try:
        return (today - date.fromisoformat(day)).days if day else None
    except ValueError:
        return None


def check_tool(repo: str, tool: dict[str, str], known: dict[str, str] | None, today: date,
               makefile: str | None, scripts: dict[str, Any] | None) -> list[dict[str, Any]]:
    rel, text = tool["path"], _read(repo, tool["path"])
    items: list[dict[str, Any]] = []

    def add(state: str, signal: str, what: str, evidence: str, action: str) -> None:
        items.append({"state": state, "signal": signal, "kind": tool["kind"], "path": rel, "what": what,
                      "evidence": evidence, "action": action})

    models = sorted({m.group(0) for m in _MODEL.finditer(text)})
    if models:
        add("à revoir", "modele", "Il nomme un modèle", ", ".join(models[:4]),
            "Retirer le nom du modèle, ou le relire à chaque changement de modèle : la consigne a pu devenir inutile.")
    if known is None:
        return items
    mine = known.get(rel)
    dead, moved = [], []
    for token in cited_paths(text):
        candidates = [_join(base, token) for base in _bases(rel)]
        alive = next((c for c in candidates if os.path.exists(os.path.join(repo, c))), None)
        if alive:
            changed = known.get(alive)
            if os.path.isfile(os.path.join(repo, alive)) and changed and mine and changed > mine \
                    and (_days(mine, today) or 0) - (_days(changed, today) or 0) > LAG_DAYS:
                moved.append(f"{alive} ({changed})")
        elif any(c in known for c in candidates):
            dead.append(token)
    for target in sorted(set(_MAKE.findall("\n".join(_CODE.findall(text))))):
        if makefile is not None and target not in {n for group in _TARGET.findall(makefile) for n in group.split()} \
                and (_git(repo, "log", "-1", "--format=%H", f"-S{target}:", "--", "Makefile") or "").strip():
            dead.append(f"make {target}")
    for script in sorted(set(_NPM.findall("\n".join(_CODE.findall(text))))):
        if scripts is not None and script not in scripts \
                and (_git(repo, "log", "-1", "--format=%H", f'-S"{script}"', "--", "package.json") or "").strip():
            dead.append(f"npm run {script}")
    if dead:
        add("cassé", "reference", "Il cite ce que le dépôt a eu et n'a plus", ", ".join(dead[:5]),
            "Corriger la référence (le fichier a été renommé ou supprimé), ou retirer l'étape qui en dépend.")
    if moved:
        add("à revoir", "change", f"Ce qu'il cite a changé depuis sa dernière relecture ({mine})", ", ".join(moved[:4]),
            "Relire l'outil à côté de ces fichiers : une étape décrit peut-être un comportement qui n'existe plus.")
    idle = _days(mine, today)
    if idle is not None and idle > IDLE_DAYS:
        add("à revoir", "immobile", f"Personne n'y a touché depuis {idle} jours", mine or "",
            "Le rejouer sur un cas réel ou une fixture : s'il sert encore tel quel, noter la date de la vérification.")
    return items


def collect(repo: str, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    repo = os.path.abspath(repo)
    known = history(repo)
    makefile = _read(repo, "Makefile") if os.path.isfile(os.path.join(repo, "Makefile")) else None
    try:
        scripts = json.loads(_read(repo, "package.json")).get("scripts")
    except (ValueError, AttributeError):
        scripts = None
    found = tools(repo)
    items: list[dict[str, Any]] = []
    for tool in found:
        items += check_tool(repo, tool, known, today, makefile, scripts if isinstance(scripts, dict) else None)

    def add(state: str, signal: str, path: str, what: str, evidence: str, action: str) -> None:
        items.append({"state": state, "signal": signal, "kind": "instructions", "path": path, "what": what,
                      "evidence": evidence, "action": action})

    collected = facts.collect(repo, today=today)
    state = maturity.evaluate(collected)
    source = collected["instructions"]["source"].get("path") or "AGENTS.md"
    for ref in state["dangling"]:
        add("cassé", "garde-fou", f"{source}:{ref.get('line')}", "Une règle cite un garde-fou ou un contrat qui n'existe pas",
            str(ref.get("ref")), "Réparer la référence, ou marquer la règle (non vérifiée) : elle ne l'est plus.")
    age = collected.get("harvest_marker_age_days")
    if isinstance(age, int) and age > maturity.MAX_MARKER_AGE_DAYS:
        add("à revoir", "harvest", source, f"Le dernier harvest a {age} jours", f"seuil : {maturity.MAX_MARKER_AGE_DAYS} jours",
            "Lancer harness-harvest : les incidents récents ne sont pas encore devenus des règles.")
    audit_age = _days((collected.get("audit") or {}).get("date"), today)
    if audit_age is not None and audit_age > AUDIT_DAYS:
        add("à revoir", "audit", ".harness/audit.json", f"Le dernier audit a {audit_age} jours", f"seuil : {AUDIT_DAYS} jours",
            "Relancer harness-audit, au moins sa revue de pertinence.")
    old = [r for r in rules.collect(repo, today) if (r["age_days"] or 0) > RULE_DAYS and not r["guarded"]]
    if old:
        add("à revoir", "regles", old[0]["file"], f"{len(old)} règle(s) de plus d'un an sans garde-fou",
            ", ".join(f"{r['file']}:{r['line']}" for r in old[:4]),
            "Les passer à la revue de pertinence de harness-audit : changent-elles encore ce que fait l'agent ?")
    order = {s: n for n, s in enumerate(STATES)}
    items.sort(key=lambda i: (order[i["state"]], i["path"], i["signal"]))
    return {"date": today.isoformat(), "git": known is not None, "tools": len(found),
            "counts": {s: sum(i["state"] == s for i in items) for s in STATES}, "items": items}


def render_md(result: dict[str, Any]) -> str:
    counts = result["counts"]
    out = [f"Fraîcheur du harness au {result['date']} : {counts['cassé']} cassé(s), {counts['à revoir']} à revoir, "
           f"sur {result['tools']} skill(s) et agent(s) et les instructions."]
    if not result["git"]:
        out.append("Hors d'un dépôt git : les skills et les agents ne sont pas confrontés à l'historique.")
    for item in result["items"]:
        out += [f"- **{item['state']}** — `{item['path']}` : {item['what']}" + (f" ({item['evidence']})" if item["evidence"] else "") + ".",
                f"  {item['action']}"]
    if not result["items"]:
        out.append("Rien n'a vieilli d'après ce qui se mesure. Ce qui ne se mesure pas : une consigne juste hier, inutile aujourd'hui.")
    return "\n".join(out) + "\n"


def render_hook(result: dict[str, Any]) -> str:
    """Trois lignes au plus, et rien du tout si rien n'est cassé ni en retard : un rappel qui parle
    à chaque session n'est plus lu."""
    urgent = [i for i in result["items"] if i["state"] == "cassé" or i["signal"] in ("harvest", "audit")]
    if not urgent:
        return ""
    lines = [f"harness fresh : {len(urgent)} point(s) du harness de ce dépôt ont vieilli."]
    lines += [f"- {i['path']} : {i['what'].lower()} ({i['evidence']})" for i in urgent[:2]]
    return "\n".join(lines + ["Détail et marche à suivre : python3 cli/harness.py fresh"]) + "\n"


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--hook", action="store_true", help="sortie courte pour un hook de début de session, vide si rien ne presse")
    p.add_argument("--strict", action="store_true", help="sort en 1 si quelque chose est cassé (pour un job planifié)")
    p.add_argument("--today", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    args = args or build_parser().parse_args(argv)
    try:
        today = date.fromisoformat(args.today) if args.today else None
    except ValueError:
        print(f"harness fresh : --today {args.today!r} n'est pas une date AAAA-MM-JJ", file=sys.stderr)
        return 2
    if not os.path.isdir(args.repo):
        print(f"harness fresh : {args.repo} n'est pas un dossier", file=sys.stderr)
        return 0 if args.hook else 2
    try:
        result = collect(args.repo, today)
    except Exception as exc:  # un hook de début de session ne doit jamais empêcher de travailler
        if not args.hook:
            raise
        print(f"harness fresh : mesure impossible ({exc})", file=sys.stderr)
        return 0
    if args.hook:
        sys.stdout.write(render_hook(result))
        return 0
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(result))
    return 1 if args.strict and result["counts"]["cassé"] else 0
