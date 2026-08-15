"""Tests for lane_health. Run: python3 tests/test_lane_health.py

Every case here is a shape the fleet actually produced or will produce. The first one is
the outage itself: 251 runs reporting success while doing nothing.
"""

import importlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if not ok else ""))
    if not ok:
        FAILURES.append(label)


def fresh():
    """A module bound to an empty state dir, so tests never see each other."""
    os.environ["GIG_STATE_DIR"] = tempfile.mkdtemp()
    import lane_health
    return importlib.reload(lane_health)


def lane_of(verdict, name):
    return next(l for l in verdict["lanes"] if l["lane"] == name)


# --- the outage --------------------------------------------------------------
lh = fresh()
for _ in range(20):
    lh.record("apply", "success", records=0)
row = lane_of(lh.check_all(), "apply")
check("success with zero work is reported down", row["status"] == "down", str(row["problems"]))
check("liveness alone would have said fine", row["success_age_h"] == 0.0, str(row))

# --- real work clears it -----------------------------------------------------
lh = fresh()
lh.record("apply", "success", records=12)
row = lane_of(lh.check_all(), "apply")
check("productive run is healthy", row["status"] == "ok", str(row["problems"]))
check("records are counted", row["records_total"] == 12, str(row))

# --- skip is not success -----------------------------------------------------
lh = fresh()
for _ in range(10):
    lh.record("apply", "skip")
row = lane_of(lh.check_all(), "apply")
check("browser-busy skips never look healthy", row["status"] == "down", str(row["problems"]))
check("skip leaves the success clock untouched", row["success_age_h"] is None, str(row))

# --- staleness ---------------------------------------------------------------
lh = fresh()
lh.record("apply", "success", records=5)
state_path = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "apply.json"
state = json.loads(state_path.read_text())
old = time.time() - 9 * 3600          # apply period is 4h, threshold 8h
state["last_success_at"] = old
state["last_productive_at"] = old
state_path.write_text(json.dumps(state))
row = lane_of(lh.check_all(), "apply")
check("silence past two periods is reported", row["status"] == "down", str(row["problems"]))
check("the report says how long", any("h 実行なし" in p for p in row["problems"]), str(row["problems"]))

# --- a quiet marketplace is not an outage ------------------------------------
lh = fresh()
lh.record("list", "success", records=1)
state_path = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "list.json"
state = json.loads(state_path.read_text())
state["last_success_at"] = time.time() - 3600      # ran an hour ago
state["last_productive_at"] = time.time() - 5 * 3600  # inside 3 x 2-period rope
state_path.write_text(json.dumps(state))
row = lane_of(lh.check_all(), "list")
check("running but idle is tolerated within the productivity rope",
      row["status"] == "ok", str(row["problems"]))

# --- repeated failure --------------------------------------------------------
lh = fresh()
lh.record("reply", "success", records=1)
for _ in range(3):
    lh.record("reply", "failure")
row = lane_of(lh.check_all(), "reply")
check("three consecutive failures are reported", row["status"] == "down", str(row["problems"]))
check("failure count is visible", row["consecutive_failures"] == 3, str(row))

lh.record("reply", "success", records=2)
row = lane_of(lh.check_all(), "reply")
check("one good run clears the failure streak", row["consecutive_failures"] == 0, str(row))

# --- edge-triggered alerting -------------------------------------------------
lh = fresh()
for _ in range(3):
    lh.record("apply", "success", records=0)
first = lh.check_all()
second = lh.check_all()
check("a new problem is announced once", any(c["lane"] == "apply" for c in first["changed"]),
      str(first["changed"]))
check("an unchanged problem stays quiet", not second["changed"], str(second["changed"]))

lh.record("apply", "success", records=7)
third = lh.check_all()
check("recovery is announced", any(c["lane"] == "apply" and c["to"] == "ok"
                                   for c in third["changed"]), str(third["changed"]))

# --- durability --------------------------------------------------------------
lh = fresh()
lh.record("fulfill", "success", records=3)
events = Path(os.environ["GIG_STATE_DIR"]) / "lane-events.jsonl"
check("every run is appended to the event log", events.exists() and events.read_text().count("\n") == 1)
state_path = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "fulfill.json"
check("no temp file is left behind",
      not list(state_path.parent.glob("*.tmp")), str(list(state_path.parent.glob("*.tmp"))))

# --- a lane nobody has touched yet -------------------------------------------
lh = fresh()
row = lane_of(lh.check_all(), "profile")
check("a lane that never ran is down, not silently absent",
      row["status"] == "down" and "一度も成功していない" in row["problems"], str(row))

