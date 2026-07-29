#!/usr/bin/env python3
"""Lane-attributed lessons for the Gig loop.

X19 (2026-07-27).  Applying well and delivering well are different skills, so they must
accumulate separately.  Before this, ~/gig/lessons.jsonl held 280 rows with no lane
attribution whatsoever -- not one row carried a `lane` key -- and LEARN was told to read
"lessons.jsonl" whole.  Every lane that consulted the pile learned mostly about work it
does not do.

ONE FILE, NOT SIX.  Measured before choosing:
  * Readers: gig_funnel.py joins applied rows to lessons by requestId and counts
    outcome=="accepted" across ALL lessons; gig_selfimprove_verify.sh uses the file's
    mtime as self-check evidence.  Both want the whole corpus.  Six files would force the
    funnel to glob-and-merge and would turn one mtime into a max() over six -- i.e. this
    change would have to break requirement "existing readers keep working" to buy
    nothing.  A `lane` column keeps both readers byte-compatible: they never look at keys
    they do not know.
  * Write frequency: one lesson per pass from LEARN.  Contention is not the problem.
  * Corruption tolerance: production line 242 is a truncated append.  Splitting does not
    prevent that -- it gives six files that can each be half-written.  What actually
    contains the damage is a tolerant line-by-line reader plus an append that starts on a
    fresh line, both of which are here and both of which are file-count agnostic.

PAST ROWS ARE NOT GUESSED.  The 280 legacy rows keep no lane and are reported as `null`.
Many of them look like apply lessons; inferring would make a fabricated attribution
indistinguishable from a real one for every future reader.  The file is also append-only
by contract, so backfilling would mean rewriting a ledger to record something nobody
observed.  `stats` keeps the null count visible instead.

WHAT GOES IN A LANE'S LESSONS vs WHAT STAYS SHARED
  Lane-scoped (here): anything whose truth depends on which lane you are in -- what makes
    a proposal get accepted, which delivery formats buyers return, when a reply lands.
    Test: would this lesson be noise or actively misleading to a different lane?  If yes,
    it is lane-scoped.
  Shared (NOT here -- it lives in step_ownership_contract() in gig_pass.sh): rules that
    are true no matter which lane is running -- browser/tab-lease etiquette, "do not
    rewrite existing JSONL", "do not invoke gig_pass.sh".  These are prohibitions on the
    agent, not learned facts about a market, and they must not be able to age out of a
    bounded window.  Test: if a lane never saw this, could it cause damage outside its
    own lane?  If yes, it is shared and belongs in the ownership contract.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

# The six lanes the pass can drive, named as lane_health.py / record_lane_attempt() name
# them so one vocabulary covers health, productivity and lessons.
LANES = ("apply", "reply", "fulfill", "list", "profile", "improve")

# gig_pass.sh step label -> lane.  Kept next to LANES so a new step cannot quietly
# acquire an unnamed lane.
STEP_LANES = {
    "B2": "apply",
    "B1": "reply",
    "PAID_WORK": "fulfill",
    "B0": "list",
    "PROFILE": "profile",
    "LEARN": "improve",
}

DEFAULT_PATH = Path.home() / "gig" / "lessons.jsonl"

# Prompt bounds. The point is not token cost today -- measured prompts are 1.7-6.1KB and
# nothing injects the 256KB ledger -- it is that an append-only file grows forever, so an
# unbounded read is a prompt-size bug scheduled for later.
DEFAULT_LIMIT = 8
MAX_LESSON_CHARS = 400
MAX_BRIEF_CHARS = 4000

# Only these keys reach a model. The row also carries requestId/reason/pass and other
# bookkeeping that a lane does not need to act.
BRIEF_FIELDS = ("ts", "category", "outcome", "lesson")


def read_rows(path: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], int]:
    """Return (object rows, malformed count). Never raises on a damaged file.

    Blank lines are not damage. A line that is not JSON, or is JSON but not an object,
    is: it is counted so the count can be surfaced rather than silently swallowed.
    """
    rows: list[dict[str, Any]] = []
    malformed = 0
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return rows, malformed
    except OSError:
        return rows, malformed
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if isinstance(value, dict):
                rows.append(value)
            else:
                malformed += 1
    return rows, malformed


def lane_of(row: dict[str, Any]) -> str | None:
    """The row's lane, or None. An unrecognised lane string is None, not a new lane --
    a typo must not silently create a private bucket only its author can read."""
    lane = row.get("lane")
    if isinstance(lane, str) and lane in LANES:
        return lane
    return None


def stats(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(rows), "attributed": 0, "null": 0}
    counts.update({lane: 0 for lane in LANES})
    for row in rows:
        lane = lane_of(row)
        if lane is None:
            counts["null"] += 1
        else:
            counts[lane] += 1
            counts["attributed"] += 1
    return counts


def select(
    rows: list[dict[str, Any]], lane: str, limit: int = DEFAULT_LIMIT
) -> list[dict[str, Any]]:
    """The most recent `limit` lessons belonging to `lane`, oldest dropped first.

    Recency is file order, not `ts`: two production rows have no ts at all, and an
    append-only ledger is already chronological. Sorting by a key that is sometimes
    missing would reorder history to no benefit.
    """
    matching = [row for row in rows if lane_of(row) == lane]
    if limit is not None and limit >= 0:
        matching = matching[-limit:] if limit else []
    return matching


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_LESSON_CHARS:
        return value[:MAX_LESSON_CHARS]
    return value


def brief(
    rows: list[dict[str, Any]], lane: str, limit: int = DEFAULT_LIMIT
) -> str:
    """Compact JSON for injection into one lane's step prompt."""
    selected = select(rows, lane, limit)
    entries = [
        {key: _clip(row[key]) for key in BRIEF_FIELDS if key in row}
        for row in selected
    ]
    while True:
        payload = json.dumps(
            {"lane": lane, "lessons": entries},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        # Drop the oldest until the whole brief fits. The bound is on the rendered
        # string because that is what actually lands in the prompt.
        if len(payload) <= MAX_BRIEF_CHARS or not entries:
            return payload
        entries.pop(0)


def append_row(
    path: str | os.PathLike[str], row: dict[str, Any], lane: str | None
) -> dict[str, Any]:
    """Append one lane-attributed lesson. The lane is mandatory and is set here.

    Enforcing at the write boundary rather than by prompt wording is the whole point:
    "the prompt asked for a lane" is not a guarantee, a rejected write is.
    """
    if not isinstance(lane, str) or lane not in LANES:
        raise ValueError(
            f"lane must be one of {', '.join(LANES)}; got {lane!r}"
        )
    if not isinstance(row, dict):
        raise ValueError("lesson row must be a JSON object")
    existing = row.get("lane")
    if existing is not None and existing != lane:
        # A payload claiming a different lane than the caller declared means one of the
        # two is wrong; guessing which would be the fabrication this module forbids.
        raise ValueError(
            f"row lane {existing!r} contradicts declared lane {lane!r}"
        )
    payload = dict(row)
    payload["lane"] = lane
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Open for append+read so a file whose last append was truncated mid-line gets its
    # own newline first. Without this the new row welds onto the damaged one and a
    # single corruption eats a second lesson.
    with open(target, "a+", encoding="utf-8") as handle:
        needs_newline = False
        if handle.tell() > 0:
            handle.seek(handle.tell() - 1)
            needs_newline = handle.read(1) != "\n"
        if needs_newline:
            handle.write("\n")
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return payload


def _resolve(path: str | None) -> Path:
    return Path(path) if path else DEFAULT_PATH


def main(argv: list[str] | None = None) -> int:
    # --path is shared rather than global so it may be written either before or after
    # the subcommand; a caller should not have to know argparse's ordering rule.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--path", default=None, help="lessons.jsonl (default ~/gig)")

    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], parents=[common]
    )
    sub = parser.add_subparsers(dest="command", required=True)

    brief_cmd = sub.add_parser(
        "brief", parents=[common], help="one lane's recent lessons as compact JSON"
    )
    brief_cmd.add_argument("--lane", required=True, choices=LANES)
    brief_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    sub.add_parser(
        "stats", parents=[common],
        help="lane attribution counts, including null and malformed",
    )

    append_cmd = sub.add_parser(
        "append", parents=[common], help="append one lane-attributed lesson"
    )
    append_cmd.add_argument("--lane", required=True)
    append_cmd.add_argument("--json", required=True, help="the lesson row as JSON")

    args = parser.parse_args(argv)
    path = _resolve(args.path)

    if args.command == "brief":
        rows, _ = read_rows(path)
        print(brief(rows, args.lane, args.limit))
        return 0

    if args.command == "stats":
        rows, malformed = read_rows(path)
        counts = stats(rows)
        counts["malformed"] = malformed
        print(json.dumps(counts, ensure_ascii=False, separators=(",", ":")))
        return 0

    if args.command == "append":
        try:
            row = json.loads(args.json)
        except ValueError as error:
            print(f"lane_lessons: invalid --json: {error}", file=sys.stderr)
            return 2
        try:
            written = append_row(path, row, args.lane)
        except ValueError as error:
            print(f"lane_lessons: {error}", file=sys.stderr)
            return 2
        print(json.dumps(written, ensure_ascii=False, separators=(",", ":")))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
