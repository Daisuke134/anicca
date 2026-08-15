#!/usr/bin/env python3
"""daily_gig_report.py -- E3 (gig loop docs/loop-engineering/26-*.md sec CC'):
daily rollup numbers so "how did today go" has an answer that is not "read every
talkroom by hand".

Pure aggregation over ledgers the loop already writes -- no model calls, no
judgment, nothing invented here. Counts are for the current JST natural day
([00:00, 24:00) at UTC+9, the same day-boundary listing_ledger.py already uses for
"published today" so this file does not become a second answer to a question that
already has one):

  applications_verified  ~/gig/applied.jsonl rows with status == "applied" today
  deliveries_confirmed   projects/*/state.json delivery_attempts rows with
                          outcome == "confirmed" and `at` today
  buyer_replies          ~/gig/buyer-outcomes.jsonl rows appended today (E2's own
                          ledger), bucketed by `reaction` -- today that bucket is
                          almost entirely "unclassified" because E2 leaves
                          `reaction` null for a later model step; this file counts
                          and groups, it does not classify
  revenue_transitions    projects/*/events.jsonl state_reconciled events whose
                          changes.transaction_state.to happened today, grouped by
                          the `to` value (取引完了 is the one that means "paid and
                          closed"; every other `to` is reported too instead of
                          being thrown away)
  cancellations           the same transitions, filtered to a `to` value containing
                          "キャンセル" -- "if visible": the marketplace does not
                          expose a dedicated event for this, so a substring match is
                          what the recorded data actually offers; a true zero and a
                          "this loop cannot see it" zero share output shape on
                          purpose, `revenue_transitions` is emitted alongside so a
                          reader can check what `to` values were actually observed
  projects_reclaimed      ~/gig/janitor.jsonl rows with ts today (disk cleanup only
                          ever fires after transaction_state == 取引完了, so this is
                          a second, independent signal on completions -- not summed
                          into revenue_transitions, kept as its own field so the two
                          can be compared instead of silently agreeing)
  score_reality           E4's ~/gig/score-reality.jsonl (e4_correlation.py), bucketed
                          by score band (predelivery_score.SCORE_FLOOR is the one
                          boundary already defined for "confidently bad"; a second
                          fixed boundary at 70 splits the rest) x first_reaction --
                          does a high predelivery score actually predict a positive
                          reaction. Rows are grouped by `scored_ts` today, which is
                          when E1 graded the deliverable, not when the buyer replied
                          or when the join ran -- e4_correlation.py runs AFTER this
                          script in the same on_exit chain, so a join written in THIS
                          pass shows up in a later report, never this one's. One pass
                          of skew is expected, same honesty as buyer_replies above.

Writes ~/gig/daily-report/<YYYY-MM-DD>.json (JST date) and prints the same JSON to
stdout. Re-running for the same day overwrites that day's file with a fresh count --
this is a read of current ledger state, not an accumulator, so no idempotency
bookkeeping is needed.

SAFETY (fail-closed, mirrors project_janitor.py's contract): a missing or unparsable
ledger file counts as zero and does not stop the other counts. One bad row, one bad
project directory, or one bad events.jsonl line is skipped, never fatal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import listing_ledger  # noqa: E402 -- shared JST day-boundary helper, not re-derived here
import predelivery_score  # noqa: E402 -- reuse SCORE_FLOOR, not a second constant

APPLIED_STATUS = "applied"
COMPLETE_STATE = "取引完了"
HIGH_BAND_MIN = 70  # second fixed boundary; SCORE_FLOOR is the first


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        pass
    return rows


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _in_window(ts: Any, start: float, end: float) -> bool:
    num = _num(ts)
    return num is not None and start <= num < end


def count_applications(gig_dir: Path, start: float, end: float) -> int:
    return sum(
        1 for row in _read_jsonl(gig_dir / "applied.jsonl")
        if row.get("status") == APPLIED_STATUS and _in_window(row.get("ts"), start, end)
    )


def count_buyer_replies(gig_dir: Path, start: float, end: float) -> dict[str, Any]:
    by_reaction: Counter[str] = Counter()
    total = 0
    for row in _read_jsonl(gig_dir / "buyer-outcomes.jsonl"):
        if not _in_window(row.get("ts"), start, end):
            continue
        total += 1
        reaction = row.get("reaction")
        by_reaction[str(reaction) if reaction else "unclassified"] += 1
    return {"total": total, "by_reaction": dict(by_reaction)}


def count_deliveries_confirmed(projects_root: Path, start: float, end: float) -> int:
    if not projects_root.is_dir():
        return 0
    count = 0
    for project_dir in sorted(projects_root.iterdir()):
        state_path = project_dir / "state.json"
        if not state_path.is_file():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(state, dict):
            continue
        attempts = state.get("delivery_attempts")
        if not isinstance(attempts, list):
            continue
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            if attempt.get("outcome") == "confirmed" and _in_window(attempt.get("at"), start, end):
                count += 1
    return count


def count_revenue_transitions(projects_root: Path, start: float, end: float) -> dict[str, Any]:
    by_to: Counter[str] = Counter()
    cancellations = 0
    if not projects_root.is_dir():
        return {"by_to": {}, "cancellations": 0}
    for project_dir in sorted(projects_root.iterdir()):
        events_path = project_dir / "events.jsonl"
        if not events_path.is_file():
            continue
        for row in _read_jsonl(events_path):
            if row.get("event") != "state_reconciled":
                continue
            if not _in_window(row.get("ts"), start, end):
                continue
            changes = row.get("changes")
            if not isinstance(changes, dict):
                continue
            transition = changes.get("transaction_state")
            if not isinstance(transition, dict):
                continue
            to_value = transition.get("to")
            if not to_value:
                continue
            to_value = str(to_value)
            by_to[to_value] += 1
            if "キャンセル" in to_value:
                cancellations += 1
    return {"by_to": dict(by_to), "cancellations": cancellations}


def count_projects_reclaimed(gig_dir: Path, start: float, end: float) -> int:
    return sum(
        1 for row in _read_jsonl(gig_dir / "janitor.jsonl")
        if _in_window(row.get("ts"), start, end)
    )


def _score_band(score: Any) -> str | None:
    if not isinstance(score, int) or isinstance(score, bool):
        return None
    if score < predelivery_score.SCORE_FLOOR:
        return f"<{predelivery_score.SCORE_FLOOR}"
    if score < HIGH_BAND_MIN:
        return f"{predelivery_score.SCORE_FLOOR}-{HIGH_BAND_MIN - 1}"
    return f"{HIGH_BAND_MIN}-100"


def count_score_reality(gig_dir: Path, start: float, end: float) -> dict[str, Any]:
    by_band: dict[str, Counter[str]] = {}
    total = 0
    for row in _read_jsonl(gig_dir / "score-reality.jsonl"):
        if not _in_window(row.get("scored_ts"), start, end):
            continue
        band = _score_band(row.get("score"))
        if band is None:
            continue
        total += 1
        reaction = str(row.get("first_reaction") or "unclear")
        by_band.setdefault(band, Counter())[reaction] += 1
    return {"total": total, "by_band": {band: dict(counts) for band, counts in by_band.items()}}


def build_report(gig_dir: Path, projects_root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    start, end = listing_ledger.jst_day_bounds_for(now)
    jst_date = now.astimezone(listing_ledger.JST).date().isoformat()

    buyer_replies = count_buyer_replies(gig_dir, start, end)
    revenue = count_revenue_transitions(projects_root, start, end)
    score_reality = count_score_reality(gig_dir, start, end)

    return {
        "date": jst_date,
        "generated_at": int(time.time()),
        "window": {"start": start, "end": end},
        "applications_verified": count_applications(gig_dir, start, end),
        "deliveries_confirmed": count_deliveries_confirmed(projects_root, start, end),
        "buyer_replies": buyer_replies["total"],
        "buyer_replies_by_reaction": buyer_replies["by_reaction"],
        "revenue_transitions": revenue["by_to"],
        "revenue_completed": revenue["by_to"].get(COMPLETE_STATE, 0),
        "cancellations": revenue["cancellations"],
        "projects_reclaimed": count_projects_reclaimed(gig_dir, start, end),
        "score_reality": score_reality["total"],
        "score_reality_by_band": score_reality["by_band"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    parser.add_argument("--gig-dir", type=Path, default=default_root)
    parser.add_argument(
        "--projects-root", type=Path,
        default=Path(os.environ.get("GIG_PROJECTS_ROOT", str(default_root / "projects"))),
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path(os.environ.get("GIG_DAILY_REPORT_DIR", str(default_root / "daily-report"))),
    )
    args = parser.parse_args(argv)

    report = build_report(args.gig_dir, args.projects_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"{report['date']}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
