#!/usr/bin/env python3
"""Collect each gig side-effect claim once for the fresh reality verifier.

The verifier used to read the last N rows from every source on every hourly run. A
non-monotonic Coconala state (for example, a listing later returned to draft by
moderation) therefore kept an already-judged historical claim permanently in the
window and spawned the same self-heal forever. This collector advances only across
rounds that captured the required real-page evidence.
"""
from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any


NO_CLAIM_ID = {"", "n/a", "na", "none", "null"}
SOURCES = (
    ("shuppin.jsonl", "shuppin"),
    ("applied.jsonl", "applied"),
    ("earnings.jsonl", "earnings"),
)


def _number_ts(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return 0.0
    return 0.0


def _jsonl(path: str):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue


def consumed_watermark(gig_dir: str) -> float:
    """Return the newest claim timestamp already checked against real-page evidence.

    New rows carry ``claims_through_ts`` explicitly. For pre-fix audit history, use
    the latest completed evidence-backed judge timestamp once as a migration
    baseline. Infra failures and deferrals never advance the cursor.
    """
    audits = list(_jsonl(os.path.join(gig_dir, "audit-reality.jsonl")) or [])
    explicit = [_number_ts(r.get("claims_through_ts")) for r in audits if r.get("claims_through_ts") is not None]
    if explicit:
        return max(explicit)

    completed = []
    for row in audits:
        required = row.get("evidence_required")
        captured = row.get("evidence_captured")
        if row.get("verdict") not in (True, False):
            continue
        if not isinstance(required, int) or not isinstance(captured, int) or captured < required:
            continue
        completed.append(_number_ts(row.get("ts")))
    return max(completed, default=0.0)


def collect_claims(gig_dir: str, per_source_limit: int) -> tuple[list[dict], float]:
    watermark = consumed_watermark(gig_dir)
    claims: list[dict] = []
    for filename, kind in SOURCES:
        fresh = []
        for row in _jsonl(os.path.join(gig_dir, filename)) or []:
            entity_id = row.get("requestId") or row.get("service_id") or ""
            if str(entity_id).strip().lower() in NO_CLAIM_ID:
                continue
            if _number_ts(row.get("ts")) <= watermark:
                continue
            claim = dict(row)
            claim["kind"] = kind
            fresh.append(claim)
        claims.extend(fresh[-per_source_limit:])

    deduped: dict[tuple[str, str], dict] = {}
    for claim in claims:
        key = (claim["kind"], str(claim.get("requestId") or claim.get("service_id") or ""))
        deduped[key] = claim
    return list(deduped.values()), watermark


def main() -> None:
    import sys

    gig_dir = sys.argv[1]
    limit = int(sys.argv[2])
    claims, watermark = collect_claims(gig_dir, limit)
    through = max((_number_ts(c.get("ts")) for c in claims), default=watermark)
    print(json.dumps({"claims": claims, "watermark": watermark, "claims_through_ts": through}, ensure_ascii=False))


if __name__ == "__main__":
    main()
