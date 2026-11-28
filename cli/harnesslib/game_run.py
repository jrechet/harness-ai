#!/usr/bin/env python3
"""The judge of a game's development loop: runs a piece of the loop and says whether it passed.

The commands are the ones the owner recorded with `harness game command`, in `.harness/config.json`
under `game.commands`. A run passes when, all at once:
  - it ends before its timeout, with exit code 0;
  - no line of its output matches one of its error patterns (some engines exit 0 on a script error);
  - its ready pattern, when one is recorded, appears in its output (the game printed it once started);
  - its output file, when one is recorded, exists, is not empty and was written by this run.

  python3 .harness/game_loop.py smoke        one piece: check, test, smoke, capture or export
  python3 .harness/game_loop.py all          every recorded piece, in the loop's order
  python3 .harness/game_loop.py --list       the recorded pieces and their commands

This file is copied by `harness game runner --write` from harness-ai (cli/harnesslib/game_run.py) and
is not to be edited by hand: `harness game loop` says when the copy is older than the plugin's.
It runs the recorded commands through the shell, like a Makefile: they are the repository's own.
Python 3.8 or later, standard library only.
Exit codes: 0 passed, 1 failed, 2 nothing to run or invalid config."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

ORDER = ("check", "test", "smoke", "capture", "export")
NOT_JUDGED = {"run": "`run` starts the game for a person: it opens a window or a server, the judge never runs it"}
DEFAULT_TIMEOUT = 300
TAIL = 30


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
    return commands if isinstance(commands, dict) else {}


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


ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=\S*")
NOT_FOUND = re.compile(r"(?:command not found|not found|No such file or directory)")


def _missing_program(command: str, code, lines: list) -> str | None:
    """The first program of the command when the shell could not find it (exit code 127)."""
    if code != 127:
        return None
    words = [w for w in command.split() if not ASSIGNMENT.fullmatch(w)]
    first = words[0] if words else command
    return first if any(NOT_FOUND.search(line) for line in lines) or not lines else None


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


def judge(piece: str, spec: dict, root: str, timeout: int | None = None) -> dict:
    """Runs one recorded command and returns the verdict: `passed`, the reasons it failed, the notes,
    the lines that matched an error pattern and the last lines of the output."""
    command = spec.get("run")
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f"the piece {piece} has no command (`harness game command {piece} \"…\"` records one)")
    errors, ready = _patterns(spec, "errors"), _patterns(spec, "ready")
    limit = timeout or int(spec.get("timeout") or DEFAULT_TIMEOUT)
    output = spec.get("output")
    target = os.path.join(root, output) if isinstance(output, str) and output else None
    started = time.time()
    failed, notes = [], []
    try:
        proc = subprocess.run(command, shell=True, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=limit, check=False)
        text, code = proc.stdout.decode("utf-8", "replace"), proc.returncode
    except subprocess.TimeoutExpired as exc:
        text = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        code = None
        failed.append(f"did not finish in {limit} s (a smoke run must quit by itself: give it a frame count)")
    lines = text.splitlines()
    if code not in (None, 0):
        failed.append(f"exit code {code}")
    hits = [line for line in lines if any(p.search(line) for p in errors)]
    if hits:
        failed.append(f"{len(hits)} error line(s) in the output, whatever the exit code")
    if ready and not any(p.search(line) for line in lines for p in ready):
        failed.append("the ready line never appeared: the game did not start, or does not print it")
    if target is not None:
        if not os.path.isfile(target) or os.path.getsize(target) == 0:
            failed.append(f"{output} was not written")
        elif os.path.getmtime(target) + 1 < started:
            failed.append(f"{output} is older than this run: it was not written by it")
        else:
            failed += _output_failures(target, output, _patterns(spec, "output_errors"))
    missing = _missing_program(command, code, lines)
    if missing:
        failed.insert(0, f"{missing} was not found: install it, or record the full path of the binary")
    if spec.get("exit_code_trusted") is False and not ready:
        message = ("this engine exits 0 on many errors and no ready line is recorded "
                   f"(`harness game command {piece} \"…\" --ready \"<line the game prints once started>\"`)")
        if piece == "smoke":
            failed.append("a pass would prove nothing: " + message)
        else:
            notes.append("a pass proves less: " + message)
    if piece == "capture" and target is not None and not failed:
        notes.append(f"open {output} and look at it before saying the change is done")
    return {"piece": piece, "command": command, "passed": not failed, "failed": failed, "notes": notes,
            "error_lines": hits[:10], "tail": lines[-TAIL:], "exit_code": code,
            "seconds": round(time.time() - started, 1), "output": output}


def render(verdict: dict) -> str:
    head = "PASS" if verdict["passed"] else "FAIL"
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


def run(piece: str, root: str, timeout: int | None = None, stream=None) -> int:
    stream = stream or sys.stdout
    try:
        commands = load_commands(root)
        pieces = selected(commands, piece)
        verdicts = []
        for name in pieces:
            verdict = judge(name, commands[name], root, timeout)
            verdicts.append(verdict)
            stream.write(render(verdict) + "\n")
    except ValueError as exc:
        print(f"game loop: {exc}", file=sys.stderr)
        return 2
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
