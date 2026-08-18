#!/usr/bin/env python3
"""Release wedge-quarantine ids the site itself says were never actually submitted.

§FG' (2026-08-09): wedge strikes were misattributed whenever a readback that was checking
one candidate hung on an UNRELATED applicant's offer page while scanning the applied-offers
history. Fixed forward in application_parent.py (ReadbackScanTimeout / readback_inconclusive),
but the fix does not retroactively un-quarantine the 24 ids that were already exiled by the
bug. This script closes that out safely: it collects every id at or above the quarantine
threshold into ONE batched readback -- the SAME paginating exact-id walk the live loop uses,
with a --max-pages budget wide enough for the whole history -- and resets a count to 0 ONLY
when that walk exhausted the applicant's applied-offers history (no next page left, no
truncation raise) without seeing the id.

Fail-closed by construction:
  - absent  -> reset to 0 (the candidate re-enters normal collection next pass; it is never
              blindly resubmitted here, this script only clears the counter)
  - present -> left quarantined (it really is already applied; resetting it would risk a
              second application to the same buyer)
  - readback itself fails/times out -> left quarantined (unknown is not evidence of absence)

Never mutates the ledger, never opens a form, never clicks anything. The only write is to
wedge-quarantine.json, and only for ids the CDP readback confirmed absent.

§FK' live-lineage adaptation: the store is dict-form with a 48h TTL
({"count": N, "updated_at": ts}, 2026-08-08). The first cut of this script parsed only
bare-int values, so against the live file it loaded {} and released nothing (tonight's
measured no-op). It now reads and writes through the SAME load_wedge_counts /
save_wedge_counts the commit boundary uses: dict entries parse, TTL decay applies on
load, and entries left quarantined keep their own updated_at.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import application_parent as parent  # noqa: E402


def release(readback, store, *, threshold: int) -> dict[str, str]:
    """Reset only the ids one exhaustive readback walk confirms are officially absent.

    `readback(ids) -> observed` is ONE call over the whole quarantined batch (review round
    2, reviewer N2): proving absence means walking the entire applied-offers history, and
    a per-id contract would repeat that identical ~20-page walk once per id -- or, worse,
    truncate every time and release nothing. The paginating readback already early-exits
    the moment every expected id has been seen, and raises (never returns) on truncation,
    so on the non-raise path "not in observed" is a verdict from an exhausted history, not
    from a page budget. Any raise -> every quarantined id stays put, zero writes.

    Every candidate below `threshold` is left completely alone -- this tool only touches
    the quarantined tail, never a count that has not yet earned a strike.
    """
    counts = parent.load_wedge_counts(store)
    outcomes: dict[str, str] = {}
    quarantined = sorted(
        (request_id for request_id, count in counts.items() if count >= threshold), key=int
    )
    for request_id in counts:
        if request_id not in set(quarantined):
            outcomes[request_id] = "below_threshold_untouched"
    if not quarantined:
        return outcomes
    try:
        observed = set(readback(set(quarantined)))
    except Exception as error:  # truncation or transport death -- never guess absence
        for request_id in quarantined:
            outcomes[request_id] = f"readback_inconclusive:{type(error).__name__}"
        return outcomes
    changed = False
    for request_id in quarantined:
        if request_id in observed:
            outcomes[request_id] = "already_applied_left_quarantined"
            continue
        counts[request_id] = 0
        outcomes[request_id] = "released"
        changed = True
    if changed:
        # save_wedge_counts drops <=0 entries and keeps each surviving entry's own
        # updated_at (count unchanged -> prior stamp), so a release run never extends
        # anyone else's TTL sentence.
        parent.save_wedge_counts(store, counts)
    return outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--lease-script", type=Path, required=True)
    parser.add_argument("--lease-task", required=True)
    parser.add_argument("--pass-id", default="wedge-quarantine-release")
    parser.add_argument("--threshold", type=int, default=parent.WEDGE_QUARANTINE_THRESHOLD)
    parser.add_argument("--heartbeat-seconds", type=float, default=20.0)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=parent._APPLIED_OFFERS_MAX_PAGES,
        help="page budget for the ONE batched absence walk; the ~450-application history "
        "needs ~25, the live per-candidate readback default is untouched",
    )
    args = parser.parse_args(argv)

    store = parent.fence.IntentStore(args.intent_root)
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    with parent.LeaseHandle(
        lease_script=args.lease_script,
        task=args.lease_task,
        heartbeat_seconds=args.heartbeat_seconds,
    ) as lease:
        effects = parent.CdpParentEffects(
            ws_url=lease.ws_url,
            evidence_dir=args.evidence_dir,
            ledger_path=args.ledger,
            pass_id=args.pass_id,
        )

        def readback(request_ids: set[str]) -> set[str]:
            return effects._official_readback(
                request_ids,
                args.evidence_dir / "wedge-release-readback.json",
                max_pages=args.max_pages,
            )

        outcomes = release(readback, store, threshold=args.threshold)
    # Always leave on-disk proof, even for a no-op. Tonight's live run (2026-08-10)
    # loaded {} from the dict-form store (the pre-port int-only parser), never called
    # the readback, and left --evidence-dir completely empty: the only record that the
    # drain ran at all was a stdout line nobody kept. wedge-release-readback.json is
    # still only written when a walk actually happens; this summary is written every run.
    parent._atomic_json(
        args.evidence_dir / "wedge-release-summary.json",
        {
            "pass_id": args.pass_id,
            "threshold": args.threshold,
            "max_pages": args.max_pages,
            "outcomes": outcomes,
            "readback_ran": any(
                value != "below_threshold_untouched" for value in outcomes.values()
            ),
        },
    )
    print(json.dumps({"ok": True, "outcomes": outcomes}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
