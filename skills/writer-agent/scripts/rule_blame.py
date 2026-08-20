#!/usr/bin/env python3
"""Accumulate, across runs, how much loss each cited rule line is
responsible for -- the ledger a human or the trainer reads to answer
"which line should die first".

Why this exists: spec 47 section 19-4a. beat_rate.py (19-3) already proved
selection_inverted is real and points blame at a `cited_rule` line (verified
live 2026-07-26 against the actual incident: SKILL.md:124, the exact line a
human identified by hand that day). A single run is one data point; a rule
that is wrong on one bad day looks identical, in isolation, to a rule that
is consistently wrong. This script is the accumulator that tells them apart
-- it also records "clean" evidence FOR a rule (every run where it was not
inverted), so a rule with a long clean streak and one bad day is not
mistaken for a rule that is reliably wrong.

Design choices made because the spec left them open (simplest option, noted
here rather than asked about):
  * `magnitude` for a "clean" observation is 0.0 -- clean means no loss was
    measured, and the schema's `magnitude` field is numeric throughout.
  * A rejected candidate inside an INVERTED run whose own beat_rate did NOT
    exceed chosen's gets NO observation at all -- neither loss nor clean.
    The spec defines "loss" (beat_rate > chosen, inverted run) and "clean"
    (every rejection, non-inverted run) explicitly and leaves this third
    case undefined; inventing a verdict for it would be redesigning, not
    implementing, so it is simply skipped. Verified against the real
    2026-07-26 incident: "バイブコーディングの本質は速度ではない" (beat_rate
    0.5, chosen 0.667, run inverted) gets no row, while
    "24年間ダメだった僕が…" (beat_rate 1.0 > 0.667) gets a loss row -- see
    tests/rule-blame-contract.sh and the module's own verify transcript.
  * A malformed or unreadable beat-rate file is skipped, not fatal -- one
    bad run must not stop the scan of every other run (same posture as
    harvest_corpus.py's per-source degrade-gracefully rule). There is no
    user-supplied structural contract here to enforce with an exit-3 style
    error; the only real "contract" is the corpus of beat-rate files
    beat_rate.py itself already validates when it writes them.
  * `--top` default is 20 -- not specified; a "which lines are worst"
    report longer than that stops being something a human skims.

Round-2 fix: both `collect` and `report` take an explicit `--ledger` path
(default unchanged: state/rule-blame.jsonl). Before this, `collect` accepted
`--state-root` but always wrote to the default ledger regardless, so
pointing it at a scratch state root silently deposited scratch observations
into production state, and there was no way to `report` on anything but the
default. See "collect --ledger leaves the default ledger untouched" in
tests/rule-blame-contract.sh.

INPUT: every <run-dir>/gates/beat-rate-<lang>.json under a state root
(default skills/article-writer/state/runs), found recursively so both a
direct `<root>/gates/...` layout (a single run passed as the root, e.g. for
manual verification) and the production `<root>/<run-id>/gates/...` layout
work identically.

OUTPUT: state/rule-blame.jsonl (append-only, one row per observation):
  {"ts":..., "run_id":..., "lang":..., "cited_rule":"SKILL.md:124",
   "verdict":"loss"|"clean", "magnitude":0.33,
   "rejected_title":..., "chosen_title":...}

Idempotent on (run_id, lang, cited_rule, rejected_title) -- re-collecting
the same runs never appends the same observation twice.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TOP = 20


# ---------------------------------------------------------------------------
# Small pure functions -- these are what the contract test drives directly.
# ---------------------------------------------------------------------------

def observations_from_run(data: dict, *, ts: str) -> list[dict]:
    """The observations one beat-rate-<lang>.json run yields (verbatim
    coordinator rule):
      - selection_inverted False: every rejected candidate with a
        cited_rule is "clean" evidence for that rule.
      - selection_inverted True: only rejected candidates whose beat_rate
        beat the chosen one's are "loss" evidence, magnitude = the gap.
        A rejected candidate that did not beat chosen in an inverted run
        yields nothing (see module docstring)."""
    run_id = data.get("run_id")
    lang = data.get("lang")
    chosen_beat_rate = data.get("chosen_beat_rate", 0.0)
    # beat_rate.py returns None (not False) when the chosen candidate had no
    # scorable pairs at all -- a judge outage, not a verdict. Coercing that to
    # False would bank "clean" evidence FOR every cited rule on a night nobody
    # measured anything, and a clean streak is what protects a rule from
    # deletion. No evidence is neither guilt nor innocence: record nothing.
    raw_inverted = data.get("selection_inverted", False)
    if raw_inverted is None:
        return []
    inverted = bool(raw_inverted)

    chosen_title = None
    for candidate in data.get("candidates", []):
        if candidate.get("role") == "chosen":
            chosen_title = candidate.get("title")
            break

    rows: list[dict] = []
    for candidate in data.get("candidates", []):
        if candidate.get("role") != "rejected":
            continue
        cited_rule = candidate.get("cited_rule")
        if not cited_rule:
            continue
        rejected_title = candidate.get("title")
        rejected_beat_rate = candidate.get("beat_rate", 0.0)

        if not inverted:
            rows.append({
                "ts": ts, "run_id": run_id, "lang": lang, "cited_rule": cited_rule,
                "verdict": "clean", "magnitude": 0.0,
                "rejected_title": rejected_title, "chosen_title": chosen_title,
            })
        elif rejected_beat_rate > chosen_beat_rate:
            rows.append({
                "ts": ts, "run_id": run_id, "lang": lang, "cited_rule": cited_rule,
                "verdict": "loss", "magnitude": rejected_beat_rate - chosen_beat_rate,
                "rejected_title": rejected_title, "chosen_title": chosen_title,
            })
    return rows


def observation_key(row: dict) -> tuple:
    """Idempotency key: same rule, same rejected candidate, same run."""
    return (row.get("run_id"), row.get("lang"), row.get("cited_rule"), row.get("rejected_title"))


def load_existing_keys(path: Path) -> set:
    keys = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        keys.add(observation_key(row))
    return keys


def append_observations(path: Path, observations: list[dict]) -> tuple[int, int]:
    """Append observations whose key is not already in the ledger. Returns
    (written, duplicate)."""
    existing = load_existing_keys(path)
    written = 0
    duplicate = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in observations:
            key = observation_key(row)
            if key in existing:
                duplicate += 1
                continue
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            existing.add(key)
            written += 1
    return written, duplicate


def aggregate_by_rule(observations: list[dict]) -> list[dict]:
    """One row per cited_rule: loss count, clean count, total loss
    magnitude, and the single highest-magnitude loss example. Ranked by
    total_magnitude descending -- "which line should die first"."""
    by_rule: dict[str, dict] = {}
    for row in observations:
        rule = row.get("cited_rule")
        if not rule:
            continue
        entry = by_rule.setdefault(rule, {
            "cited_rule": rule, "losses": 0, "cleans": 0,
            "total_magnitude": 0.0, "worst_example": None,
        })
        if row.get("verdict") == "loss":
            entry["losses"] += 1
            magnitude = row.get("magnitude", 0.0)
            entry["total_magnitude"] += magnitude
            worst = entry["worst_example"]
            if worst is None or magnitude > worst["magnitude"]:
                entry["worst_example"] = {
                    "rejected_title": row.get("rejected_title"),
                    "chosen_title": row.get("chosen_title"),
                    "magnitude": magnitude,
                    "run_id": row.get("run_id"),
                }
        elif row.get("verdict") == "clean":
            entry["cleans"] += 1
    return sorted(by_rule.values(), key=lambda entry: entry["total_magnitude"], reverse=True)


def format_report_table(rows: list[dict], top: int) -> str:
    header = f"{'cited_rule':<40} {'losses':>7} {'cleans':>7} {'total_magnitude':>16}  worst_example"
    lines = [header]
    if not rows:
        lines.append("(no observations recorded yet)")
        return "\n".join(lines)
    for entry in rows[:top]:
        worst = entry["worst_example"]
        if worst:
            worst_text = (
                f'"{worst["rejected_title"]}" beat "{worst["chosen_title"]}" '
                f'by {worst["magnitude"]:.3f} (run {worst["run_id"]})'
            )
        else:
            worst_text = "-"
        lines.append(
            f"{entry['cited_rule']:<40} {entry['losses']:>7} {entry['cleans']:>7} "
            f"{entry['total_magnitude']:>16.3f}  {worst_text}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Disk scanning (impure) -- everything above this line is what the contract
# test drives directly with in-memory fixtures.
# ---------------------------------------------------------------------------

def load_ledger_observations(path: Path) -> list[dict]:
    """Every observation currently on disk in state/rule-blame.jsonl."""
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def scan_runs(state_root: Path) -> list[dict]:
    """Every beat-rate-<lang>.json under state_root, recursively (matches
    both a run dir passed directly as the root, and the production
    <root>/<run-id>/gates/ layout)."""
    runs: list[dict] = []
    if not state_root.exists():
        return runs
    for path in sorted(state_root.glob("**/gates/beat-rate-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            runs.append(data)
    return runs


def collect(state_root: Path, ledger_path: Path) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    observations: list[dict] = []
    for run in scan_runs(state_root):
        observations.extend(observations_from_run(run, ts=ts))
    written, duplicate = append_observations(ledger_path, observations)
    return {"ok": True, "path": str(ledger_path), "scanned": len(observations), "written": written, "duplicate": duplicate}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_state_root() -> Path:
    return Path(__file__).resolve().parent.parent / "state" / "runs"


def _default_ledger_path() -> Path:
    return Path(__file__).resolve().parent.parent / "state" / "rule-blame.jsonl"


def cmd_collect(args: argparse.Namespace) -> int:
    state_root = Path(args.state_root) if args.state_root else _default_state_root()
    ledger_path = Path(args.ledger) if args.ledger else _default_ledger_path()
    result = collect(state_root, ledger_path)
    print(json.dumps(result))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger) if args.ledger else _default_ledger_path()
    rows = aggregate_by_rule(load_ledger_observations(ledger_path))
    print(format_report_table(rows, args.top))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="scan beat-rate runs and append new observations")
    p_collect.add_argument("--state-root", default=None)
    p_collect.add_argument("--ledger", default=None, help="observation ledger path (default: state/rule-blame.jsonl)")

    p_report = sub.add_parser("report", help="ranked table: rule line, losses, cleans, total magnitude, worst example")
    p_report.add_argument("--top", type=int, default=DEFAULT_TOP)
    p_report.add_argument("--ledger", default=None, help="observation ledger path (default: state/rule-blame.jsonl)")

    args = parser.parse_args(argv)
    if args.command == "collect":
        return cmd_collect(args)
    if args.command == "report":
        return cmd_report(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
