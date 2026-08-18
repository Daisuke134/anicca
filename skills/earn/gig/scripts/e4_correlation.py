#!/usr/bin/env python3
"""e4_correlation.py -- E4 (26-gig-loop §CC'/§EW' item 4): does E1's predelivery score
predict what E2's buyer_outcome_ledger later records? A score with nothing behind it is
just a number the model made up; this file is what turns that into a checkable claim.

For each project with BOTH a predelivery-score.json (E1, acceptance/predelivery-score.json,
``score`` not null) AND at least one classified reaction in buyer-outcomes.jsonl (E2 +
buyer_reaction_classify.py) at or after the score was taken, appends one row to
``~/gig/score-reality.jsonl``:

    {project_id, talkroom_id, score, first_reaction, reaction_ts, scored_ts}

``first_reaction`` is the EARLIEST classified reaction whose ``ts >= scored_ts`` -- the
closest available proxy for "the buyer's reaction after seeing this graded deliverable".
The score is taken immediately before delivery (same call site as artifact_judge's own
binary gate), so "at or after the score" is the same boundary already used elsewhere in
this pipeline, not a new one invented here. A reaction from before the score was taken
tells us nothing about this delivery and is skipped, not guessed at.

DEDUPE (mirrors buyer_outcome_ledger.py): keyed on ``(project_id, scored_ts)``,
recomputed from what is already in score-reality.jsonl rather than tracked separately,
so this file's schema stays exactly the six fields above. Running twice over the same
state appends nothing the second time. A project that gets re-scored (a new
``scored_ts`` -- a second delivery, e.g. after a revision) is free to join again; that
is a different delivery, not a duplicate of the first.

SAFETY (fail-closed, mirrors project_janitor.py's contract): a missing or unparsable
score/ledger file, or one bad project directory, is skipped, never fatal. No network
calls, no writes outside ``--out``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


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


def _existing_keys(out_path: Path) -> set[tuple[str, Any]]:
    keys: set[tuple[str, Any]] = set()
    for row in _read_jsonl(out_path):
        project_id = row.get("project_id")
        scored_ts = row.get("scored_ts")
        if project_id is not None and scored_ts is not None:
            keys.add((str(project_id), scored_ts))
    return keys


def _score_record(project_dir: Path) -> dict[str, Any] | None:
    path = project_dir / "acceptance" / "predelivery-score.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict):
        return None
    if record.get("score") is None or record.get("scored_at") is None:
        return None
    return record


def _talkroom_id(project_dir: Path, fallback: str) -> str:
    try:
        state = json.loads((project_dir / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    if isinstance(state, dict) and state.get("talkroom_id"):
        return str(state["talkroom_id"])
    return fallback


def _first_reaction(
    reactions_by_project: dict[str, list[dict[str, Any]]], project_id: str, scored_at: float
) -> dict[str, Any] | None:
    rows = reactions_by_project.get(project_id, [])
    candidates = [
        row for row in rows
        if row.get("reaction") and _num(row.get("ts")) is not None and _num(row.get("ts")) >= scored_at
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda row: _num(row.get("ts")))


def correlate(projects_root: Path, outcomes_path: Path, out_path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "scanned_projects": 0, "scored_projects": 0, "joined": 0, "skipped_existing": 0,
    }
    if not projects_root.is_dir():
        return summary

    reactions_by_project: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(outcomes_path):
        project_id = row.get("project_id")
        if project_id is None:
            continue
        reactions_by_project.setdefault(str(project_id), []).append(row)

    existing = _existing_keys(out_path)
    new_rows: list[dict[str, Any]] = []

    for project_dir in sorted(p for p in projects_root.iterdir() if p.is_dir()):
        summary["scanned_projects"] += 1
        record = _score_record(project_dir)
        if record is None:
            continue
        summary["scored_projects"] += 1
        project_id = project_dir.name
        scored_ts = record["scored_at"]
        key = (project_id, scored_ts)
        if key in existing:
            summary["skipped_existing"] += 1
            continue
        scored_at = _num(scored_ts)
        if scored_at is None:
            continue
        reaction_row = _first_reaction(reactions_by_project, project_id, scored_at)
        if reaction_row is None:
            continue
        new_rows.append({
            "project_id": project_id,
            "talkroom_id": _talkroom_id(project_dir, project_id),
            "score": record["score"],
            "first_reaction": reaction_row["reaction"],
            "reaction_ts": reaction_row.get("ts"),
            "scored_ts": scored_ts,
        })

    if new_rows:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as handle:
            for row in new_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary["joined"] = len(new_rows)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    parser.add_argument(
        "--projects-root", type=Path,
        default=Path(os.environ.get("GIG_PROJECTS_ROOT", str(default_root / "projects"))),
    )
    parser.add_argument(
        "--outcomes", type=Path,
        default=Path(os.environ.get("GIG_BUYER_OUTCOMES_LEDGER", str(default_root / "buyer-outcomes.jsonl"))),
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path(os.environ.get("GIG_SCORE_REALITY_LEDGER", str(default_root / "score-reality.jsonl"))),
    )
    args = parser.parse_args(argv)

    summary = correlate(args.projects_root, args.outcomes, args.out)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
