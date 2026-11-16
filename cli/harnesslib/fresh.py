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
MAX_PROBES = 20        # au plus tant de recherches dans l'historique d'un Makefile ou d'un manifeste
RULE_DAYS = 365        # une règle sans garde-fou de plus d'un an repasse en revue de pertinence
STATES = ("cassé", "à revoir")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
_SKIP_TOKEN = re.compile(r"[<>*${}|=…]|^-|^~|://|^@")
_MODEL = re.compile(r"\bclaude-(?:\d|opus|sonnet|haiku|fable|instant)[\w.-]*|\b(?:opus|sonnet|haiku)[ -]?\d(?:\.\d)?\b"
                    r"|\bgpt-\d[\w.-]*|\bgemini-\d[\w.-]*", re.IGNORECASE)
_MAKE = re.compile(r"\bmake\s+(?:-C\s+\S+\s+)?([A-Za-z0-9][\w.-]*)")
_NPM = re.compile(r"\b(?:npm|pnpm|yarn)\s+run\s+([\w:.-]+)")
_TARGET = re.compile(r"^([A-Za-z0-9][^:=#\t]*?)\s*:(?![:=])", re.MULTILINE)


def _git(repo: str, *args: str, stdin: bytes | None = None) -> str | None:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args], capture_output=True, timeout=120,
                             input=stdin)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.decode("utf-8", "replace") if out.returncode in (0, 1) else None


def is_repo(repo: str) -> bool:
    """Un dépôt git qui a au moins un commit : sans historique, rien ne se confronte."""
    return bool((_git(repo, "rev-parse", "--verify", "--quiet", "HEAD") or "").strip())


def last_dates(repo: str, paths: list[str], deleted_only: bool = False) -> dict[str, str]:
    """La date du dernier commit qui touche chacun de ces chemins (ou qui les supprime, avec
    `deleted_only`). Un seul appel, borné aux chemins demandés : le coût suit le nombre de citations,
    pas la taille de l'historique lu en entier."""
    found: dict[str, str] = {}
    for start in range(0, len(paths), 400):
        args = ["--literal-pathspecs", "log", "--no-renames", "-z", "--name-only", "--relative", "--format=%x01%cs%x01"]
        out = _git(repo, *args, *(["--diff-filter=D"] if deleted_only else []), "--", *paths[start:start + 400]) or ""
        day = ""
        for part in out.split("\0"):
            match = re.match(r"^\n*\x01(\d{4}-\d{2}-\d{2})\x01\n*(.*)$", part, re.DOTALL)
            day, name = (match[1], match[2]) if match else (day, part)
            if name.strip("\n"):
                found.setdefault(name.strip("\n"), day)
    return found


def ignored(repo: str, paths: list[str]) -> set[str]:
    """Ceux de ces chemins que .gitignore écarte : un fichier produit localement n'est pas un fichier disparu."""
    if not paths:
        return set()
    out = _git(repo, "check-ignore", "-z", "--stdin", stdin="\0".join(paths).encode("utf-8")) or ""
    return {p for p in out.split("\0") if p}


def tools(repo: str) -> list[dict[str, str]]:
    """Les skills et les agents du dépôt, hors données de test et hors copies du dépôt (worktrees, sous-dépôts)."""
    found = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in facts.SKIP_DIRS and d != "worktrees"
                         and not os.path.exists(os.path.join(root, d, ".git")))
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
    """Ce qui, dans le code d'un texte ou la cible d'un lien, a la forme d'un chemin relatif : au moins
    un `/`, pas de variable."""
    seen: list[str] = []
    spans = [span.strip("`") for span in _CODE.findall(text)] + re.findall(r"\]\(([^)\s#]+)", text)
    for span in spans:
        for token in span.split():
            token = re.sub(r":\d+(?:-\d+)?$", "", token.strip("'\"`(),;")).rstrip(".:").removeprefix("./")
            if ("/" in token.strip("/") or (token.endswith("/") and len(token) > 2)) and not _SKIP_TOKEN.search(token) and not token.startswith("/") and token not in seen:
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


