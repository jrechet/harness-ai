"""The guardrail "an agent does not deliver": says whether a shell command tags, publishes or deploys.

Called by a hook of the plugin before each command of the agent. It refuses what sends something out: a
git tag created, moved or pushed, a release or a workflow started on the forge, a package or image
publication, a deployment through the usual tools, a `make` target or a delivery script, and the commands
the team's procedure writes itself.

It is a barrier against accidents and against an instruction slipped into a ticket or a commit, not a
sandbox: a script that deploys, run by its name, passes, as does a command assembled from variables. What
really protects a production system is the agent's permissions and the forge's protection. This module
imports nothing from the rest of the plugin: a hook must start fast and not fall with it."""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from typing import Any

MAX_COMMAND = 20_000        # beyond this, the command is judged on its text, without being split
MAX_STDIN = 5_000_000
MAX_DEPTH = 4
MAX_WORK = 300              # nested commands examined, at most: beyond this we refuse rather than spin
GIT_TIMEOUT = 3             # seconds: the whole hook must answer before its own timeout
ALLOW_ENV = "AI_SDLC_ALLOW_AGENT_DELIVERY"   # set by the team in the session's environment, never by the agent
ALLOW_ENV_ALIASES = (ALLOW_ENV, "AI_SDLC_LIVRAISON_PAR_AGENT")   # the former name is still read
# the team's delivery procedure, under its English name and its former French name: both are read
PROCEDURES = ("docs/agents/delivery.md", "docs/agents/livraison.md")

_VERB = re.compile(r"^(?:deploy\w*|release[sd]?|publish\w*|livr\w+|ship(?:it|ping)?|rollout|promote\w*|revenir|rollback|golive|go-live)$", re.IGNORECASE)
_BENIGN = re.compile(r"^(?:notes?|docs?|check\w*|tests?|lint|preview|dry|dryrun|plan|diff|status|list|logs?|verify|validate)$", re.IGNORECASE)
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SPAN = re.compile(r"`([^`\n]{2,400})`")
_SPACES = {ord(ch): " " for ch in "               　\r"}
_WRAPPERS = {"sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T"}, "doas": {"-u", "-C"}, "nice": {"-n"}, "ionice": {"-c", "-n", "-p"},
             "exec": {"-a"}, "env": {"-u", "-C"}, "command": set(), "time": {"-f", "-o"}, "nohup": set(), "builtin": set(),
             "stdbuf": {"-i", "-o", "-e"}, "setsid": set(), "caffeinate": {"-t", "-w"}, "chronic": set(), "unbuffer": set()}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
_INTERPRETERS = {"python", "python3", "node", "perl", "ruby", "php", "deno", "bun"}
_OPERATORS = {"&&", "||", ";", "|", "&", "|&", ";;", "(", ")", "{", "}", "!", "then", "do", "else", "elif", "if", "while", "until", "done", "fi"}
_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}
_TAG_READ = {"-l", "--list", "-n", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--sort", "--format",
             "--column", "--no-column", "-v", "--verify", "-i", "--ignore-case", "--color", "--no-color"}
_TAG_WRITE = {"-a", "-s", "-u", "-f", "--force", "-d", "--delete", "-m", "-F", "--annotate", "--sign", "--file", "--message"}
_VERSION_REF = re.compile(r"v?\d+\.\d+(?:\.\d+)?[\w.+-]*|v\d+")
_VALUE_OPTS = {"-n", "--namespace", "--context", "--kubeconfig", "--kube-context", "--profile", "--region", "--project", "--subscription",
               "-g", "--resource-group", "--cwd", "--prefix", "-C", "--dir", "--filter", "-F", "-w", "--workspace", "-f", "--file",
               "--registry", "--config", "-c", "--cluster", "-p", "--values", "-chdir"}
