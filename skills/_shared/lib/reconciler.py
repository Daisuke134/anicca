"""Earn ROI reconciler — sprint-4 (b).

Matches settle events from `~/loops/<slot>/settle.jsonl` (produced by LAYER C,
feature (a)) to roi.jsonl rows by pass_id and populates roi_jpy_realized.
Runs as a menu item (hourly cadence, ROI=0 lowest priority). Pure fixture-
testable core + one I/O sink function. No subprocess, no shell.

FAIL-CLOSED: never fabricates roi_jpy_realized. Ambiguous → .unmatched.jsonl.
INV-4: writes ONLY under `~/loops/<slot>/`. Never touches other ledgers.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Optional


def parse_settle_line(line: str) -> Optional[dict]:
    """PURE: parse a settle.jsonl line. Return dict or None on malformed."""
    s = line.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def merge_realized(existing: int, new: int) -> tuple[int, str]:
    """PURE REQ-R4 monotone-max: return (new_value, status).

    status ∈ {"updated", "skipped_dup", "noop"}.
    """
    try:
        e = int(existing)
        n = int(new)
    except (TypeError, ValueError):
        return int(existing or 0), "skipped_dup"
    if e == 0 and n > 0:
        return n, "updated"
    if n > e:
        return n, "updated"
    if n == e:
        # FIND-001 + FIND-006 fix: distinguish
        # (a) both zero (nothing to replay): "noop" — not counted in skipped_dup
        # (b) positive same-value replay (idempotent Coconala re-settle):
        #     "skipped_dup" per REQ-R4 + EDGE-E5
        return e, ("skipped_dup" if e > 0 else "noop")
    # n < e — never shrink
    return e, "skipped_dup"


def _atomic_replace_jsonl(path: Path, lines: list[str]) -> None:
    """REQ-R5(ii) atomic replace via tempfile in same dir + os.replace."""
    tmp = path.parent / f".{path.name}.tmp"
    tmp.write_text("".join(lines))
    os.replace(tmp, path)


def _read_offset(state_dir: Path) -> int:
    p = state_dir / "reconciler-offset.json"
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text()).get("last_settle_line", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        return 0


def _write_offset_atomic(state_dir: Path, value: int) -> None:
    """REQ-R5(v) — offset LAST, atomic."""
    state_dir.mkdir(parents=True, exist_ok=True)
    tmp = state_dir / ".reconciler-offset.json.tmp"
    tmp.write_text(json.dumps({"last_settle_line": int(value)}, indent=2))
    os.replace(tmp, state_dir / "reconciler-offset.json")


def _load_unmatched_tail_keys(unmatched_path: Path, n: int = 200) -> set:
    """REQ-R7a: read last N lines of unmatched, return set of (pass_id, ts) keys."""
    if not unmatched_path.exists():
        return set()
    try:
        lines = unmatched_path.read_text().splitlines()[-n:]
    except OSError:
        return set()
    keys = set()
    for l in lines:
        try:
            r = json.loads(l)
            keys.add((r.get("pass_id"), r.get("ts")))
        except (json.JSONDecodeError, ValueError):
            pass
    return keys


def reconcile(slot_dir: Path | str, now_ts: int) -> dict:
    """REQ-R1 canonical entry. See spec REQ-R5(i)-(v) for ordering.

    Returns report dict: {matched, unmatched, updated_rows, skipped_dup, elapsed_ms}.
    NEVER raises for missing files or malformed rows.
    """
    slot = Path(slot_dir)
    state_dir = slot / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    settle_path = slot / "settle.jsonl"
    roi_path = slot / "roi.jsonl"
    unmatched_path = slot / ".unmatched.jsonl"

    started_ms = int(time.time() * 1000)

    # (i) BUILD in-memory
    offset_before = _read_offset(state_dir)
    settle_lines: list[str] = []
    if settle_path.exists():
        try:
            settle_lines = settle_path.read_text().splitlines()
        except OSError:
            settle_lines = []
    # EDGE-E9: offset > file → reset
    if offset_before > len(settle_lines):
        offset_before = 0

    new_settle_slice = settle_lines[offset_before:]
    parsed_new_settles: list[tuple[int, dict]] = []
    malformed_indices: list[int] = []
    for idx, line in enumerate(new_settle_slice):
        row = parse_settle_line(line)
        if row is None:
            malformed_indices.append(idx)
        else:
            parsed_new_settles.append((offset_before + idx, row))

    # Load current roi.jsonl. FIND-002 fix: preserve malformed rows verbatim
    # so the atomic rewrite does NOT silently delete them. Malformed rows are
    # stored as {"__raw__": "<original-line>"} sentinels that are re-emitted
    # verbatim on rewrite (see line-render below).
    roi_rows: list[dict] = []
    roi_row_errors: list[dict] = []
    if roi_path.exists():
        try:
            for line_idx, l in enumerate(roi_path.read_text().splitlines()):
                try:
                    roi_rows.append(json.loads(l))
                except (json.JSONDecodeError, ValueError) as _e:
                    # Preserve raw line for round-trip; record error for observability.
                    roi_rows.append({"__raw__": l})
                    roi_row_errors.append({"line": line_idx, "reason": "malformed-json"})
        except OSError:
            pass

    # Build pass_id → roi_row index (for match). Skip preserved __raw__ rows.
    roi_by_pass = {r.get("pass_id"): r for r in roi_rows
                   if r.get("pass_id") and "__raw__" not in r}

    # For each settle event: compute merge, group by pass_id keep highest
    best_by_pass: dict[str, dict] = {}
    unmatched_new: list[dict] = []
    for _idx, srow in parsed_new_settles:
        pid = srow.get("pass_id")
        if not pid or pid not in roi_by_pass:
            # unmatched
            unmatched_new.append({**srow, "reason": ("no-pass-id" if not pid else "unknown-pass-id")})
            continue
        # Store the highest-value settle per pass_id (E5 highest wins)
        prev = best_by_pass.get(pid)
        if prev is None or int(srow.get("jpy", 0) or 0) > int(prev.get("jpy", 0) or 0):
            best_by_pass[pid] = srow

    # Also add malformed lines to unmatched. FIND-004 fix: dedup uses
    # (pass_id, ts) — if we set both to None, all malformed lines in one
    # run share the same key and get collapsed to 1. Use a unique-per-line
    # ts fallback derived from the file offset instead.
    for idx in malformed_indices:
        raw_line = new_settle_slice[idx]
        malformed_ts_sentinel = -(offset_before + idx + 1)  # negative → cannot collide with any real ts (real ts is unix seconds > 0)
        unmatched_new.append({"raw": raw_line, "reason": "malformed-json",
                              "pass_id": f"__malformed__:{offset_before + idx}",
                              "ts": malformed_ts_sentinel})

    matched = 0
    updated_rows = 0
    skipped_dup = 0
    dup_counted_within_slice = 0  # count same-pass_id settles beyond the highest
    # Count within-slice dedup: any settle that was NOT chosen as best is a dup
    seen_in_best = {p: False for p in best_by_pass}
    for _idx, srow in parsed_new_settles:
        pid = srow.get("pass_id")
        if not pid or pid not in best_by_pass:
            continue  # unmatched, counted separately
        if not seen_in_best[pid]:
            seen_in_best[pid] = True
        else:
            dup_counted_within_slice += 1

    # Apply the best settles
    for pid, srow in best_by_pass.items():
        roi_row = roi_by_pass[pid]
        existing = int(roi_row.get("roi_jpy_realized", 0) or 0)
        try:
            new_val = int(srow.get("jpy", 0) or 0)
        except (TypeError, ValueError):
            new_val = 0
        merged, status = merge_realized(existing, new_val)
        matched += 1
        if status == "updated":
            roi_row["roi_jpy_realized"] = merged
            updated_rows += 1
        elif status == "skipped_dup":
            skipped_dup += 1
        # "noop" doesn't increment either

    skipped_dup += dup_counted_within_slice

    # REQ-R7a: dedup unmatched against tail
    tail_keys = _load_unmatched_tail_keys(unmatched_path, n=200)
    to_append = []
    for u in unmatched_new:
        key = (u.get("pass_id"), u.get("ts"))
        if key in tail_keys:
            continue
        to_append.append(u)
        tail_keys.add(key)

    # (ii) atomic replace roi.jsonl. FIND-002: __raw__ sentinels re-emit
    # the original malformed line verbatim so the rewrite is lossless.
    if roi_rows:
        new_lines = []
        for r in roi_rows:
            if "__raw__" in r:
                new_lines.append(r["__raw__"] + "\n")
            else:
                new_lines.append(json.dumps(r) + "\n")
        _atomic_replace_jsonl(roi_path, new_lines)

    # (iii) append unmatched
    if to_append:
        with unmatched_path.open("a", encoding="utf-8") as f:
            for u in to_append:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")

    # (iv) report
    report = {
        "matched": matched,
        "unmatched": len(to_append),
        "updated_rows": updated_rows,
        "skipped_dup": skipped_dup,
        "elapsed_ms": int(time.time() * 1000) - started_ms,
    }
    last_run_path = state_dir / "reconciler-last-run.json"
    tmp = state_dir / ".reconciler-last-run.json.tmp"
    tmp.write_text(json.dumps({**report, "ts": int(now_ts)}, indent=2))
    os.replace(tmp, last_run_path)

    # (v) offset LAST
    _write_offset_atomic(state_dir, len(settle_lines))

    return report
