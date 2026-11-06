"""Read-only connectivity check for Listen Labs Public Study API.

Does NOT store or echo API keys, wallet balances, study titles, participant
records, transcripts or response data. Does not POST/create/launch/delete.
Key is provided through standard input, lives in process memory only. The machine-readable
summary deliberately reports ONLY statuses / counts and anonymous shapes.

Usage:
  python3 experiments/p05_2_listenlabs_readonly_probe.py

This code is NOT a Twin prediction API. Review the vendor's current docs.
"""
from __future__ import annotations
from getpass import getpass
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from time import time
import json

ORIGIN = "https://listenlabs.ai"
PATHS = {
    "wallets": "/api/public/v1/wallets",
    "studies": "/api/public/v1/studies",
}

def safe_get(name: str, path: str, key: str) -> dict:
    if path not in PATHS.values() or not path.startswith("/api/public/v1/"):
        raise ValueError("unapproved route")
    req = Request(
        ORIGIN + path,
        headers={
            "x-api-key": key,
            "accept": "application/json",
            "user-agent": "Manager-Research-ReadOnly-2026-11",
        },
        method="GET",
    )
    begin = time()
    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read(1_000_000)
            status = response.status
    except HTTPError as err:
        status = err.code
        raw = err.read(10_000)
    except (URLError, TimeoutError) as err:
        return {"route": name, "network_error_type": type(err).__name__}
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return {"route": name, "http_status": status, "json": False}
    summary = {
        "route": name,
        "http_status": status,
        "elapsed_ms": round((time() - begin) * 1000),
        "json": True,
        "response_type": type(body).__name__,
        # Explicitly allow-list MACHINE-READABLE ERROR CODE only, not error text.
        "error_code": body.get("code") if isinstance(body, dict)
                      and isinstance(body.get("code"), str) else None,
    }
    if status == 200 and isinstance(body, dict):
        for list_key in ("wallets", "studies"):
            if isinstance(body.get(list_key), list):
                summary[f"{list_key}_count"] = len(body[list_key])
        summary["recognized_study_api"] = bool(
            isinstance(body.get("wallets"), list)
            or isinstance(body.get("studies"), list)
            or isinstance(body.get("data"), list)
        )
    # No raw response, no titles, no IDs, no credit balances, no transcripts.
    return summary

def main() -> None:
    if sys.stdin.isatty():
        key = getpass("Listen Labs API key (input hidden, not saved): ")
    else:
        # MCP pipes provide no TTY, so getpass would warn and may echo.
        # Read the already-supplied stdin without running a shell with secrets.
        print("READONLY_PROBE_AWAITING_KEY_STDIN", flush=True)
        key = sys.stdin.readline().rstrip("\r\n")
    if not key or len(key) < 16:
        print(json.dumps({"probe": "invalid credential input"}, ensure_ascii=False))
        return
    try:
        records = [safe_get(name, path, key) for name, path in PATHS.items()]
    finally:
        key = None
    print(json.dumps({
        "provider": "Listen Labs Public Study API",
        "mode": "two authorized GET requests only",
        "external_mutations": 0,
        "participant_content_persisted": False,
        "credential_persisted": False,
        "records": records
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
