#!/usr/bin/env python3
"""Fail-closed gate for the one-time, owner-posted Life Manager X launch."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re


def _lm_video_state_root() -> Path:
    """Portable lm-video state root: LM_DATA_DIR when set (absolute only,
    mirroring resolveDataRoot in apps/life-manager/lib/runtime-paths.js and
    default_video_root in skills/video/daily-lm-video/generate.py), else
    <home>/.local/state/life-manager."""
    override = os.environ.get("LM_DATA_DIR", "").strip()
    if override:
        if not Path(override).is_absolute():
            raise SystemExit("LM_DATA_DIR must be an absolute path")
        data_root = Path(override)
    else:
        data_root = Path.home() / ".local/state/life-manager"
    return data_root / "state" / "lm-video"


REQUIRED_ROWS = ("8e", "8f", "9b", "9c", "9d", "9e")
X_STATUS_URL = re.compile(r"https://(?:www\.)?x\.com/[^/]+/status/[0-9]+/?")


def _status_cells(spec_text: str) -> dict[str, str]:
    statuses = {}
    required = set(REQUIRED_ROWS)
    for line in spec_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if cells and cells[0] in required and len(cells) >= 4:
            statuses[cells[0]] = cells[-1]
    return statuses


def _done(status: str | None) -> bool:
    if not status:
        return False
    normalized = status.strip().lstrip("*").casefold()
    return normalized.startswith("done")


def evaluate(spec_text: str, ledger_rows: list[dict]) -> dict:
    completed = [
        row
        for row in ledger_rows
        if isinstance(row, dict)
        and row.get("status") == "published_by_owner"
        and isinstance(row.get("public_url"), str)
        and X_STATUS_URL.fullmatch(row["public_url"])
    ]
    if completed:
        return {
            "status": "already_done",
            "blockers": [],
            "owner_handoff_allowed": False,
            "agent_posting_allowed": False,
            "public_url": completed[-1]["public_url"],
        }
    statuses = _status_cells(spec_text)
    blockers = [row for row in REQUIRED_ROWS if not _done(statuses.get(row))]
    return {
        "status": "blocked" if blockers else "ready_for_owner_handoff",
        "blockers": blockers,
        "owner_handoff_allowed": not blockers,
        "agent_posting_allowed": False,
        "public_url": None,
    }


def _read_ledger(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("launch ledger rows must be objects")
        rows.append(row)
    return rows


def run(spec: Path, ledger: Path) -> dict:
    return evaluate(
        Path(spec).read_text(encoding="utf-8"),
        _read_ledger(Path(ledger)),
    )


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        type=Path,
        default=root / "docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=_lm_video_state_root() / "x-launch.jsonl",
    )
    args = parser.parse_args()
    print(json.dumps(run(args.spec, args.ledger), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
