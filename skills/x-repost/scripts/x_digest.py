#!/usr/bin/env python3
"""Build the daily x-repost digest from state. Prints the message body on stdout.

The per-post report answers "what did the loop just do". This answers "is it working", which is a
different question and the one that decides whether anything should change. It therefore reports
medians and a day-over-day delta rather than the latest event, and it says plainly when a number is
missing instead of printing a zero that looks like a measurement.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def when(row: dict, key: str):
    try:
        return datetime.fromisoformat(row[key]).astimezone(timezone.utc)
    except (KeyError, ValueError, TypeError):
        return None


def median(values):
    return round(statistics.median(values)) if values else None


def show(value, suffix=""):
    return "—" if value is None else f"{value}{suffix}"


def latest_metrics(samples: list[dict]) -> dict:
    """Latest successful sample per post."""
    best = {}
    for s in samples:
        if not s.get("ok"):
            continue
        at = when(s, "sampled_at")
        url = s.get("post_url")
        if not at or not url:
            continue
        if url not in best or at > best[url][0]:
            best[url] = (at, s)
    return {url: s for url, (_, s) in best.items()}


def early_views(samples: list[dict], url: str):
    """Views at the first sample taken at least 60 minutes after posting.

    Velocity in the first couple of hours is what the ranker rewards, so this is the number worth
    comparing across days -- a final count mostly reflects how long ago the post went out.
    """
    candidates = [s for s in samples
                  if s.get("post_url") == url and s.get("ok") and (s.get("age_minutes") or 0) >= 60]
    if not candidates:
        return None
    return min(candidates, key=lambda s: s["age_minutes"]).get("views")


def build(posted_path: Path, window_hours: int) -> str:
    posted = [r for r in read_jsonl(posted_path) if r.get("post_url")]
    samples = read_jsonl(posted_path.with_name("engagement.jsonl"))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)
    prev_cutoff = cutoff - timedelta(hours=window_hours)

    def in_window(rows, start, end):
        out = []
        for r in rows:
            at = when(r, "posted_at")
            if at and start <= at < end:
                out.append(r)
        return out

    today = in_window(posted, cutoff, now)
    yesterday = in_window(posted, prev_cutoff, cutoff)
    metrics = latest_metrics(samples)

    def stat(rows, key):
        return median([metrics[r["post_url"]][key] for r in rows
                       if r["post_url"] in metrics and metrics[r["post_url"]].get(key) is not None])

    def early(rows):
        vals = [v for v in (early_views(samples, r["post_url"]) for r in rows) if v is not None]
        return median(vals)

    lines = [f"日次 {datetime.now(JST):%Y-%m-%d}（直近{window_hours}時間）"]

    if not today:
        lines.append("投稿 0 — この窓では1本も公開していない")
    else:
        kinds = {}
        for r in today:
            kinds[r.get("kind", "quote")] = kinds.get(r.get("kind", "quote"), 0) + 1
        lines.append("投稿 %d（%s）" % (len(today),
                                       " / ".join(f"{k} {v}" for k, v in sorted(kinds.items()))))

        v_now, v_prev = stat(today, "views"), stat(yesterday, "views")
        delta = "" if v_prev is None or v_now is None else f"（前窓 {v_prev}）"
        lines.append(f"中央値 views {show(v_now)}{delta}／likes {show(stat(today, 'likes'))}"
                     f"／replies {show(stat(today, 'replies'))}")

        e_now, e_prev = early(today), early(yesterday)
        if e_now is not None:
            lines.append(f"1時間後 views 中央値 {e_now}"
                         + ("" if e_prev is None else f"（前窓 {e_prev}）"))

        ranked = [(metrics[r["post_url"]].get("views", 0), r) for r in today
                  if r["post_url"] in metrics]
        if ranked:
            ranked.sort(key=lambda p: p[0])
            worst_v, worst = ranked[0]
            best_v, best = ranked[-1]
            m = metrics[best["post_url"]]
            lines.append(f"最も伸びた: views {best_v} likes {m.get('likes', 0)} — {best['post_url']}")
            lines.append(f"最も伸びず: views {worst_v} — {worst['post_url']}")

    # Coverage is part of the report, not a footnote: a median computed over half the posts is not
    # the same claim as a median over all of them.
    recent_urls = {r["post_url"] for r in today}
    covered = len(recent_urls & set(metrics))
    failed = sum(1 for s in samples if not s.get("ok") and when(s, "sampled_at")
                 and when(s, "sampled_at") >= cutoff)
    lines.append(f"計測 {covered}/{len(recent_urls)} 本を取得"
                 + (f"、失敗 {failed}" if failed else ""))

    # Only report machinery that exists. Naming what is still missing keeps the digest honest
    # instead of quietly implying the loop is closed when it is not.
    strategy = posted_path.with_name("strategy.json")
    experiments = read_jsonl(posted_path.with_name("experiments.jsonl"))
    lessons = read_jsonl(posted_path.with_name("lessons.jsonl"))
    if experiments:
        e = experiments[-1]
        lines.append(f"実験: {e.get('knob')} {e.get('from')} → {e.get('to')}"
                     f"（{e.get('verdict', '判定待ち')}）")
    else:
        lines.append("実験: まだ無し（実験機構は未実装）")
    if lessons:
        lines.append(f"教訓: {lessons[-1].get('lesson', '')[:120]}")
    if not strategy.exists():
        lines.append("strategy.json 未作成 — 測っているが、まだ何も自動で変わっていない")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--posted", required=True)
    ap.add_argument("--window-hours", type=int, default=24)
    args = ap.parse_args()
    print(build(Path(args.posted).expanduser(), args.window_hours))


if __name__ == "__main__":
    main()
