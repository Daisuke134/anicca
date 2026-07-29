"""test_funnel.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-004 / REQ-LV-015 — summarize_gig_funnel(applied_rows) -> {applied, replied, won, paid}
(all int). Pure: input is ONLY the already-collected `~/gig/applied.jsonl` rows for the current
pass (CloakBrowser's real reads produced these rows elsewhere — this function adds zero new browser
access, per spec).

Design choice (documented here since the spec's own examples are consistent with either a raw
per-status count or a CUMULATIVE funnel; a funnel's business meaning — 応募→返信率→受注率→入金,
REQ-LV-110's own gig metric — is cumulative, so a row currently at 検収完了 also counts toward
`applied`/`replied`/`won`, since it necessarily passed through those stages): a row's `status`
represents the FURTHEST stage that applicant/case has reached; each bucket counts every row whose
furthest stage is >= that bucket. "受注"/"成約" are synonyms for the `won` bucket; "検収完了"/"支払"
are synonyms for the `paid` bucket (spec's own "/" notation).

funnel.py does not exist yet -> ImportError -> RED.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from funnel import summarize_gig_funnel  # RED: does not exist yet

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


chk("empty applied_rows -> all zero",
    summarize_gig_funnel([]),
    {"applied": 0, "replied": 0, "won": 0, "paid": 0})

chk("3 rows all status=applied -> applied:3, rest 0",
    summarize_gig_funnel([{"status": "applied"}, {"status": "applied"}, {"status": "applied"}]),
    {"applied": 3, "replied": 0, "won": 0, "paid": 0})

chk("mixed: applied + replied + 検収完了 -> cumulative funnel counts",
    summarize_gig_funnel([
        {"status": "applied"},
        {"status": "replied"},
        {"status": "検収完了"},
    ]),
    {"applied": 3, "replied": 2, "won": 1, "paid": 1})

chk("受注 synonym counts toward won (same as 成約)",
    summarize_gig_funnel([{"status": "受注"}, {"status": "成約"}]),
    {"applied": 2, "replied": 2, "won": 2, "paid": 0})

chk("支払 synonym counts toward paid (same as 検収完了)",
    summarize_gig_funnel([{"status": "支払"}]),
    {"applied": 1, "replied": 1, "won": 1, "paid": 1})

chk("unrecognized/housekeeping status rows (e.g. pass-log rows, not real applications) are ignored",
    summarize_gig_funnel([{"status": "no_new_client_reply"}, {"status": "applied"}]),
    {"applied": 1, "replied": 0, "won": 0, "paid": 0})

print(f"=== test_funnel (gig): {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
