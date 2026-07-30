from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .ledger import Ledger


def migrate_and_rebuild(path: Path) -> dict[str, Any]:
    ledger = Ledger(path)
    try:
        projection = ledger.rebuild_strategy_outcome_projection()
        integrity = str(
            ledger.connection.execute("PRAGMA integrity_check").fetchone()[0]
        )
        counts = {
            "applications": int(
                ledger.connection.execute(
                    "SELECT COUNT(*) FROM applications"
                ).fetchone()[0]
            ),
            "assignments": int(
                ledger.connection.execute(
                    "SELECT COUNT(*) FROM application_strategy_assignments"
                ).fetchone()[0]
            ),
            "funnel_outcomes": int(
                ledger.connection.execute(
                    "SELECT COUNT(*) FROM funnel_outcomes"
                ).fetchone()[0]
            ),
            "projection_rows": len(projection),
            "strategy_generations": int(
                ledger.connection.execute(
                    "SELECT COUNT(*) FROM strategy_generations"
                ).fetchone()[0]
            ),
            "unassigned_applications": int(
                ledger.connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM applications
                    LEFT JOIN application_strategy_assignments AS assignments
                      ON assignments.application_id = applications.id
                    WHERE assignments.application_id IS NULL
                    """
                ).fetchone()[0]
            ),
        }
        capture_status = Counter(
            {
                str(row["capture_status"]): int(row["count"])
                for row in ledger.connection.execute(
                    """
                    SELECT capture_status, COUNT(*) AS count
                    FROM application_strategy_assignments
                    GROUP BY capture_status
                    """
                )
            }
        )
    finally:
        ledger.close()
    if integrity != "ok":
        raise RuntimeError(f"ledger integrity failed: {integrity}")
    if counts["unassigned_applications"] != 0:
        raise RuntimeError("one or more applications lack strategy attribution")
    return {
        "applications": counts["applications"],
        "assignments": counts["assignments"],
        "capture_status": dict(sorted(capture_status.items())),
        "funnel_outcomes": counts["funnel_outcomes"],
        "integrity": integrity,
        "projection_rows": counts["projection_rows"],
        "strategy_generations": counts["strategy_generations"],
        "unassigned_applications": counts["unassigned_applications"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parsed = parser.parse_args(argv)
    receipt = migrate_and_rebuild(parsed.ledger)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
