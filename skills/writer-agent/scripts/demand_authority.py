#!/usr/bin/env python3
"""Fail-closed authority check before article-daily may select a topic."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_supply import _is_paid_demand_queue_card  # noqa: E402


class DemandAuthorityError(RuntimeError):
    """The required demand authority is not ready for topic selection."""


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise DemandAuthorityError(f"{label} is missing or not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemandAuthorityError(f"{label} is invalid") from error
    if not isinstance(value, dict):
        raise DemandAuthorityError(f"{label} is not an object")
    return value


def validate_required_authority(
    skill_dir: Path | str,
    *,
    demand_mode: str = "required",
) -> dict[str, Any]:
    skill_dir = Path(skill_dir)
    if demand_mode != "required":
        raise DemandAuthorityError("production authority requires demand_mode=required")
    config = _read_json(skill_dir / "config/claim-watch.json", "claim-watch config")
    if config.get("demand_mode") != "required":
        raise DemandAuthorityError("claim-watch config is not in required demand mode")
    state = Path(os.environ.get("ARTICLE_STATE_DIR", str(skill_dir / "state")))
    receipt = _read_json(state / "claim-loop-latest.json", "claim-loop receipt")
    demand = receipt.get("demand")
    if not isinstance(demand, dict) or demand.get("mode") != "required":
        raise DemandAuthorityError("claim-loop receipt is not required demand mode")
    supply = receipt.get("supply")
    supply_status = supply.get("status") if isinstance(supply, dict) else None
    if supply_status not in {"FILLED", "SUFFICIENT"}:
        # A pre-publication retry already owns one immutable paid-demand card.
        # Coconala keeps that claimed work resumable when a later board poll is
        # temporarily unavailable; do the same without weakening new-topic
        # selection. The card itself remains the authority and is revalidated
        # against the immutable opportunity evidence below.
        resume_basename = os.environ.get("ARTICLE_RESUME_CARD_BASENAME", "").strip()
        resume_card = state / "topics/queue" / resume_basename
        if not resume_basename or "/" in resume_basename or "\\" in resume_basename:
            raise DemandAuthorityError(
                f"claim-loop supply status is not ready: {supply_status}"
            )
        if (
            resume_card.is_symlink()
            or not resume_card.is_file()
            or not _is_paid_demand_queue_card(
                resume_card, opportunity_database=state / "opportunities.sqlite3"
            )
        ):
            raise DemandAuthorityError(
                f"claim-loop supply status is not ready: {supply_status}"
            )
        supply_status = "RESUME_CARD"
    queue = state / "topics/queue"
    if queue.is_symlink() or not queue.is_dir():
        raise DemandAuthorityError("demand topic queue is missing or not a directory")
    cards = sorted(path for path in queue.glob("*.md") if path.is_file())
    if not cards:
        raise DemandAuthorityError("demand topic queue is empty")
    opportunity_database = state / "opportunities.sqlite3"
    invalid = [
        path.name
        for path in cards
        if not _is_paid_demand_queue_card(
            path, opportunity_database=opportunity_database
        )
    ]
    if invalid:
        raise DemandAuthorityError(
            "demand topic queue contains non-paid-demand cards: " + ",".join(invalid)
        )
    return {
        "demand_mode": "required",
        "supply_status": supply_status,
        "queue_cards": [path.name for path in cards],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--demand-mode", default="required")
    args = parser.parse_args(argv)
    try:
        result = validate_required_authority(
            args.skill_dir,
            demand_mode=args.demand_mode,
        )
    except DemandAuthorityError as error:
        print(str(error), file=sys.stderr)
        return 75
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