# --- EDF selection: the anti-starvation property ------------------------------
# Measured: with one model call per pass and a fixed priority order, delivery took the
# call on 37 of 48 daily passes and applications ran 5 times in a week. These cases pin
# the property that made that impossible.

lh = fresh()
verdict = lh.select()
check("with nothing ever run, some lane is selected",
      verdict["selected"] is not None and verdict["due_count"] == len(lh.LANES),
      str(verdict["selected"]))

lh = fresh()
now = time.time()
# Delivery just ran; applications have been silent for a day.
lh.record("fulfill", "success", records=1)
apply_state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "apply.json"
apply_state.parent.mkdir(parents=True, exist_ok=True)
apply_state.write_text(json.dumps({
    "lane": "apply", "last_attempt_at": now - 24 * 3600,
    "last_success_at": now - 24 * 3600, "last_productive_at": now - 24 * 3600,
    "consecutive_failures": 0, "totals": {k: 0 for k in lh.OUTCOMES},
    "records_total": 0, "alert_state": "ok",
}), encoding="utf-8")
verdict = lh.select(now=now)
check("a lane that just ran does not take the pass from a starving one",
      verdict["selected"]["lane"] != "fulfill", str(verdict["selected"]))

lh = fresh()
now = time.time()
# The exact starvation shape: delivery runs every pass, everything else waits.
for _ in range(40):
    lh.record("fulfill", "success", records=1)
verdict = lh.select(now=now)
check("40 consecutive delivery runs cannot keep delivery selected",
      verdict["selected"]["lane"] != "fulfill", str(verdict["selected"]))

lh = fresh()
now = time.time()
# A lane failing forever must not monopolise the schedule: the deadline clock is the
# attempt, not the success. If it were the success, this lane would stay maximally
# overdue and every pass would go to it while the rest starved.
for _ in range(5):
    lh.record("apply", "failure")
verdict = lh.select(now=now)
check("a permanently failing lane does not swallow every pass",
      verdict["selected"]["lane"] != "apply", str(verdict["selected"]))

lh = fresh()
now = time.time()
for lane in lh.LANES:
    state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / f"{lane}.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({
        "lane": lane, "last_attempt_at": now, "last_success_at": now,
        "last_productive_at": now, "consecutive_failures": 0,
        "totals": {k: 0 for k in lh.OUTCOMES}, "records_total": 0, "alert_state": "ok",
    }), encoding="utf-8")
verdict = lh.select(now=now)
check("when every lane is fresh, nothing is forced to run",
      verdict["selected"] is None and verdict["due_count"] == 0, str(verdict))

lh = fresh()
check("every lane maps to a real gig_pass step",
      set(lh.LANE_STEPS) == set(lh.LANES),
      f"{sorted(set(lh.LANE_STEPS) ^ set(lh.LANES))}")

lh = fresh()
now = time.time()
first = lh.select(now=now)
second = lh.select(now=now)
check("selection is deterministic for the same state and clock",
      first["selected"]["lane"] == second["selected"]["lane"],
      f"{first['selected']['lane']} vs {second['selected']['lane']}")

lh = fresh()
now = time.time()
# Round-robin emerges without being coded: recording the winner lets the next one win.
seen = []
for _ in range(len(lh.LANES)):
    choice = lh.select(now=now)["selected"]["lane"]
    seen.append(choice)
    lh.record(choice, "success", records=1)
check("every lane gets driven within one cycle, none is unreachable",
      set(seen) == set(lh.LANES), str(seen))

# --- productive: the ledger-driven productivity clock (X2) --------------------
# record() was only ever called without --records, so last_productive_at sat at 0.0
# forever and "alive but earning nothing" was undetectable. productive() is the
# separate, ledger-fed writer for the productivity clock; it must not touch the
# attempt bookkeeping that record() owns.
lh = fresh()
lh.record("apply", "success", records=0)   # liveness moves, productivity stays frozen
state_path = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "apply.json"
before = json.loads(state_path.read_text())
state = lh.productive("apply", records=3, detail="pass-test")
check("productive advances the productivity clock", state["last_productive_at"] > 0.0, str(state))
check("productive counts records", state["records_total"] == 3, str(state))
check("productive leaves attempt totals alone", state["totals"] == before["totals"],
      f"{before['totals']} -> {state['totals']}")
check("productive leaves the liveness clock alone",
      state["last_attempt_at"] == before["last_attempt_at"]
      and state["last_success_at"] == before["last_success_at"], str(state))
