"""test_escalation_and_reporting.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-015 (B10修正, REQ-CEO-060): validate_escalation_schema (justification presence gate only,
never content judgment) + the B10 disproof (weekly_realized_profit_usd must be the
realized_profit_usd()-converted value).
PROP-CEO-016 (m1修正, REQ-CEO-071): is_ceo_weekly_due (Monday-origin week gate).
PROP-CEO-017 (REQ-CEO-080/081): build_ceo_report_args / build_evidence_pointer.

ceo/allocator.py does not exist yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from allocator import (  # noqa: E402  RED: does not exist yet
    build_ceo_report_args,
    build_evidence_pointer,
    is_ceo_weekly_due,
    realized_profit_usd,
    validate_escalation_schema,
)

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


def chk_true(name, cond):
    chk(name, bool(cond), True)


# ---------- PROP-CEO-015: validate_escalation_schema (presence gate, never content judgment) ----------
chk("validate_escalation_schema: justification='' -> False (empty string rejected)", validate_escalation_schema({"justification": ""}), False)
chk("validate_escalation_schema: justification key missing entirely -> False", validate_escalation_schema({}), False)
chk(
    "validate_escalation_schema: any non-empty justification -> True (content is NOT judged, per REQ-CEO-061)",
    validate_escalation_schema({"justification": "realized $50 last week, scaling fleet 2->4"}),
    True,
)

# B10 disproof: JPY-denominated loop, raw 7500 JPY @150 -> 50.0 USD converted. The escalation
# record's weekly_realized_profit_usd MUST be this converted 50.0, never the raw 7500 (INV-CEO-1).
fx = {"jpy_usd_rate": 150.0}
jpy_entries = [{"amount": 0, "currency": "usd"}, {"amount": 7500, "currency": "jpy"}]
converted = realized_profit_usd(jpy_entries, fx)
chk("B10: realized_profit_usd(7500 JPY @150) -> 50.0 USD (the value the record must carry)", converted, 50.0)
record = {"justification": "scaling fleet based on realized profit", "weekly_realized_profit_usd": converted}
chk_true("B10: schema-valid escalation record built from the converted value", validate_escalation_schema(record))
chk("B10: record's weekly_realized_profit_usd is 50.0, not the raw 7500", record["weekly_realized_profit_usd"], 50.0)

# ---------- PROP-CEO-016: is_ceo_weekly_due (Monday-origin, no private-symbol cross-module import) ----------
chk("is_ceo_weekly_due: last_run Mon 2026-07-06, today Tue 2026-07-07 (same week) -> False", is_ceo_weekly_due("2026-07-06", "2026-07-07"), False)
chk("is_ceo_weekly_due: last_run Mon 2026-06-29, today Mon 2026-07-06 (next week) -> True", is_ceo_weekly_due("2026-06-29", "2026-07-06"), True)
chk("is_ceo_weekly_due: last_run=None (first ever run) -> True", is_ceo_weekly_due(None, "2026-07-06"), True)

# ---------- PROP-CEO-017: build_ceo_report_args / build_evidence_pointer ----------
args_earning = build_ceo_report_args(company_score=15.0, actions_summary="paused: bounty", verification_summary="beats_previous_week=true, rollback_fired=false")
chk("build_ceo_report_args: earned_usdc mirrors company_score, no independent recompute", args_earning["earned_usdc"], 15.0)
chk_true("build_ceo_report_args: summary includes the actions summary", "paused: bounty" in args_earning["summary"])
chk_true("build_ceo_report_args: summary includes the verification summary", "beats_previous_week=true" in args_earning["summary"])
chk("build_ceo_report_args: company_score=15.0 (>0) -> result='success'", args_earning["result"], "success")

args_zero = build_ceo_report_args(company_score=0.0, actions_summary="none", verification_summary="beats_previous_week=false, rollback_fired=false")
chk("build_ceo_report_args: company_score<=0 -> result='queue-empty' (mirrors founderReportArgs pattern)", args_zero["result"], "queue-empty")

pointer = build_evidence_pointer("/home/life-manager/.anicca-founder/state/ceo-verification.jsonl", "2026-06-29")
chk_true("build_evidence_pointer: non-empty roster -> includes the real file path", "/home/life-manager/.anicca-founder/state/ceo-verification.jsonl" in pointer)
chk_true("build_evidence_pointer: non-empty roster -> includes the week_start pointer value", "2026-06-29" in pointer)
chk_true("build_evidence_pointer: non-empty roster -> is NOT the bare 'none' string alone", pointer != "none")

pointer_empty = build_evidence_pointer(None, None)
chk("build_evidence_pointer: empty roster (no path) -> 'none: no loops registered yet' (satisfies lr_valid_evidence gate)", pointer_empty, "none: no loops registered yet")

print(f"=== test_escalation_and_reporting: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
