#!/usr/bin/env python3
"""Track and alert on per-lane liveness AND productivity.

The failure this exists for: 251 scheduled passes over 13 days each reported success
while executing zero of the five duties. Applications stopped for 4.5 days and nothing
noticed, because the existing auditor watches a single global heartbeat and sums
applied.jsonl across all lanes -- so one working lane masks another that has died.

The lesson, which liveness monitoring alone cannot give you: a run that succeeds while
doing nothing is invisible to "did it run?". Prometheus' own instrumentation guidance
names the metric that matters for batch jobs -- "The key metric of a batch job is the
last time it succeeded" -- but success is not enough here, so this keeps TWO clocks:

    last_success_at     the run finished without error   (liveness)
    last_productive_at  the run actually did work        (productivity)

A lane that returns "nothing to do" every time keeps its liveness clock fresh and its
productivity clock frozen, which is exactly the shape of the outage we had.

Thresholds follow the convention found in production alert rules: roughly two periods,
with a floor. NAV's rule reads `(time() - last_success) > clamp_min(2 * period, 300)`,
and an independent implementation comments "2x its scheduled interval". Alerts fire on
state CHANGE only, the way healthchecks.io does it (`if self.status != new_status`),
because re-alerting every evaluation trains everyone to ignore the channel.

Outcomes use the four values OpenTelemetry settled on for pipeline runs -- success,
failure, timeout, skip -- so "skipped because the browser was busy" is never mistaken
for "ran and found nothing".

Usage:
  lane_health.py record <lane> <outcome> [--records N] [--detail TEXT]
  lane_health.py productive <lane> --records N [--detail TEXT]  # ledger-counted work
  lane_health.py check [--json]        # verdicts for every lane
  lane_health.py digest                # human-readable daily summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

STATE = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
LANES_DIR = STATE / "state" / "lanes"
EVENTS = STATE / "lane-events.jsonl"

OUTCOMES = ("success", "failure", "timeout", "skip")

# period_s: how often the lane should do real work.
# A lane silent for longer than max(2 * period, 300s) is reported.
LANES = {
    "apply":     {"period_s": 3600,      "label": "応募"},
    "reply":     {"period_s": 3600,      "label": "返信"},
    "fulfill":   {"period_s": 3600,      "label": "納品"},
    "list":      {"period_s": 3600,      "label": "出品"},
    "profile":   {"period_s": 24 * 3600, "label": "プロフィール"},
    "improve":   {"period_s": 24 * 3600, "label": "自己改善"},
}

# Barren streak (X7): consecutive attempts that advanced the attempt clock while
# the productivity clock stayed frozen. This is the measured shape of the 4.5-day
# outage -- passes kept running, ledgers gained nothing -- counted from lane state
# alone, never from model self-report. Only the four revenue lanes participate:
# improve/profile legitimately produce no ledger rows for days, so a streak there
# is normal life and alerting on it would train everyone to ignore the channel.
BARREN_STREAK_THRESHOLD = 3
REVENUE_LANES = ("apply", "reply", "fulfill", "list")
FAILURE_RETRY_SECONDS = 5 * 60


def _lane_file(lane: str) -> Path:
    return LANES_DIR / f"{lane}.json"


def _load(lane: str) -> dict:
    path = _lane_file(lane)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "lane": lane,
            "last_attempt_at": 0.0,
            "last_success_at": 0.0,
            "last_productive_at": 0.0,
            "consecutive_failures": 0,
            "totals": {k: 0 for k in OUTCOMES},
            "records_total": 0,
            "alert_state": "ok",
            "barren_streak": 0,
            "barren_streak_started_at": 0.0,
        }


def _atomic_write(path: Path, payload: dict) -> None:
    # node_exporter documents this exact dance for cron-written metrics: write to a
    # temp name, then rename, so a reader never sees a half-written file.
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def record(lane: str, outcome: str, records: int = 0, detail: str = "") -> dict:
    if outcome not in OUTCOMES:
        raise SystemExit(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    now = time.time()
    state = _load(lane)
    state["lane"] = lane
    state["last_attempt_at"] = now
    state["totals"][outcome] = state["totals"].get(outcome, 0) + 1

    if outcome == "success":
        state["last_success_at"] = now
        state["consecutive_failures"] = 0
        if records > 0:
            # Productivity only advances on real work. "Ran and found nothing" keeps
            # the lane alive but visibly unproductive -- the distinction that would
            # have surfaced the outage on day one.
            state["last_productive_at"] = now
            state["records_total"] = state.get("records_total", 0) + records
    elif outcome in ("failure", "timeout"):
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
    # skip: neither clock moves. A lane permanently unable to get the browser must not
    # look healthy, so skip is deliberately not a success.

    if outcome == "success" and records > 0:
        # This very call proved real work, so the barren streak ends here.
        state["barren_streak"] = 0
        state["barren_streak_started_at"] = 0.0
    elif outcome == "skip":
        # Nothing to do is not failure to produce. X14, measured 2026-07-27: fulfill
        # reached a streak of 11 and alarmed at 3 while its delivery queue held
        # items:[] -- the order it had was finished, so there was nothing to deliver.
        # Counting an empty queue as barren is how an alarm learns to cry wolf, and an
        # alarm nobody believes is how the 4.5-day outage survived. A skip neither
        # extends a streak nor forgives one already earned; it simply says nothing.
        pass
    else:
        # The attempt clock moved and the productivity clock did not: one more
        # barren attempt. productive() resets this when the lane's own ledger
        # gains rows later in the pass. The anchor is stamped only on the first
        # barren attempt and stays fixed for the whole streak -- the Telegram
        # outbox event key embeds it, and a moving anchor would re-alert forever.
        state["barren_streak"] = state.get("barren_streak", 0) + 1
        if state["barren_streak"] == 1:
            state["barren_streak_started_at"] = now

    _atomic_write(_lane_file(lane), state)

    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "ts": now, "lane": lane, "outcome": outcome,
            "records_processed": records, "detail": detail,
        }, ensure_ascii=False) + "\n")
        handle.flush()
    return state


def productive(lane: str, records: int = 0, detail: str = "") -> dict:
    """Advance ONLY the productivity clock, from ledger-counted real effects.

    record() owns the attempt bookkeeping (last_attempt_at, totals, failure streak);
    this owns last_productive_at/records_total and touches nothing else. The split
    exists because the pass driver knows an attempt happened the moment a step runs,
    but real work is only knowable after the fact, from the lane's authoritative
    ledger -- and wiring record() without --records left every productivity clock at
    0.0 forever while the liveness clocks looked fine.

    records <= 0 is a no-op: "the ledger gained nothing this pass" must leave the
    clock frozen, because a frozen clock is exactly the signal check() alerts on.
    """
    state = _load(lane)
    if records <= 0:
        return state
    now = time.time()
    state["lane"] = lane
    state["last_productive_at"] = now
    state["records_total"] = state.get("records_total", 0) + records
    # Ledger-counted real work ends the barren streak; no recovery notification
    # exists anywhere, silence after recovery IS the design.
    state["barren_streak"] = 0
    state["barren_streak_started_at"] = 0.0
    _atomic_write(_lane_file(lane), state)

    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "ts": now, "lane": lane, "outcome": "productive",
            "records_processed": records, "detail": detail,
        }, ensure_ascii=False) + "\n")
        handle.flush()
    return state


def barren_alerts() -> list[dict]:
    """Revenue lanes whose measured barren streak has reached the alarm threshold.

    Consumed by telegram_report.py lane-barren at the per-pass choke point. The
    streak anchor rides along so the outbox event key stays constant for one
    streak and changes for the next -- dedupe without any extra state here.
    """
    alerts = []
    for lane in REVENUE_LANES:
        state = _load(lane)
        streak = int(state.get("barren_streak", 0))
        if streak >= BARREN_STREAK_THRESHOLD:
            alerts.append({
                "lane": lane,
                "label": LANES[lane]["label"],
                "streak": streak,
                "streak_started_at": float(state.get("barren_streak_started_at") or 0.0),
            })
    return alerts


def _threshold(period_s: int) -> float:
    return max(2 * period_s, 300)


def check_lane(lane: str, meta: dict) -> dict:
    now = time.time()
    state = _load(lane)
    threshold = _threshold(meta["period_s"])

    success_age = now - (state.get("last_success_at") or 0)
    productive_age = now - (state.get("last_productive_at") or 0)
    never_ran = not state.get("last_success_at")
    never_produced = not state.get("last_productive_at")

    problems = []
    if never_ran:
        problems.append("一度も成功していない")
    elif success_age > threshold:
        problems.append(f"{success_age/3600:.1f}h 実行なし")
    # The productivity clock gets a longer rope: a quiet marketplace is legitimate.
    if never_produced:
        problems.append("一度も実作業なし")
    elif productive_age > threshold * 3:
        problems.append(f"{productive_age/3600:.1f}h 実作業なし")
    if state.get("consecutive_failures", 0) >= 3:
        problems.append(f"{state['consecutive_failures']}回連続失敗")

    status = "down" if problems else "ok"
    return {
        "lane": lane,
        "label": meta["label"],
        "status": status,
        "problems": problems,
        "period_h": meta["period_s"] / 3600,
        "success_age_h": None if never_ran else round(success_age / 3600, 1),
        "productive_age_h": None if never_produced else round(productive_age / 3600, 1),
        "totals": state.get("totals", {}),
        "records_total": state.get("records_total", 0),
        "consecutive_failures": state.get("consecutive_failures", 0),
        "prev_alert_state": state.get("alert_state", "ok"),
    }


def check_all() -> dict:
    results = [check_lane(lane, meta) for lane, meta in LANES.items()]
    # Edge-triggered: only lanes whose status changed since the last check are worth
    # announcing. healthchecks.io creates a notification only on a status flip.
    flipped = []
    for row in results:
        if row["status"] != row["prev_alert_state"]:
            flipped.append(row)
            state = _load(row["lane"])
            state["alert_state"] = row["status"]
            _atomic_write(_lane_file(row["lane"]), state)
    return {
        "ts": time.time(),
        "lanes": results,
        "down": [r["lane"] for r in results if r["status"] == "down"],
        "changed": [{"lane": r["lane"], "to": r["status"], "problems": r["problems"]}
                    for r in flipped],
    }


# Which gig_pass step drives each lane. One pass drives every lane that is past its
# deadline (X18); GIG_MODEL_CALL_LIMIT bounds how many of them fit in one waking.
LANE_STEPS = {
    "apply": "B2",
    "reply": "B1",
    "fulfill": "PAID_WORK",
    "list": "B0",
    "profile": "PROFILE",
    "improve": "LEARN",
}

# Revenue lanes always precede maintenance lanes. There are three model-backed revenue
# lanes and four model slots, so the oldest due maintenance lane still gets the fourth
# slot. Within each class EDF remains authoritative; business priority only breaks ties.
LANE_PRIORITY = {
    "reply": 0,
    "fulfill": 0,
    "apply": 1,
    "list": 2,
    "profile": 3,
    "improve": 4,
}


def select(now: float | None = None) -> dict:
    """Rank the lanes by deadline and return every one that is past it.

    Why this exists: the pass may make one model call, and the old code walked a
    fixed priority order. Delivery sat at the top and was almost always eligible, so
    it took the one call on 37 of 48 daily passes and applications never ran -- for
    4.5 days. A fixed order plus a budget of one is a starvation machine; the lane at
    the bottom is not deprioritised, it is unreachable.

    The deadline clock is last_attempt_at, not last_success_at. Scheduling on success
    would let a lane that fails every time stay maximally overdue forever and swallow
    every pass, which is the same starvation with a different victim. A failed attempt
    uses a bounded five-minute retry period instead of the normal lane period: failure
    is not a successful hourly check, and hiding it for a full hour made a corrected B2
    miss the very next pass. Revenue-first ordering and the model-call limit still stop
    one broken lane from excluding the others.

    Returns the full due set in deadline order, the head of it as `selected` for callers
    that still want one lane, and the full ranking so the pass report can show what lost
    and by how much.

    X18 (2026-07-27): `selected` alone was a bottleneck nobody chose. The pass could make
    one model call because every worker shared one browser tab; measured occupancy was
    1.3% of the period, so the serialisation protected nothing and cost the loop the
    ability to apply and reply in the same waking. G1 makes all four revenue lanes hourly
    while profile/improve remain daily. Revenue is ranked as a class before maintenance,
    so a long-stale maintenance clock cannot close the application entrance.
    """
    now = time.time() if now is None else now
    ranking = []
    for lane, meta in LANES.items():
        state = _load(lane)
        last = state.get("last_attempt_at") or 0.0
        failed_revenue = (
            lane in REVENUE_LANES
            and state.get("consecutive_failures", 0) > 0
        )
        period_s = (
            min(meta["period_s"], FAILURE_RETRY_SECONDS)
            if failed_revenue else meta["period_s"]
        )
        if not last:
            deadline = 0.0
        elif lane in REVENUE_LANES:
            # Revenue cadence is one check per wall-clock hour. A retry or a long
            # pass can finish at :32; the next obligation is still the next :00,
            # not :32. JST is an integer-hour UTC offset, so epoch-hour buckets
            # have the same boundaries.
            next_hour = (int(last) // 3600 + 1) * 3600
            deadline = (
                min(next_hour, last + FAILURE_RETRY_SECONDS)
                if failed_revenue else next_hour
            )
        else:
            deadline = last + period_s
        ranking.append({
            "lane": lane,
            "step": LANE_STEPS[lane],
            "label": meta["label"],
            # Never attempted sorts first: its deadline is in 1970.
            "overdue_s": now - deadline,
            "last_attempt_at": last,
            "deadline_at": deadline,
            "period_s": period_s,
            "normal_period_s": meta["period_s"],
        })
    ranking.sort(key=lambda row: (
        0 if row["lane"] in REVENUE_LANES else 1,
        -row["overdue_s"],
        LANE_PRIORITY[row["lane"]],
        row["lane"],
    ))
    due = [row for row in ranking if row["overdue_s"] > 0]
    return {
        "selected": due[0] if due else None,
        "due": due,
        "due_count": len(due),
        "ranking": ranking,
    }


def digest() -> str:
    verdict = check_all()
    lines = ["gig lane 状況"]
    for row in verdict["lanes"]:
        mark = "✅" if row["status"] == "ok" else "⚠️"
        totals = row["totals"]
        lines.append(
            f"{mark} {row['label']}: 実作業 {row['records_total']}件 / "
            f"成功 {totals.get('success', 0)} 失敗 {totals.get('failure', 0)} "
            f"skip {totals.get('skip', 0)}"
            + (f" — {', '.join(row['problems'])}" if row["problems"] else "")
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record")
    rec.add_argument("lane")
    rec.add_argument("outcome", choices=OUTCOMES)
    rec.add_argument("--records", type=int, default=0)
    rec.add_argument("--detail", default="")

    prod = sub.add_parser("productive")
    prod.add_argument("lane")
    prod.add_argument("--records", type=int, required=True)
    prod.add_argument("--detail", default="")

    chk = sub.add_parser("check")
    chk.add_argument("--json", action="store_true")

    sub.add_parser("digest")

    sel = sub.add_parser("select")
    sel.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cmd == "select":
        verdict = select()
        if args.json:
            print(json.dumps(verdict, ensure_ascii=False))
        elif verdict["selected"]:
            # Bare step name so callers can use it directly: STEP=$(... select)
            print(verdict["selected"]["step"])
        # Exit 3 = nothing is due. Distinct from 1 so a caller can tell "no work
        # scheduled" from "the selector broke".
        return 0 if verdict["selected"] else 3

    if args.cmd == "record":
        print(json.dumps(record(args.lane, args.outcome, args.records, args.detail),
                         ensure_ascii=False))
    elif args.cmd == "productive":
        print(json.dumps(productive(args.lane, args.records, args.detail),
                         ensure_ascii=False))
    elif args.cmd == "check":
        verdict = check_all()
        print(json.dumps(verdict, ensure_ascii=False) if args.json else digest())
        return 1 if verdict["down"] else 0
    else:
        print(digest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