check("productive leaves the failure streak alone",
      state["consecutive_failures"] == before["consecutive_failures"], str(state))
row = lane_of(lh.check_all(), "apply")
check("a lane made productive is healthy", row["status"] == "ok", str(row["problems"]))
persisted = json.loads(state_path.read_text())
check("productive persists to the lane file", persisted["records_total"] == 3, str(persisted))

lh = fresh()
state = lh.productive("apply", records=0)
check("zero records is a no-op", state["records_total"] == 0
      and state["last_productive_at"] == 0.0, str(state))
state = lh.productive("apply", records=-2)
check("negative records is a no-op", state["records_total"] == 0
      and state["last_productive_at"] == 0.0, str(state))
check("a no-op writes no lane file",
      not (Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "apply.json").exists())

lh = fresh()
lh.productive("reply", records=2)
lh.productive("reply", records=5)
state_path = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "reply.json"
persisted = json.loads(state_path.read_text())
check("records accumulate across passes", persisted["records_total"] == 7, str(persisted))

# --- barren streak: attempts pile up, the ledger gains nothing (X7) -----------
# The 4.5-day outage had exactly this shape: passes ran (attempt clock moved) while
# last_productive_at froze. The streak counts consecutive attempts without ledger
# gain, so the alarm derives from measured state, never from model self-report.
lh = fresh()
for expected in (1, 2, 3):
    state = lh.record("apply", "success", records=0)
    check(f"attempt without ledger gain grows the barren streak to {expected}",
          state.get("barren_streak") == expected, str(state))

lh = fresh()
lh.record("apply", "success", records=0)
lh.record("apply", "success", records=0)
state = lh.productive("apply", records=2)
check("a ledger-counted productive pass resets the barren streak",
      state.get("barren_streak") == 0, str(state))
state = lh.record("apply", "success", records=0)
check("after recovery the streak restarts from one", state.get("barren_streak") == 1, str(state))

lh = fresh()
lh.record("reply", "success", records=0)
state = lh.record("reply", "success", records=4)
check("record with real records also resets the streak",
      state.get("barren_streak") == 0, str(state))

# Dedupe anchor: the streak start timestamp must stay fixed for the whole streak,
# because the outbox event key embeds it and a moving anchor would re-alert forever.
lh = fresh()
first = lh.record("fulfill", "failure")
started = first.get("barren_streak_started_at")
check("the first barren attempt stamps the streak start", bool(started), str(first))
for _ in range(2):
    later = lh.record("fulfill", "failure")
check("the streak start is stable across the whole streak",
      later.get("barren_streak_started_at") == started, f"{started} -> {later}")
state = lh.productive("fulfill", records=1)
check("recovery clears the streak anchor",
      state.get("barren_streak_started_at") == 0.0, str(state))

# barren_alerts: what the Telegram hook consumes.
lh = fresh()
for _ in range(2):
    lh.record("apply", "success", records=0)
check("two barren attempts stay below the alarm threshold",
      lh.barren_alerts() == [], str(lh.barren_alerts()))
lh.record("apply", "success", records=0)
alerts = lh.barren_alerts()
check("three consecutive barren attempts raise exactly one alert",
      len(alerts) == 1 and alerts[0]["lane"] == "apply" and alerts[0]["streak"] == 3,
      str(alerts))
check("the alert carries the stable streak anchor for outbox dedupe",
      alerts and alerts[0].get("streak_started_at", 0) > 0, str(alerts))
lh.productive("apply", records=1)
check("recovery silences the alert with no recovery notification path",
      lh.barren_alerts() == [], str(lh.barren_alerts()))

# improve/profile do work that legitimately yields no ledger rows for days
# (self-study, profile polish), so a streak there is normal life, not an outage.
lh = fresh()
for _ in range(10):
    lh.record("improve", "success", records=0)
    lh.record("profile", "success", records=0)
check("improve and profile lanes never barren-alert because daily productivity is not guaranteed",
      lh.barren_alerts() == [], str(lh.barren_alerts()))
check("the alarm scope is exactly the four revenue lanes",
      set(getattr(lh, "REVENUE_LANES", ())) == {"apply", "reply", "fulfill", "list"},
      str(getattr(lh, "REVENUE_LANES", None)))

# X14, measured 2026-07-27: fulfill alarmed at 3 and reached a streak of 11 while its
# delivery queue held items:[] and no paid-work transaction had been written for over a
# day. The lane was not failing -- it had nothing to deliver, because the order it had
# was finished. Counting "no work available" as "failed to produce" is how an alarm
# learns to cry wolf, and an alarm nobody believes is how the 4.5-day outage survived.
lh = fresh()
for _ in range(5):
    lh.record("fulfill", "skip", records=0)
