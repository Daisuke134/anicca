#!/usr/bin/env python3
"""Execute one already-routed Writer runbook and persist a bounded receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


SECRET_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|bearer|cookie|password|secret|token)"
    r"(\s*[:=]\s*|\s+)[^\s,;]+"
)
MAX_OUTPUT = 12000


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _safe(value: str) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)[-MAX_OUTPUT:]


def execute(route: dict[str, Any], observed_at: str, timeout: int) -> dict[str, Any]:
    if route.get("route") != "KNOWN":
        raise ValueError("only KNOWN routes can execute")
    command = route.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
        raise ValueError("route command is invalid")
    expected = hashlib.sha256("\0".join(command).encode()).hexdigest()
    if route.get("command_sha256") != expected:
        raise ValueError("route command hash mismatch")
    try:
        process = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
        )
        status = "SUCCEEDED" if process.returncode == 0 else "FAILED"
        return_code = process.returncode
        stdout = _safe(process.stdout)
        stderr = _safe(process.stderr)
    except subprocess.TimeoutExpired as exc:
        status = "TIMEOUT"
        return_code = None
        stdout = _safe(exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
        stderr = _safe(exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
    return {
        "schema": "writer.self-heal.runbook-receipt",
        "version": 1,
        "observed_at": observed_at,
        "fingerprint": route["fingerprint"],
        "runbook_id": route["runbook_id"],
        "runbook_version": route["runbook_version"],
        "mode": route["mode"],
        "command_sha256": expected,
        "status": status,
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    route = json.loads(args.route.read_text(encoding="utf-8"))
    value = execute(route, args.observed_at, args.timeout)
    _atomic(args.out, value)
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0 if value["status"] == "SUCCEEDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
