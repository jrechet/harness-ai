"""Le garde-fou « un agent ne livre pas » : dit si une commande shell pose un tag, publie ou déploie.

Appelé par un hook du plugin avant chaque commande de l'agent. Il refuse ce qui fait partir quelque
chose : un tag git créé, déplacé ou poussé, une release ou un workflow lancés sur la forge, une
publication de paquet ou d'image, un déploiement par les outils courants, une cible `make` ou un script
de livraison, et les commandes que la procédure de l'équipe écrit elle-même.

C'est une barrière contre l'accident et contre la consigne glissée dans un ticket ou un commit, pas un
bac à sable : un script qui déploie, lancé par son nom, passe. Ce qui tient vraiment une production,
ce sont les droits de l'agent et la protection de la forge."""
from __future__ import annotations

import json
import os
import re
import shlex
from typing import Any

MAX_COMMAND = 20_000
MAX_DEPTH = 4
_DELIVERY = re.compile(r"(?:^|[-_:.])(?:deploy\w*|release\w*|publish\w*|livr\w*|ship\w*|prod|production|rollout|promote|revenir|rollback)(?:$|[-_:.])",
                       re.IGNORECASE)
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"sudo", "doas", "command", "exec", "time", "nohup", "nice", "env", "builtin", "stdbuf", "ionice", "setsid", "caffeinate"}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
_OPERATORS = {"&&", "||", ";", "|", "&", "|&", ";;", "(", ")", "{", "}", "!", "then", "do", "else", "elif", "if", "while", "until"}
_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}
_TAG_READ = {"-l", "--list", "-n", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--sort", "--format",
             "--column", "--no-column", "-v", "--verify", "-i", "--ignore-case", "--color", "--no-color"}
# outil → sous-commandes qui font partir quelque chose (une suite de mots à retrouver dans l'ordre)
_TOOLS: dict[str, list[tuple[str, ...]]] = {
    "gh": [("release", "create"), ("release", "edit"), ("release", "upload"), ("release", "delete"), ("workflow", "run"),
           ("workflow", "enable"), ("run", "rerun")],
    "glab": [("release", "create"), ("release", "upload"), ("release", "delete"), ("ci", "run"), ("ci", "trigger"), ("ci", "retry")],
    "kubectl": [("apply",), ("rollout",), ("set",), ("delete",), ("scale",), ("patch",), ("replace",), ("create",), ("edit",), ("drain",)],
    "oc": [("apply",), ("rollout",), ("delete",), ("new-app",), ("start-build",)],
    "helm": [("install",), ("upgrade",), ("rollback",), ("uninstall",), ("delete",), ("push",)],
    "helmfile": [("apply",), ("sync",), ("destroy",)],
    "terraform": [("apply",), ("destroy",), ("import",), ("taint",)], "tofu": [("apply",), ("destroy",)],
    "terragrunt": [("apply",), ("destroy",), ("run-all",)], "pulumi": [("up",), ("destroy",), ("refresh",)],
    "cdk": [("deploy",), ("destroy",)], "sam": [("deploy",), ("delete",)], "serverless": [("deploy",), ("remove",)],
    "sls": [("deploy",), ("remove",)], "docker": [("push",), ("stack", "deploy"), ("service", "update"), ("buildx", "build", "--push")],
    "podman": [("push",)], "skaffold": [("run",), ("deploy",)], "argocd": [("app", "sync"), ("app", "rollback"), ("app", "set")],
    "flux": [("reconcile",)], "npm": [("publish",), ("unpublish",), ("deprecate",), ("dist-tag",)], "pnpm": [("publish",)],
    "yarn": [("publish",), ("npm", "publish")], "bun": [("publish",)], "lerna": [("publish",)], "twine": [("upload",)],
    "poetry": [("publish",)], "uv": [("publish",)], "flit": [("publish",)], "hatch": [("publish",)], "cargo": [("publish",), ("yank",)],
    "gem": [("push",), ("yank",)], "mvn": [("deploy",), ("release:perform",)], "gradle": [("publish",)], "gradlew": [("publish",)],
    "dotnet": [("nuget", "push"),], "nuget": [("push",)], "goreleaser": [("release",)], "vercel": [("deploy",), ("--prod",), ("promote",)],
    "netlify": [("deploy",)], "fly": [("deploy",)], "flyctl": [("deploy",)], "heroku": [("container:release",), ("releases:rollback",), ("pipelines:promote",)],
    "firebase": [("deploy",)], "wrangler": [("deploy",), ("publish",)], "railway": [("up",)], "cap": [("deploy",)],
    "ansible-playbook": [()], "fab": [("deploy",)], "eb": [("deploy",)], "copilot": [("deploy",)], "gcloud": [("deploy",), ("rollouts",)],
    "aws": [("deploy",), ("ecs", "update-service"), ("lambda", "update-function-code"), ("cloudformation", "deploy"), ("s3", "sync")],
    "az": [("deployment",), ("webapp", "deploy"), ("functionapp", "deployment")],
}
_RUNNERS = {"make": 1, "gmake": 1, "just": 1, "task": 1, "rake": 1, "invoke": 1, "nox": 1}
_SCRIPT_RUNNERS = {("npm", "run"), ("npm", "run-script"), ("pnpm", "run"), ("yarn", "run"), ("bun", "run"), ("composer", "run"), ("composer", "run-script")}


