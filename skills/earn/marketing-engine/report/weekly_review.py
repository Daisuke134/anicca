#!/usr/bin/env python3
"""weekly_review.py — the once-a-week message that decides what to cut and what to feed.

The daily report answers "what happened". This answers "what do we do next week":
which accounts are still reaching people, which have decayed, and where the posting
slots should go. It only ever compares measured windows — a week with no data says so.

  weekly_review.py [--days 7] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

LIB = pathlib.Path(os.path.expanduser(os.environ.get(
    "MKT_LIBRARY_DIR", "~/.openclaw/state/content-library")))
TELEGRAM_TARGET = os.environ.get("MKT_TELEGRAM_TARGET", "8547730585")


def rows(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line, strict=False))
        except json.JSONDecodeError:
            continue
    return out


def parse_ts(value: str):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def window(records: list[dict], start, end) -> list[dict]:
    out = []
    for r in records:
        ts = parse_ts(r.get("ts", ""))
        if ts and start <= ts < end:
            out.append(r)
    return out


def latest_per_post(records: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for r in records:
        pid = r.get("post_id")
        if not pid:
            continue
        if pid not in best or (r.get("ts") or "") >= (best[pid].get("ts") or ""):
            best[pid] = r
    return best


def money_trend(days: int) -> list[str]:
    metrics = rows(LIB / "daily-metrics.jsonl")
    if not metrics:
        return ["money: unavailable"]
    now = metrics[-1].get("revenuecat", {})
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    older = [m for m in metrics if (parse_ts(m.get("ts", "")) or dt.datetime.now(dt.timezone.utc)) < cutoff]
    line = (f"MRR {now.get('mrr', 'unavailable')} · subs {now.get('active_subscriptions')} "
            f"· trials {now.get('active_trials')}")
    if older:
        before = older[-1].get("revenuecat", {}).get("mrr")
        if isinstance(before, (int, float)) and isinstance(now.get("mrr"), (int, float)):
            line += f" (week change {now['mrr'] - before:+g})"
    else:
        line += " (no reading old enough to compare — first full week still accruing)"
    return [line]


def account_reach(days: int) -> list[str]:
    end = dt.datetime.now(dt.timezone.utc)
    mid = end - dt.timedelta(days=days)
    start = mid - dt.timedelta(days=days)
    metrics = rows(LIB / "post-metrics.jsonl")

    this_week = latest_per_post(window(metrics, mid, end))
    last_week = latest_per_post(window(metrics, start, mid))
    if not this_week:
        return ["accounts: no measured posts this week"]

    def by_account(bucket: dict[str, dict]) -> dict[str, list[int]]:
        agg: dict[str, list[int]] = {}
        for r in bucket.values():
            if r.get("views") is None:
                continue
            agg.setdefault(r.get("account") or "?", []).append(r["views"])
        return agg

    now_agg, prev_agg = by_account(this_week), by_account(last_week)
    out = [f"accounts measured: {len(now_agg)} · posts {sum(len(v) for v in now_agg.values())}"]
    scale, cut = [], []
    for acct, views in sorted(now_agg.items(), key=lambda kv: -sum(kv[1])):
        avg = sum(views) / len(views)
        prev = prev_agg.get(acct)
        delta = ""
        if prev:
            prev_avg = sum(prev) / len(prev)
            if prev_avg:
                pct = (avg - prev_avg) / prev_avg * 100
                delta = f" ({pct:+.0f}% vs prior week)"
                (cut if pct <= -50 else scale if pct >= 50 else []).append(acct)
        out.append(f"  {acct}: {len(views)} posts · avg {avg:.0f} views{delta}")
        if avg == 0:
            cut.append(acct)
    if scale:
        out.append("feed more slots: " + ", ".join(sorted(set(scale))))
    if cut:
        out.append("cut or re-provision: " + ", ".join(sorted(set(cut))))
    if not scale and not cut:
        out.append("no account moved enough to change its slots")
    return out


def verdict_recap() -> list[str]:
    path = LIB / "brain.json"
    if not path.exists():
        return ["verdict history: unavailable"]
    brain = json.loads(path.read_text())
    if brain.get("status") == "insufficient_data":
        return [f"verdict: still below the judging cohort "
                f"({brain.get('judged')}/{brain.get('min_cohort')}). "
                f"Raise posting volume before trusting any hook comparison."]
    winners = brain.get("winners", [])
    return [f"verdict: {len(winners)} winning hook(s) carried into next week"] + [
        f"  {(w.get('hook') or '').replace(chr(10), ' ')[:52]!r} · {w.get('views')} views"
        for w in winners[:5]]


def send(message: str) -> bool:
    r = subprocess.run(
        ["openclaw", "message", "send", "--channel", "telegram",
         "--target", TELEGRAM_TARGET, "--message", message, "--json"],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"send failed rc={r.returncode}: {(r.stderr or r.stdout)[:200]}", file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    body = [f"ANICCA weekly · week ending {today}", ""]
    body += money_trend(a.days) + [""] + account_reach(a.days) + [""] + verdict_recap()
    message = "\n".join(body)

    if a.dry_run:
        print(message)
        return 0
    ok = send(message)
    print("sent" if ok else "send failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
