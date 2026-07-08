"""test_cost_events_and_spend.py — RED (Phase 2a, feature claude-p-ceo-loop).
PROP-CEO-004 (REQ-CEO-020/021): build_cost_event / monthly_spend_by_loop / weekly_spend_by_loop,
agent-os `orchestrator/budgets.py::monthly_spend_by_agent`/`current_month_key` copy+tweak
(agent->loop) + weekly_report.py::_rows_in_week-style JST week bucketing (new, for bandit reward).
B12 fallback rule: pm-earner has no cost-event rows -> absent from the dict (not zero-filled).

ceo/budget.py does not exist yet -> ImportError -> RED.
"""
import datetime
import os
import sys
import zoneinfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from budget import build_cost_event, monthly_spend_by_loop, weekly_spend_by_loop  # noqa: E402  RED: does not exist yet

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


def chk_true(name, cond):
    chk(name, bool(cond), True)


def iso_utc(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- build_cost_event: {ts, month_key(UTC), loop, usd_estimate} ----------
ev = build_cost_event("2026-06-15T12:00:00Z", "clip", 1.0)
chk("build_cost_event: ts passed through unchanged", ev["ts"], "2026-06-15T12:00:00Z")
chk("build_cost_event: month_key derived as UTC YYYY-MM", ev["month_key"], "2026-06")
chk("build_cost_event: loop passed through unchanged", ev["loop"], "clip")
chk("build_cost_event: usd_estimate passed through unchanged", ev["usd_estimate"], 1.0)

# ---------- monthly_spend_by_loop: UTC calendar-month aggregation, per-loop ----------
june_rows = [
    build_cost_event("2026-06-01T00:00:00Z", "clip", 1.0),
    build_cost_event("2026-06-15T00:00:00Z", "clip", 2.0),
    build_cost_event("2026-06-30T23:59:00Z", "clip", 3.0),
    build_cost_event("2026-07-01T00:00:00Z", "clip", 100.0),  # month boundary -- excluded from June
]
monthly = monthly_spend_by_loop(june_rows, "2026-06")
chk("monthly_spend_by_loop: same-month 3 events sum to 6.0", monthly.get("clip"), 6.0)
chk_true("monthly_spend_by_loop: July event ($100) did not leak into June aggregate", monthly.get("clip") != 106.0)

# ---------- weekly_spend_by_loop: JST Mon-Sun week bucket, per-loop (bandit reward denominator) ----------
# Build a known JST Monday-midnight programmatically (no hardcoded weekday assumption).
some_jst_day = datetime.datetime(2026, 6, 17, 10, 0, tzinfo=JST)  # arbitrary anchor
monday_jst = (some_jst_day - datetime.timedelta(days=some_jst_day.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
in_week_a = monday_jst + datetime.timedelta(hours=1)            # Mon 01:00 JST, this week
in_week_b = monday_jst + datetime.timedelta(days=6, hours=23)   # Sun 23:00 JST, still this week (< week_end)
prev_week = monday_jst - datetime.timedelta(hours=1)            # Sun 23:00 JST, PREVIOUS week (before this Monday's midnight)

week_rows = [
    build_cost_event(iso_utc(in_week_a.astimezone(datetime.timezone.utc)), "gig", 5.0),
    build_cost_event(iso_utc(in_week_b.astimezone(datetime.timezone.utc)), "gig", 7.0),
    build_cost_event(iso_utc(prev_week.astimezone(datetime.timezone.utc)), "gig", 1000.0),  # excluded, previous week
]
weekly = weekly_spend_by_loop(week_rows, monday_jst.date().isoformat())
chk("weekly_spend_by_loop: two in-week events sum to 12.0 (5.0+7.0)", weekly.get("gig"), 12.0)
chk_true("weekly_spend_by_loop: previous-week event ($1000) excluded from this week's bucket", weekly.get("gig") != 1012.0)

# ---------- B12 fallback rule: pm-earner never has cost-event rows -> absent, not zero-filled ----------
no_pm_rows = [build_cost_event("2026-06-05T00:00:00Z", "clip", 1.0)]
monthly_no_pm = monthly_spend_by_loop(no_pm_rows, "2026-06")
weekly_no_pm = weekly_spend_by_loop(no_pm_rows, "2026-06-01")
chk_true("B12: monthly_spend_by_loop has no 'pm-earner' key (not zero-filled)", "pm-earner" not in monthly_no_pm)
chk_true("B12: weekly_spend_by_loop has no 'pm-earner' key (not zero-filled)", "pm-earner" not in weekly_no_pm)
chk("B12: caller reads pm-earner via dict.get(loop, 0.0) -> 0.0 default, no new branch needed", monthly_no_pm.get("pm-earner", 0.0), 0.0)

print(f"=== test_cost_events_and_spend: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