_DEPLOY_REMOTES = {"heroku", "dokku", "production", "prod", "live"}
# tool → word sequences that send something out. They are read at the head of the command's words (options aside),
# except for the tools of _ANYWHERE, where the verb comes after a service name (`gcloud run deploy`).
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
    "sls": [("deploy",), ("remove",)], "docker": [("push",), ("stack", "deploy"), ("service", "update"), ("compose", "push"),
                                                  ("buildx", "imagetools", "create")],
    "docker-compose": [("push",)], "podman": [("push",)], "skaffold": [("run",), ("deploy",)],
    "argocd": [("app", "sync"), ("app", "rollback"), ("app", "set")], "flux": [("reconcile",)],
    "npm": [("publish",), ("unpublish",), ("deprecate",), ("dist-tag", "add"), ("dist-tag", "rm")], "pnpm": [("publish",)],
    "yarn": [("publish",), ("npm", "publish")], "bun": [("publish",)], "lerna": [("publish",)], "twine": [("upload",)],
    "poetry": [("publish",)], "uv": [("publish",)], "flit": [("publish",)], "hatch": [("publish",)], "cargo": [("publish",), ("yank",)],
    "gem": [("push",), ("yank",)], "mvn": [("deploy",), ("release:perform",)], "gradle": [("publish",)], "gradlew": [("publish",)],
    "dotnet": [("nuget", "push")], "nuget": [("push",)], "goreleaser": [("release",)], "semantic-release": [()], "release-it": [()],
    "standard-version": [()], "np": [()], "changeset": [("publish",)], "vercel": [("deploy",), ("promote",)],
    "netlify": [("deploy",)], "fly": [("deploy",)], "flyctl": [("deploy",)],
    "heroku": [("container:release",), ("releases:rollback",), ("pipelines:promote",)], "firebase": [("deploy",)],
    "wrangler": [("deploy",), ("publish",)], "railway": [("up",)], "cap": [("deploy",)], "ansible-playbook": [()], "fab": [("deploy",)],
    "eb": [("deploy",)], "copilot": [("deploy",)], "prisma": [("migrate", "deploy")], "gcloud": [("deploy",), ("rollouts",)],
    "aws": [("deploy", "create-deployment"), ("deploy", "push"), ("ecs", "update-service"), ("lambda", "update-function-code"),
            ("cloudformation", "deploy"), ("s3", "sync")],
    "az": [("deployment", "create"), ("webapp", "deploy"), ("functionapp", "deployment")],
    "setup.py": [("upload",)],
}
_ANYWHERE = {"gcloud", "az", "aws"}
_FLAGS = {"vercel": {"--prod"}, "docker": {"--push"}, "netlify": {"--prod"}}
_DRY = re.compile(r"^--dry-run(?:=(?!none$|false$).*)?$|^--snapshot$|^--plan-only$")
_RUNNERS = {"make", "gmake", "just", "task", "rake", "invoke", "nox", "tox"}
_SCRIPT_RUNNERS = {("npm", "run"), ("npm", "run-script"), ("pnpm", "run"), ("yarn", "run"), ("bun", "run"), ("composer", "run"), ("composer", "run-script")}
# "runs the rest as a command": after these words, the command starts again
_PASS = {("npx",), ("bunx",), ("pnpx",), ("npm", "exec"), ("npm", "x"), ("pnpm", "dlx"), ("pnpm", "exec"), ("yarn", "dlx"), ("yarn", "exec"),
         ("uv", "run"), ("uvx",), ("pipx", "run"), ("poetry", "run"), ("pipenv", "run"), ("bundle", "exec"), ("python", "-m"),
         ("python3", "-m"), ("python", "setup.py"), ("python3", "setup.py"), ("docker", "exec"), ("mise", "exec"), ("direnv", "exec")}
_CRUDE = re.compile(r"\bgit\b[^\n;&|]{0,200}\btag\s+(?!-l\b|--list\b|-n\b|--contains\b|--sort\b|--points-at\b)\S|\bpush\b[^\n;&|]{0,200}(?:--tags|\btag\s)|"
                    r"\bgh\s+(?:release|workflow)\s+(?:create|run)|\b(?:npm|pnpm|yarn|cargo|twine|poetry)\s+(?:publish|upload)\b|"
                    r"\b(?:kubectl|helm|terraform)\s+(?:apply|upgrade|install|destroy)\b|\bmake\s+(?:deploy|release|livr|publish)", re.IGNORECASE)
_HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_]\w*)\1")
_TO_SHELL = re.compile(r"(?:^|[|;&(\s])(?:sudo\s+)?(?:/[\w/.-]*/)?(?:sh|bash|zsh|dash|ksh)\b")


def _blank_quotes(line: str) -> str:
    """The line where what is between quotes is replaced by spaces: to look for a shell operator in it."""
    out, quote, escaped = [], "", False
    for ch in line:
        if escaped:
            escaped = False
            out.append(" ")
        elif ch == "\\" and quote != "'":
            escaped = True
            out.append(" ")
        elif quote:
            quote = "" if ch == quote else quote
            out.append(" ")
        elif ch in "'\"":
            quote = ch
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _blank_single(line: str) -> str:
    """The line where only what is between single quotes is blanked: between double quotes, a `$(…)` is still shell."""
    out, quote, in_double = [], False, False
    for ch in line:
        if quote:
            quote = ch != "'"
            out.append(" ")
        elif ch == "'" and not in_double:
            quote = True
            out.append(" ")
        else:
            in_double = (not in_double) if ch == '"' else in_double
            out.append(ch)
    return "".join(out)


def _heredoc_in(line: str) -> re.Match[str] | None:
    """The opening of a here-document on this line, if its `<<` is not in a single-quoted string."""
    visible = _blank_single(line)
    return next((m for m in _HEREDOC.finditer(line) if visible[m.start():m.start() + 2] == "<<"), None)


def _without_heredocs(command: str) -> tuple[str, list[str], list[str]]:
    """The command without the bodies of its here-documents, then the bodies given to a shell (they are commands),
    then the literal bodies (quoted delimiter: nothing is executed there). A `<<` opens a here-document only
    outside quotes, outside `<<<`, and if the line that closes it exists: otherwise it is a bit shift."""
    lines = command.split("\n")
    kept, to_shell, literal, index = [], [], [], 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        found = _heredoc_in(line)
        index += 1
        if not found:
            continue
        quoted = bool(found[1])
        end = next((i for i in range(index, len(lines)) if lines[i].strip() == found[2]), None)
        if end is None:
            continue
        body = "\n".join(lines[index:end])
        if _TO_SHELL.search(_blank_quotes(line)):
            to_shell.append(body)
        elif quoted:
            literal.append(body)
        else:
            kept.append(body)   # an unprotected body: the shell expands $(…) in it; it is still read as text of the command
            kept.append(found[2])
        index = end + 1
    return "\n".join(kept), to_shell, literal


def _join_lines(command: str) -> str:
    """A newline outside quotes becomes a ";"."""
    out, quote, escaped, line = [], "", False, ""
    for ch in command + "\n":
        if ch == "\n" and not quote:
            out.append(line)
            line, escaped = "", False
            continue
        line += ch
        if escaped:
            escaped = False
        elif ch == "\\" and quote != "'":
            escaped = True
        elif quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
    if line:
        out.append(line)   # a quote never closed: the rest is judged as is
    return " ; ".join(part for part in out if part.strip())


def _executed_inside(command: str) -> list[str]:
    """What a shell would execute inside the words: `$(…)` and backticks, outside single quotes
    (where nothing runs: a commit message may quote a command)."""
    out, quote, escaped, visible = [], "", False, []
    for ch in command:
        if escaped:
            escaped = False
            visible.append(ch if quote != "'" else " ")
        elif ch == "\\" and quote != "'":
            escaped = True
            visible.append(" ")
        elif quote == "'":
            quote = "" if ch == "'" else quote
            visible.append(" ")
        elif ch == "'" and not quote:
            quote = "'"
            visible.append(" ")
        else:
            if ch == '"':
                quote = "" if quote == '"' else '"'
            visible.append(ch)
    text = "".join(visible)
    out += re.findall(r"\$\(([^()]{1,2000})\)", text) + re.findall(r"`([^`]{1,2000})`", text) + re.findall(r"<\(([^()]{1,2000})\)", text)
    return out


