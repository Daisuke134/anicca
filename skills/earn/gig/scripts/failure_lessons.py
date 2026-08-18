#!/usr/bin/env python3
"""F4 (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md sec CC'/EW'): the loop reads
its own scar tissue.

record_failure() in gig_pass.sh has appended every pass failure to ~/gig/pass-failures.jsonl
for weeks (690 rows measured 2026-08-09) and nothing ever read it back into the step that
keeps failing the same way. b2_parent_boundary_failed alone recurred 165 times; nothing in
any B2 prompt ever said so.

Deterministic on purpose: which (failed_step, reason) pairs recur, how often, and when last
seen are facts readable straight off the ledger by counting -- no judgment required. Turning
those counts into PROSE advice ("retry twice before trusting the boundary check") is a
judgment call for the model reading the prompt, not for this script. That is future work;
this only surfaces the counts.

Output has two forms because the two existing injection points want different shapes:
  ~/gig/failure-lessons.json          the full aggregate, for anything that wants raw numbers
  domain-skills/failure-lessons.md    "## <STEP>" sections domain_skills.py's existing
                                       section-extraction (BY_STEP/sections()) already knows
                                       how to slice per step -- no new injection mechanism.

Regenerated once per pass from gig_pass.sh's on_exit trap (same contract as
daily_gig_report.py and the other pure-aggregation reporters there): log and continue, never
change the pass's exit code.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = Path.home() / "gig" / "pass-failures.jsonl"
DEFAULT_OUT = Path.home() / "gig" / "failure-lessons.json"
DEFAULT_MARKDOWN = Path(__file__).resolve().parent.parent / "domain-skills" / "failure-lessons.md"

WINDOW_DAYS = 7.0
THRESHOLD = 5
TOP_N = 5

# failed_step, as record_failure() stamps it in gig_pass.sh -> the domain_skills.py step
# key whose prompt is actually built from that failure site. Only steps with a real
# domain_skills.py call site can carry a fragment back into a prompt; anything else here
# is still counted into failure-lessons.json, just never injected (nowhere to inject it).
#   B0/B1/B2/PROFILE/LEARN: gig_pass.sh step() calls domain_skills.py "$label" directly.
#   PAID_WORK: the paid-work builder's own domain_skills.py PAID_WORK call.
#   PAID_QUEUE_DELIVERY -> REPLY: assess_paid_queue's browser-delivery agent is the sole
#     caller of `domain_skills.py REPLY`; its own record_failure calls are stamped
#     PAID_QUEUE_DELIVERY, not REPLY, so the alias corrects for that naming split.
STEP_ALIASES = {
    "B0": "B0",
    "gig-B0": "B0",
    "B1": "B1",
    "B2": "B2",
    "PROFILE": "PROFILE",
    "LEARN": "LEARN",
    "gig-LEARN": "LEARN",
    "PAID_WORK": "PAID_WORK",
    "PAID_QUEUE_DELIVERY": "REPLY",
}


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Tolerant line-by-line read, same contract as lane_lessons.py: a damaged line is
    skipped, never fatal to the reporter that follows."""
    rows: list[dict[str, Any]] = []
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return rows
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def aggregate(
    rows: list[dict[str, Any]],
    *,
    now: float,
    window_days: float = WINDOW_DAYS,
    threshold: int = THRESHOLD,
) -> list[dict[str, Any]]:
    """(failed_step, reason) pairs seen at least `threshold` times inside the trailing
    `window_days`, newest-count-first. A row missing ts/failed_step/reason is not counted
    -- there is nothing to attribute it to."""
    cutoff = now - window_days * 86400
    counts: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"count": 0, "last_seen": 0})
    for row in rows:
        ts = row.get("ts")
        if not isinstance(ts, (int, float)) or isinstance(ts, bool) or ts < cutoff:
            continue
        step = row.get("failed_step")
        reason = row.get("reason")
        if not isinstance(step, str) or not step or not isinstance(reason, str) or not reason:
            continue
        entry = counts[(step, reason)]
        entry["count"] += 1
        entry["last_seen"] = max(entry["last_seen"], int(ts))
    recurring = [
        {"failed_step": step, "reason": reason, "count": v["count"], "last_seen": v["last_seen"]}
        for (step, reason), v in counts.items()
        if v["count"] >= threshold
    ]
    recurring.sort(key=lambda r: (-r["count"], -r["last_seen"]))
    return recurring


def by_domain_step(recurring: list[dict[str, Any]], *, top_n: int = TOP_N) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in recurring:
        target = STEP_ALIASES.get(row["failed_step"])
        if target is None:
            continue
        grouped[target].append(row)
    return {step: entries[:top_n] for step, entries in grouped.items()}


def render_markdown(grouped: dict[str, list[dict[str, Any]]]) -> str:
    if not grouped:
        return ""
    lines: list[str] = []
    for step in sorted(grouped):
        lines.append(f"## {step}")
        for row in grouped[step]:
            when = (
                time.strftime("%Y-%m-%d", time.gmtime(row["last_seen"]))
                if row["last_seen"]
                else "unknown"
            )
            lines.append(f"- 直近{WINDOW_DAYS:.0f}日で{row['count']}回: {row['reason']}（最終観測 {when}）")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--markdown", default=str(DEFAULT_MARKDOWN))
    ap.add_argument("--window-days", type=float, default=WINDOW_DAYS)
    ap.add_argument("--threshold", type=int, default=THRESHOLD)
    ap.add_argument("--top", type=int, default=TOP_N)
    args = ap.parse_args(argv)

    now = time.time()
    rows = read_rows(Path(args.ledger))
    recurring = aggregate(rows, now=now, window_days=args.window_days, threshold=args.threshold)
    grouped = by_domain_step(recurring, top_n=args.top)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": int(now),
        "window_days": args.window_days,
        "threshold": args.threshold,
        "recurring": recurring,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_path = Path(args.markdown)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(grouped), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
