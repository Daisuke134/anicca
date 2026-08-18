#!/usr/bin/env python3
"""Tell "the cron stopped" apart from "the cron ran and failed" — spec §0.1.4 #8 (P1c).

Measured on 2026-08-05: the heartbeat was 42 hours old and the auditor had spent that whole
time reporting `STALE (no pass in 2509min — in-session cron likely stopped; healthcheck
should restart)`. In the same window the loop ran 57 passes and recorded 128 failures. The
cron never stopped. Every pass failed, and the heartbeat is only written on success.

So the auditor prescribed restarting something that had never stopped — a no-op — for two
days, while the real causes went unnamed: b2_parent_boundary_failed 54 times,
paid_work_validation_failed 44.

A stale heartbeat is not evidence of silence. It is evidence of no *success*, and those are
different diagnoses with different remedies:

    stale + recent failures  ->  it is running and failing. Fix the failure.
    stale + nothing at all   ->  it really is not running. Restart it.

FAILING is not the gentler verdict. A loop that wakes every hour, burns tokens and produces
nothing is not healthier than one that stopped; it is more expensive and harder to notice.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

# Wide enough to contain several hourly passes, short enough that failures from days ago
# cannot disguise a cron that has since died.
WINDOW_MINUTES = 180
STALE_THRESHOLD_MINUTES = 90


def classify(
    *,
    heartbeat_age_min: int | None,
    failures: list[dict[str, Any]],
    now: float,
    stale_threshold_min: int = STALE_THRESHOLD_MINUTES,
    window_minutes: int = WINDOW_MINUTES,
) -> dict[str, Any]:
    """Return the verdict for the pass loop, given heartbeat age and recorded failures."""
    base = {"window_minutes": window_minutes, "failures_in_window": 0, "top_reason": None}

    if heartbeat_age_min is None:
        return {**base, "kind": "NO_HEARTBEAT", "healthy": False, "text": "NO_HEARTBEAT (no pass yet)"}

    if heartbeat_age_min < stale_threshold_min:
        return {
            **base,
            "kind": "FIRING",
            "healthy": True,
            "text": f"FIRING (last successful pass {heartbeat_age_min}min ago)",
        }

    cutoff = now - window_minutes * 60
    recent = [row for row in failures if isinstance(row, dict) and (row.get("ts") or 0) >= cutoff]

    if recent:
        reasons = Counter(str(row.get("reason") or "unknown") for row in recent)
        top_reason, top_count = reasons.most_common(1)[0]
        return {
            **base,
            "kind": "FAILING",
            "healthy": False,
            "failures_in_window": len(recent),
            "top_reason": top_reason,
            # Deliberately does not suggest a restart. The thing is already running; the
            # remedy is the named failure, and pointing at a restart is what wasted two days.
            "text": (
                f"FAILING (no successful pass in {heartbeat_age_min}min, but "
                f"{len(recent)} failures in the last {window_minutes}min — the loop is "
                f"running and failing. Top reason: {top_reason} x{top_count})"
            ),
        }

    return {
        **base,
        "kind": "STALE",
        "healthy": False,
        "text": (
            f"STALE (no pass in {heartbeat_age_min}min and no failures in the last "
            f"{window_minutes}min — nothing is running; healthcheck should restart)"
        ),
    }
