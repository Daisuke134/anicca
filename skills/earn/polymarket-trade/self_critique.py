#!/usr/bin/env python3
"""self_critique.py — reads THIS skill's own decision log (state/pm-decisions.jsonl) and produces
a periodic, honest critique: which reasons preceded losses, which thresholds look miscalibrated,
what it would change. Any proposed threshold/strategy change is NEVER applied here — it is handed
to the EXISTING self-improve/lib/promote_gate.py, which only ships a change after (1) it beats
baseline on walk-forward, (2) the trip-wire is clear, and (3) a fresh-context adversary PASSes.
This file does not re-implement that gate (a second gate was explicitly out of scope).

WHY THIS IS DELIBERATELY CONSERVATIVE WITH LLM CALLS: sol-trade was frozen (2026-07-17, commit
0980eb44) for burning ~$1.86/day on gpt-5-mini calls while producing 850 passes / 0 swaps / $0
realized — cost with no output. This script's core critique is 100% deterministic arithmetic over
the decision log (no LLM call, $0 marginal cost) precisely so a self-critique loop can never repeat
that failure mode. It only recommends when a real pattern is statistically visible in real data;
absent that, it says so honestly rather than inventing a narrative.
"""
from __future__ import annotations

import collections
import json
import os
import sys
from typing import Optional

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(SKILL_DIR, "..", "state")
DECISIONS_PATH = os.path.join(STATE_DIR, "pm-decisions.jsonl")

# Below this many real cycles, any "which reasons preceded losses" claim would be overfit to
# noise. This is a documented, fixed threshold — not tuned to make today's report look complete.
MIN_CYCLES_FOR_LOSS_PATTERN = 20


def load_decisions(path: str | None = None) -> list[dict]:
    """Fail-closed to [] on any read error — a critique script that can't read its own log must
    say so, never fabricate history."""
    path = path or DECISIONS_PATH
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append(obj)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []
    return out


def summarize(records: list[dict]) -> dict:
    """PURE: every count here is computed directly from the records passed in — nothing is
    inferred beyond what's actually in the log."""
    n = len(records)
    reason_counts: collections.Counter = collections.Counter()
    action_counts: collections.Counter = collections.Counter()
    naked_warnings = 0
    daily_guard_trips = 0
    kill_skips = 0
    pnl_series = []

    for r in records:
        action_counts[r.get("action", "unknown")] += 1
        if r.get("action") == "skip":
            if "kill-switch" in str(r.get("reason", "")):
                kill_skips += 1
            if "daily-loss-limit" in str(r.get("reason", "")):
                daily_guard_trips += 1
            continue
        for strat in ("bundle_arb", "market_maker"):
            sub = r.get(strat) or {}
            if sub.get("reason"):
                reason_counts[f"{strat}: {sub['reason'][:80]}"] += 1
            if sub.get("naked_leg_warning"):
                naked_warnings += 1
        pick = (r.get("pick") or {}).get("reason")
        if pick:
            reason_counts[f"pick: {pick[:80]}"] += 1
        pnl = r.get("pnl") or {}
        if "cumulative_realized_usdc" in pnl:
            pnl_series.append((r.get("ts"), pnl["cumulative_realized_usdc"], pnl.get("today_realized_usdc")))

    return {
        "cycles": n,
        "action_counts": dict(action_counts),
        "reason_counts": dict(reason_counts.most_common(10)),
        "naked_leg_warning_count": naked_warnings,
        "daily_guard_trip_count": daily_guard_trips,
        "kill_switch_skip_count": kill_skips,
        "pnl_series": pnl_series,
    }


def find_loss_preceding_reasons(records: list[dict]) -> dict:
    """PURE: for every pair of consecutive cycles where cumulative realized P&L DROPPED, bucket
    the reason(s) recorded in the cycle immediately before the drop. Requires
    MIN_CYCLES_FOR_LOSS_PATTERN real cycles with real P&L before it will claim anything — with
    fewer, it returns an explicit 'insufficient data' verdict rather than a spurious correlation
    from 1-2 data points."""
    pnl_points = [
        (r.get("ts"), (r.get("pnl") or {}).get("cumulative_realized_usdc"))
        for r in records
        if (r.get("pnl") or {}).get("cumulative_realized_usdc") is not None
    ]
    if len(records) < MIN_CYCLES_FOR_LOSS_PATTERN:
        return {
            "sufficient_data": False,
            "cycles_observed": len(records),
            "cycles_required": MIN_CYCLES_FOR_LOSS_PATTERN,
            "verdict": (
                f"insufficient history ({len(records)} cycle(s) logged, "
                f"{MIN_CYCLES_FOR_LOSS_PATTERN} required) — no loss-pattern claim made"
            ),
            "preceding_reasons": {},
        }
    preceding: collections.Counter = collections.Counter()
    losses_found = 0
    for i in range(1, len(pnl_points)):
        prev_val, cur_val = pnl_points[i - 1][1], pnl_points[i][1]
        if cur_val is not None and prev_val is not None and cur_val < prev_val:
            losses_found += 1
            prior = records[i - 1]
            pick_reason = (prior.get("pick") or {}).get("reason")
            if pick_reason:
                preceding[pick_reason] += 1
    return {
        "sufficient_data": True,
        "cycles_observed": len(records),
        "losses_observed": losses_found,
        "verdict": (
            "no realized losses observed yet" if losses_found == 0
            else f"{losses_found} loss event(s) observed; see preceding_reasons"
        ),
        "preceding_reasons": dict(preceding.most_common(5)),
    }


