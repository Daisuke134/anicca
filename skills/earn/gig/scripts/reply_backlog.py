#!/usr/bin/env python3
"""How many buyers are still owed a reply, regardless of what arrived this hour.

The pass gates the inquiry-reply lane on the number of inquiries found in the current
snapshot. That is the wrong question. On 2026-08-05 seven buyers sat at state='pending' --
the oldest since 2026-08-01 -- and six more at 'blocked' since 2026-07-23, while the lane
skipped itself on every pass because no NEW message had arrived. reply_lane already knows how
to drain pending_actions(); the gate simply never let it start.

    python3 reply_backlog.py --database ~/gig/connector-outbox.sqlite3   -> 7
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def pending_count(database: Path) -> int:
    """Buyers with an owed reply that no pass has sent yet.

    Never raises. This runs in front of the lane on every pass, so a counter that threw would
    silence the reply lane for a reason that has nothing to do with any buyer -- the same
    shape of failure it exists to end.
    """
    database = Path(database)
    if not database.exists():
        return 0
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM connector_actions WHERE state='pending'"
            ).fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0]) if row else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    print(pending_count(parser.parse_args().database))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
