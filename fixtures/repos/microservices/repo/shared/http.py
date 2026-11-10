"""Serves a service over HTTP with the standard library.

A service is an object with `handle(method, path, body) -> (status, payload)`. This
module only translates HTTP to that call and back, in JSON: no routing, no rule.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Protocol


class App(Protocol):
    def handle(self, method: str, path: str, body: Any = None) -> tuple[int, dict[str, Any]]: ...


def make_server(app: App, port: int, host: str = "127.0.0.1") -> HTTPServer:
    """An HTTP server for `app`, not started yet. Port 0 picks a free port."""

    class Handler(BaseHTTPRequestHandler):
        def _answer(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _dispatch(self) -> None:
            body = None
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                try:
                    body = json.loads(self.rfile.read(length))
                except ValueError:
                    self._answer(400, {"error": "invalid_json"})
                    return
            self._answer(*app.handle(self.command, self.path, body))

        do_GET = do_POST = _dispatch

        def log_message(self, *args: Any) -> None:
            pass

    return HTTPServer((host, port), Handler)


def serve(app: App, port: int) -> None:
    make_server(app, port, host="0.0.0.0").serve_forever()
