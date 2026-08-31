#!/usr/bin/env python3
"""selfimprove_consumer.py -- F1 (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md sec CC'):
the missing consumer for ~/gig/selfimprove-audit.jsonl.

WHY: gig_selfimprove_verify.sh has appended one row per pass to selfimprove-audit.jsonl for
weeks -- each row already says which self-improve step this pass skipped evidence for
(`missing`) and whether applied.jsonl had malformed rows (`ledger_diagnostics`). Nothing
read that file: selfheal-request generation measured zero for a week straight not because
nothing needed fixing, but because no code converted an audit row into a repair request.

WHAT THIS SCRIPT DOES (routes and formats only -- it never diagnoses or fixes anything):
1. Reads selfimprove-audit.jsonl from a byte-offset cursor so each row is converted at most
   once (idempotent: a second run over the same file appends nothing new).
2. A row qualifies as a gap worth repairing when verification_mode=="material_or_improve"
   AND missing is non-empty (a real pass that should have produced evidence and didn't), OR
   any ledger_diagnostics entry has malformed_count>0 (a writer produced unparseable rows).
   verification_mode=="normal_noop" rows never qualify -- that shape means the pass legitimately
   did nothing (poll-only wake), not a gap. Any other shape (missing keys, wrong types, an
   unrecognised verification_mode) is fail-closed skipped and logged to stderr, never guessed.
3. Each qualifying row becomes ONE append-only line in ~/gig/selfheal-request.jsonl (the durable
   ledger this task's gate reads) with the same {kind, reason, failure_reason, ts} shape
   gig_reality_verify.sh already writes into the singular selfheal-request file, so it is
   consumable by the same downstream reader without inventing a new schema.
4. It also feeds the EXISTING self-fix entrypoint: if the singular configured host-state slot is
   not already occupied by a pending request, this writes one there. The existing auditor wire
   (unchanged by this script)
   picks it up next run and spawns self-fix.sh -- the same fresh-agent diagnose/fix/commit path
   reality-verify failures already use. This script never calls self-fix.sh itself and never
   decides what the fix should be; that judgment stays with the model self-fix.sh spawns.
   If the slot IS occupied, the ledger row is still appended (observability never blocks) but
   the singular file is left alone so an in-flight request is never clobbered.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_selfheal  # noqa: E402 -- F3: sibling module, not a second consumer pipeline

KIND = "selfimprove_gap"


def _read_cursor(cursor_path: Path) -> int:
    try:
        return int(cursor_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _write_cursor(cursor_path: Path, offset: int) -> None:
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cursor_path.with_suffix(cursor_path.suffix + ".tmp")
    tmp.write_text(str(offset), encoding="utf-8")
    tmp.replace(cursor_path)


def _classify(row: dict) -> tuple[bool, str | None]:
    """Return (qualifies, detail). detail is None when the row shape itself is unrecognised
    (fail-closed skip) -- distinct from a recognised row that simply does not qualify."""
    missing = row.get("missing")
    mode = row.get("verification_mode")
    diagnostics = row.get("ledger_diagnostics")
    if not isinstance(missing, list) or not isinstance(mode, str) or not isinstance(diagnostics, dict):
        return False, None  # unrecognised shape -- caller logs+skips, never guesses

    malformed: dict[str, int] = {}
    for name, entry in diagnostics.items():
        if isinstance(entry, dict) and isinstance(entry.get("malformed_count"), int) and entry["malformed_count"] > 0:
            malformed[str(name)] = entry["malformed_count"]

    if mode == "normal_noop":
        # By gig_selfimprove_verify.sh's own contract normal_noop always carries missing=[],
        # so only a malformed-ledger finding can still qualify a no-op pass.
        gap_present = False
    elif mode == "material_or_improve":
        gap_present = len(missing) > 0
    else:
        return False, None  # unrecognised verification_mode -- fail-closed skip

    qualifies = gap_present or bool(malformed)
    if not qualifies:
        return False, ""  # recognised, evaluated, genuinely nothing to repair

    parts = []
    if gap_present:
        parts.append(f"missing evidence for {', '.join(sorted(missing))}")
    if malformed:
        parts.append("malformed rows in " + ", ".join(f"{k}({v})" for k, v in sorted(malformed.items())))
    return True, "; ".join(parts)


def _iter_new_rows(audit_path: Path, start_offset: int) -> tuple[list[tuple[dict | None, str]], int]:
    """Read complete lines from start_offset onward. Returns (rows, new_offset). A row is
    (parsed_dict_or_None, raw_line) so malformed JSON is reported without stopping the scan."""
    if not audit_path.exists():
        return [], start_offset
    size = audit_path.stat().st_size
    if start_offset > size:
        start_offset = 0  # file was rotated/truncated -- restart from the top, never crash
    results: list[tuple[dict | None, str]] = []
    offset = start_offset
    with audit_path.open("rb") as handle:
        handle.seek(start_offset)
        while True:
            line_start = handle.tell()
            raw = handle.readline()
            if not raw:
                break
            if not raw.endswith(b"\n"):
                break  # partial trailing line not yet flushed -- leave it for next run
            offset = handle.tell()
            text = raw.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                results.append((None, text))
                continue
            results.append((parsed if isinstance(parsed, dict) else None, text))
    return results, offset


def run(
    audit_path: Path,
    cursor_path: Path,
    request_ledger: Path,
    selfheal_req: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    # FIRST-RUN GUARD: no cursor file means F1 just went live. The audit file already holds
    # weeks of historical rows (752 at wiring time, oldest source_ts from July) whose problems
    # are likely long stale -- converting them now would flood the selfheal channel with
    # ancient requests. Initialize the cursor to the CURRENT EOF and process nothing; only
    # rows appended AFTER F1 goes live ever become requests.
    if not cursor_path.exists():
        eof = audit_path.stat().st_size if audit_path.exists() else 0
        if not dry_run:
            _write_cursor(cursor_path, eof)
        return {
            "processed": 0,
            "qualified": 0,
            "skipped_unrecognised": 0,
            "skipped_no_gap": 0,
            "selfheal_req_written": False,
            "sample": None,
            "dry_run": dry_run,
            "initialized_cursor_at_eof": eof,
        }

    start_offset = _read_cursor(cursor_path)
    rows, new_offset = _iter_new_rows(audit_path, start_offset)

    summary: dict[str, Any] = {
        "processed": 0,
        "qualified": 0,
        "skipped_unrecognised": 0,
        "skipped_no_gap": 0,
        "selfheal_req_written": False,
        "sample": None,
        "dry_run": dry_run,
    }
    new_requests: list[dict[str, Any]] = []
    now = int(time.time())

    for parsed, raw in rows:
        summary["processed"] += 1
        if parsed is None:
            summary["skipped_unrecognised"] += 1
            print(f"selfimprove_consumer: skipping malformed audit row: {raw[:160]}", file=sys.stderr)
            continue
        qualifies, detail = _classify(parsed)
        if not qualifies:
            if detail is None:
                summary["skipped_unrecognised"] += 1
                print(
                    f"selfimprove_consumer: skipping audit row with unrecognised shape "
                    f"(missing/verification_mode/ledger_diagnostics not as expected): {raw[:160]}",
                    file=sys.stderr,
                )
            else:
                summary["skipped_no_gap"] += 1
            continue
        reason = f"selfimprove-audit gap ({detail}) from pass ts={parsed.get('ts')}"
        request = {
            "ts": now,
            "source_ts": parsed.get("ts"),
            "kind": KIND,
            "reason": reason,
            "failure_reason": reason,
            "missing": parsed.get("missing"),
        }
        new_requests.append(request)
        summary["qualified"] += 1
        if summary["sample"] is None:
            summary["sample"] = request

    if dry_run:
        return summary

    if new_requests:
        request_ledger.parent.mkdir(parents=True, exist_ok=True)
        with request_ledger.open("a", encoding="utf-8") as handle:
            for request in new_requests:
                handle.write(json.dumps(request, ensure_ascii=False) + "\n")
        # Feed the EXISTING self-fix entrypoint (auditor.sh's already-built wire) only if the
        # single-slot queue is free -- never clobber a pending reality-verify request.
        if not selfheal_req.exists():
            selfheal_req.parent.mkdir(parents=True, exist_ok=True)
            tmp = selfheal_req.with_suffix(selfheal_req.suffix + ".tmp")
            tmp.write_text(json.dumps(new_requests[-1], ensure_ascii=False), encoding="utf-8")
            tmp.replace(selfheal_req)
            summary["selfheal_req_written"] = True

    _write_cursor(cursor_path, new_offset)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    host_state = Path(os.environ.get(
        "GIG_HOST_STATE_DIR",
        str(Path.home() / ".local" / "state" / "mr-bot" / "state"),
    ))
    parser.add_argument("--audit", type=Path, default=default_root / "selfimprove-audit.jsonl")
    parser.add_argument("--cursor", type=Path, default=default_root / ".selfimprove-consumer-cursor")
    parser.add_argument("--request-ledger", type=Path, default=default_root / "selfheal-request.jsonl")
    parser.add_argument(
        "--selfheal-req", type=Path,
        default=Path(os.environ.get(
            "GIG_SELFHEAL_REQ", str(host_state / ".gig-core-selfheal-request.json")
        )),
    )
    parser.add_argument(
        "--reconcile-state", type=Path, default=default_root / ".reconcile-selfheal-state.json",
        help="F3: persistence-tracking state for site_ledger_reconcile.py's reconcile-report.json",
    )
    parser.add_argument(
        "--reconcile-evidence-root", type=Path, default=default_root / "evidence",
        help="F3: where passes write gig-pass-*/reconcile-report.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="report what would happen; write nothing")
    args = parser.parse_args(argv)

    summary = run(
        args.audit, args.cursor, args.request_ledger, args.selfheal_req,
        dry_run=args.dry_run,
    )
    # F3: same on_exit invocation, same request ledger and singular slot as F1 above --
    # not a second consumer pipeline. Folded in here so on_exit still runs one process and
    # this prints one JSON summary line.
    reconcile_summary = reconcile_selfheal.run(
        args.reconcile_state, args.request_ledger, args.selfheal_req,
        evidence_root=args.reconcile_evidence_root, dry_run=args.dry_run,
    )
    print(json.dumps({"selfimprove": summary, "reconcile": reconcile_summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