check("a lane with nothing to do does not accrue a barren streak",
      lh._load("fulfill")["barren_streak"] == 0,
      str(lh._load("fulfill")["barren_streak"]))
check("and therefore does not alarm",
      lh.barren_alerts() == [], str(lh.barren_alerts()))

# The distinction must not become an escape hatch: attempting and producing nothing is
# still barren, which is the outage this alarm exists to catch.
lh = fresh()
for _ in range(3):
    lh.record("fulfill", "success", records=0)
check("attempting and producing nothing still counts as barren",
      lh._load("fulfill")["barren_streak"] == 3,
      str(lh._load("fulfill")["barren_streak"]))

# Skip must not launder an existing streak either: it neither adds nor forgives.
lh = fresh()
for _ in range(3):
    lh.record("fulfill", "success", records=0)
lh.record("fulfill", "skip", records=0)
check("a skip neither extends nor clears a streak already earned",
      lh._load("fulfill")["barren_streak"] == 3,
      str(lh._load("fulfill")["barren_streak"]))

# --- X18: every due lane, not just the most overdue one -----------------------
# The single-lane rule was never a design choice; it fell out of GIG_MODEL_CALL_LIMIT=1,
# which itself fell out of every worker fighting for one browser tab. Measured 2026-07-27:
# browser occupancy median 1.3% (24s of a 1800s period), so serialising the whole pass to
# protect the tab bought nothing and cost the loop its ability to apply AND reply in the
# same waking. select() therefore has to expose the whole due set, in deadline order.
#
# It stays demand-driven: due is what is PAST its deadline, never a forced quota. This is
# G1 deliberately changes the four revenue lanes to one hour; profile/improve remain
# daily maintenance.

lh = fresh()
check("all four revenue lanes are due hourly",
      {lane: lh.LANES[lane]["period_s"] for lane in lh.REVENUE_LANES}
      == {lane: 3600 for lane in lh.REVENUE_LANES},
      str({lane: lh.LANES[lane]["period_s"] for lane in lh.REVENUE_LANES}))
check("maintenance lanes stay daily",
      {lane: lh.LANES[lane]["period_s"] for lane in ("profile", "improve")}
      == {"profile": 24 * 3600, "improve": 24 * 3600},
      str({lane: lh.LANES[lane]["period_s"] for lane in ("profile", "improve")}))

lh = fresh()
now = time.time()
verdict = lh.select(now=now)
check("with nothing ever run, every lane is due, not just one",
      [row["lane"] for row in verdict["due"]] and len(verdict["due"]) == len(lh.LANES),
      str(verdict.get("due")))

lh = fresh()
# Keep the fixture in the middle of a wall-clock hour. Revenue lanes are due once
# per wall-clock hour, so using the real minute made a "10 minutes ago" fixture
# cross the hour boundary and fail only during minutes 00–09.
now = (int(time.time()) // 3600) * 3600 + 1800
# Two lanes past deadline, the rest fresh: exactly those two come back, worst first.
for lane, age in (("apply", 30 * 3600), ("reply", 9 * 3600), ("list", 600),
                  ("profile", 1 * 3600), ("improve", 1 * 3600), ("fulfill", 600)):
    state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / f"{lane}.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({
        "lane": lane, "last_attempt_at": now - age, "last_success_at": now - age,
        "last_productive_at": now - age, "consecutive_failures": 0,
        "totals": {k: 0 for k in lh.OUTCOMES}, "records_total": 0, "alert_state": "ok",
    }), encoding="utf-8")
verdict = lh.select(now=now)
check("only lanes past their deadline are due",
      [row["lane"] for row in verdict["due"]] == ["apply", "reply"],
      str([row["lane"] for row in verdict["due"]]))
check("due is ordered earliest-deadline-first",
      verdict["due"][0]["overdue_s"] > verdict["due"][1]["overdue_s"],
      str([row["overdue_s"] for row in verdict["due"]]))
check("selected stays the head of due, so old callers see no change",
      verdict["selected"]["lane"] == verdict["due"][0]["lane"], str(verdict["selected"]))
check("due_count still counts the due set", verdict["due_count"] == len(verdict["due"]),
      f"{verdict['due_count']} vs {len(verdict['due'])}")

lh = fresh()
now = time.time()
for lane in lh.LANES:
    state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / f"{lane}.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({
        "lane": lane, "last_attempt_at": now, "last_success_at": now,
        "last_productive_at": now, "consecutive_failures": 0,
        "totals": {k: 0 for k in lh.OUTCOMES}, "records_total": 0, "alert_state": "ok",
    }), encoding="utf-8")
