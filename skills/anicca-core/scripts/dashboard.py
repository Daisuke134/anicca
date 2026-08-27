#!/usr/bin/env python3
"""dashboard.py — Anicca self-healing dashboard generator.

Aggregates event_log (cron.ok/failed/crime + watchdog/friction/fix actions) into:
  - state/dashboard.json        — full internal view (cron health, chronic failers, crimes, recent fixes)
  - state/dashboard-public.json — REDACTED for aniccaai.com/dashboard (counts/rates/fix-titles/MRR only;
                                  NO raw why strings / emails / paths / keys)
  - state/dashboard.html        — simple static internal view

Run from HEARTBEAT or a cron (e.g. existing dashboard-refresh 5:00). The public JSON is
generated here but DEPLOYING it to aniccaai.com is a separate, owner-gated step.

Usage: dashboard.py [--window 7d]
"""
from __future__ import annotations
import json, os, re, sys, time, collections
from pathlib import Path

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
EVDIR = ANICCA_HOME / "state" / "events"
ST = ANICCA_HOME / "state"
WINDOW_S = 7 * 86400
if "--window" in sys.argv:
    try:
        w = sys.argv[sys.argv.index("--window") + 1]
        WINDOW_S = int(w[:-1]) * {"h": 3600, "d": 86400, "w": 604800}[w[-1]]
    except Exception:
        pass
NOW = time.time()
SINCE_MS = (NOW - WINDOW_S) * 1000
TRANSIENT = re.compile(r"rate.?limit|cooldown|usage limit|All models failed|timed? out|FailoverError", re.I)


def load_events():
    evs = []
    if not EVDIR.exists():
        return evs
    for f in EVDIR.glob("events-*.jsonl"):
        try:
            for line in f.read_text().splitlines():
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                ts = e.get("ts", 0); tsms = ts * 1000 if ts < 1e12 else ts
                if tsms >= SINCE_MS:
                    e["_tsms"] = tsms
                    evs.append(e)
        except Exception:
            continue
    return evs


def mrr_if_known():
    # reuse the public aniccaai dashboard.json if it exists locally; else None
    for p in [ANICCA_HOME / "state" / "aniccaai-dashboard.json",
              Path.home() / "anicca-oss" / "public" / "dashboard.json"]:
        try:
            d = json.loads(p.read_text())
            for k in ("mrr", "MRR", "totalMrr"):
                if k in d:
                    return d[k]
        except Exception:
            pass
    return None


def main():
    evs = load_events()
    kinds = collections.Counter(e.get("kind") for e in evs)
    ok = kinds.get("cron.ok", 0); failed = kinds.get("cron.failed", 0); crime = kinds.get("crime.detected", 0)
    total = ok + failed
    health_rate = round(100 * ok / total, 1) if total else 100.0

    # chronic failers: cron with most distinct real failures
    fail_by_cron = collections.Counter()
    for e in evs:
        if e.get("kind") == "cron.failed" and e.get("severity") not in ("transient",):
            fail_by_cron[e.get("cron")] += 1
    chronic = [{"cron": c, "fails": n} for c, n in fail_by_cron.most_common(10) if n >= 2]

    # crime crons (distinct)
    crime_crons = sorted({e.get("cron") for e in evs if e.get("kind") == "crime.detected" and e.get("cron")})

    # recent self-heal actions (watchdog/fix/friction)
    actions = [{"ts": e["_tsms"], "kind": e.get("kind"), "cron": e.get("cron"), "target": e.get("target")}
               for e in evs if e.get("kind", "").startswith(("watchdog.", "fix.", "friction."))]
    actions.sort(key=lambda x: x["ts"], reverse=True)

    full = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(NOW)),
        "window_days": round(WINDOW_S / 86400, 1),
        "cron_runs": {"ok": ok, "failed": failed, "crime": crime, "health_rate_pct": health_rate},
        "chronic_failers": chronic,
        "crime_crons": crime_crons,
        "recent_actions": actions[:30],
        "mrr": mrr_if_known(),
    }
    ST.mkdir(parents=True, exist_ok=True)
    (ST / "dashboard.json").write_text(json.dumps(full, ensure_ascii=False, indent=2))

    # PUBLIC: redact — counts/rates/MRR + crime COUNT (not the raw why), no cron internals beyond names
    public = {
        "generated": full["generated"],
        "window_days": full["window_days"],
        "health_rate_pct": health_rate,
        "runs_ok": ok, "runs_failed": failed,
        "auto_fix_actions": len(actions),
        "dry_run_crons_flagged": len(crime_crons),
        "mrr": full["mrr"],
        "tagline": "Anicca watches its own logs, catches every error (even fake successes), and fixes itself.",
    }
    (ST / "dashboard-public.json").write_text(json.dumps(public, ensure_ascii=False, indent=2))

    html = f"""<!doctype html><meta charset=utf-8><title>Anicca self-heal</title>
<body style="font:14px system-ui;max-width:760px;margin:40px auto;color:#222">
<h2>Anicca · self-healing ({full['window_days']}d)</h2>
<p>health <b>{health_rate}%</b> · ok {ok} · failed {failed} · 🔴dry-run crons {len(crime_crons)} · auto-fix actions {len(actions)}</p>
<h3>Chronic failers</h3><ul>{''.join(f"<li>{c['cron']} — {c['fails']} fails</li>" for c in chronic) or '<li>none</li>'}</ul>
<h3>Dry-run / fake crons flagged</h3><p>{', '.join(crime_crons) or 'none'}</p>
</body>"""
    (ST / "dashboard.html").write_text(html)

    print(f"dashboard: health={health_rate}% ok={ok} failed={failed} crime_crons={len(crime_crons)} actions={len(actions)}")
    print(f"  → {ST/'dashboard.json'} (internal) · {ST/'dashboard-public.json'} (redacted) · {ST/'dashboard.html'}")


if __name__ == "__main__":
    main()
