#!/usr/bin/env python3
"""earning-health.py — detects an earn loop that RUNS every wake but produces NOTHING (the Franklin
sol-trade 2-day-silent-break, 2026-07-08 -> 2026-07-10): its trace.jsonl got a new line EVERY wake
(a fresh "skip" line), so healthcheck-lib.sh's existing OUT_STALE_HRS artifact-AGE staleness check
(FIND-009, step (d) of hc_run()) never fired -- age alone cannot see a loop that is alive and writing
but mechanically rejecting every single wake before the agent ever runs. This is a CONTENT check on
the trace, never an age check.

Pure, no I/O -- mirrors cadence.py's contract exactly: all real file/mtime/JSONL reads are the
CALLER's job (the companion *-healthcheck.sh script gathers the trace tail and pipes it in here).

Judgment about WHETHER TO TRADE stays entirely with the agent (rules/building-effective-ai-agents.md:
"no hardcoded judgment, the model decides") -- this detector never looks at price/signal/conviction,
only at the loop's own bookkeeping of what it DID on each wake:
    action == "skip"       -> a deterministic guard (identity-mismatch / kill-switch / earn-guard
                               breach) rejected the wake before the agent ever got a chance to decide
                               anything. That is a MECHANISM failure, not a trading decision.
    action == "live-pass"  -> the agent actually ran and made its own WAIT-or-trade call, even if the
                               outcome was "WAIT" every time (e.g. TradingSignal stayed neutral for
                               days) -- that is a real, legitimate decision and must NEVER be flagged.
So a long run of live-pass WAITs (a genuine trading strategy holding out for an edge) is healthy; only
a run of identical-reason skip lines (the mechanism itself never let the agent run at all) is barren.
"""
from __future__ import annotations

import json
import sys


def is_fresh_but_barren(trace_tail: list[dict], min_run: int = 20) -> bool:
    """trace_tail: the trace's own recent lines (dicts), in original file order (oldest..newest --
    the caller decides how many lines to pass in; only the final min_run of them are examined here).

    Returns True (BARREN -> escalate to self-fix) iff there are at least min_run entries AND the
    LAST min_run are ALL action == "skip" AND they all share one identical, non-empty `reason`
    string. Anything else -- fewer than min_run entries (not enough evidence yet), any non-skip
    entry in the window (the agent DID run, e.g. a live-pass), or mixed/rotating skip reasons (a
    transient blip, not a sustained single-cause mechanism failure) -- returns False. This mirrors
    the "AND, never OR/majority" discipline cadence.py's compound kind already established for this
    codebase (REQ-LV-101): only a real, sustained, single-cause mechanical rejection escalates.
    """
    if len(trace_tail) < min_run:
        return False
    window = trace_tail[-min_run:]
    if not all(entry.get("action") == "skip" for entry in window):
        return False
    reasons = {entry.get("reason") for entry in window}
    if len(reasons) != 1:
        return False
    (only_reason,) = reasons
    return bool(only_reason)


def _main():
    if len(sys.argv) < 2:
        print("usage: earning-health.py is-barren [min_run] < trace_tail.jsonl", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "is-barren":
        min_run = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        entries = []
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                # fail-soft: a partial/corrupted trailing line (mid-append) must never crash the
                # check or be misread as a skip -- same "never fabricate, never brick" discipline as
                # every other trace/ledger reader in this codebase (record_earn.py, positions.py).
                continue
        result = is_fresh_but_barren(entries, min_run)
        print("true" if result else "false")
        sys.exit(0 if result else 1)
    else:
        print(f"unknown subcommand: {cmd!r}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _main()