def _segments(command: str) -> list[list[str]]:
    """Les commandes simples d'une ligne de shell, chacune en liste de mots. Lève ValueError si elle ne se découpe pas."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    out, current = [], []
    for token in lexer:
        if token in _OPERATORS or set(token) <= set("&|;()<>"):
            if current:
                out.append(current)
            current = []
        else:
            current.append(token)
    return out + ([current] if current else [])


def _strip(argv: list[str]) -> list[str]:
    """La commande sans ce qui l'enrobe : affectations, sudo, env, time…"""
    while argv:
        word = argv[0]
        if _ASSIGN.match(word):
            argv = argv[1:]
        elif word.rsplit("/", 1)[-1] in _WRAPPERS:
            argv = argv[1:]
            while argv and (argv[0].startswith("-") or _ASSIGN.match(argv[0])):
                argv = argv[1:]
        else:
            break
    return argv


def _git(argv: list[str]) -> str | None:
    rest = argv[1:]
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in _GIT_VALUE_OPTS else rest[1:]
    if not rest:
        return None
    sub, args = rest[0], rest[1:]
    if sub == "tag":
        names = [a for a in args if not a.startswith("-")]
        flags = {a.split("=")[0] for a in args if a.startswith("-")}
        writes = flags & {"-a", "-s", "-u", "-f", "--force", "-d", "--delete", "-m", "-F", "--annotate", "--sign", "--file", "--message"}
        if writes or (names and not flags & _TAG_READ):
            return "un tag git est posé, déplacé ou supprimé"
    if sub == "push":
        if any(a in ("--tags", "--follow-tags", "--mirror") or "refs/tags" in a for a in args):
            return "des tags sont poussés"
        refs = [a for a in args if not a.startswith("-")][1:]
        if any(re.fullmatch(r"(?:.*:)?v?\d+\.\d+(?:\.\d+)?[\w.-]*", ref) for ref in refs):
            return "un tag de version est poussé"
    if sub == "update-ref" and any("refs/tags" in a for a in args):
        return "un tag git est écrit"
    return None


def _contains(args: list[str], words: tuple[str, ...]) -> bool:
    position = 0
    for word in words:
        try:
            position = args.index(word, position) + 1
        except ValueError:
            return False
    return True


