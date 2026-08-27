#!/usr/bin/env python3
"""funnel.py — summarize_bounty_funnel(gated, attempts_rows) -> {checked, survivors, claimed,
submitted, stalled} (REQ-LV-016). Pure: gated is the parsed state/gated.json dict
({"survivors": [...], "checked": int}); attempts_rows are parsed state/attempts.jsonl rows.

claimed = rows with status=="claim" AND pr is falsy (claimed but not yet a PR — never
double-counted into submitted or stalled). submitted = rows whose pr is non-null (a PR was
actually opened), regardless of the claim status word. stalled = rows with status=="stalled"
(never counted in claimed even if a bare "claim" word appears elsewhere). No double counting.
"""


def summarize_bounty_funnel(gated, attempts_rows):
    gated = gated or {}
    checked = gated.get("checked", 0)
    survivors = len(gated.get("survivors") or [])
    claimed = submitted = stalled = 0
    for row in attempts_rows or []:
        row = row or {}
        pr = row.get("pr")
        status = row.get("status")
        if pr:
            submitted += 1
        elif status == "stalled":
            stalled += 1
        elif status == "claim":
            claimed += 1
    return {
        "checked": checked,
        "survivors": survivors,
        "claimed": claimed,
        "submitted": submitted,
        "stalled": stalled,
    }
