"""test_cadence.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-020/021/022/035/036/037/040 — cadence_met() 5-kind dispatcher + streak().
cadence.py does not exist yet -> ImportError -> RED.

cadence_met(today_jst_date, contract, evidence) -> bool  (REQ-LV-101, pure, no I/O)
streak(evidence_by_date, today_jst_date, contract) -> int  (REQ-LV-103, pure)

★ PROP-LV-040 is the G1 iteration-2 blocking-finding regression test: pm-earner's hourly-pass
sub-condition must use kind="recency" (pure elapsed-seconds check), NOT kind="pass-marker"
(JST-calendar-day check) — a pass-marker check would wrongly say "healthy" for a loop that ran
ONCE at 00:01 JST and then sat dead for the rest of the day. This is the single most important
test in this file; do not weaken it.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from cadence import cadence_met, streak  # RED: cadence.py does not exist yet

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


# ---------------------------------------------------------------------------
# PROP-LV-020: kind == "row-exists" (clip/affiliate/video/gig)
# ---------------------------------------------------------------------------
row_exists_contract = {"kind": "row-exists", "cadence": "1/day", "unit": "reel", "boundary_tz": "Asia/Tokyo"}
chk("row-exists: today in event_dates -> true",
    cadence_met("2026-07-08", row_exists_contract, {"event_dates": ["2026-07-08"]}), True)
chk("row-exists: only yesterday -> false",
    cadence_met("2026-07-08", row_exists_contract, {"event_dates": ["2026-07-07"]}), False)
chk("row-exists: empty event_dates -> false",
    cadence_met("2026-07-08", row_exists_contract, {"event_dates": []}), False)
# JST day-boundary case: UTC 2026-07-08T16:00Z == JST 2026-07-09T01:00 — the CALLER is responsible
# for converting to JST calendar date before building event_dates; cadence_met itself just compares
# strings. This case proves the evidence passed in must already be JST-correct (2026-07-09, not
# the UTC-naive 2026-07-08) for a pass that really happened at JST 01:00 on the 9th to count for
# the 9th and NOT be mistakenly credited to (or missed for) the 8th.
chk("row-exists: JST-correct date from a UTC-midnight-crossing ts credits the right JST day",
    cadence_met("2026-07-09", row_exists_contract, {"event_dates": ["2026-07-09"]}), True)
chk("row-exists: same UTC-crossing ts must NOT satisfy the UTC-naive (wrong) day",
    cadence_met("2026-07-08", row_exists_contract, {"event_dates": ["2026-07-09"]}), False)

# ---------------------------------------------------------------------------
# PROP-LV-035: kind == "increment" (bounty)
# ---------------------------------------------------------------------------
increment_contract = {"kind": "increment", "field": "checked", "boundary_tz": "Asia/Tokyo"}
chk("increment: today=5 prev=3 (+2) -> true",
    cadence_met("2026-07-08", increment_contract, {"today_value": 5, "previous_value": 3}), True)
chk("increment: today=5 prev=5 (0 delta) -> FALSE (row-existence alone is not enough)",
    cadence_met("2026-07-08", increment_contract, {"today_value": 5, "previous_value": 5}), False)
chk("increment: today=3 prev=5 (decrease, defensive) -> false",
    cadence_met("2026-07-08", increment_contract, {"today_value": 3, "previous_value": 5}), False)

# ---------------------------------------------------------------------------
# PROP-LV-036: kind == "pass-marker" (founder-loop)
# ---------------------------------------------------------------------------
pass_marker_contract = {"kind": "pass-marker", "source": "STATE.md mtime", "boundary_tz": "Asia/Tokyo"}
chk("pass-marker: marker_jst_date == today -> true (even if ledger is empty)",
    cadence_met("2026-07-08", pass_marker_contract, {"marker_jst_date": "2026-07-08"}), True)
chk("pass-marker: marker_jst_date == yesterday -> false",
    cadence_met("2026-07-08", pass_marker_contract, {"marker_jst_date": "2026-07-07"}), False)

# ---------------------------------------------------------------------------
# PROP-LV-040 (G1 blocking finding — THE critical regression test): kind == "recency"
# Exact scenario from spec: marker at 00:01 JST, now at 21:00 JST same day, max_age_min=40
# (matches healthcheck-runtime-loop.sh:97's existing earner.log staleness threshold for pm-earner).
# ---------------------------------------------------------------------------
recency_contract = {"kind": "recency", "source": "earner.log mtime", "max_age_min": 40}
import datetime, zoneinfo
JST = zoneinfo.ZoneInfo("Asia/Tokyo")
marker_0001 = int(datetime.datetime(2026, 7, 8, 0, 1, 0, tzinfo=JST).timestamp())
now_2100 = int(datetime.datetime(2026, 7, 8, 21, 0, 0, tzinfo=JST).timestamp())
chk("recency: G1 SCENARIO — marker=00:01 JST, now=21:00 JST, max_age_min=40 -> FALSE "
    "(00:01-only pass must NOT read as healthy at 21:00 — this is the exact bug G1 caught)",
    cadence_met("2026-07-08", recency_contract, {
        "marker_epoch_seconds": marker_0001, "now_epoch_seconds": now_2100,
    }), False)
chk("recency: elapsed 1500s (25min) < max_age_min*60(2400s) -> true",
    cadence_met("2026-07-08", recency_contract, {
        "marker_epoch_seconds": 1000000, "now_epoch_seconds": 1000000 + 1500,
    }), True)
chk("recency: elapsed exactly 2400s (40min boundary) -> true (<= inclusive)",
    cadence_met("2026-07-08", recency_contract, {
        "marker_epoch_seconds": 1000000, "now_epoch_seconds": 1000000 + 2400,
    }), True)
chk("recency: elapsed 2401s (1s past boundary) -> false",
    cadence_met("2026-07-08", recency_contract, {
        "marker_epoch_seconds": 1000000, "now_epoch_seconds": 1000000 + 2401,
    }), False)

# ---------------------------------------------------------------------------
# PROP-LV-037: kind == "compound" (pm-earner: hourly-pass(recency) AND daily-redeem(row-exists))
# hourly-pass's true/false MUST be derived from a real recency evaluation (not a hardcoded bool) —
# this test wires the SAME recency contract/evidence used in PROP-LV-040 above into the compound
# evidence, proving compound actually calls cadence_met recursively rather than trusting an opaque
# flag.
# ---------------------------------------------------------------------------
compound_contract = {
    "kind": "compound",
    "conditions": [
        {"id": "hourly-pass", "kind": "recency", "cadence": "1/hour", "source": "earner.log mtime", "max_age_min": 40},
        {"id": "daily-redeem", "kind": "row-exists", "cadence": "1/day", "unit": "redeem", "boundary_tz": "Asia/Tokyo"},
    ],
}
chk("compound: hourly-pass=true(recency) AND daily-redeem=true -> true",
    cadence_met("2026-07-08", compound_contract, {"by_condition": {
        "hourly-pass": {"marker_epoch_seconds": 1000000, "now_epoch_seconds": 1000000 + 60},
        "daily-redeem": {"event_dates": ["2026-07-08"]},
    }}), True)
chk("compound: hourly-pass=true(recency) AND daily-redeem=false -> FALSE (AND, not OR)",
    cadence_met("2026-07-08", compound_contract, {"by_condition": {
        "hourly-pass": {"marker_epoch_seconds": 1000000, "now_epoch_seconds": 1000000 + 60},
        "daily-redeem": {"event_dates": ["2026-07-07"]},
    }}), False)
chk("compound: hourly-pass=false(recency, G1 stale case) AND daily-redeem=true -> false",
    cadence_met("2026-07-08", compound_contract, {"by_condition": {
        "hourly-pass": {"marker_epoch_seconds": marker_0001, "now_epoch_seconds": now_2100},
        "daily-redeem": {"event_dates": ["2026-07-08"]},
    }}), False)
chk("compound: both false -> false",
    cadence_met("2026-07-08", compound_contract, {"by_condition": {
        "hourly-pass": {"marker_epoch_seconds": marker_0001, "now_epoch_seconds": now_2100},
        "daily-redeem": {"event_dates": ["2026-07-07"]},
    }}), False)

# ---------------------------------------------------------------------------
# F-VERIF-2 (Phase 5 hardening, non-blocking finding turned into a regression guard): compound
# with an EMPTY conditions list must NOT be vacuously true. Pure "AND over zero sub-contracts"
# logic returns True, but operationally that means "nothing was actually verified" — the same
# "artifact/contract exists but proves nothing" blind spot G1 already fixed once (pass-marker vs
# recency). A misconfigured empty conditions list must read as NOT met.
# ---------------------------------------------------------------------------
chk("compound: empty conditions list -> FALSE (not vacuous-true; nothing was actually verified)",
    cadence_met("2026-07-08", {"kind": "compound", "conditions": []}, {"by_condition": {}}), False)

# ---------------------------------------------------------------------------
# F-VERIF-3 (Phase 5 hardening, non-blocking finding turned into a regression guard): recency with
# a marker in the FUTURE (now < marker — clock skew or a tampered mtime) must be treated as NOT
# met, never as healthy. Fail-closed, consistent with record_earn.py/positions.py/ytdlp_parse.py's
# "never fabricate" design across this codebase.
# ---------------------------------------------------------------------------
chk("recency: marker in the future (now < marker, clock skew) -> FALSE (fail-closed, not fail-open)",
    cadence_met("2026-07-08", {"kind": "recency", "max_age_min": 40},
                {"marker_epoch_seconds": 2000000, "now_epoch_seconds": 1000000}), False)

# ---------------------------------------------------------------------------
# PROP-LV-022: streak() — kind-agnostic, works off whatever cadence_met returns per day
# ---------------------------------------------------------------------------
def evidence_for(dates_true):
    """Build an evidence_by_date map for a row-exists contract where each key's own date is
    considered 'met' iff that date string is in dates_true (each day's evidence lists itself)."""
    return {d: {"event_dates": [d] if d in dates_true else []} for d in
            ["2026-07-04", "2026-07-05", "2026-07-06", "2026-07-07", "2026-07-08"]}

streak_contract = row_exists_contract
chk("streak: 3 consecutive days met (07-06,07,08) -> 3",
    streak(evidence_for(["2026-07-06", "2026-07-07", "2026-07-08"]), "2026-07-08", streak_contract), 3)
chk("streak: 2 days met then a gap (07-06 missing) resets — does not add across the gap",
    streak(evidence_for(["2026-07-04", "2026-07-07", "2026-07-08"]), "2026-07-08", streak_contract), 2)
chk("streak: today itself missing -> 0",
    streak(evidence_for(["2026-07-07"]), "2026-07-08", streak_contract), 0)

print(f"=== test_cadence: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