verdict = lh.select(now=now)
check("nothing due means an empty due set, not a forced lane",
      verdict["due"] == [] and verdict["selected"] is None, str(verdict))

# A failed attempt is not a successful hourly check. The 08:00 natural pass reached B2
# but the pass breaker blocked provider launch; last_attempt_at advanced and the old
# scheduler then hid apply for a full hour. Retry a failed lane after a bounded five
# minutes while healthy lanes keep their normal period.
apply_state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "apply.json"
payload = json.loads(apply_state.read_text())
payload["last_attempt_at"] = now - 301
payload["last_success_at"] = now - 7200
payload["consecutive_failures"] = 1
apply_state.write_text(json.dumps(payload), encoding="utf-8")
verdict = lh.select(now=now)
check("a failed revenue lane retries after five minutes",
      "apply" in [row["lane"] for row in verdict["due"]], str(verdict["due"]))
improve_state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "improve.json"
payload = json.loads(improve_state.read_text())
payload["last_attempt_at"] = now - 301
payload["last_success_at"] = now - 7200
payload["consecutive_failures"] = 1
improve_state.write_text(json.dumps(payload), encoding="utf-8")
verdict = lh.select(now=now)
check("failed maintenance cannot use the revenue five-minute retry lane",
      "improve" not in [row["lane"] for row in verdict["due"]], str(verdict["due"]))

# Hourly means one authoritative check in each wall-clock hour, not "wait 3,600
# seconds since whichever minute the prior run happened to finish." A bounded retry at
# 08:32 must not make the natural 09:00 pass skip apply merely because only 28 minutes
# elapsed.
lh = fresh()
hour_boundary = ((int(time.time()) // 3600) + 1) * 3600
now = hour_boundary + 605
for lane in lh.LANES:
    state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / f"{lane}.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({
        "lane": lane, "last_attempt_at": now - 10, "last_success_at": now - 10,
        "last_productive_at": now - 10, "consecutive_failures": 0,
        "totals": {k: 0 for k in lh.OUTCOMES}, "records_total": 0, "alert_state": "ok",
    }), encoding="utf-8")
apply_state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / "apply.json"
payload = json.loads(apply_state.read_text())
payload["last_attempt_at"] = hour_boundary - 60
payload["last_success_at"] = hour_boundary - 60
apply_state.write_text(json.dumps(payload), encoding="utf-8")
verdict = lh.select(now=now)
check("a revenue check in the previous hour is due at the new hour boundary",
      [row["lane"] for row in verdict["due"]] == ["apply"], str(verdict["due"]))

# Ties are the cold-start shape (every clock at 0), and a tie broken alphabetically put
# 応募 ahead of 返信, which inverts spec 0.3 (Reply/Nouhin > Oubo > Shuppin). Deadline
# still wins; priority only decides who goes first among lanes equally late, so the
# anti-starvation property above is untouched.
lh = fresh()
now = time.time()
verdict = lh.select(now=now)
order = [row["lane"] for row in verdict["due"]]
check("among equally overdue lanes, spec 0.3 priority orders them",
      order.index("reply") < order.index("apply") < order.index("list"), str(order))
check("every lane has a spec 0.3 priority", set(lh.LANE_PRIORITY) == set(lh.LANES),
      str(sorted(set(lh.LANE_PRIORITY) ^ set(lh.LANES))))

# Daily maintenance may be much more overdue after downtime. It may use the fourth
# model slot, but it must never push B0/B1/B2 out of the first three.
lh = fresh()
now = time.time()
for lane in lh.LANES:
    age = 2 * 3600 if lane in lh.REVENUE_LANES else 30 * 86400
    state = Path(os.environ["GIG_STATE_DIR"]) / "state" / "lanes" / f"{lane}.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({
        "lane": lane, "last_attempt_at": now - age, "last_success_at": now - age,
        "last_productive_at": now - age, "consecutive_failures": 0,
        "totals": {k: 0 for k in lh.OUTCOMES}, "records_total": 0, "alert_state": "ok",
    }), encoding="utf-8")
order = [row["lane"] for row in lh.select(now=now)["due"]]
check("revenue lanes precede overdue maintenance lanes",
      set(order[:4]) == set(lh.REVENUE_LANES), str(order))

print()
if FAILURES:
    print(f"{len(FAILURES)} failed: {FAILURES}")
    sys.exit(1)
print("all lane health tests passed")
