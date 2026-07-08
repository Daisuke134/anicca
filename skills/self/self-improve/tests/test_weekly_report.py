"""test_weekly_report.py — REQ-LV-111 wiring test (Tier2, real temp ledger files, real evaluator
modules loaded -- only the network/browser-free evaluate_stage1 path, no side effects beyond the
temp ledger). Proves weekly_report.run() correctly buckets rows into this-week/last-week (Mon-Sun
JST), scores each half through the REAL per-loop evaluator, and appends the beats_previous_week
verdict to a SEPARATE weekly file (F-ITER3-2 fix) without corrupting the existing metrics ledger.
"""
import datetime
import json
import os
import sys
import tempfile
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekly_report as WR  # noqa: E402

JST = zoneinfo.ZoneInfo("Asia/Tokyo")

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


TMP = tempfile.mkdtemp()

# this-week rows (high views) vs last-week rows (low views) -> this week should beat last week
today = datetime.date(2026, 7, 8)  # a Wednesday
this_monday = today - datetime.timedelta(days=today.weekday())
last_monday = this_monday - datetime.timedelta(days=7)


def ts_for(date_obj):
    return int(datetime.datetime.combine(date_obj, datetime.time(12, 0), tzinfo=JST).timestamp())


ledger = os.path.join(TMP, "clip-ledger.jsonl")
rows = [
    {"ts": ts_for(this_monday), "views": 5000, "earn_usdc": 1.0},   # this week
    {"ts": ts_for(last_monday), "views": 100, "earn_usdc": 0.1},    # last week
]
with open(ledger, "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")

record = WR.run("clip", ledger_path=ledger, today=today.isoformat())
chk("weekly_report: week_start is the correct Monday", record["week_start"], this_monday.isoformat())
chk("weekly_report: this-week (high views) beats last-week (low views)", record["beats_previous_week"], True)
chk("weekly_report: combined_score is a real number > 0", record["combined_score"] > 0, True)

# F-ITER3-2 fix: the weekly record must NOT land in the same file cadence-evidence.py reads for
# row-exists evidence -- it goes to a sibling "-weekly" file instead.
weekly_path = WR._weekly_output_path(ledger)
chk("weekly_report: weekly record written to a SEPARATE sibling file, not the ledger itself",
    weekly_path != ledger, True)
chk("weekly_report: sibling weekly file path is the expected <ledger>-weekly.jsonl",
    weekly_path, os.path.join(TMP, "clip-ledger-weekly.jsonl"))

with open(ledger) as f:
    ledger_lines = [json.loads(l) for l in f if l.strip()]
chk("F-ITER3-2 fix: original metrics ledger UNCHANGED (still exactly 2 rows, not 3)", len(ledger_lines), 2)
chk("weekly_report: original rows untouched (still have views field)", "views" in ledger_lines[0], True)

with open(weekly_path) as f:
    weekly_lines = [json.loads(l) for l in f if l.strip()]
chk("weekly_report: the weekly record landed in the sibling file", len(weekly_lines), 1)
chk("weekly_report: sibling file's record has the expected shape", weekly_lines[0]["beats_previous_week"], True)

# a losing week: this week's ledger is EMPTY (no rows at all) -> score 0, must not beat a real
# positive last week (never a false "improvement")
ledger2 = os.path.join(TMP, "clip-ledger-losing.jsonl")
with open(ledger2, "w") as f:
    f.write(json.dumps({"ts": ts_for(last_monday), "views": 9000, "earn_usdc": 5.0}) + "\n")
record2 = WR.run("clip", ledger_path=ledger2, today=today.isoformat())
chk("weekly_report: empty this-week vs a real last-week -> beats_previous_week=False (honest)",
    record2["beats_previous_week"], False)

# ---------------------------------------------------------------------------
# F-ITER3-2 REGRESSION: the exact false-positive iteration-3 adversary review reproduced live —
# running weekly_report on a metrics ledger that has ZERO rows for today must NOT make
# cadence-evidence.py's row-exists check for that loop suddenly read "met=true" for today.
# ---------------------------------------------------------------------------
import importlib.util  # noqa: E402

# .../skills/self/self-improve/tests/test_weekly_report.py -> up 3 levels -> .../skills/self/
_SELF_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location("cadence_evidence", os.path.join(_SELF_DIR, "cadence-evidence.py"))
CE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CE)

today_jst_str = datetime.datetime.now(tz=JST).date().isoformat()
empty_ledger = os.path.join(TMP, "affiliate-metrics-empty.jsonl")
open(empty_ledger, "w").close()  # zero rows today -- no real activity happened
os.environ["AFFILIATE_METRICS_PATH"] = empty_ledger

status_before = CE.status_for_loop("affiliate")
chk("F-ITER3-2 regression: BEFORE weekly_report, empty-today ledger -> met=false", status_before["met"], False)

WR.run("affiliate", ledger_path=empty_ledger, today=today_jst_str)  # simulates the weekly audit step

status_after = CE.status_for_loop("affiliate")
chk("F-ITER3-2 regression: AFTER weekly_report runs on the SAME ledger, still met=false "
    "(no false-positive cadence contamination -- this is the exact bug iteration-3 reproduced)",
    status_after["met"], False)

del os.environ["AFFILIATE_METRICS_PATH"]

print(f"=== test_weekly_report: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