def _one(argv: list[str], team: list[list[str]]) -> str | None:
    argv = _strip(argv)
    if not argv:
        return None
    name = argv[0].rsplit("/", 1)[-1]
    args = argv[1:]
    for known in team:
        if [name, *args][:len(known)] == known:
            return "c'est une commande de la procédure de livraison de l'équipe"
    if name == "git":
        return _git(argv)
    if name in _TOOLS and any(_contains(args, words) for words in _TOOLS[name]):
        return f"`{name}` publie ou déploie"
    if name == "gh" and args[:1] == ["api"] and any(re.search(r"/(?:releases|dispatches|deployments|git/(?:refs|tags))\b", a) for a in args) \
            and any(a in ("-X", "--method", "-f", "-F", "--field", "--raw-field", "--input") for a in args):
        return "`gh api` écrit une release, un tag ou un déclenchement sur la forge"
    if name in ("curl", "wget", "http", "https") and any(re.search(r"/(?:releases|dispatches|deployments)\b|hooks?/deploy|deploy[-_]?hook", a) for a in args):
        return "une requête déclenche une release ou un déploiement"
    if name in _RUNNERS:
        hit = next((a for a in args if not a.startswith("-") and not _ASSIGN.match(a) and _DELIVERY.search(a)), None)
        if hit:
            return f"la cible `{hit[:40]}` de `{name}` est une livraison"
    if (name, *args[:1]) in _SCRIPT_RUNNERS or name in ("yarn", "pnpm", "bun"):
        script = next((a for a in (args[1:] if (name, *args[:1]) in _SCRIPT_RUNNERS else args) if not a.startswith("-")), None)
        if script and _DELIVERY.search(script):
            return f"le script `{script[:40]}` est une livraison"
    return None


def _nested(argv: list[str]) -> list[str]:
    """Les lignes de shell portées par les mots d'une commande : `sh -c "…"`, `eval "…"`, `$(…)`, accents graves."""
    stripped = _strip(argv)
    inner = []
    if stripped:
        name = stripped[0].rsplit("/", 1)[-1]
        if name in _SHELLS and len(stripped) > 2:
            for index, word in enumerate(stripped[1:-1], 1):
                if word.startswith("-") and not word.startswith("--") and "c" in word:
                    inner.append(stripped[index + 1])
        if name in ("eval", "xargs", "watch", "timeout", "ssh", "parallel"):
            # la commande portée commence après des options et des valeurs qu'on ne connaît pas : chaque fin est essayée
            inner += [shlex.join(stripped[start:]) for start in range(1, min(len(stripped), 8))]
            inner += stripped[1:]
    return inner


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")


def _lines(command: str) -> str:
    """La commande où un saut de ligne hors guillemets devient un « ; », et où le corps d'un here-document
    (du texte donné à une commande, pas des commandes) est retiré."""
    out, quote, escaped, skip_until, line = [], "", False, None, ""
    for ch in command + "\n":
        if ch == "\n" and not quote:
            if skip_until is not None:
                if line.strip() == skip_until:
                    skip_until = None
            else:
                out.append(line)
                found = _HEREDOC.search(line)
                skip_until = found[2] if found else None
            line, escaped = "", False
            continue
        line += ch
        if skip_until is not None:
            continue
        if escaped:
            escaped = False
        elif ch == "\\" and quote != "'":
            escaped = True
        elif quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
    if line:
        out.append(line)   # un guillemet jamais fermé : le reste se juge tel quel
    return " ; ".join(part for part in out if part.strip())


def reasons(command: str, team: list[str] | None = None, depth: int = 0) -> list[str]:
    """Pourquoi cette commande est refusée ; liste vide si elle ne fait rien partir de connu."""
    if not isinstance(command, str) or not command.strip():
        return []
    if len(command) > MAX_COMMAND:
        return [f"commande de plus de {MAX_COMMAND} caractères : elle n'est pas lue, elle n'est pas lancée"]
    known = []
    for line in team or []:
        try:
            words = _strip(shlex.split(line))[:2]
        except ValueError:
            continue
        if len(words) == 2 and not words[1].startswith(("-", "<")):
            known.append([words[0].rsplit("/", 1)[-1], words[1]])
    found: list[str] = []
    if depth < MAX_DEPTH:   # ce qu'un shell exécuterait à l'intérieur d'un mot, guillemets doubles compris
        for inner in re.findall(r"\$\(([^()]{1,2000})\)", command) + re.findall(r"`([^`]{1,2000})`", command):
            found += reasons(inner, team, depth + 1)
    try:
        segments = _segments(_lines(command.replace("\\\n", " ")))
    except ValueError:
        # une ligne que shlex ne sait pas découper se juge sur son texte : mieux vaut un refus de trop
        hits = [why for line in re.split(r"[\n;&|]+", command) for why in ([_one(line.split(), known)] if line.split() else []) if why]
        return found + (hits[:1] or (["la commande ne se découpe pas, et son texte parle de livraison"] if _DELIVERY.search(command) else []))
    for argv in segments:
        why = _one(argv, known)
        if why:
            found.append(why)
        if depth < MAX_DEPTH:
            for inner in _nested(argv):
                found += reasons(inner, team, depth + 1)
    return list(dict.fromkeys(found))