def _segments(command: str) -> list[tuple[list[str], list[str]]]:
    """The simple commands of a shell line: (words, texts given by `<<<`). Redirections are removed with their
    target. Raises ValueError if the line cannot be split."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    out: list[tuple[list[str], list[str]]] = []
    words: list[str] = []
    fed: list[str] = []
    skip = ""
    for token in lexer:
        if skip:
            if skip == "<<<":
                fed.append(token)
            skip = ""
            continue
        if token and set(token) <= set("<>&|;()"):
            if "<" in token or ">" in token:           # a redirection: neither a command nor a separator
                if words and words[-1].isdigit():
                    words.pop()
                skip = token if not token.endswith("&") else ""
                if token.endswith("&"):
                    skip = "&"                         # `2>&1`: the descriptor that follows is not a word
                continue
            if words or fed:
                out.append((words, fed))
            words, fed = [], []
        elif token in _OPERATORS:
            if words or fed:
                out.append((words, fed))
            words, fed = [], []
        else:
            words.append(token)
    return out + ([(words, fed)] if words or fed else [])


def _strip(argv: list[str]) -> list[str]:
    """The command without what wraps it: assignments, sudo, env, nice… and their options that take a value."""
    while argv:
        word = argv[0]
        name = word.rsplit("/", 1)[-1].lstrip("\\")
        if _ASSIGN.match(word):
            argv = argv[1:]
        elif name in _WRAPPERS:
            valued, argv = _WRAPPERS[name], argv[1:]
            while argv and (argv[0].startswith("-") or _ASSIGN.match(argv[0])):
                argv = argv[2:] if argv[0] in valued else argv[1:]
        else:
            break
    return argv


def _positional(args: list[str]) -> list[str]:
    """The words of a command, without options and without the value of the options that take one."""
    out, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg.startswith("-"):
            skip = arg in _VALUE_OPTS
        else:
            out.append(arg)
    return out


def _delivery_name(name: str) -> bool:
    """A target or script name that is a delivery: one of its segments is a delivery verb, and none says it is
    something else (`release-notes`, `deploy-preview`, `test:release`)."""
    parts = [p for p in re.split(r"[-_:./]", name) if p]
    return any(_VERB.match(p) for p in parts) and not any(_BENIGN.match(p) for p in parts)


def _git(argv: list[str], tags: set[str]) -> str | None:
    rest = argv[1:]
    while rest and rest[0].startswith("-"):
        if rest[0] == "-c" and len(rest) > 1 and rest[1].lower().startswith("alias."):
            return "a git alias defined on the fly can hide a delivery"
        rest = rest[2:] if rest[0] in _GIT_VALUE_OPTS else rest[1:]
    if not rest:
        return None
    sub, args = rest[0], rest[1:]
    if sub == "tag":
        names = [a for a in args if not a.startswith("-")]
        flags = {a.split("=")[0] for a in args if a.startswith("-")}
        if flags & _TAG_WRITE or (names and not flags & _TAG_READ):
            return "a git tag is created, moved or deleted"
    if sub == "push":
        if any(a in ("--tags", "--follow-tags", "--mirror") or "refs/tags" in a for a in args):
            return "tags are pushed"
        words = [a for a in args if not a.startswith("-")]
        if any(a.startswith("--repo=") for a in args):
            words = ["", *words]
        remote, refs = (words[0] if words else ""), words[1:]
        if "tag" in refs:
            return "a tag is pushed"
        if remote.lower() in _DEPLOY_REMOTES:
            return f"pushing to `{remote[:30]}` triggers a deployment"
        for ref in refs:
            for side in ref.lstrip("+").split(":"):
                side = side.split("^")[0]
                if side and (side in tags or _VERSION_REF.fullmatch(side)):
                    return "a version tag is pushed or deleted remotely"
    if sub == "update-ref" and any("refs/tags" in a for a in args):
        return "a git tag is written"
    if sub == "config" and any(a.lower().startswith("alias.") for a in args) and re.search(r"\b(?:tag|push)\b|!", " ".join(args)):
        return "a git alias can hide a delivery"
    return None


def _http(name: str, args: list[str]) -> str | None:
    joined = " ".join(args)
    if not re.search(r"/(?:releases|dispatches|deployments|git/(?:refs|tags))\b|hooks?/deploy|deploy[-_]?hooks?", joined):
        return None
    method = next((a[2:] or (args[i + 1] if i + 1 < len(args) else "") for i, a in enumerate(args) if a.startswith("-X")), "") \
        or next((a.split("=", 1)[1] if "=" in a else (args[i + 1] if i + 1 < len(args) else "")
                 for i, a in enumerate(args) if a.split("=")[0] in ("--request", "--method")), "")
    writes = any(a.split("=")[0] in ("-d", "--data", "--data-raw", "--data-binary", "--json", "-F", "--form", "-T", "--upload-file",
                                     "-f", "--field", "--raw-field", "--input") or a.startswith("--post-") for a in args)
    if method.upper() in ("POST", "PUT", "PATCH", "DELETE") or (writes and method.upper() != "GET"):
        return "a request writes a release, a tag or a trigger on the forge"
    return None


def _one(argv: list[str], team: list[list[str]], tags: set[str]) -> tuple[str | None, list[str]]:
    """Why this simple command delivers, or None; and the command it runs in turn, if there is one."""
    argv = _strip(argv)
    if not argv:
        return None, []
    name = argv[0].rsplit("/", 1)[-1].lstrip("\\")
    args = argv[1:]
    for known in team:
        if len(argv) >= len(known) and all(_team_word(want, got) for want, got in zip(known, [name, *args])):
            return "it is a command of the team's delivery procedure", []
    for prefix in _PASS:
        if (name, *args[:len(prefix) - 1]) == prefix:
            rest = args[len(prefix) - 1:]
            while rest and rest[0].startswith("-") and prefix[-1] not in ("-m", "setup.py"):
                rest = rest[2:] if rest[0] in ("-p", "--package", "-c", "--call", "--with", "--from", "-u", "-e", "-w") else rest[1:]
            if prefix[-1] == "setup.py":
                rest = ["setup.py", *rest]
            if prefix == ("docker", "exec"):
                rest = rest[1:]   # the container name
            return None, rest
    if name == "git":
        return _git(argv, tags), []
    if name in _TOOLS and not any(_DRY.match(a) for a in args):
        words = _positional(args)
        for wanted in _TOOLS[name]:
            if (name in _ANYWHERE and _subsequence(words, wanted)) or (name not in _ANYWHERE and tuple(words[:len(wanted)]) == wanted):
                return f"`{name}` publishes or deploys", []
        if _FLAGS.get(name, set()) & set(args):
            return f"`{name}` publishes or deploys", []
    if name == "gh" and args[:1] == ["api"] or name in ("curl", "wget", "http", "https", "xh"):
        return _http(name, args), []
    if name in _RUNNERS and not any(a in ("-n", "--dry-run", "--just-print", "--recon", "-q", "--question") for a in args):
        hit = next((a for a in _positional(args) if not _ASSIGN.match(a) and _delivery_name(a)), None)
        if hit:
            return f"the target `{hit[:40]}` of `{name}` is a delivery", []
    runs_script = (name, *args[:1]) in _SCRIPT_RUNNERS
    if runs_script or name in ("yarn", "pnpm", "bun"):
        words = _positional(args[1:] if runs_script else args)
        if words[:1] == ["workspace"]:
            words = words[2:]
        if words and _delivery_name(words[0]):
            return f"the script `{words[0][:40]}` is a delivery", []
    return None, []


def _team_word(want: str, got: str) -> bool:
    """A word of the team's command against a word of the examined command. What follows an opening angle bracket
    is a value to replace: `VERSION=<version>` recognises `VERSION=v2.0.0`."""
    fixed = want.split("<", 1)[0]
    want_name = fixed if "/" not in fixed or "<" in want else fixed.rsplit("/", 1)[-1]
    return got == want or got.rsplit("/", 1)[-1] == want.rsplit("/", 1)[-1] or ("<" in want and got.startswith(want_name) and len(got) >= len(want_name))


def _subsequence(words: list[str], wanted: tuple[str, ...]) -> bool:
    position = 0
    for word in wanted:
        try:
            position = words.index(word, position) + 1
        except ValueError:
            return False
    return True


def _nested(argv: list[str], fed: list[str]) -> tuple[list[str], list[str]]:
    """What the words of a command carry: shell lines (`sh -c "…"`, `eval`, `ssh host "…"`, `find -exec`, a text
    given to a shell by `<<<`), and code in another language (`python -c`), which is judged on its text."""
    stripped = _strip(argv)
    shell, code = [], []
    if not stripped:
        return shell, code
    name = stripped[0].rsplit("/", 1)[-1]
    if name in _SHELLS:
        shell += fed
        for index, word in enumerate(stripped[1:-1], 1):
            if word.startswith("-") and not word.startswith("--") and "c" in word:
                rest = [w for w in stripped[index + 1:] if w != "--"]
                shell += rest[:1]
    if name in ("eval", "xargs", "watch", "timeout", "ssh", "parallel", "su", "env", "flock", "retry"):
        # the carried command starts after options and values we do not know: each ending is tried
        shell += [shlex.join(stripped[start:]) for start in range(1, min(len(stripped), 8))]
        shell += stripped[1:]
    if name == "find":
        for index, word in enumerate(stripped):
            if word in ("-exec", "-execdir", "-ok", "-okdir"):
                end = next((i for i in range(index + 1, len(stripped)) if stripped[i] in (";", "+", "\\;")), len(stripped))
                shell.append(shlex.join(stripped[index + 1:end]))
    if name in _INTERPRETERS:
        for index, word in enumerate(stripped[1:-1], 1):
            if word in ("-c", "-e", "--eval", "-r", "-p", "--print"):
                code.append(stripped[index + 1])
    return shell, code


class _Budget:
    def __init__(self) -> None:
        self.left, self.seen = MAX_WORK, set()


def reasons(command: Any, team: list[str] | None = None, tags: set[str] | None = None, depth: int = 0,
            budget: _Budget | None = None) -> list[str]:
    """Why this command is refused; an empty list if it sends nothing known out."""
    if not isinstance(command, str) or not command.strip():
        return []
    budget = budget or _Budget()
    if command in budget.seen:
        return []
    budget.seen.add(command)
    budget.left -= 1
    if budget.left < 0:
        return ["the command nests too many commands to be read: it is not run"]
    command = command.translate(_SPACES)
    tags = tags or set()
    known = []
    for line in team or []:
        try:
            words = _strip(shlex.split(line))
        except ValueError:
            continue
        if len(words) >= 2:
            known.append([words[0].rsplit("/", 1)[-1], *words[1:]])
    found: list[str] = []
    text, to_shell, _literal = _without_heredocs(command)
    if len(text) > MAX_COMMAND:   # too long to be split: judged on its text, not refused outright
        return ["the command is very long and its text looks like a delivery"] if _CRUDE.search(text) else []
    executed = _executed_inside(text)
    inner = executed + to_shell if depth < MAX_DEPTH else []
    for piece in inner:
        found += reasons(piece, team, tags, depth + 1, budget)
    visible = _blank_single(text)
    if (_TO_SHELL.search(visible) or re.search(r"(?:^|[;&|\s])eval\s", visible)) and any(_CRUDE.search(piece) for piece in executed):
        found.append("a text produced by a command is given to a shell, and it looks like a delivery")
    try:
        segments = _segments(_join_lines(text.replace("\\\n", " ")))
    except ValueError:
        # a line shlex cannot split is judged on its text: better one refusal too many
        return found + (["the command cannot be split, and its text looks like a delivery"] if _CRUDE.search(text) else [])
    for argv, fed in segments:
        why, launched = _one(argv, known, tags)
        if why:
            found.append(why)
        if depth >= MAX_DEPTH:
            if _CRUDE.search(" ".join(argv)):
                found.append("a command nested too deep looks like a delivery")
            continue
        if launched:
            found += reasons(shlex.join(launched), team, tags, depth + 1, budget)
        shell, code = _nested(argv, fed)
        for piece in shell:
            found += reasons(piece, team, tags, depth + 1, budget)
        if any(_CRUDE.search(piece) for piece in code):
            found.append("code passed to an interpreter runs a delivery")
    return list(dict.fromkeys(found))


def render(found: list[str]) -> str:
    return ("ai-sdlc: command refused, " + "; ".join(found) + ".\n"
            "An agent does not tag, publish or deploy. Write the command in your proposal "
            "(`ship render`): a human runs it, in their terminal.\n")


def team_commands(procedure: str) -> list[str]:
    """The commands the team's procedure writes between backticks."""
    return list(dict.fromkeys(" ".join(m.split()) for m in _SPAN.findall(procedure) if " " in m.strip()))


