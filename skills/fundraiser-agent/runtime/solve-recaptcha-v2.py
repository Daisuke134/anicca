#!/usr/bin/env python3
"""Solve one reCAPTCHA v2 challenge with the owner's existing CapSolver account."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen


API_ROOT = "https://api.capsolver.com"


def api_key() -> str:
    if value := os.environ.get("CAPSOLVER_API_KEY", "").strip():
        return value
    env_path = Path.home() / ".openclaw" / ".env"
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "CAPSOLVER_API_KEY":
            return value.strip().strip("'\"")
    raise RuntimeError("CAPSOLVER_API_KEY is unavailable")


def post(path: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        f"{API_ROOT}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def solve(website_url: str, website_key: str, timeout: int) -> str:
    key = api_key()
    created = post(
        "/createTask",
        {
            "clientKey": key,
            "task": {
                "type": "ReCaptchaV2TaskProxyLess",
                "websiteURL": website_url,
                "websiteKey": website_key,
                "isInvisible": False,
            },
        },
    )
    task_id = str(created.get("taskId", ""))
    if not task_id:
        raise RuntimeError(str(created.get("errorCode", "CREATE_TASK_FAILED")))

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(2)
        result = post("/getTaskResult", {"clientKey": key, "taskId": task_id})
        if result.get("status") == "ready":
            solution = result.get("solution")
            if isinstance(solution, dict):
                token = str(solution.get("gRecaptchaResponse", ""))
                if token:
                    return token
            raise RuntimeError("CAPSOLVER_READY_WITHOUT_TOKEN")
        if result.get("status") == "failed" or result.get("errorId"):
            raise RuntimeError(str(result.get("errorCode", "SOLVE_FAILED")))
    raise RuntimeError("CAPSOLVER_TIMEOUT")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-url", required=True)
    parser.add_argument("--website-key", required=True)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    try:
        token = solve(args.website_url, args.website_key, args.timeout)
    except Exception as error:
        print(f"capsolver: {error}", file=sys.stderr)
        return 1
    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
