#!/usr/bin/env python3
"""The judge of a game's development loop: runs a piece of the loop and says whether it passed.

The commands are the ones the owner recorded with `harness game command`, in `.harness/config.json`
under `game.commands`. A run passes when, all at once:
  - it is not a publishing command (itch.io, Steam, a store, a package registry, a site, git push or tag);
  - it ends before its timeout, with exit code 0, every command of a pipe included;
  - no line of its output matches one of its error patterns (some engines exit 0 on a script error),
    and the shell did not report a program it could not find;
  - its ready pattern, when one is recorded, appears in its output (the game printed it once started);
  - its output file, when one is recorded, is inside the repository, exists, is not empty, was written
    by this run, and reports none of its failure patterns.
On a timeout, the whole process group of the run is stopped, not only the shell.

  python3 .harness/game_loop.py smoke        one piece: check, test, smoke, capture or export
  python3 .harness/game_loop.py all          every recorded piece, in the loop's order
  python3 .harness/game_loop.py --list       the recorded pieces and their commands

Each verdict is written to `.harness/game_runs/last.json`, which `harness game loop` reads: a piece counts
as in place only when the last judged run of its current command passed. The folder ignores itself in git:
the verdicts are this machine's.
This file is copied by `harness game runner --write` from harness-ai (cli/harnesslib/game_run.py) and
is not to be edited by hand: `harness game loop` says when the copy is older than the plugin's.
It runs the recorded commands through the shell, like a Makefile: they are the repository's own, and the
publishing check reads the command's words, not what a script it calls does.
Python 3.8 or later, standard library only, POSIX shells.
Exit codes: 0 passed, 1 failed, 2 nothing to run or invalid config."""
from __future__ import annotations

import argparse
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
RESULTS = "game_runs/last.json"      # under .harness/; the folder ignores itself
PUBLISH_WHY = "publishing the game (itch.io, Steam, a store, a package registry, a site, git push or tag) is the owner's release, not a piece of the loop"

# --- the publishing check: the words of the command, segment by segment ------------------------------

SEPARATORS = re.compile(r"&&|\|\||[;|&\n]|\$\(|`")
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
WRAPPERS = {"sudo", "env", "command", "exec", "time", "nohup", "nice", "xvfb-run", "npx", "bunx", "pnpx"}
RUNNERS = {"pnpm": {"dlx", "exec"}, "yarn": {"dlx", "exec"}, "npm": {"exec", "x"}, "bun": {"x"}}
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
PUBLISH_SUBCOMMANDS = {
    "git": {"push", "tag"}, "npm": {"publish", "unpublish", "deprecate"}, "pnpm": {"publish"},
    "yarn": {"publish", "npm"}, "bun": {"publish"}, "cargo": {"publish", "yank"}, "twine": {"upload"},
    "poetry": {"publish"}, "gem": {"push"}, "docker": {"push"}, "podman": {"push"}, "gh": {"release"},
    "firebase": {"deploy"}, "netlify": {"deploy"}, "netlify-cli": {"deploy"}, "wrangler": {"deploy", "publish", "pages"},
    "vercel": {"deploy", "--prod"}, "flyctl": {"deploy"}, "fly": {"deploy"}, "heroku": {"releases"},
}
ALWAYS = {"butler", "steamcmd", "surge", "gh-pages", "itch", "ghp-import"}
SCRIPT_PARTS = {"deploy", "publish", "upload"}       # a word of a script's name: `deploy-web.sh`, `npm run publish:itch`
SCRIPT_WHOLE = {"release", "ship"}                   # the whole name only: `./release.sh`, not `build:release`
REMOTE = re.compile(r"^(?:s3|gs|az)://|^(?:[\w.-]+@)?[\w.-]+:(?!//)")


def _words(segment: str) -> list:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


OPERATOR = re.compile(r"[();<>|&]+")


def segments(command: str) -> list:
    """The simple commands of a shell line, each as its words: split at `&&`, `||`, `;`, `|`, `&` and
    parentheses outside quotes, so `python3 -c "a; b"` stays one command."""
    out = []
    for line in (command or "").splitlines():
        try:
            lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            out += [_words(part) for part in SEPARATORS.split(line)]
            continue
        current: list = []
        for token in tokens:
            if OPERATOR.fullmatch(token):
                if current:
                    out.append(current)
                current = []
            else:
                current.append(token)
        if current:
            out.append(current)
    return [words for words in out if words]


def _program(words: list) -> tuple:
    """The program a segment runs and its arguments, past assignments and wrappers (`npx`, `env`…)."""
    i, wrapped = 0, False
    while i < len(words):
        word = words[i]
        name = os.path.basename(word)
        if ASSIGNMENT.fullmatch(word) or wrapped and word.startswith("-"):
            i += 1
        elif name in WRAPPERS:
            i, wrapped = i + 1, True
        elif name in RUNNERS and i + 1 < len(words) and words[i + 1] in RUNNERS[name]:
            i, wrapped = i + 2, True
        elif re.fullmatch(r"python[\d.]*", name) and i + 2 < len(words) and words[i + 1] == "-m":
            return words[i + 2], words[i + 3:]
        else:
            return name, words[i + 1:]
    return "", []


def _named_to_publish(name: str, separators: str) -> bool:
    stem = re.sub(r"\.(?:sh|py|js|mjs|bash)$", "", name)
    return stem in SCRIPT_WHOLE or any(part in SCRIPT_PARTS for part in re.split(separators, stem))


