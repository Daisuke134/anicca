#!/usr/bin/env python3
"""Fetch public stats (no auth) into a measurement ledger — generalized example.

Pattern (see ../05-measurement-ledger.md):
- one small script per metric, one `type` of row per script;
- bounded retries with exponential backoff;
- on failure, append an *error row* — the ledger records the outage,
  it never stays silent;
- measured fields and computed fields are named distinctly (`_computed`).

Usage: copy this file, set API_URL and LEDGER, adapt `build_row()` to the
endpoint you actually read, schedule it with your other metric scripts.

Requires: Python 3.10+, `requests`.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# --- configure these three -------------------------------------------------
LEDGER = Path("./measurement-ledger.jsonl")
ROW_TYPE = "example_stats"
API_URL = "https://api.example.com/v2/public-stats/your-resource"
# ---------------------------------------------------------------------------


def fetch(retries: int = 4) -> dict:
    delay = 5.0
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(API_URL, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
    assert last_exc is not None
    raise last_exc


def build_row(data: dict, ts: str) -> dict:
    """Map the endpoint's JSON onto ledger fields. Replace with your fields."""
    stats = data.get("stats") or {}
    total = stats.get("total", 0)
    ok = stats.get("ok", 0)
    return {
        "type": ROW_TYPE,
        "ts": ts,
        "total": total,
        "ok": ok,
        "ok_rate_computed": (ok / total) if total else None,
    }


def main() -> int:
    ts = datetime.now(timezone.utc).isoformat()
    row: dict = {"type": ROW_TYPE, "ts": ts}
    try:
        row = build_row(fetch(), ts)
    except Exception as e:  # noqa: BLE001
        row["error"] = f"{type(e).__name__}: {e}"
    with LEDGER.open("a") as f:
        f.write(json.dumps(row) + "\n")
    if "error" in row:
        print(f"{ROW_TYPE}: ERROR {row['error']}")
        return 1
    print(f"{ROW_TYPE}: {json.dumps(row)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