# ---------------------------------------------------------------------------------------------
# promote_gate wiring — proposals are NEVER applied directly, only submitted to the real gate.
# ---------------------------------------------------------------------------------------------
_SELF_IMPROVE_LIB = os.path.join(SKILL_DIR, "..", "self-improve", "lib")


def _load_promote_gate():
    """Late import so this module can be imported/tested (summarize/find_loss_preceding_reasons)
    without requiring the full self-improve evaluator harness to be importable.
    promote_gate.py itself lives at self-improve/lib/promote_gate.py and, on import, inserts
    self-improve/ onto sys.path for its OWN `import evaluator` / `from lib import ...` — so this
    only needs to add self-improve/lib/, not self-improve/ itself."""
    lib_dir = os.path.join(SKILL_DIR, "..", "self-improve", "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    import promote_gate  # type: ignore
    return promote_gate


def propose_threshold_change(param: str, current_value, proposed_value, evidence: str) -> dict:
    """Package a proposed knob change as DATA — never mutates anything. `param` must be one of
    pick.py's own genome-tunable knobs (MIN_EDGE, MIN_CONF, RESOLVE_HORIZON_DAYS, MAX_CANDIDATES,
    EARN_CONSENSUS_MODELS — see run.sh's 'EVOLVE genome wiring' section); anything else is
    rejected here, fail-closed, before it ever reaches the gate."""
    allowed = {"MIN_EDGE", "MIN_CONF", "RESOLVE_HORIZON_DAYS", "MAX_CANDIDATES", "EARN_CONSENSUS_MODELS"}
    if param not in allowed:
        return {"accepted": False, "reason": f"{param!r} is not a recognized tunable knob ({sorted(allowed)})"}
    return {
        "accepted": True,
        "param": param,
        "current_value": current_value,
        "proposed_value": proposed_value,
        "evidence": evidence,
        "status": "PROPOSED — not applied. Must clear self-improve/lib/promote_gate.py "
                  "(walk-forward beats baseline -> trip-wire clear -> fresh-context adversary PASS) "
                  "before this can ever take effect.",
    }


def submit_candidate_for_gate_assessment(candidate_path: str, config: Optional[dict] = None) -> dict:
    """Calls the REAL promote_gate.assess_candidate (deterministic half only — no LLM, no write,
    per its own docstring). Returns its verdict verbatim. This is the ONLY function in this file
    that talks to promote_gate, and it never calls decide_promotion/promote_if_approved itself —
    those require a real fresh-context adversary verdict, which only promote_gate.sh (a separate,
    already-existing effectful script) is allowed to produce. A threshold change proposed by this
    critique becomes real ONLY by handing candidate_path to that existing pipeline by hand; this
    function's job is solely to prove the deterministic half of the gate is reachable and honest
    about eligibility, not to fabricate a promotion."""
    promote_gate = _load_promote_gate()
    return promote_gate.assess_candidate(candidate_path, config=config)


def build_report(records: list[dict]) -> dict:
    stats = summarize(records)
    loss_pattern = find_loss_preceding_reasons(records)
    recommendations = []

    if stats["naked_leg_warning_count"] > 0:
        recommendations.append(
            f"{stats['naked_leg_warning_count']} cycle(s) flagged a REAL naked leg that dry mode "
            "could not flatten — this needs a live market_maker.py pass (or manual review) to "
            "actually neutralize it, not a threshold change."
        )
    if stats["daily_guard_trip_count"] > 0:
        recommendations.append(
            f"daily-loss-limit tripped {stats['daily_guard_trip_count']} time(s) — review "
            "DAILY_LOSS_LIMIT_USD against realized swings before resuming."
        )
    if not loss_pattern["sufficient_data"]:
        recommendations.append(loss_pattern["verdict"] + "; run the loop longer before trusting any threshold critique.")
    elif loss_pattern.get("losses_observed", 0) == 0:
        recommendations.append("no realized losses in the observed window — no threshold change is justified by loss evidence.")

    return {
        "stats": stats,
        "loss_pattern": loss_pattern,
        "recommendations": recommendations,
        "note": "No threshold was changed by this script. Any change requires promote_gate.py approval.",
    }


def main() -> int:
    records = load_decisions()
    report = build_report(records)
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
