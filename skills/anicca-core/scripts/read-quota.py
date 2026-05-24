#!/usr/bin/env python3
"""read-quota.py — report the per-beat quota tier the autonomous loop should use.

Ported from Sutando's skills/quota-tracker/read-quota.py. Anicca runs on TWO
harnesses with different quota systems, so this reports a unified tier:

  - claude -p path (launchd hourly, Sonnet 4.6 on the Claude Max subscription):
    reads quota-state.json (written by the credential proxy / `claude` itself)
    and derives util %, time-to-reset, and the per-beat budget.
  - OpenClaw path (cron 6h, gpt-5.4-mini on the GPT subscription): no Anthropic
    rate-limit headers apply, so report FULL (the GPT sub is metered separately
    and the cron cadence already bounds spend).

Tiers (Sutando-faithful):
  budget_per_beat = remaining% / (minutes_until_reset / beat_interval_minutes)
    >3%/beat  → FULL     (subagents, write+push code, heavy research)
    1-3%/beat → MEDIUM   (code fixes, monitoring, no subagents)
    <1%/beat  → LIGHT    (chores + health checks only)
    0% remain → MINIMAL  (process owner tasks + health + update log)

Usage:
  read-quota.py            # human readable
  read-quota.py --json     # machine readable {tier, remaining_pct, ...}
  read-quota.py --gate     # exit 1 if exhausted (MINIMAL)
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
WS = Path(os.environ.get("ANICCA_WORKSPACE", str(ANICCA_HOME / "workspace")))
BEAT_MIN = float(os.environ.get("ANICCA_BEAT_INTERVAL_MIN", "60"))  # claude -p = hourly

QUOTA_CANDIDATES = [
    WS / "quota-state.json",
    ANICCA_HOME / "quota-state.json",
    Path.home() / ".claude" / "quota-state.json",
]


def _tier(budget_per_beat: float, remaining: float) -> str:
    if remaining <= 0:
        return "MINIMAL"
    if budget_per_beat > 3:
        return "FULL"
    if budget_per_beat >= 1:
        return "MEDIUM"
    return "LIGHT"


def _mins_until(reset_iso: str) -> float:
    try:
        dt = datetime.fromisoformat(reset_iso.replace("Z", "+00:00"))
        return max(1.0, (dt - datetime.now(timezone.utc)).total_seconds() / 60.0)
    except Exception:
        return 300.0  # assume a 5h window if reset unparseable


def read_quota() -> dict:
    qf = next((c for c in QUOTA_CANDIDATES if c.exists()), None)
    if qf is None:
        # No Anthropic quota signal (OpenClaw/GPT path, or proxy not running).
        return {
            "tier": "FULL",
            "remaining_pct": None,
            "source": "no-quota-file (OpenClaw/GPT path → FULL)",
            "budget_per_beat": None,
        }
    data = json.loads(qf.read_text())
    h = data.get("headers", data)
    util_5h = float(h.get("anthropic-ratelimit-unified-5h-utilization", 0) or 0)
    reset_5h = h.get("anthropic-ratelimit-unified-5h-reset", "")
    remaining = max(0.0, 100.0 - util_5h)
    mins = _mins_until(reset_5h) if reset_5h else 300.0
    beats_left = max(1.0, mins / BEAT_MIN)
    budget = remaining / beats_left
    return {
        "tier": _tier(budget, remaining),
        "remaining_pct": round(remaining, 1),
        "util_5h": round(util_5h, 1),
        "minutes_until_reset": round(mins),
        "beats_left": round(beats_left, 1),
        "budget_per_beat": round(budget, 2),
        "source": str(qf),
    }


def main() -> int:
    q = read_quota()
    if "--json" in sys.argv:
        print(json.dumps(q))
    else:
        if q["remaining_pct"] is None:
            print(f"tier={q['tier']} ({q['source']})")
        else:
            print(
                f"tier={q['tier']} remaining={q['remaining_pct']}% "
                f"budget/beat={q['budget_per_beat']}% reset_in={q['minutes_until_reset']}m"
            )
    if "--gate" in sys.argv and q["tier"] == "MINIMAL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