def _git_out(repo: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", repo, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args],
                             capture_output=True, timeout=GIT_TIMEOUT, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else ""


def team_lines(repo: str) -> list[str]:
    """The commands of the team's procedure, read on the remote branch, in the last commit and in the working
    copy, under its English and its former French file name: removing the line from one's copy, or renaming the
    file, does not disarm the guardrail."""
    texts = [_git_out(repo, "show", f"{ref}:{path}")[:200_000] for path in PROCEDURES for ref in ("origin/HEAD", "HEAD")]
    for path in PROCEDURES:
        try:
            with open(os.path.join(repo, path), encoding="utf-8", errors="replace") as fh:
                texts.append(fh.read(200_000))
        except OSError:
            pass
    return list(dict.fromkeys(line for text in texts for line in team_commands(text)))


def tag_names(repo: str) -> set[str]:
    return set(_git_out(repo, "tag", "--list").split("\n")[:5000]) - {""}


def hook(payload: Any, team: list[str] | None = None, tags: set[str] | None = None) -> tuple[int, str]:
    """The answer to a PreToolUse hook call: (exit code, message). 2 refuses the call, 0 lets it through."""
    if not isinstance(payload, dict):
        return 0, ""
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if payload.get("tool_name") != "Bash" or not isinstance(command, str):
        return 0, ""
    found = reasons(command, team, tags)
    return (2, render(found)) if found else (0, "")


def run_hook(raw: str, environ: dict[str, str]) -> tuple[int, str]:
    """The hook end to end. It does not crash: an input that is not a tool call lets through, but an unreadable
    or truncated input, or an internal error, is judged on its text rather than opening the door."""
    if any(environ.get(name) == "1" for name in ALLOW_ENV_ALIASES):
        return 0, ""
    fallback = (2, render(["the call could not be read and its text looks like a delivery"])) if _CRUDE.search(raw[:MAX_STDIN]) else (0, "")
    try:
        payload = json.loads(raw)
    except (ValueError, RecursionError):
        return fallback
    try:
        repo = environ.get("CLAUDE_PROJECT_DIR") or (payload.get("cwd") if isinstance(payload, dict) else None) or "."
        known = isinstance(repo, str) and "\0" not in repo and os.path.isdir(repo)
        return hook(payload, team_lines(repo) if known else None, tag_names(repo) if known else None)
    except Exception:   # noqa: BLE001 — a guardrail that crashes would let everything through: fall back, do not raise
        return fallback