def _gone_targets(repo: str, code: str, cache: dict[str, bool]) -> list[str]:
    """Les cibles `make` et scripts `npm run` cités que le dépôt a eus et n'a plus. Jugés seulement
    quand ils se lisent sans ambiguïté : Makefile racine sans `include`, commande sans `-C`."""
    gone = []
    makefile = _read(repo, "Makefile") if os.path.isfile(os.path.join(repo, "Makefile")) else None
    if makefile is not None and not re.search(r"^-?include\b", makefile, re.MULTILINE):
        present = {n for group in _TARGET.findall(makefile) for n in group.split()}
        for target in sorted(set(_MAKE.findall(code)) - present):
            key = f"make {target}"
            if key not in cache and len(cache) < MAX_PROBES:
                cache[key] = bool((_git(repo, "log", "-1", "--format=%H", f"-G^{re.escape(target)}\\s*:", "--", "Makefile") or "").strip())
            if cache.get(key):
                gone.append(key)
    try:
        scripts = json.loads(_read(repo, "package.json")).get("scripts")
    except (ValueError, AttributeError):
        scripts = None
    if isinstance(scripts, dict):
        for script in sorted(set(_NPM.findall(code)) - set(scripts)):
            key = f"npm run {script}"
            if key not in cache and len(cache) < MAX_PROBES:
                cache[key] = bool((_git(repo, "log", "-1", "--format=%H", f'-G"{re.escape(script)}"\\s*:', "--", "package.json") or "").strip())
            if cache.get(key):
                gone.append(key)
    return gone


def collect(repo: str, today: date | None = None, fast: bool = False) -> dict[str, Any]:
    """`fast` (le hook) saute ce qui coûte un appel git par règle ou par cible."""
    today = today or date.today()
    repo = os.path.abspath(repo)
    has_git = is_repo(repo)
    found = tools(repo)
    items: list[dict[str, Any]] = []
    plans = []
    for tool in found:
        text = _read(repo, tool["path"])
        alive, missing = [], {}
        for token in cited_paths(text):
            candidates = [_join(base, token) for base in _bases(tool["path"])]
            hit = next((c for c in candidates if os.path.exists(os.path.join(repo, c))), None)
            if hit:
                alive.append(hit)
            else:
                missing[token] = [c for c in candidates if not c.startswith("..")]
        plans.append((tool, text, alive, missing))
    gone: dict[str, str] = {}
    dates: dict[str, str] = {}
    skipped: set[str] = set()
    if has_git:
        wanted = sorted({c for _, _, _, missing in plans for cs in missing.values() for c in cs})
        gone = last_dates(repo, wanted, deleted_only=True)
        # suivi par git mais absent du disque : supprimé sans que ce soit encore commité
        tracked = _git(repo, "--literal-pathspecs", "ls-files", "-z", "--", *wanted[:400]) or ""
        gone.update({p: "" for p in tracked.split("\0") if p and not os.path.exists(os.path.join(repo, p))})
        skipped = ignored(repo, wanted)
        files = sorted({t["path"] for t, _, _, _ in plans} | {a for _, _, alive, _ in plans for a in alive
                                                              if os.path.isfile(os.path.join(repo, a))})
        dates = last_dates(repo, files)
    probes: dict[str, bool] = {}
    for tool, text, alive, missing in plans:
        def add(state: str, signal: str, what: str, evidence: str, action: str, tool: dict[str, str] = tool) -> None:
            items.append({"state": state, "signal": signal, "kind": tool["kind"], "path": tool["path"], "what": what,
                          "evidence": evidence, "action": action})

        models = sorted({m.group(0) for m in _MODEL.finditer(text)})
        if models:
            add("à revoir", "modele", "Il nomme un modèle", ", ".join(models[:4]),
                "Retirer le nom du modèle, ou le relire à chaque changement de modèle : la consigne a pu devenir inutile.")
        if not has_git:
            continue
        dead = [token for token, candidates in missing.items()
                if any(c not in skipped and (c in gone or any(g.startswith(c.rstrip("/") + "/") for g in gone)) for c in candidates)]
        if dead:
            add("cassé", "reference", "Il cite ce que le dépôt a eu et n'a plus", ", ".join(dead[:5]),
                "Corriger la référence (le fichier a été renommé ou supprimé), ou retirer l'étape qui en dépend.")
        targets = [] if fast else _gone_targets(repo, "\n".join(_CODE.findall(text)), probes)
        if targets:
            add("à revoir", "cible", "Il cite une cible ou un script que le dépôt a eu et n'a plus", ", ".join(targets[:5]),
                "Vérifier s'il parle de ce dépôt : si oui, corriger la commande.")
        mine = dates.get(tool["path"])
        moved = [f"{a} ({dates[a]})" for a in dict.fromkeys(alive) if a in dates and mine and dates[a] > mine
                 and (_days(mine, today) or 0) - (_days(dates[a], today) or 0) > LAG_DAYS]
        if moved:
            add("à revoir", "change", f"Ce qu'il cite a changé depuis sa dernière relecture ({mine})", ", ".join(moved[:4]),
                "Relire l'outil à côté de ces fichiers : une étape décrit peut-être un comportement qui n'existe plus.")
        idle = _days(mine, today)
        if idle is not None and idle > IDLE_DAYS:
            add("à revoir", "immobile", f"Personne n'y a touché depuis {idle} jours", mine or "",
                "Le rejouer sur un cas réel ou une fixture : s'il sert encore tel quel, noter la date de la vérification.")

    def note(state: str, signal: str, path: str, what: str, evidence: str, action: str) -> None:
        items.append({"state": state, "signal": signal, "kind": "instructions", "path": path, "what": what,
                      "evidence": evidence, "action": action})

    collected = facts.collect(repo, today=today)
    state = maturity.evaluate(collected)
    source = collected["instructions"]["source"].get("path") or "AGENTS.md"
    for ref in state["dangling"]:
        note("cassé", "garde-fou", f"{source}:{ref.get('line')}", "Une règle cite un garde-fou ou un contrat qui n'existe pas",
             str(ref.get("ref")), "Réparer la référence, ou marquer la règle (non vérifiée) : elle ne l'est plus.")
    age = collected.get("harvest_marker_age_days")
    if isinstance(age, int) and age > maturity.MAX_MARKER_AGE_DAYS:
        note("à revoir", "harvest", source, f"Le dernier harvest a {age} jours", f"seuil : {maturity.MAX_MARKER_AGE_DAYS} jours",
             "Lancer harness-harvest : les incidents récents ne sont pas encore devenus des règles.")
    audit_age = _days((collected.get("audit") or {}).get("date"), today)
    if audit_age is not None and audit_age > AUDIT_DAYS:
        note("à revoir", "audit", ".harness/audit.json", f"Le dernier audit a {audit_age} jours", f"seuil : {AUDIT_DAYS} jours",
             "Relancer harness-audit, au moins sa revue de pertinence.")
    old = [r for r in rules.collect(repo, today, blame=not fast) if (r["age_days"] or 0) > RULE_DAYS and not r["guarded"]]
    if old:
        note("à revoir", "regles", old[0]["file"], f"{len(old)} règle(s) de plus d'un an sans garde-fou",
             ", ".join(f"{r['file']}:{r['line']}" for r in old[:4]),
             "Les passer à la revue de pertinence de harness-audit : changent-elles encore ce que fait l'agent ?")
    order = {s: n for n, s in enumerate(STATES)}
    items.sort(key=lambda i: (order[i["state"]], i["path"], i["signal"]))
    return {"date": today.isoformat(), "git": has_git, "tools": len(found),
            "counts": {s: sum(i["state"] == s for i in items) for s in STATES}, "items": items}


