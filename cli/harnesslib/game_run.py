#!/usr/bin/env python3
"""The judge of a game's development loop: runs a piece of the loop and says whether it passed.

The commands are the ones the owner recorded with `harness game command`, in `.harness/config.json`
under `game.commands`. A run passes when, all at once:
  - its words do not publish (itch.io, Steam, a store, a package registry, a site, git push or tag);
  - it ends before its timeout, with exit code 0, every command of a pipe included where the shell
    knows pipefail (bash does; without it, the verdict says pipes were not checked);
  - no line of its output matches one of its error patterns (some engines exit 0 on a script error);
  - its ready pattern, when one is recorded, appears in its output (the game printed it once started);
  - its output file, when one is recorded, is inside the repository, exists, is not empty, was written
    by this run, and reports none of its failure patterns.
On a timeout, the whole process group of the run is stopped, not only the shell.

  python3 .harness/game_loop.py smoke        one piece: check, test, smoke, capture or export
  python3 .harness/game_loop.py all          every recorded piece, in the loop's order
  python3 .harness/game_loop.py --list       the recorded pieces and their commands

Each verdict is written to `.harness/game_runs/<piece>.json` with a key of the exact spec it judged;
`harness game loop` counts a piece as in place only when that key matches the spec recorded today and
the run passed. The folder ignores itself in git: the verdicts are this machine's.
The publishing check guards the loop against publishing by mistake. It is not a barrier: it reads the
command's words, so a script whose name says nothing, or a command built at run time, is not seen.
This file is copied by `harness game runner --write` from harness-ai (cli/harnesslib/game_run.py) and
is not to be edited by hand: `harness game loop` says when the copy is older than the plugin's.
It runs the recorded commands through the shell, like a Makefile: they are the repository's own.
Python 3.8 or later, standard library only, POSIX shells.
Exit codes: 0 passed, 1 failed, 2 nothing to run or invalid config."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import date

ORDER = ("check", "test", "smoke", "capture", "export")
NOT_JUDGED = {"run": "`run` starts the game for a person: it opens a window or a server, the judge never runs it"}
DEFAULT_TIMEOUT = 300
TAIL = 30
GRACE = 3
RESULTS = "game_runs"      # under .harness/: one file per piece; the folder ignores itself
PUBLISH_WHY = ("publishing the game (itch.io, Steam, a store, a package registry, a site, git push or tag) "
               "is the owner's release, not a piece of the loop")

# --- reading a shell line ----------------------------------------------------------------------------

ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
SEPARATOR = re.compile(r"[();|&]+")             # a token made of these alone ends a simple command
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w-]*)\1")
KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "{", "}", "!", "time", "case", "esac"}
LOOP_HEADS = {"for", "select", "case", "function"}


def _words(text: str) -> list:
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def _logical_lines(command: str) -> list:
    """The command's lines as the shell reads them: `\\` + newline joined, heredoc bodies left out."""
    lines, body_end = [], None
    for line in re.sub(r"\\\n", " ", command or "").splitlines():
        if body_end is not None:
            if line.strip() == body_end:
                body_end = None
            continue
        lines.append(line)
        match = HEREDOC.search(line)
        if match:
            body_end = match.group(2)
    return lines


