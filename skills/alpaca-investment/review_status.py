#!/usr/bin/env python3
"""Read Alpaca's authenticated dashboard and persist its explicit review state."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BROWSER = REPO / "skills/browser"
DASHBOARD = "https://app.alpaca.markets/dashboard/overview"


def classify_dashboard(text: str) -> str | None:
    normalized = " ".join(text.lower().split())
    if "application submitted: in review" in normalized:
        return "in_review"
    if "action required" in normalized and "application" in normalized:
        return "action_required"
    if "application rejected" in normalized:
        return "rejected"
    if re.search(r"\blive\s*-\s*[a-z0-9]{6,}\b", normalized):
        return "active"
    return None


def dashboard_ready(url: str, text: str) -> bool:
    return "/login" in url or "Paper -" in text or classify_dashboard(text) is not None


def due(receipt: dict, *, now: datetime | None = None, interval_seconds: int = 1800) -> bool:
    now = now or datetime.now(timezone.utc)
    try:
        observed = datetime.fromisoformat(str(receipt["observed_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return True
    return (now - observed.astimezone(timezone.utc)).total_seconds() >= interval_seconds


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _command(args: list[str], *, stdin: str | None = None, env=None) -> str:
    result = subprocess.run(args, input=stdin, text=True, capture_output=True, env=env, timeout=30)
    if result.returncode:
        raise RuntimeError(f"review_command_failed:{Path(args[0]).name}")
    return result.stdout.strip()


def refresh(state: Path, *, force: bool = False) -> dict:
    receipt_path = state / "account-status.json"
    previous = _read(receipt_path)
    if not force and not due(previous):
        return {**previous, "checked": False}
    owner = f"alpaca-review-{os.getpid()}"
    env = {**os.environ, "AI_BROWSER_HOLDER_PID": str(os.getpid())}
    lease = None
    try:
        health = _command(["/bin/bash", str(BROWSER / "ensure_browser.sh")], env={**env, "CLOAK_BROWSER_OWNER": owner})
        if health not in {"ALIVE", "RECOVERED"}:
            raise RuntimeError("review_browser_unavailable")
        lease = json.loads(_command([sys.executable, str(BROWSER / "scripts/cdp_context_lease.py"), "acquire", owner], env=env))
        target = lease["target_id"]
        cdp = [sys.executable, str(BROWSER / "scripts/cdp.py")]
        _command([*cdp, "nav", target, DASHBOARD], env=env)
        snapshot = None
        expression = '({url:location.href,text:(document.body?.innerText||"")})'
        for _ in range(20):
            snapshot = json.loads(_command([*cdp, "eval", target, "-"], stdin=expression, env=env))
            if dashboard_ready(snapshot.get("url", ""), snapshot.get("text", "")):
                break
            time.sleep(0.5)
        if not snapshot or "/login" in snapshot.get("url", ""):
            raise RuntimeError("review_session_logged_out")
        text = snapshot.get("text", "")
        if "Paper -" in text:
            click_selector = '[...document.querySelectorAll("button")].find(x=>x.innerText.includes("Paper -"))?.click(); true'
            _command([*cdp, "eval", target, "-"], stdin=click_selector, env=env)
            time.sleep(0.5)
            text = json.loads(_command([*cdp, "eval", target, "-"], stdin='document.body?.innerText||""', env=env))
        status = classify_dashboard(text)
        if status is None:
            raise RuntimeError("review_status_unrecognized")
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt = {"application_status": status, "observed_at": observed_at,
                   "source": "authenticated_provider_readback"}
        _write(receipt_path, receipt)
        return {**receipt, "checked": True, "changed": status != previous.get("application_status")}
    finally:
        if lease:
            _command([sys.executable, str(BROWSER / "scripts/cdp_context_lease.py"), "release", owner,
                      "--token", lease["token"], "--generation", str(lease["generation"])], env=env)


if __name__ == "__main__":
    root = Path(os.environ.get("ALPACA_INVESTMENT_STATE_DIR", "~/.local/state/life-manager/alpaca-investment")).expanduser()
    print(json.dumps(refresh(root, force="--force" in sys.argv), separators=(",", ":")))