def _subcommands(program: str, args: list) -> list:
    """The words that are not options; for git, past its global options (`-C dir`, `--no-pager`)."""
    out, skip = [], False
    for arg in args:
        if skip:
            skip = False
            continue
        if program == "git" and arg in GIT_VALUE_FLAGS:
            skip = True
            continue
        if arg.startswith("-") and not (program == "vercel" and arg == "--prod"):
            continue
        out.append(arg)
    return out


def publishing(command: str) -> str | None:
    """The segment of the command that publishes, or None. A dry run publishes nothing."""
    for words in segments(command):
        segment = " ".join(words)
        if "--dry-run" in words or "-n" in words and os.path.basename(words[0]) == "rsync":
            continue
        program, args = _program(words)
        if any(os.path.basename(w) in ALWAYS for w in words) or _named_to_publish(program, r"[-_.]"):
            return segment.strip()
        subs = _subcommands(program, args)
        if program in PUBLISH_SUBCOMMANDS and (set(subs[:1]) | ({"--prod"} & set(args))) & PUBLISH_SUBCOMMANDS[program]:
            return segment.strip()
        if program in ("npm", "pnpm", "yarn", "bun") and subs[:1] == ["run"] and len(subs) > 1 and \
                _named_to_publish(subs[1], r"[-:_.]"):
            return segment.strip()
        if program == "gh" and subs[:2] == ["workflow", "run"]:
            return segment.strip()
        if program in ("aws", "gsutil", "rsync", "scp", "rclone") and any(REMOTE.search(a) for a in args):
            return segment.strip()
    return None


# --- running and judging ---------------------------------------------------------------------------

BUILTINS = {"cd", "echo", "printf", "export", "set", "unset", "true", "false", "test", "[", "exit", ":", "source",
            ".", "read", "wait", "kill", "eval", "exec", "command", "type", "shift", "trap", "umask", "ulimit", "pwd",
            "if", "then", "else", "fi", "for", "do", "done", "while", "case", "esac", "{", "}", "(", ")", "!", "time"}


def missing_programs(command: str, root: str) -> list:
    """The programs of the command that the shell cannot find, looked up the way it does, whatever the
    language of its messages: not a builtin, not on the PATH, not a path that exists."""
    out = []
    for words in segments(command):
        words = [w for w in words if not ASSIGNMENT.fullmatch(w)]
        while words and os.path.basename(words[0]) in WRAPPERS - {"npx", "bunx", "pnpx"}:
            words = words[1:]
            while words and words[0].startswith("-"):
                words = words[1:]
        if not words:
            continue
        word = words[0].strip("()")
        if not word or word in BUILTINS:
            continue
        found = os.path.exists(os.path.join(root, word)) if "/" in word else shutil.which(word) is not None
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


def _shell(command: str) -> list:
    """bash with pipefail when there is one, so a pipe does not hide a failure; sh otherwise."""
    bash = shutil.which("bash")
    return [bash, "-c", "set -o pipefail; " + command] if bash else ["/bin/sh", "-c", command]


def _execute(command: str, root: str, limit: int) -> tuple:
    """Runs the command in its own process group, its output in a file: (text, exit code or None)."""
    with tempfile.TemporaryFile() as log:
        proc = subprocess.Popen(_shell(command), cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            code = None
        _stop_group(proc)
        log.seek(0)
        return log.read().decode("utf-8", "replace"), code


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
    base = {"piece": piece, "command": command, "error_lines": [], "tail": [], "exit_code": None, "output": output}
    published = publishing(command)
    if published:
        return {**base, "passed": False, "failed": [f"refused, not run: `{published}`: {PUBLISH_WHY}"], "notes": [],
                "seconds": 0.0, "refused": True}
    target = inside(root, output) if isinstance(output, str) and output else None
    before = os.path.getmtime(target) if target and os.path.isfile(target) else None
    text, code = _execute(command, root, limit)
    lines = text.splitlines()
    failed, notes = [], []
    if code is None:
        failed.append(f"did not finish in {limit} s, and everything it started was stopped "
                      "(a smoke run must quit by itself: give it a frame count)")
    elif code != 0:
        failed.append(f"exit code {code}")
    missing = missing_programs(command, root) if code != 0 else []
    if missing:
        failed.insert(0, f"{', '.join(missing)} was not found: install it, or record the full path of the binary")
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


def record_results(root: str, verdicts: list) -> None:
    """The last verdict of each piece, with its command, for `harness game loop`. A file that cannot be
    written does not change the verdict: the run already said it."""
    path = os.path.join(root, ".harness", RESULTS)
    folder = os.path.dirname(path)
    if os.path.islink(os.path.join(root, ".harness")) or os.path.islink(folder) or os.path.islink(path):
        print(f"game loop: {folder} holds a symbolic link: the verdicts were not written", file=sys.stderr)
        return
    try:
        with open(path, encoding="utf-8") as fh:
            known = json.load(fh)
    except (OSError, ValueError):
        known = {}
    known = known if isinstance(known, dict) else {}
    for v in verdicts:
        known[v["piece"]] = {"command": v["command"], "passed": v["passed"], "date": date.today().isoformat(),
                             "seconds": v["seconds"]}
    try:
        os.makedirs(folder, exist_ok=True)
        ignore = os.path.join(folder, ".gitignore")
        if not os.path.exists(ignore):               # the verdicts are this machine's, not the repository's
            with open(ignore, "w", encoding="utf-8") as fh:
                fh.write("*\n")
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".last.")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(known, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError as exc:
        print(f"game loop: the verdicts were not written to {path}: {exc}", file=sys.stderr)


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
