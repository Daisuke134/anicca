#!/usr/bin/env python3
"""Solve one reCAPTCHA v2 challenge with the owner's existing CapSolver account."""

from __future__ import annotations

import argparse
import importlib.util
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


def inject(target_id: str, token: str) -> dict[str, object]:
    cdp_path = Path.cwd() / "skills" / "browser" / "scripts" / "cdp.py"
    spec = importlib.util.spec_from_file_location("fundraiser_cdp", cdp_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CDP_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    encoded = json.dumps(token)
    source = f"""
    (() => {{
      const token = {encoded};
      let textareas = 0;
      let callbacks = 0;
      document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach((element) => {{
        element.value = token;
        element.innerHTML = token;
        element.dispatchEvent(new Event('input', {{bubbles: true}}));
        element.dispatchEvent(new Event('change', {{bubbles: true}}));
        textareas += 1;
      }});
      document.querySelectorAll('[data-sitekey][data-callback]').forEach((element) => {{
        const name = element.getAttribute('data-callback');
        if (!name) return;
        let callback = window;
        for (const part of name.split('.')) callback = callback && callback[part];
        if (typeof callback === 'function') {{
          try {{ callback(token); callbacks += 1; }} catch (_) {{}}
        }}
      }});
      return {{textareas, callbacks}};
    }})()
    """
    result = module.evaluate(target_id, source)
    if not isinstance(result, dict) or int(result.get("textareas", 0)) < 1:
        raise RuntimeError("RECAPTCHA_TEXTAREA_UNAVAILABLE")
    if int(result.get("callbacks", 0)) != 1:
        raise RuntimeError("RECAPTCHA_NAMED_CALLBACK_UNAVAILABLE")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--website-url", required=True)
    parser.add_argument("--website-key", required=True)
    parser.add_argument("--target-id")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    try:
        token = solve(args.website_url, args.website_key, args.timeout)
        if args.target_id:
            result = inject(args.target_id, token)
    except Exception as error:
        print(f"capsolver: {error}", file=sys.stderr)
        return 1
    if args.target_id:
        print(
            "CAPSOLVER_INJECTED=true "
            f"TEXTAREAS={result['textareas']} CALLBACKS={result['callbacks']}"
        )
    else:
        print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