def render_md(result: dict[str, Any]) -> str:
    counts = result["counts"]
    out = [f"Fraîcheur du harness au {result['date']} : {counts['cassé']} cassé(s), {counts['à revoir']} à revoir, "
           f"sur {result['tools']} skill(s) et agent(s) et les instructions."]
    if not result["git"]:
        out.append("Pas de dépôt git, ou pas encore de commit : les skills et les agents ne sont pas confrontés à l'historique.")
    for item in result["items"]:
        out += [f"- **{item['state']}** — `{item['path']}` : {item['what']}" + (f" ({item['evidence']})" if item["evidence"] else "") + ".",
                f"  {item['action']}"]
    if not result["items"]:
        out.append("Rien n'a vieilli d'après ce qui se mesure. Ce qui ne se mesure pas : une consigne juste hier, inutile aujourd'hui.")
    return "\n".join(out) + "\n"


LABELS = {"reference": "skill(s) ou agent(s) citent un fichier que le dépôt n'a plus",
          "garde-fou": "règle(s) citent un garde-fou introuvable",
          "harvest": "harvest en retard", "audit": "audit trop ancien"}


def render_hook(result: dict[str, Any]) -> str:
    """Deux lignes au plus, et rien du tout si rien n'est cassé ni en retard : un rappel qui parle à
    chaque session n'est plus lu. Des comptes seulement : aucun texte du dépôt n'entre ainsi dans le
    contexte de la session, un nom de fichier pourrait y porter une consigne."""
    counts = {signal: sum(i["signal"] == signal for i in result["items"]) for signal in LABELS}
    said = [f"{n} {LABELS[signal]}" if signal in ("reference", "garde-fou") else LABELS[signal]
            for signal, n in counts.items() if n]
    if not said:
        return ""
    return f"harness fresh : {' ; '.join(said)}.\nDétail et marche à suivre : python3 cli/harness.py fresh\n"


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
    if args.hook:
        try:  # un hook de début de session ne doit jamais empêcher de travailler, ni sortir autre chose que 0
            text = render_hook(collect(args.repo, today, fast=True))
            raw = getattr(sys.stdout, "buffer", None)   # en octets : une console ASCII ne fait pas échouer le hook
            if raw is None:
                sys.stdout.write(text)
            else:
                raw.write(text.encode("utf-8", "replace"))
                raw.flush()
        except Exception as exc:
            print(f"harness fresh : mesure impossible ({type(exc).__name__})", file=sys.stderr)
        return 0
    result = collect(args.repo, today)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_md(result))
    return 1 if args.strict and result["counts"]["cassé"] else 0
