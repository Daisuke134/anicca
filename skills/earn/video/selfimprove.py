#!/usr/bin/env python3
"""selfimprove.py — the closed self-improvement loop's DETERMINISTIC tools (no judgment here; the agent decides
how to improve — AI-agnostic). Three jobs, file + browser only:

  record_post(handle, post_url, script, date)  — after a post lands, link the post_url ↔ the script that made it.
  measure_due(handle, tid, port, date)          — measure metrics of posts not yet measured today (bounded), append.
  performance_summary(handle)                    — compact JSON the agent READS before writing the next script:
        per recent post {date, views, likes, comments} + total USDC earned. The agent uses this to iterate the
        hook/topic. The ULTIMATE metric is USDC (onchain ledger); views/engagement are the leading indicator.

CLI: selfimprove.py summary --handle H            → prints performance_summary (for the agent)
     selfimprove.py measure --handle H --tid T --port P --date D
     selfimprove.py record  --handle H --url U --script-file F --date D
"""
import argparse, json, os

CLOAK = os.path.expanduser("~/.cloak")


def _content(handle): return os.path.join(CLOAK, f"earn-video-content-{handle}.jsonl")
def _metrics(handle): return os.path.join(CLOAK, f"earn-video-metrics-{handle}.jsonl")
def _ledger():        return os.path.join(CLOAK, "earn-video-ledger.jsonl")


def _read_jsonl(p):
    out = []
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out


def record_post(handle, post_url, script, date):
    with open(_content(handle), "a") as f:
        f.write(json.dumps({"date": date, "post_url": post_url, "script": (script or "")[:600]}, ensure_ascii=False) + "\n")


def measure_due(handle, tid, port, date, max_posts=2):
    """measure metrics for posts whose latest metric is not from `date` (most recent first), bounded by max_posts."""
    import metrics as M
    posts = _read_jsonl(_content(handle))
    measured_today = {m.get("url") for m in _read_jsonl(_metrics(handle)) if m.get("measured_date") == date}
    todo = [p for p in reversed(posts) if p.get("post_url") and p["post_url"] not in measured_today][:max_posts]
    done = []
    for p in todo:
        m = M.read_reel_metrics(p["post_url"], tid, port)
        m["measured_date"] = date
        with open(_metrics(handle), "a") as f:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
        done.append(m)
    return done


def performance_summary(handle):
    posts = _read_jsonl(_content(handle))
    metrics = _read_jsonl(_metrics(handle))
    # latest metric per post_url
    latest = {}
    for m in metrics:
        u = m.get("url")
        if u and (u not in latest or (m.get("measured_date") or "") >= (latest[u].get("measured_date") or "")):
            latest[u] = m
    usdc = sum(float(r.get("amount", 0) or 0) for r in _read_jsonl(_ledger()))
    recent = []
    for p in posts[-7:]:
        u = p.get("post_url"); lm = latest.get(u, {})
        recent.append({"date": p.get("date"), "post_url": u, "script_hook": (p.get("script") or "")[:80],
                       "views": lm.get("views"), "likes": lm.get("likes"), "comments": lm.get("comments")})
    return {
        "handle": handle,
        "total_usdc_earned": round(usdc, 6),       # ★ the metric that ultimately matters ★
        "posts": len(posts),
        "recent": recent,
        "guidance": "Iterate to MAXIMIZE total_usdc_earned. If recent posts have low views/likes or earned $0, "
                    "change the hook/topic/CTA for the next script. Keep what correlates with higher views AND money.",
    }


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary"); s.add_argument("--handle", required=True)
    me = sub.add_parser("measure"); me.add_argument("--handle", required=True); me.add_argument("--tid", required=True); me.add_argument("--port", default="9334"); me.add_argument("--date", default="")
    re_ = sub.add_parser("record"); re_.add_argument("--handle", required=True); re_.add_argument("--url", required=True); re_.add_argument("--script-file", default=""); re_.add_argument("--date", default="")
    a = ap.parse_args()
    if a.cmd == "summary":
        print(json.dumps(performance_summary(a.handle), ensure_ascii=False))
    elif a.cmd == "measure":
        import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        print(json.dumps(measure_due(a.handle, a.tid, a.port, a.date), ensure_ascii=False))
    elif a.cmd == "record":
        script = open(os.path.expanduser(a.script_file)).read() if a.script_file and os.path.exists(os.path.expanduser(a.script_file)) else ""
        record_post(a.handle, a.url, script, a.date); print("recorded")


if __name__ == "__main__":
    main()
