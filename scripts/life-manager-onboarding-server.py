#!/usr/bin/env python3
"""Serve the local Life Manager onboarding and integration control surface."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
HTML = REPO / "apps" / "oss-onboarding" / "index.html"
GRAPH = REPO / "scripts" / "integration-onboarding.py"
CHILDREN: dict[str, subprocess.Popen[bytes]] = {}


def _json_command(command: list[str], timeout: int = 30) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, timeout=timeout, check=False,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    try:
        value = json.loads(lines[-1]) if lines else {}
    except json.JSONDecodeError:
        value = {"status": "issue", "error": "invalid structured output"}
    return completed.returncode, value


def _graph() -> dict[str, Any]:
    code, graph = _json_command([sys.executable, str(GRAPH), "graph"])
    if code != 0:
        raise RuntimeError("integration graph unavailable")
    for integration in graph["integrations"]:
        integration_id = integration["integration_id"]
        child = CHILDREN.get(integration_id)
        if child is not None and child.poll() is None:
            integration["state"] = "waiting"
            continue
        preflight_code, preflight = _json_command(integration["preflight"]["command"])
        if preflight_code != 0 or preflight.get("status") != "ready":
            integration["state"] = "needs_you"
            integration["next_action"] = "Prepare this Mac"
            continue
        readiness_code, readiness = _json_command(integration["readiness"]["command"])
        status = readiness.get("status")
        if readiness_code == 0 and status == "ready":
            integration["state"] = "ready"
            integration["next_action"] = None
        elif status in {"uninitialized", "needs_setup", "blocked"}:
            integration["state"] = "needs_you"
            integration["next_action"] = "Connect or resume official setup"
        else:
            integration["state"] = "issue"
            integration["next_action"] = "Open diagnostics"
        integration["readiness_state"] = status or "unknown"
    return graph


def _manifest(integration_id: str) -> dict[str, Any]:
    path = REPO / "integrations" / f"{integration_id}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("integration_id") != integration_id:
        raise ValueError("unknown integration")
    return value


def _connect(integration_id: str) -> dict[str, Any]:
    child = CHILDREN.get(integration_id)
    if child is not None and child.poll() is None:
        return {"status": "already_running", "integration_id": integration_id}
    manifest = _manifest(integration_id)
    child = subprocess.Popen(
        manifest["connect"], cwd=REPO, stdin=None,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    CHILDREN[integration_id] = child
    return {"status": "started", "integration_id": integration_id}


class Handler(BaseHTTPRequestHandler):
    token = ""

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("content-security-policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict[str, Any]) -> None:
        self._send(status, "application/json; charset=utf-8",
                   json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/?"):
            body = HTML.read_text(encoding="utf-8").replace("__TOKEN__", self.token)
            self._send(HTTPStatus.OK, "text/html; charset=utf-8", body.encode("utf-8"))
            return
        if self.path == "/api/graph":
            try:
                self._json(HTTPStatus.OK, _graph())
            except Exception as error:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)[:160]})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/connect":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if self.headers.get("x-life-manager-token") != self.token:
            self._json(HTTPStatus.FORBIDDEN, {"error": "invalid local action token"})
            return
        try:
            length = int(self.headers.get("content-length") or 0)
            if length <= 0 or length > 8192:
                raise ValueError("invalid request size")
            value = json.loads(self.rfile.read(length))
            integration_id = str(value.get("integration_id") or "")
            self._json(HTTPStatus.ACCEPTED, _connect(integration_id))
        except Exception as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)[:160]})

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18791)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("port must be between 1024 and 65535")
    Handler.token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(json.dumps({"status": "ready", "url": url}), flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
