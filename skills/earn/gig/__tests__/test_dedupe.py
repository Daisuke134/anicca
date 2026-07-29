"""test_dedupe.py — F-VERIF-5 fix regression test: dedupe_latest_status(rows) keeps only the
LAST-occurring row per requestId (append-only file order = chronological = most recent status),
proving the exact multi-count scenario the Phase 5 hardening review flagged
(applied->replied->受注 for the SAME requestId no longer triple-counts through
summarize_gig_funnel).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from funnel import dedupe_latest_status, summarize_gig_funnel  # noqa: E402

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


rows = [
    {"requestId": "R1", "status": "applied"},
    {"requestId": "R1", "status": "replied"},
    {"requestId": "R1", "status": "受注"},
]
deduped = dedupe_latest_status(rows)
chk("dedupe: 3 rows same requestId -> 1 row kept", len(deduped), 1)
chk("dedupe: kept row is the LATEST status (受注)", deduped[0]["status"], "受注")

summary_raw = summarize_gig_funnel(rows)
chk("F-VERIF-5 regression proof: raw rows triple-count (the bug)", summary_raw, {"applied": 3, "replied": 2, "won": 1, "paid": 0})
summary_fixed = summarize_gig_funnel(dedupe_latest_status(rows))
chk("F-VERIF-5 fix: deduped rows count exactly ONE real application",
    summary_fixed, {"applied": 1, "replied": 1, "won": 1, "paid": 0})

# multiple distinct requestIds each with their own progression -> each counted once
rows2 = [
    {"requestId": "R1", "status": "applied"},
    {"requestId": "R2", "status": "applied"},
    {"requestId": "R2", "status": "replied"},
    {"requestId": "R3", "status": "検収完了"},
]
deduped2 = dedupe_latest_status(rows2)
chk("dedupe: 3 distinct requestIds -> 3 rows kept (not merged across ids)", len(deduped2), 3)
chk("dedupe: multi-id summary correct",
    summarize_gig_funnel(deduped2), {"applied": 3, "replied": 2, "won": 1, "paid": 1})

# rows without requestId pass through unchanged (never dropped)
rows3 = [{"status": "applied"}, {"requestId": "R1", "status": "applied"}, {"requestId": "R1", "status": "replied"}]
deduped3 = dedupe_latest_status(rows3)
chk("dedupe: rows without requestId are never dropped", len(deduped3), 2)

print(f"=== test_dedupe: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
