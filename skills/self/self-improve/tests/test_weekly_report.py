"""test_weekly_report.py — REQ-LV-111 wiring test (Tier2, real temp ledger files, real evaluator
modules loaded -- only the network/browser-free evaluate_stage1 path, no side effects beyond the
temp ledger). Proves weekly_report.run() correctly buckets rows into this-week/last-week (Mon-Sun
JST), scores each half through the REAL per-loop evaluator, and appends the beats_previous_week
verdict to the ledger without corrupting the existing rows.
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

with open(ledger) as f:
    lines = [json.loads(l) for l in f if l.strip()]
chk("weekly_report: original 2 rows preserved + 1 new record appended", len(lines), 3)
chk("weekly_report: original rows untouched (still have views field)", "views" in lines[0], True)

# a losing week: this week's ledger is EMPTY (no rows at all) -> score 0, must not beat a real
# positive last week (never a false "improvement")
ledger2 = os.path.join(TMP, "clip-ledger-losing.jsonl")
with open(ledger2, "w") as f:
    f.write(json.dumps({"ts": ts_for(last_monday), "views": 9000, "earn_usdc": 5.0}) + "\n")
record2 = WR.run("clip", ledger_path=ledger2, today=today.isoformat())
chk("weekly_report: empty this-week vs a real last-week -> beats_previous_week=False (honest)",
    record2["beats_previous_week"], False)

print(f"=== test_weekly_report: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
