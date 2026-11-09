"""Sous-commande `serve` : sert l'application de suivi (app/) en local et expose
l'état courant et l'historique du dépôt. Bibliothèque standard uniquement.

  GET /               l'application Vue (app/index.html, app/app.js, app/vendor/…)
  GET /api/state      l'état courant, recalculé à chaque appel (facts + maturity)
  GET /api/history    les states.json versionnés dans git, du plus ancien au plus
                      récent, suivis de l'état courant s'il diffère du dernier commit
"""
from __future__ import annotations

import argparse
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
    """Le résumé d'un état pour l'historique : assez pour tracer, pas tout le fichier."""
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

    def log_message(self, fmt, *args):  # silencieux : la sortie du serveur n'intéresse pas l'utilisateur
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
        except Exception as exc:  # noqa: BLE001 — l'erreur doit arriver à l'écran, pas tuer le serveur
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
    p.add_argument("repo", nargs="?", default=".", help="chemin du dépôt (défaut : .)")
    p.add_argument("--harness-dir", default=".harness")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--today", help="AAAA-MM-JJ, pour des sorties reproductibles")
    return p


def main(argv: list[str] | None = None, args: argparse.Namespace | None = None) -> int:
    if args is None:
        args = build_parser().parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else None
    server = make_server(args.repo, args.host, args.port, args.harness_dir, today)
    print(f"harness : {os.path.abspath(args.repo)}\nhttp://{args.host}:{server.server_address[1]}  (Ctrl-C pour arrêter)",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def serve_in_thread(repo: str, harness_dir: str = ".harness", today: date | None = None) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Pour les tests : serveur sur un port libre, dans un thread."""
    server = make_server(repo, "127.0.0.1", 0, harness_dir, today)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