def _tokens(line: str) -> list:
    try:
        lexer = shlex.shlex(line.replace("`", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        return list(lexer)
    except ValueError:
        return line.split()


def segments(command: str) -> list:
    """The simple commands of a shell line, each as its words: split at `&&`, `||`, `;`, `|`, `&`,
    parentheses and backticks outside quotes; a redirection and its target are left out (`2>&1`,
    `> build.log`, `<<EOF`), so `python3 -c "a; b"` stays one command and a log file is not one."""
    out = []
    for line in _logical_lines(command):
        current: list = []
        tokens = _tokens(line)
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if SEPARATOR.fullmatch(token):
                if current:
                    out.append(current)
                current = []
            elif "<" in token or ">" in token:
                if current and current[-1] in ("0", "1", "2"):
                    current.pop()                   # the fd of `2>`
                if token.endswith("("):            # process substitution `<(…)`: a command of its own
                    if current:
                        out.append(current)
                    current = []
                else:
                    i += 1                          # the target of the redirection
            else:
                current.append(token)
            i += 1
        if current:
            out.append(current)
    return [words for words in out if words]


# --- the publishing check: the words of each simple command --------------------------------------------

WRAPPERS = {  # programs that run another one; the options of theirs that take a value
    "sudo": {"-u", "-g", "-C", "-h", "-p", "-U"}, "doas": {"-u"}, "env": {"-u", "-C", "-S"}, "command": set(),
    "exec": {"-a"}, "nohup": set(), "nice": {"-n"}, "ionice": {"-c", "-n"}, "stdbuf": {"-i", "-o", "-e"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"}, "xargs": {"-I", "-n", "-P", "-d", "-L", "-s", "-E", "-a"},
    "xvfb-run": {"-n", "-s", "-f", "-e", "-p", "-w", "--server-num", "--server-args", "--auth-file", "--error-file"},
    "npx": {"-p", "--package"}, "bunx": set(), "pnpx": set(), "caffeinate": set(), "time": set(),
}
DURATION = re.compile(r"\d+(?:\.\d+)?[smhd]?")
RUNNERS = {"pnpm": {"dlx", "exec"}, "yarn": {"dlx", "exec"}, "npm": {"exec", "x"}, "bun": {"x"}}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
INTERPRETERS = SHELLS | {"node", "deno", "ruby", "perl", "php", "lua", "luajit"}
TASK_RUNNERS = {"make", "just", "task", "rake", "invoke", "nox", "tox"}
VALUE_FLAGS = {
    "git": {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"},
    "npm": {"-w", "--workspace", "--prefix", "-C"}, "pnpm": {"-F", "--filter", "-C", "--dir"}, "yarn": {"--cwd"},
    "bun": {"--cwd"}, "cargo": {"-p", "--package", "--manifest-path", "-Z", "--config", "--registry", "--token"},
    "gh": {"-R", "--repo"}, "docker": {"-H", "--host", "--context", "-c", "--config", "-l", "--log-level"},
    "podman": {"--url", "-c", "--connection"}, "aws": {"--profile", "--region", "--endpoint-url", "--output"},
    "butler": {"-i", "--identity", "--address", "--userversion", "--userversion-file"}, "gsutil": {"-o", "-h", "-u"},
}
PUBLISH_SUBCOMMANDS = {"npm": {"publish", "unpublish", "deprecate", "dist-tag"}, "pnpm": {"publish"},
                       "bun": {"publish"}, "cargo": {"publish", "yank", "owner"}, "twine": {"upload"},
                       "poetry": {"publish"}, "gem": {"push", "yank"}, "flyctl": {"deploy"}, "fly": {"deploy"},
                       "netlify": {"deploy"}, "netlify-cli": {"deploy"}, "firebase": {"deploy", "hosting:channel:deploy"},
                       "butler": {"push"}}
ALWAYS = {"gh-pages", "ghp-import"}
QUIET = {"vercel": {"dev", "build", "pull", "env", "link", "login", "logout", "whoami", "ls", "list", "inspect", "logs",
                    "help", "--version", "-v"},
         "surge": {"login", "logout", "whoami", "list", "--version", "help"}}
SCRIPT_PARTS = {"deploy", "publish", "upload"}   # a word of a script's name: `deploy-web.sh`, `npm run publish:itch`
SCRIPT_WHOLE = {"release", "ship"}               # the whole name only: `./release.sh`, not `build:release`
NOT_A_DELIVERY = {"test", "tests", "spec", "check", "mock", "fake", "dry", "notes", "lint"}
GIT_TAG_READS = {"-l", "--list", "--contains", "--no-contains", "--points-at", "--merged", "--no-merged", "-n",
                 "--sort", "--format", "-v", "--verify", "--column", "--no-column"}
GIT_TAG_WRITES = {"-a", "-s", "-d", "-f", "-m", "-F", "-u", "--delete", "--annotate", "--sign", "--force", "--message"}
REMOTE = re.compile(r"^(?:s3|gs|az|r2)://|^(?:[\w.-]+@)?[\w.-]+:(?!//)[^\s]*$")


def _program(words: list) -> tuple:
    """The program a simple command runs and its arguments, past assignments, shell keywords and wrappers
    (`timeout 60`, `sudo -u ci`, `npx`, `pnpm dlx`); `python3 -m twine` runs `twine`."""
    i = 0
    while i < len(words):
        word, name = words[i], os.path.basename(words[i])
        if ASSIGNMENT.fullmatch(word) or word in KEYWORDS:
            i += 1
            continue
        if name in WRAPPERS:
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 2 if words[i] in WRAPPERS[name] else 1
            if name == "timeout" and i < len(words) and DURATION.fullmatch(words[i]):
                i += 1
            continue
        if name in RUNNERS and i + 1 < len(words) and words[i + 1] in RUNNERS[name]:
            i += 2
            continue
        if re.fullmatch(r"python[\d.]*", name) and i + 2 < len(words) and words[i + 1] == "-m":
            return words[i + 2], words[i + 3:]
        return re.sub(r"@[^/]*$", "", name), words[i + 1:]      # `wrangler@3` is wrangler
    return "", []


def _positional(program: str, args: list) -> list:
    """The words that are not options, past the options of the program that take a value."""
    out, flags, skip = [], VALUE_FLAGS.get(program, set()), False
    for arg in args:
        if skip:
            skip = False
        elif arg in flags:
            skip = True
        elif not arg.startswith("-") and not (program == "cargo" and arg.startswith("+")):
            out.append(arg)
    return out


def _named_to_publish(name: str, separators: str = r"[-_.:/]") -> bool:
    stem = re.sub(r"\.(?:sh|py|js|mjs|cjs|ts|rb|pl|bash|zsh)$", "", os.path.basename(name or ""))
    parts = set(re.split(separators, stem.lower()))
    return stem.lower() in SCRIPT_WHOLE or bool(parts & SCRIPT_PARTS) and not parts & NOT_A_DELIVERY


def _dry_run(program: str, subs: list, args: list) -> bool:
    """A dry run, only where the tool honours its flag: never for a script, which decides for itself."""
    if program in ("npm", "pnpm", "yarn", "bun", "cargo", "wrangler", "butler", "twine") and "--dry-run" in args:
        return program not in ("npm", "pnpm", "yarn", "bun") or subs[:1] == ["publish"]
    if program == "git" and subs[:1] == ["push"]:
        return "--dry-run" in args or "-n" in args
    if program == "rsync":
        return "--dry-run" in args or any(re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", a) for a in args)
    return program == "aws" and "--dryrun" in args


def _remote_destination(subs: list) -> bool:
    return len(subs) >= 2 and REMOTE.search(subs[-1]) is not None


def _tool_publishes(program: str, subs: list, args: list) -> bool:
    first = subs[0] if subs else ""
    if program == "git":
        if first == "push":
            return True
        if first == "tag":
            return not any(a in GIT_TAG_READS or a.split("=")[0] in GIT_TAG_READS for a in args) and \
                (len(subs) > 1 or any(a in GIT_TAG_WRITES for a in args))
        return False
    if program in PUBLISH_SUBCOMMANDS and first in PUBLISH_SUBCOMMANDS[program]:
        return True
    if program == "yarn":
        return first == "publish" or subs[:2] in (["npm", "publish"], ["npm", "tag"])
    if program in ("docker", "podman"):
        return first == "push" or subs[:2] == ["image", "push"] or (first in ("build", "buildx") and "--push" in args)
    if program == "gh":
        return subs[:2] in (["release", "create"], ["release", "upload"], ["release", "edit"], ["release", "delete"],
                            ["workflow", "run"])
    if program == "wrangler":
        return first in ("deploy", "publish") or subs[:2] in (["pages", "deploy"], ["pages", "publish"])
    if program in QUIET:
        return first not in QUIET[program]
    if program == "steamcmd":
        return any(a.lower() in ("+run_app_build", "+run_app_build_http", "+workshop_build_item") for a in args)
    if program == "aws":
        return (subs[:2] in (["s3", "cp"], ["s3", "sync"], ["s3", "mv"]) and _remote_destination(subs[2:])) or \
            subs[:2] == ["s3api", "put-object"]
    if program == "gsutil":
        return first in ("cp", "rsync", "mv") and _remote_destination(subs[1:])
    if program == "gcloud":
        return subs[:2] in (["storage", "cp"], ["storage", "rsync"], ["storage", "mv"]) and _remote_destination(subs[2:]) \
            or subs[:2] == ["app", "deploy"]
    if program in ("rsync", "scp"):
        return _remote_destination(subs)
    if program == "rclone":
        return first in ("copy", "sync", "move", "copyto", "moveto") and _remote_destination(subs[1:])
    return False


def _segment_publishes(words: list, depth: int = 0) -> bool:
    if not words or words[0] in LOOP_HEADS:
        return False
    program, args = _program(words)
    if not program:
        return False
    subs = _positional(program, args)
    if program in SHELLS and "-c" in args and depth < 3:
        script = args[args.index("-c") + 1] if args.index("-c") + 1 < len(args) else ""
        return publishing(script, depth + 1) is not None
    if _dry_run(program, subs, args):
        return False
    if program in ALWAYS or _named_to_publish(program):
        return True
    if (program in INTERPRETERS or re.fullmatch(r"python[\d.]*", program)) and subs and _named_to_publish(subs[0]):
        return True
    if program in TASK_RUNNERS and subs and _named_to_publish(subs[0]):
        return True
    if program in ("npm", "pnpm", "yarn", "bun") and subs[:1] in (["run"], ["run-script"]) and len(subs) > 1 \
            and _named_to_publish(subs[1]):
        return True
    if program in ("pnpm", "yarn", "bun") and subs and subs[0] != "publish" and _named_to_publish(subs[0]):
        return True                                   # `yarn deploy` runs the script `deploy`
    return _tool_publishes(program, subs, args)


def publishing(command: str, depth: int = 0) -> str | None:
    """The simple command of the line that publishes, as its words, or None."""
    for words in segments(command):
        if _segment_publishes(words, depth):
            return " ".join(words)
    return None


# --- running and judging ---------------------------------------------------------------------------

BUILTINS = {"cd", "echo", "printf", "export", "set", "unset", "true", "false", "test", "[", "exit", ":", "source",
            ".", "read", "wait", "kill", "eval", "exec", "command", "type", "shift", "trap", "umask", "ulimit", "pwd",
            "pushd", "popd", "local", "return", "alias", "hash"}


def missing_programs(command: str, root: str) -> list:
    """The programs of the command the shell could not have found, looked up the way it does, whatever the
    language of its messages: not a builtin, not on the PATH, not a path that exists from the folder a
    `cd` of the line moved to. Asked only when the shell said so (exit code 126 or 127)."""
    out, here = [], root
    defined = set(re.findall(r"(?:^|[\s;&|{(])([A-Za-z_][\w-]*)\s*\(\s*\)", command or ""))   # `f() { …; }`
    for words in segments(command):
        if words[0] in LOOP_HEADS:
            continue
        words = [w for w in words if not ASSIGNMENT.fullmatch(w) and w not in KEYWORDS]
        while words and os.path.basename(words[0]) in WRAPPERS and words[0] not in ("npx", "bunx", "pnpx"):
            name, words = os.path.basename(words[0]), words[1:]
            while words and words[0].startswith("-"):
                words = words[2:] if words[0] in WRAPPERS[name] else words[1:]
            if name == "timeout" and words and DURATION.fullmatch(words[0]):
                words = words[1:]
        if not words:
            continue
        word = words[0]
        if word == "cd":
            here = os.path.join(here, words[1]) if len(words) > 1 and not os.path.isabs(words[1]) else \
                (words[1] if len(words) > 1 else here)
            continue
        if word in BUILTINS or word in defined or word.endswith("()"):
            continue
        found = os.path.exists(os.path.join(here, word)) if "/" in word else shutil.which(word) is not None
        if not found and word not in out:
            out.append(word)
    return out


def repo_root() -> str:
    """The repository is the folder above `.harness/`, where this file lives once copied."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here) if os.path.basename(here) == ".harness" else os.getcwd()


def load_commands(root: str) -> dict:
    path = os.path.join(root, ".harness", "config.json")
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    game = config.get("game") if isinstance(config, dict) else None
    commands = game.get("commands") if isinstance(game, dict) else None
    return {k: v for k, v in commands.items() if isinstance(v, dict)} if isinstance(commands, dict) else {}


def spec_key(spec: dict) -> str:
    """The key of the exact spec a run judged: a verdict counts only for the spec recorded today."""
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _patterns(spec: dict, key: str) -> list:
    raw = spec.get(key) or []
    raw = [raw] if isinstance(raw, str) else raw
    out = []
    for item in raw:
        try:
            out.append(re.compile(str(item)))
        except re.error as exc:
            raise ValueError(f"the pattern {item!r} is not a valid regular expression: {exc}") from exc
    return out


def inside(root: str, rel: str) -> str | None:
    """The absolute path of `rel` when it stays inside the repository, else None."""
    if not rel or os.path.isabs(rel):
        return None
    full = os.path.realpath(os.path.join(root, rel))
    base = os.path.realpath(root)
    return full if full == base or full.startswith(base + os.sep) else None


_SH_PIPEFAIL = {}


def _shell(command: str) -> tuple:
    """The shell and whether it checks every command of a pipe: bash with pipefail when there is one,
    otherwise sh, with pipefail when that sh knows it."""
    bash = shutil.which("bash")
    if bash:
        return [bash, "-c", "set -o pipefail; " + command], True
    if "sh" not in _SH_PIPEFAIL:
        probe = subprocess.run(["/bin/sh", "-c", "set -o pipefail"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
        _SH_PIPEFAIL["sh"] = probe.returncode == 0
    if _SH_PIPEFAIL["sh"]:
        return ["/bin/sh", "-c", "set -o pipefail; " + command], True
    return ["/bin/sh", "-c", command], False


def _execute(command: str, root: str, limit: int) -> tuple:
    """Runs the command in its own process group, its output in a file: (text, exit code or None,
    whether pipes were checked)."""
    argv, pipefail = _shell(command)
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen(argv, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            code = None
        _stop_group(proc)
        log.seek(0)
        return log.read().decode("utf-8", "replace"), code, pipefail


def _stop_group(proc: subprocess.Popen) -> None:
    """Whatever the run left behind in its group (an engine, a server) is stopped, then killed."""
    if not hasattr(os, "killpg"):
        if proc.poll() is None:
            proc.kill()
        return
    for sig, wait in ((signal.SIGTERM, GRACE), (signal.SIGKILL, 0)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            break
        deadline = time.time() + wait
        while time.time() < deadline:
            try:
                os.killpg(proc.pid, 0)
            except (ProcessLookupError, PermissionError):
                break
            time.sleep(0.05)
    if proc.poll() is None:
        proc.wait()


def _output_failures(target: str, output: str, patterns: list) -> list:
    """A results file that reports failures (Unity's test results) fails the run whatever its exit code."""
    if not patterns:
        return []
    try:
        with open(target, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return [f"{output} could not be read: {exc}"]
    hit = next((p.pattern for p in patterns if p.search(text)), None)
    return [f"{output} reports failures ({hit})"] if hit else []


def _check_output(root: str, output, patterns: list, before) -> list:
    if not isinstance(output, str) or not output:
        return []
    target = inside(root, output)
    if target is None:
        return [f"{output} is outside the repository: record an output inside it"]
    if not os.path.isfile(target) or os.path.getsize(target) == 0:
        return [f"{output} was not written"]
    if before is not None and os.path.getmtime(target) <= before:
        return [f"{output} is older than this run: it was not written by it"]
    return _output_failures(target, output, patterns)


def judge(piece: str, spec: dict, root: str, timeout: int | None = None) -> dict:
    """Runs one recorded command and returns the verdict: `passed`, the reasons it failed, the notes,
    the lines that matched an error pattern and the last lines of the output."""
    command = spec.get("run")
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f"the piece {piece} has no command (`harness game command {piece} \"…\"` records one)")
    errors, ready = _patterns(spec, "errors"), _patterns(spec, "ready")
    output_errors = _patterns(spec, "output_errors")
    limit = timeout or int(spec.get("timeout") or DEFAULT_TIMEOUT)
    output = spec.get("output")
    started = time.time()
    base = {"piece": piece, "command": command, "error_lines": [], "tail": [], "exit_code": None, "output": output,
            "spec": spec_key(spec)}
    published = publishing(command)
    if published:
        return {**base, "passed": False, "failed": [f"refused, not run: `{published}`: {PUBLISH_WHY}"], "notes": [],
                "seconds": 0.0, "refused": True}
    target = inside(root, output) if isinstance(output, str) and output else None
    before = os.path.getmtime(target) if target and os.path.isfile(target) else None
    text, code, pipefail = _execute(command, root, limit)
    lines = text.splitlines()
    failed, notes = [], []
    if code is None:
        failed.append(f"did not finish in {limit} s, and everything it started was stopped "
                      "(a smoke run must quit by itself: give it a frame count)")
    elif code != 0:
        failed.append(f"exit code {code}")
    if code in (126, 127):
        missing = missing_programs(command, root)
        failed.insert(0, (f"{', '.join(missing)} was not found" if missing else "a program was not found or could not run")
                      + ": install it, or record the full path of the binary")
    hits = [line for line in lines if any(p.search(line) for p in errors)]
    if hits:
        failed.append(f"{len(hits)} error line(s) in the output, whatever the exit code")
    if ready and not any(p.search(line) for line in lines for p in ready):
        failed.append("the ready line never appeared: the game did not start, or does not print it")
    failed += _check_output(root, output, output_errors, before)
    if spec.get("exit_code_trusted") is False and not ready:
        message = ("this engine exits 0 on many errors and no ready line is recorded "
                   f"(`harness game command {piece} \"…\" --ready \"<line the game prints once started>\"`)")
        if piece == "smoke":
            failed.append("a pass would prove nothing: " + message)
        else:
            notes.append("a pass proves less: " + message)
    if not pipefail and "|" in command:
        notes.append("this shell has no pipefail: a failure before a `|` was not checked")
    if piece == "capture" and output and not failed:
        notes.append(f"open {output} and look at it before saying the change is done")
    return {**base, "passed": not failed, "failed": failed, "notes": notes, "error_lines": hits[:10],
            "tail": lines[-TAIL:], "exit_code": code, "seconds": round(time.time() - started, 1)}


def render(verdict: dict) -> str:
    head = "PASS" if verdict["passed"] else ("REFUSED" if verdict.get("refused") else "FAIL")
    out = [f"{head} {verdict['piece']} ({verdict['seconds']} s): {verdict['command']}"]
    out += [f"  - {reason}" for reason in verdict["failed"]]
    if verdict["error_lines"]:
        out.append("  error lines:")
        out += [f"    {line}" for line in verdict["error_lines"]]
    if not verdict["passed"] and verdict["tail"]:
        out.append(f"  last {len(verdict['tail'])} lines:")
        out += [f"    {line}" for line in verdict["tail"]]
    out += [f"  note: {note}" for note in verdict["notes"]]
    return "\n".join(out)


def selected(commands: dict, piece: str) -> list:
    if piece in NOT_JUDGED:
        raise ValueError(NOT_JUDGED[piece])
    if piece == "all":
        chosen = [p for p in ORDER if isinstance(commands.get(p), dict)]
        if not chosen:
            raise ValueError("no piece of the loop is recorded yet (`harness game command <piece> \"…\"`)")
        return chosen
    if piece not in ORDER:
        raise ValueError(f"{piece} is not a piece the judge runs ({', '.join(ORDER)} or all)")
    if not isinstance(commands.get(piece), dict):
        raise ValueError(f"the piece {piece} is not recorded (`harness game command {piece} \"…\"`)")
    return [piece]


def _write_new(folder: str, name: str, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=f".{name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    umask = os.umask(0)
    os.umask(umask)
    os.chmod(tmp, 0o666 & ~umask)
    os.replace(tmp, os.path.join(folder, name))


def record_results(root: str, verdicts: list) -> None:
    """The last verdict of each piece, in a file of its own (two runs of different pieces never overwrite
    each other), with the key of the spec it judged. A file that cannot be written does not change the
    verdict: the run already said it."""
    harness = os.path.join(root, ".harness")
    folder = os.path.join(harness, RESULTS)
    if os.path.islink(harness) or os.path.islink(folder):
        print(f"game loop: {folder} is a symbolic link: the verdicts were not written", file=sys.stderr)
        return
    try:
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(os.path.join(folder, ".gitignore")):   # the verdicts are this machine's
            _write_new(folder, ".gitignore", "*\n")
        for v in verdicts:
            if os.path.islink(os.path.join(folder, f"{v['piece']}.json")):
                continue
            entry = {"piece": v["piece"], "command": v["command"], "spec": v["spec"], "passed": v["passed"],
                     "date": date.today().isoformat(), "seconds": v["seconds"]}
            _write_new(folder, f"{v['piece']}.json", json.dumps(entry, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"game loop: the verdicts were not written to {folder}: {exc}", file=sys.stderr)


def read_results(root: str) -> dict:
    """The last verdict of each piece, as `record_results` wrote it."""
    folder = os.path.join(root, ".harness", RESULTS)
    out = {}
    for piece in ORDER:
        try:
            with open(os.path.join(folder, f"{piece}.json"), encoding="utf-8") as fh:
                entry = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(entry, dict):
            out[piece] = entry
    return out


def run(piece: str, root: str, timeout: int | None = None, stream=None, commands: dict | None = None) -> int:
    stream = stream or sys.stdout
    try:
        commands = load_commands(root) if commands is None else commands
        pieces = selected(commands, piece)
        verdicts = []
        for name in pieces:
            verdict = judge(name, commands[name], root, timeout)
            verdicts.append(verdict)
            stream.write(render(verdict) + "\n")
    except ValueError as exc:
        print(f"game loop: {exc}", file=sys.stderr)
        return 2
    record_results(root, verdicts)
    if len(verdicts) > 1:
        passed = sum(1 for v in verdicts if v["passed"])
        stream.write(f"{passed} of {len(verdicts)} passed\n")
    return 0 if all(v["passed"] for v in verdicts) else 1


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="game_loop.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("piece", nargs="?", help="check, test, smoke, capture, export or all")
    parser.add_argument("--list", action="store_true", help="the recorded pieces and their commands")
    parser.add_argument("--timeout", type=int, help="seconds, overrides the recorded timeout")
    args = parser.parse_args(argv)
    root = repo_root()
    if args.list or not args.piece:
        try:
            commands = load_commands(root)
        except ValueError as exc:
            print(f"game loop: {exc}", file=sys.stderr)
            return 2
        recorded = [p for p in ("run",) + ORDER if isinstance(commands.get(p), dict)]
        if not recorded:
            print("No piece of the loop is recorded yet.")
        for name in recorded:
            print(f"{name}: {commands[name].get('run')}")
        return 0 if recorded or args.list else 2
    return run(args.piece, root, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
