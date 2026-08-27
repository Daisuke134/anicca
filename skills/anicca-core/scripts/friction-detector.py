#!/usr/bin/env python3
"""friction-detector.py — surface things piling up that Anicca might not notice are
building up, BEFORE they become a crisis. Anicca port of sutando src/friction-detector.py
(MIT), adapted to Anicca's sources.

Detects (proactive, not reactive):
  1. CHRONIC failers   — a cron with ≥3 real (non-transient) failures in the window.
  2. SILENT crons      — an enabled cron whose last finished run is way past its cadence
                         (fired-and-died, or stopped firing) — the "nobody noticed" killer.
  3. STALE questions   — pending-questions.md entries older than 24h (Dais never answered).
  4. PILING crimes     — distinct crons emitting dry-run/fake (from event_log).

Run from HEARTBEAT §2. Prints a friction brief; emits event_log friction.* entries.
Usage: friction-detector.py [--window 3d]
"""
from __future__ import annotations
import json, os, re, sys, time, collections
from pathlib import Path

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
RUNS = ANICCA_HOME / "cron" / "runs"
JOBS = ANICCA_HOME / "cron" / "jobs.json"
EVDIR = ANICCA_HOME / "state" / "events"
PQ = ANICCA_HOME / "workspace" / "pending-questions.md"
sys.path.insert(0, str(ANICCA_HOME / "skills" / "_shared"))
try:
    from event_log import log_event
except Exception:
    def log_event(k, **f): pass

TRANSIENT = re.compile(r"rate.?limit|cooldown|usage limit|All models failed|timed? out|ETIMEDOUT|ECONNRESET|FailoverError", re.I)
WINDOW_S = 3 * 86400
if "--window" in sys.argv:
    try:
        w = sys.argv[sys.argv.index("--window") + 1]
        WINDOW_S = int(w[:-1]) * {"h": 3600, "d": 86400, "w": 604800}[w[-1]]
    except Exception:
        pass
NOW = time.time()
SINCE_MS = (NOW - WINDOW_S) * 1000


def load_jobs():
    try:
        d = json.loads(JOBS.read_text()); jobs = d if isinstance(d, list) else d.get("jobs", [])
    except Exception:
        jobs = []
    return jobs


def main():
    jobs = load_jobs()
    by_id = {(j.get("id") or j.get("name")): j for j in jobs}
    chronic, silent, stale_q, crimes = [], [], [], []

    # 1) chronic failers — per cron, count recent real failures from its runs file
    for j in jobs:
        if not j.get("enabled"):
            continue
        jid = j.get("id") or j.get("name"); name = j.get("name", jid)
        f = RUNS / f"{jid}.jsonl"
        if not f.exists():
            continue
        recent = []
        try:
            for line in f.read_text().splitlines():
                try: r = json.loads(line)
                except: continue
                if r.get("action") == "finished" and r.get("ts", 0) >= SINCE_MS:
                    recent.append(r)
        except Exception:
            continue
        if not recent:
            continue
        real_fails = [r for r in recent if r.get("status") == "error"
                      and not TRANSIENT.search(str(r.get("error") or "") + str(r.get("summary") or ""))]
        if len(real_fails) >= 3:
            why = str(real_fails[-1].get("error") or real_fails[-1].get("summary") or "")[:120].replace("\n", " ")
            chronic.append(f"{name}: {len(real_fails)} real fails — {why}")
        # 2) silent: last finished run too old (> 2× expected gap, heuristic 26h for dailies)
        last_ts = max((r.get("ts", 0) for r in recent), default=0)
        age_h = (NOW - last_ts / 1000) / 3600 if last_ts else 999
        # only flag if it has run before but went quiet > 26h (covers daily/hourly; skips weekly/monthly)
        expr = (j.get("schedule") or {}).get("expr", "")
        looks_frequent = any(tok in expr for tok in ["* * *", "*/", " * * *"]) and not re.search(r"\b1,4,7,10\b|\* \* [0-9]", expr)
        if looks_frequent and 26 < age_h < 24 * 14:
            silent.append(f"{name}: last ran {age_h:.0f}h ago (cadence looks frequent — may have silently stopped)")

    # 3) stale pending-questions (>24h)
    if PQ.exists():
        txt = PQ.read_text()
        for m in re.finditer(r"(?:Asked|asked|日付)[:：]\s*(\d{4}-\d{2}-\d{2})", txt):
            try:
                d = time.mktime(time.strptime(m.group(1), "%Y-%m-%d"))
                if (NOW - d) > 24 * 3600:
                    stale_q.append(f"pending question from {m.group(1)} (>{int((NOW-d)/86400)}d unanswered)")
            except Exception:
                pass

    # 4) piling crimes (distinct crons) from event_log in window
    seen = set()
    for ev in EVDIR.glob("events-*.jsonl") if EVDIR.exists() else []:
        try:
            for line in ev.read_text().splitlines():
                try: e = json.loads(line)
                except: continue
                ts = e.get("ts", 0); tsms = ts * 1000 if ts < 1e12 else ts
                if tsms < SINCE_MS: continue
                if e.get("kind") == "crime.detected":
                    seen.add(e.get("cron"))
        except Exception:
            continue
    crimes = sorted(x for x in seen if x)

    # report
    total = len(chronic) + len(silent) + len(stale_q) + len(crimes)
    print(f"friction-detector: chronic={len(chronic)} silent={len(silent)} stale_q={len(stale_q)} crimes={len(crimes)}")
    if chronic:
        print("🔁 CHRONIC failers (fix root cause — recurring):")
        for x in chronic[:15]: print("  " + x)
    if silent:
        print("🔇 SILENT crons (frequent cadence but went quiet — may be dead):")
        for x in silent[:15]: print("  " + x)
    if stale_q:
        print("❓ STALE pending-questions (>24h):")
        for x in stale_q[:10]: print("  " + x)
    if crimes:
        print(f"🔴 CRIME crons piling up ({len(crimes)}): " + ", ".join(crimes[:20]))
    if total:
        log_event("friction.detected", chronic=len(chronic), silent=len(silent), stale_q=len(stale_q), crimes=len(crimes))


if __name__ == "__main__":
    main()
