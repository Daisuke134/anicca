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
    action == "error"      -> (FIND-001) pm-trade's run.sh has a genuine THIRD state sol-trade's
                               clean skip/live-pass-only vocabulary does not: a code/automation bug
                               firing on every wake (AGENT_HOME missing, pick.py non-zero exit --
                               skills/earn/polymarket-trade/run.sh:23,185-186), never a "skip" per
                               se. That is ALSO a mechanism failure -- the loop is alive but broken,
                               arguably MORE urgent than a skip since nothing downstream even ran --
                               and must be just as escalate-eligible as a sustained skip run.
    action == "live-pass"  -> the agent actually ran and made its own WAIT-or-trade call, even if the
                               outcome was "WAIT" every time (e.g. TradingSignal stayed neutral for
                               days) -- that is a real, legitimate decision and must NEVER be flagged.
So a long run of live-pass WAITs (a genuine trading strategy holding out for an edge) is healthy; only
a run of identical-cause skip/error lines (the mechanism itself never let the agent run at all, or
broke outright) is barren/unhealthy.
"""
from __future__ import annotations

import json
import re
import sys

# FIND-001: mechanism-failure actions eligible for the barren/unhealthy window. "skip" = a
# deterministic guard rejected the wake; "error" = the loop itself crashed/misconfigured before the
# agent could run. Both are code/env bugs, never a trading decision -- unlike "live-pass"/"wait"/
# "trade"/... which mean the agent genuinely ran and must never be flagged.
_MECHANISM_FAILURE_ACTIONS = frozenset({"skip", "error"})


def _mechanism_failure_cause(entry: dict) -> str | None:
    """The single failure-cause string for one mechanism-failure entry, or None if `entry` is not a
    mechanism-failure entry at all (i.e. the agent genuinely ran that wake). `action == "skip"`
    entries carry their cause in `reason`; `action == "error"` entries carry it in `error`
    (skills/earn/polymarket-trade/run.sh's own trace shape -- it never writes a `reason` field for
    its error lines) -- FIND-001.
    """
    action = entry.get("action")
    if action not in _MECHANISM_FAILURE_ACTIONS:
        return None
    return entry.get("reason") if action == "skip" else entry.get("error")


def is_fresh_but_barren(trace_tail: list[dict], min_run: int = 20) -> bool:
    """trace_tail: the trace's own recent lines (dicts), in original file order (oldest..newest --
    the caller decides how many lines to pass in; only the final min_run of them are examined here).

    Returns True (BARREN/unhealthy -> escalate to self-fix) iff there are at least min_run entries
    AND the LAST min_run are ALL a mechanism-failure action (`skip` OR `error` -- FIND-001) AND they
    all share one identical, non-empty cause string (`reason` for skip, `error` for error). Anything
    else -- fewer than min_run entries (not enough evidence yet), any entry in the window where the
    agent genuinely ran (live-pass/wait/trade/...), or mixed/rotating causes (a transient blip, not a
    sustained single-cause mechanism failure) -- returns False. This mirrors the "AND, never
    OR/majority" discipline cadence.py's compound kind already established for this codebase
    (REQ-LV-101): only a real, sustained, single-cause mechanical rejection or crash escalates.
    """
    if len(trace_tail) < min_run:
        return False
    window = trace_tail[-min_run:]
    causes = [_mechanism_failure_cause(entry) for entry in window]
    if any(cause is None for cause in causes):
        return False
    reasons = set(causes)
    if len(reasons) != 1:
        return False
    (only_reason,) = reasons
    return bool(only_reason)


# FIND-005: allowlist-only (not a blocklist) safe-char set for trace-derived free text that will be
# embedded in an autonomous self-fix.sh spawn's task prompt (a `--dangerously-skip-permissions`
# claude spawn with ZERO human confirmation gate -- self-fix.sh:75-84). Keeps letters, digits,
# spaces, and the small set of punctuation actually seen in real reason/error strings across this
# codebase (". , : ( ) = / -"); drops everything else, including every shell/prompt-injection
# metacharacter (backtick, $, quotes, backslash, pipes, semicolons, angle/square/curly brackets,
# newlines, control chars, ...) rather than trying to escape them.
_SAFE_PROMPT_CHARS_RE = re.compile(r"[^A-Za-z0-9 ._,:()=/-]")


def sanitize_for_prompt(text: object, max_len: int = 200) -> str:
    """Neutralizes ONE piece of trace-derived free text (a loop's own `reason`/`error` field, or a
    registry-derived slot id) before it is embedded in self-fix.sh's task prompt. `reason`/`error`
    text ultimately originates from loop-controlled/environment-influenced strings, not reviewed
    human input, so it must never reach an autonomous, unconfirmed agent spawn's prompt
    un-neutralized (FIND-005). Fail-soft (never raises): non-string input returns "". Also hard-caps
    length so a single oversized trace field can never balloon the prompt.
    """
    if not isinstance(text, str):
        return ""
    return _SAFE_PROMPT_CHARS_RE.sub("", text)[:max_len]


def _main():
    if len(sys.argv) < 2:
        print(
            "usage: earning-health.py is-barren [min_run] < trace_tail.jsonl\n"
            "       earning-health.py sanitize-reason [max_len] < raw_text",
            file=sys.stderr,
        )
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
    elif cmd == "sanitize-reason":
        # FIND-005: the shell caller's single, testable seam for neutralizing trace-derived free
        # text before it reaches self-fix.sh's autonomous spawn prompt (see sanitize_for_prompt's
        # own docstring). Reads the raw text whole from stdin (not JSONL -- the caller already
        # extracts the bare reason/error string before piping it in here).
        max_len = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        raw = sys.stdin.read().strip()
        print(sanitize_for_prompt(raw, max_len))
        sys.exit(0)
    else:
        print(f"unknown subcommand: {cmd!r}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    _main()