def render(found: list[str]) -> str:
    return ("ai-sdlc : commande refusée, " + " ; ".join(found) + ".\n"
            "Un agent ne pose pas de tag, ne publie pas et ne déploie pas. Écris la commande dans ta proposition "
            "(`ship render`) : c'est un humain qui la lance, dans son terminal.\n")


def hook(payload: Any, team: list[str] | None = None) -> tuple[int, str]:
    """La réponse à un appel de hook PreToolUse : (code de sortie, message). 2 refuse l'appel, 0 le laisse passer."""
    if not isinstance(payload, dict):
        return 0, ""
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if payload.get("tool_name") != "Bash" or not isinstance(command, str):
        return 0, ""
    found = reasons(command, team)
    return (2, render(found)) if found else (0, "")


ALLOW_ENV = "AI_SDLC_LIVRAISON_PAR_AGENT"   # posée par l'équipe dans l'environnement de la session, jamais par l'agent
PROCEDURE = "docs/agents/livraison.md"
_CRUDE = re.compile(r"\bgit\b[^\n;&|]{0,200}\btag\s+(?!-l\b|--list\b)\S|\bpush\b[^\n;&|]{0,200}--tags|\bgh\s+(?:release|workflow)\s+(?:create|run)|"
                    r"\b(?:npm|pnpm|yarn|cargo|twine)\s+(?:publish|upload)\b|\b(?:kubectl|helm|terraform)\s+(?:apply|upgrade|install|destroy)\b|"
                    r"\bmake\s+\S*(?:deploy|release|livr|publish)", re.IGNORECASE)


def team_lines(repo: str) -> list[str]:
    """Les commandes que la procédure de l'équipe écrit entre accents graves, lues sur la branche de base si elle
    se résout et dans la copie de travail : retirer la ligne de sa copie ne désarme pas le garde-fou."""
    from . import context, ship
    texts = []
    try:
        commit = context.resolve_base(repo, "origin/HEAD")
        texts.append(context._read_at(repo, commit, PROCEDURE) or "")
    except context.Refused:
        pass
    try:
        with open(os.path.join(repo, PROCEDURE), encoding="utf-8", errors="replace") as fh:
            texts.append(fh.read(200_000))
    except OSError:
        pass
    return list(dict.fromkeys(line for text in texts for line in ship.team_commands(text)))


def run_hook(raw: str, environ: dict[str, str]) -> tuple[int, str]:
    """Le hook de bout en bout. Il ne plante pas : une entrée illisible laisse passer (ce n'est pas un appel de
    commande qu'on sait lire), une erreur interne se rabat sur un motif grossier plutôt que d'ouvrir la porte."""
    if environ.get(ALLOW_ENV) == "1":
        return 0, ""
    try:
        payload = json.loads(raw)
    except (ValueError, RecursionError):
        return 0, ""
    repo = environ.get("CLAUDE_PROJECT_DIR") or (payload.get("cwd") if isinstance(payload, dict) else None) or "."
    try:
        return hook(payload, team_lines(repo) if isinstance(repo, str) and os.path.isdir(repo) else None)
    except Exception:   # noqa: BLE001 — un garde-fou qui plante laisserait tout passer : on se rabat, on ne lève pas
        tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
        command = tool_input.get("command") if isinstance(tool_input, dict) else ""
        if isinstance(command, str) and _CRUDE.search(command[:MAX_COMMAND]):
            return 2, render(["la commande ressemble à une livraison (lecture de secours)"])
        return 0, ""
