"""`serve` subcommand: serves the tracking app (app/) locally and exposes the
repository's current state and history. Standard library only.

  GET /               the Vue app (app/index.html, app/app.js, app/vendor/…)
  GET /api/state      the current state, recomputed on every call (facts + maturity)
  GET /api/history    the state.json files versioned in git, from oldest to newest,
                      followed by the current state if it differs from the last commit
"""
from __future__ import annotations

import argparse
import errno
import json
import mimetypes
import os
import subprocess
import sys
import threading
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import facts, maturity

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app")


def _git(repo: str, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True)
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def summarize(state: dict, sha: str | None = None, committed_at: str | None = None) -> dict[str, Any]:
    """The summary of a state for the history: enough to plot, not the whole file."""
    return {
        "sha": sha,
        "date": committed_at or state.get("date"),
        "level": state["level"]["reached"],
        "checks_passed": sum(l["passed_checks"] for l in state["levels"]),
        "checks_total": sum(l["total_checks"] for l in state["levels"]),
        "levels": [{"level": l["level"], "passed": l["passed_checks"], "total": l["total_checks"], "achieved": l["achieved"]}
                   for l in state["levels"] if l["level"]],
        "layers": state["layers"]["layers"],
        "layers_source": state["layers"]["source"],
        "health_score": state["layers"].get("health_score"),
    }


def current_state(repo: str, harness_dir: str, today: date | None = None) -> dict:
    return maturity.evaluate(facts.collect(repo, harness_dir, today=today))


def history(repo: str, harness_dir: str = ".harness", today: date | None = None) -> list[dict]:
    rel = f"{harness_dir}/state.json"
    entries: list[dict] = []
    log = _git(repo, "log", "--reverse", "--format=%H %cI", "--", rel)
    for line in (log or "").splitlines():
        sha, _, when = line.partition(" ")
        raw = _git(repo, "show", f"{sha}:{rel}")
        if not raw:
            continue
        try:
            entries.append(summarize(json.loads(raw), sha=sha, committed_at=when[:10]))
        except (json.JSONDecodeError, KeyError):
            continue
    now = summarize(current_state(repo, harness_dir, today))
    now["sha"] = None
    if not entries or (entries[-1]["checks_passed"], entries[-1]["level"]) != (now["checks_passed"], now["level"]):
        entries.append(now)
    return entries


class Handler(SimpleHTTPRequestHandler):
    repo: str = "."
    harness_dir: str = ".harness"
    today: date | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APP_DIR, **kwargs)

    def log_message(self, fmt, *args):  # silent: the server's output does not interest the user
        pass

    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/state":
                return self._json(current_state(self.repo, self.harness_dir, self.today))
            if path == "/api/history":
                return self._json(history(self.repo, self.harness_dir, self.today))
        except Exception as exc:  # noqa: BLE001 — the error must reach the screen, not kill the server
            return self._json({"error": str(exc)}, 500)
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()


def make_server(repo: str, host: str, port: int, harness_dir: str = ".harness", today: date | None = None) -> ThreadingHTTPServer:
    mimetypes.add_type("application/javascript", ".js")
    handler = type("BoundHandler", (Handler,), {"repo": os.path.abspath(repo), "harness_dir": harness_dir, "today": today})
    return ThreadingHTTPServer((host, port), handler)


def build_parser(parser: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    p = parser or argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", nargs="?", default=".", help="repository path (default: .)")
    p.add_argument("--harness-dir", default=".harness")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--today", help="YYYY-MM-DD, for reproducible outputs")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else None
    try:
        server = make_server(args.repo, args.host, args.port, args.harness_dir, today)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        print(f"harness serve: port {args.port} is taken: give --port <n>", file=sys.stderr)
        return 2
    print(f"harness: {os.path.abspath(args.repo)}\nhttp://{args.host}:{server.server_address[1]}  (Ctrl-C to stop)",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def serve_in_thread(repo: str, harness_dir: str = ".harness", today: date | None = None) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """For tests: server on a free port, in a thread."""
    server = make_server(repo, "127.0.0.1", 0, harness_dir, today)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
