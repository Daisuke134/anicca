#!/usr/bin/env python3
"""Refresh the repo-external Capafy Publisher Console token before expiry."""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


API = "https://api.capafy.ai"
CREDENTIALS = Path.home() / ".local/share/anicca/credentials.json"
REFRESH_BEFORE_SECONDS = 7 * 86400


def _post(path: str, body: dict) -> dict:
    request = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict) or value.get("code", 0) != 0:
        raise RuntimeError(f"Capafy auth failed: {value.get('code') if isinstance(value, dict) else 'shape'}")
    return value.get("data", value)


def _expiry(token: str) -> int:
    parts = token.split(".")
    if len(parts) != 3:
        return 0
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    return int(payload.get("exp") or 0)


def _credential_entry() -> tuple[dict, dict]:
    value = json.loads(CREDENTIALS.read_text())
    matches = [row for row in value.get("credentials", []) if row.get("service") == "capafy-publisher"]
    if len(matches) != 1:
        raise RuntimeError("capafy-publisher credential is not unique")
    return value, matches[0]


def _latest_otp(email: str, not_before_ms: int) -> str:
    env = dict(os.environ)
    for _ in range(12):
        raw = subprocess.check_output(
            ["gog", "gmail", "search", 'newer_than:1d from:noreply@capafy.ai subject:"login verification code"',
             "--account", email, "--json", "--results-only", "--no-input"],
            text=True, env=env, timeout=30,
        )
        threads = json.loads(raw)
        if threads:
            thread_id = threads[0]["id"]
            thread = json.loads(subprocess.check_output(
                ["gog", "gmail", "thread", "get", thread_id, "--account", email,
                 "--json", "--full", "--no-input"],
                text=True, env=env, timeout=30,
            ))["thread"]
            messages = [m for m in thread.get("messages", []) if int(m.get("internalDate") or 0) >= not_before_ms]
            if messages:
                message = max(messages, key=lambda m: int(m["internalDate"]))
                bodies: list[str] = []

                def collect(part: dict) -> None:
                    data = (part.get("body") or {}).get("data")
                    if data:
                        bodies.append(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace"))
                    for child in part.get("parts") or []:
                        collect(child)

                collect(message["payload"])
                codes = re.findall(r"font-size:32px[^>]*>(\d{6})</div>", "\n".join(bodies))
                if codes:
                    return codes[-1]
        time.sleep(5)
    raise RuntimeError("fresh Capafy OTP was not observed")


def _find_jwt(value: object) -> str:
    if isinstance(value, str) and _expiry(value):
        return value
    if isinstance(value, dict):
        for child in value.values():
            found = _find_jwt(child)
            if found:
                return found
    return ""


def main() -> int:
    document, entry = _credential_entry()
    token = str(entry.get("web_token") or "")
    exp = _expiry(token)
    remaining = exp - int(time.time())
    if remaining > REFRESH_BEFORE_SECONDS:
        print(json.dumps({"ok": True, "action": "healthy_noop", "expires_at": exp, "remaining_days": remaining // 86400}))
        return 0
    email = str(entry.get("email") or entry.get("username") or "")
    if not email:
        raise RuntimeError("Capafy publisher email missing")
    started_ms = int(time.time() * 1000)
    challenge = _post("/auth/login", {"loginMethod": "email", "email": email})
    challenge_id = challenge.get("challengeId") if isinstance(challenge, dict) else None
    if not challenge_id:
        raise RuntimeError("Capafy challengeId missing")
    code = _latest_otp(email, started_ms)
    verified = _post("/auth/login/verify", {"challengeId": challenge_id, "code": code, "source": "web"})
    new_token = _find_jwt(verified)
    if not new_token:
        raise RuntimeError("Capafy web token missing from verify response")
    entry["web_token"] = new_token
    entry["web_token_updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    temporary = CREDENTIALS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, CREDENTIALS)
    print(json.dumps({"ok": True, "action": "refreshed", "expires_at": _expiry(new_token)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"ok": False, "error": type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
