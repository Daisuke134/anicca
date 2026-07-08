"""test_gig_cadence_real_evidence.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-036 (required:true evidence-review, spec-review iteration-2's explicit demand — real-production-
ledger evidence, NOT a synthetic fixture) / REQ-GFV-022, REQ-GFV-023 — running
`_gig_activity_event_dates` against the REAL `~/gig/applied.jsonl` must yield `event_dates` covering
EVERY distinct JST calendar day that independently contains a row whose `status` is EXACTLY
`"applied"`, `"replied"`, or a member of `_WON_STATUSES`/`_PAID_STATUSES` — demonstrating ZERO false
negatives against the loop's actual, currently-live, still-growing production ledger (this is the
direct verification spec-review iteration-2 demanded to close BLOCKING-1; NOT a synthetic fixture).

This test computes its OWN independent reference tally (stdlib-only: tolerant epoch/ISO-8601 parse +
the exact-match status vocabulary), then asserts the SUT (`_gig_activity_event_dates`) reproduces
that reference set exactly. It reads the REAL file directly — never a copy, never a fixture — and is
SKIPPED (not failed) if `~/gig/applied.jsonl` is absent in this execution environment (e.g. a fresh
CI box without the live loop's ledger), matching this test's evidence-review nature rather than a
portable unit test.

`cadence-evidence.py` does not export `_gig_activity_event_dates` yet -> AttributeError -> RED.
"""
import datetime
import importlib.util
import json
import os
import sys
import zoneinfo

_SELF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SELF_DIR)
_spec = importlib.util.spec_from_file_location("cadence_evidence", os.path.join(_SELF_DIR, "cadence-evidence.py"))
CE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CE)

JST = zoneinfo.ZoneInfo("Asia/Tokyo")
REAL_APPLIED_PATH = os.path.expanduser("~/gig/applied.jsonl")

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


def _read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue
    return rows


def _reference_ts_to_jst_date(ts):
    """Independent reference parser (deliberately NOT calling the SUT's own parser), stdlib-only."""
    if isinstance(ts, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(ts, tz=JST).date().isoformat()
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(ts, str) and ts:
        s = ts.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.datetime.fromisoformat(s)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(JST).date().isoformat()
    return None


_WON_STATUSES = {"受注", "成約"}
_PAID_STATUSES = {"検収完了", "支払"}
_REAL_ACTION_STATUSES = {"applied", "replied"} | _WON_STATUSES | _PAID_STATUSES


if not os.path.exists(REAL_APPLIED_PATH):
    print(f"  SKIPPED — {REAL_APPLIED_PATH} not present in this execution environment "
          f"(evidence-review test, requires the live production ledger)")
    print("=== test_gig_cadence_real_evidence: 0 passed 0 failed (SKIPPED) ===")
    sys.exit(0)

real_rows = _read_jsonl(REAL_APPLIED_PATH)
chk("real ~/gig/applied.jsonl has rows (loop is live)", len(real_rows) > 0, True)

reference_dates = set()
for row in real_rows:
    status = (row or {}).get("status")
    if status not in _REAL_ACTION_STATUSES:
        continue
    d = _reference_ts_to_jst_date(row.get("ts"))
    if d:
        reference_dates.add(d)

chk("independent reference tally against REAL applied.jsonl found >=1 distinct real-activity day",
    len(reference_dates) >= 1, True)

sut_dates = CE._gig_activity_event_dates(real_rows, [])  # RED: AttributeError, does not exist yet

chk("SUT _gig_activity_event_dates(real applied.jsonl) matches the independent reference tally exactly "
    "(zero false negatives against production data)",
    set(sut_dates), reference_dates)

# Sanity floor from the design-doc's own measured session data (§0 Reality check, behavioral-spec.md):
# 2026-06-29 is the earliest JST day this feature's spec claims has real activity. If it's present in
# the real file at all, it must appear in event_dates (never silently dropped).
earliest_known_day = "2026-06-29"
has_earliest_row = any(
    _reference_ts_to_jst_date(r.get("ts")) == earliest_known_day and r.get("status") in _REAL_ACTION_STATUSES
    for r in real_rows
)
if has_earliest_row:
    chk(f"earliest measured real-activity day ({earliest_known_day}) is present in SUT event_dates",
        earliest_known_day in set(sut_dates), True)
else:
    print(f"  (skip earliest-day check — {earliest_known_day} no longer has a qualifying row in the "
          f"current, still-growing real file)")

print(f"=== test_gig_cadence_real_evidence: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
