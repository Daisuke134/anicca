#!/usr/bin/env python3
"""Turn measurements into one knob change, or say why not. Writes the verdict, never guesses.

The loop measured things for two days and changed nothing, which is the definition of an open
loop. This closes it with the smallest honest mechanism: compare the two actions the loop can take
over the SAME window -- a time-split comparison would confound the action with whatever else
changed that day -- and move the ratio toward whichever earns more early reach.

It refuses to move on thin data. A knob turned on two posts is noise dressed as learning.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

MIN_PER_ARM = 3          # below this, any difference is noise
STEP = 0.15              # how far the ratio moves per verdict
FLOOR, CEILING = 0.2, 0.9  # never stop doing either action entirely: that ends the comparison


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def parse_dt(value):
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def early_views(samples: list[dict], url: str):
    """Views at the first sample at least an hour old: reach earned, not time elapsed."""
    rows = [s for s in samples if s.get("post_url") == url and s.get("ok")
            and (s.get("age_minutes") or 0) >= 60]
    return min(rows, key=lambda s: s["age_minutes"]).get("views") if rows else None


def evaluate(state: Path, window_hours: int, apply: bool) -> dict:
    posted = [r for r in read_jsonl(state / "posted.jsonl") if r.get("post_url")]
    samples = read_jsonl(state / "engagement.jsonl")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    arms: dict[str, list[int]] = {"reply": [], "quote": []}
    for row in posted:
        at = parse_dt(row.get("posted_at"))
        if not at or at < cutoff:
            continue
        views = early_views(samples, row["post_url"])
        if views is None:
            continue
        arms.setdefault(row.get("kind", "quote"), []).append(views)

    strategy_path = state / "strategy.json"
    try:
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    except Exception:
        strategy = {"reply_ratio": 0.75}
    current = float(strategy.get("reply_ratio", 0.75))

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "knob": "reply_ratio",
        "from": current,
        "window_hours": window_hours,
        "samples": {k: len(v) for k, v in arms.items()},
        "median_early_views": {k: (round(statistics.median(v)) if v else None) for k, v in arms.items()},
    }

    # An arm that is switched off will never fill, so waiting on it is not patience, it is a report
    # that reads like pending work when nothing is pending. Say the comparison is off instead.
    if current <= 0.0 or current >= 1.0:
        disabled = "quote" if current >= 1.0 else "reply"
        result.update({"to": current, "verdict": "one-arm-only",
                       "reason": f"{disabled} is disabled by strategy, so there is nothing to compare"})
        return result

    thin = [k for k, v in arms.items() if len(v) < MIN_PER_ARM]
    if thin:
        result.update({"to": current, "verdict": "insufficient-data",
                       "reason": f"fewer than {MIN_PER_ARM} measured posts for: {', '.join(thin)}"})
        return result

    reply_med = statistics.median(arms["reply"])
    quote_med = statistics.median(arms["quote"])
    if reply_med == quote_med:
        result.update({"to": current, "verdict": "tie", "reason": "identical medians"})
        return result

    direction = STEP if reply_med > quote_med else -STEP
    new = round(min(CEILING, max(FLOOR, current + direction)), 2)
    result.update({"to": new,
                   "verdict": "moved" if new != current else "at-bound",
                   "reason": f"reply {reply_med} vs quote {quote_med} early views"})

    if apply and new != current:
        strategy["reply_ratio"] = new
        strategy["updated_at"] = result["ts"]
        strategy["updated_because"] = result["reason"]
        strategy_path.write_text(json.dumps(strategy, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--window-hours", type=int, default=48)
    ap.add_argument("--apply", action="store_true", help="write strategy.json and the ledger")
    args = ap.parse_args()

    state = Path(args.state).expanduser()
    result = evaluate(state, args.window_hours, args.apply)
    if args.apply:
        with (state / "experiments.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
