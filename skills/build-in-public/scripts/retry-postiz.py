#!/usr/bin/env python3
"""
retry-postiz.py — Retry wrapper for Postiz API calls.

30s wait, max 3 attempts, Slack 🚨 on final fail.

Usage as a library:
  from retry_postiz import post_with_retry
  result = post_with_retry(url, payload, headers)

Usage as a CLI (for shell scripts):
  echo '{"posts":[...]}' | python3 retry-postiz.py --url https://app.postiz.com/api/posts
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import request, error

LOG_DIR = Path.home() / ".openclaw" / "logs" / "build-in-public"
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "{{profile.channels.reportChannel}}")
MAX_ATTEMPTS = int(os.environ.get("BIP_RETRY_ATTEMPTS", "3"))
WAIT_SEC = int(os.environ.get("BIP_RETRY_WAIT_SEC", "30"))


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}")


def slack_alert(text: str) -> None:
    """Best-effort: write to a delivery queue file Anicca's Slack delivery picks up."""
    queue = Path.home() / ".openclaw" / "delivery-queue" / "build-in-public-alerts"
    queue.mkdir(parents=True, exist_ok=True)
    payload = {
        "channel": SLACK_CHANNEL,
        "text": f"🚨 build-in-public retry exhausted: {text}",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    out = queue / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def post_with_retry(url: str, payload: dict, headers: dict | None = None) -> dict:
    headers = dict(headers or {})
    headers.setdefault("Content-Type", "application/json")
    body = json.dumps(payload).encode("utf-8")
    last_err: str | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = request.Request(url, data=body, headers=headers, method="POST")
            with request.urlopen(req, timeout=60) as resp:
                code = resp.getcode()
                data = resp.read().decode("utf-8")
                if 200 <= code < 300:
                    log(f"OK {code} on attempt {attempt}")
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        return {"_raw": data, "_status": code}
                last_err = f"HTTP {code}: {data[:200]}"
        except error.HTTPError as e:
            last_err = f"HTTPError {e.code}: {e.read().decode('utf-8', 'replace')[:200]}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
        log(f"attempt {attempt}/{MAX_ATTEMPTS} failed: {last_err}")
        if attempt < MAX_ATTEMPTS:
            time.sleep(WAIT_SEC)

    slack_alert(f"{url} — {last_err}")
    raise RuntimeError(f"retry exhausted: {last_err}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--api-key", default=os.environ.get("POSTIZ_API_KEY", ""))
    args = ap.parse_args()

    payload = json.loads(sys.stdin.read())
    headers = {"Authorization": f"Bearer {args.api_key}"} if args.api_key else {}
    try:
        result = post_with_retry(args.url, payload, headers)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except RuntimeError as e:
        log(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
