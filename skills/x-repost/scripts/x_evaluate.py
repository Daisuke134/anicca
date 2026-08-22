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
ORIGINAL_STEP = 0.05
ORIGINAL_FLOOR, ORIGINAL_CEILING = 0.05, 0.50


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


def evaluate_tone(posted, samples, cutoff, state: Path, apply: bool, result: dict) -> dict:
    """Move the tone mix toward whichever tone earns more early reach."""
    arms: dict[str, list[int]] = {}
    audience_tones = {"primary", "empathy", "funny"}
    for row in posted:
        at = parse_dt(row.get("posted_at"))
        tone = row.get("tone", "primary")
        if not at or at < cutoff or tone not in audience_tones:
            continue
        views = early_views(samples, row["post_url"])
        if views is not None:
            arms.setdefault(tone, []).append(views)

    strategy_path = state / "strategy.json"
    try:
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    except Exception:
        strategy = {}
    weights = strategy.get("tone_weights") or {"primary": 1.0, "empathy": 1.0, "funny": 1.0}

    result.update({"knob": "tone_weights", "from": dict(weights),
                   "samples": {k: len(v) for k, v in arms.items()},
                   "median_early_views": {k: float(statistics.median(v)) for k, v in arms.items()}})

    measured = {k: v for k, v in arms.items() if len(v) >= MIN_PER_ARM}
    if len(measured) < 2:
        result.update({"to": dict(weights), "verdict": "insufficient-data",
                       "reason": f"fewer than {MIN_PER_ARM} measured posts for at least two tones"})
        return result

    best = max(measured, key=lambda k: statistics.median(measured[k]))
    worst = min(measured, key=lambda k: statistics.median(measured[k]))
    if statistics.median(measured[best]) == statistics.median(measured[worst]):
        result.update({"to": dict(weights), "verdict": "tie", "reason": "identical medians"})
        return result

    weights[best] = round(min(4.0, float(weights.get(best, 1.0)) + 0.5), 2)
    weights[worst] = round(max(0.25, float(weights.get(worst, 1.0)) - 0.5), 2)
    # Do not round here. Rounding made a real 16.0-vs-16.5 difference print as "16 vs 16", so the
    # ledger read as a knob moved for no reason -- a report that argues against its own decision.
    result.update({"to": dict(weights), "verdict": "moved",
                   "reason": f"{best} {statistics.median(measured[best]):g} vs "
                             f"{worst} {statistics.median(measured[worst]):g} early views"})
    if apply:
        strategy["tone_weights"] = weights
        strategy["updated_at"] = result["ts"]
        strategy["updated_because"] = result["reason"]
        strategy_path.write_text(json.dumps(strategy, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    return result


def evaluate_original_ratio(posted, samples, cutoff, state: Path, apply: bool,
                            result: dict) -> dict:
    """Move additional-original share using same-window early reach, never affiliate rows."""
    arms: dict[str, list[int]] = {"original": [], "quote": []}
    for row in posted:
        at = parse_dt(row.get("posted_at"))
        kind = row.get("kind")
        if not at or at < cutoff or kind not in arms:
            continue
        views = early_views(samples, row["post_url"])
        if views is not None:
            arms[kind].append(views)

    strategy_path = state / "strategy.json"
    try:
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    except Exception:
        strategy = {}
    current = float(strategy.get("original_ratio", 0.50))
    result.update({"knob": "original_ratio", "from": current,
                   "samples": {k: len(v) for k, v in arms.items()},
                   "median_early_views": {
                       k: (float(statistics.median(v)) if v else None) for k, v in arms.items()}})
    thin = [k for k, values in arms.items() if len(values) < MIN_PER_ARM]
    if thin:
        result.update({"to": current, "verdict": "insufficient-data",
                       "reason": f"fewer than {MIN_PER_ARM} measured posts for: {', '.join(thin)}"})
        return result
    original_med = statistics.median(arms["original"])
    quote_med = statistics.median(arms["quote"])
    if original_med == quote_med:
        result.update({"to": current, "verdict": "tie", "reason": "identical medians"})
        return result
    direction = ORIGINAL_STEP if original_med > quote_med else -ORIGINAL_STEP
    new = round(min(ORIGINAL_CEILING, max(ORIGINAL_FLOOR, current + direction)), 2)
    result.update({"to": new, "verdict": "moved" if new != current else "at-bound",
                   "reason": f"original {original_med:g} vs quote {quote_med:g} early views"})
    if apply and new != current:
        strategy["original_ratio"] = new
        strategy["updated_at"] = result["ts"]
        strategy["updated_because"] = result["reason"]
        strategy_path.write_text(json.dumps(strategy, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
    return result


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
        # One action is switched off, so that arm will never fill. Alternate the two live knobs
        # instead of waiting forever or changing format and tone in the same daily experiment.
        experiments = read_jsonl(state / "experiments.jsonl")
        last_knob = experiments[-1].get("knob") if experiments else None
        if last_knob != "original_ratio":
            return evaluate_original_ratio(posted, samples, cutoff, state, apply, result)
        return evaluate_tone(posted, samples, cutoff, state, apply, result)

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
