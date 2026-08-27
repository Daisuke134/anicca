"""test_funnel.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-005 / REQ-LV-016 — summarize_bounty_funnel(gated, attempts_rows) -> {checked, survivors,
claimed, submitted, stalled} (all int). Pure: gated is the parsed state/gated.json dict
({"survivors": [...], "checked": int}); attempts_rows are parsed state/attempts.jsonl rows.

claimed = rows with status=="claim" AND pr is None (claimed but not yet a PR — not double-counted
into submitted or stalled). submitted = rows whose pr is non-null (a PR was actually opened,
regardless of the claim status word). stalled = rows with status=="stalled" (never counted in
claimed even if a bare "claim" word appears elsewhere — no double counting, per spec).

funnel.py does not exist yet -> ImportError -> RED.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from funnel import summarize_bounty_funnel  # RED: does not exist yet

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


chk("survivors empty + attempts empty -> all zero (checked still reported from gated)",
    summarize_bounty_funnel({"survivors": [], "checked": 0}, []),
    {"checked": 0, "survivors": 0, "claimed": 0, "submitted": 0, "stalled": 0})

chk("checked=38, survivors=0, no attempts -> checked reflects gated.json, rest 0",
    summarize_bounty_funnel({"survivors": [], "checked": 38}, []),
    {"checked": 38, "survivors": 0, "claimed": 0, "submitted": 0, "stalled": 0})

chk("status:claim, pr:null (1 row) -> claimed:1, submitted:0",
    summarize_bounty_funnel({"survivors": [], "checked": 5}, [{"status": "claim", "pr": None}]),
    {"checked": 5, "survivors": 0, "claimed": 1, "submitted": 0, "stalled": 0})

chk("pr non-null -> counted in submitted (not double-counted in claimed)",
    summarize_bounty_funnel({"survivors": [], "checked": 5}, [{"status": "claim", "pr": "https://github.com/x/y/pull/1"}]),
    {"checked": 5, "survivors": 0, "claimed": 0, "submitted": 1, "stalled": 0})

chk("status:stalled -> counted in stalled, NOT double-counted from claimed",
    summarize_bounty_funnel({"survivors": [], "checked": 5}, [{"status": "stalled", "pr": None}]),
    {"checked": 5, "survivors": 0, "claimed": 0, "submitted": 0, "stalled": 1})

chk("survivors list with 3 entries -> survivors:3",
    summarize_bounty_funnel({"survivors": [{"id": 1}, {"id": 2}, {"id": 3}], "checked": 40}, []),
    {"checked": 40, "survivors": 3, "claimed": 0, "submitted": 0, "stalled": 0})

chk("mixed attempts: 1 claimed(no pr), 1 submitted(pr), 1 stalled -> all buckets correct, no double count",
    summarize_bounty_funnel(
        {"survivors": [{"id": 1}], "checked": 10},
        [
            {"status": "claim", "pr": None},
            {"status": "claim", "pr": "https://github.com/x/y/pull/2"},
            {"status": "stalled", "pr": None},
        ],
    ),
    {"checked": 10, "survivors": 1, "claimed": 1, "submitted": 1, "stalled": 1})

print(f"=== test_funnel (bounty): {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
