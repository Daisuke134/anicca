"""reconcile.py — IMPURE orchestration for the Hyperliquid fill-based realized-P&L pipeline
(Group B/C/D). See behavioral-spec.md and verification-architecture.md (this module is the
"IMPURE" rows of the purity boundary map, plus the PURE `plan_batch`).

Composition root: `reconcile(...)`. Acquires an exclusive non-blocking flock FIRST (REQ-B10),
reads the checkpoint (REQ-B7), fetches fills via `Info.user_fills_by_time` (REQ-B8, using the raw
checkpoint value itself as the INCLUSIVE lower bound — no offset is ever added to it — and never
the unbounded `Info.user_fills`), selects/plans a batch (REQ-B2/B3/B4), records each planned fill
EXCLUSIVELY through `record.mjs` (REQ-D1, via an injectable `record_line_fn` — defaults to the
real subprocess call), and advances the checkpoint atomically (REQ-B6) to the last fill it
successfully recorded or confirmed-as-duplicate, written LAST after every append attempt has
resolved.

This module is READ-ONLY against the Hyperliquid exchange (REQ-D3): it places, modifies, and
cancels no order, and never touches the position-closing / leverage-update exchange calls that
`hl.py`'s own `open`/`close` commands use. It resolves NO signing key of its own (REQ-D2) — the
caller (hl.py's `cmd_reconcile`) passes an already-resolved `info`/`address` from the SAME
`_clients()` every other hl.py subcommand uses.
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import tempfile

from fills import compute_realized_pnl, is_unprocessable, select_close_fills

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_RECORD_MJS = os.path.join(_LIB_DIR, "..", "..", "lib", "record.mjs")

# Process-lifetime supplementary dedup cache, keyed by ledger_path: bridges REQ-B4.1's tid-dedup
# across multiple reconcile() calls made within ONE process before a just-recorded fill's real
# ledger append (routed through record.mjs, an out-of-process subprocess) is itself visible to a
# fresh disk scan. In production `hl.py reconcile` is invoked as a brand-new CLI subprocess every
# wake (skills/earn/run.sh) — this cache is always empty there, so the disk scan in
# already_recorded_tids() below remains the sole, authoritative, cross-wake source (NFR-4).
_recorded_tids_cache: dict = {}


def plan_batch(candidates: list, already_recorded_tids: set) -> dict:
    """PURE (REQ-B4): walk `candidates` (already time-ordered by select_close_fills) and decide,
    for each, whether it is a no-op duplicate (REQ-B4.1), a batch-halting UNPROCESSABLE fill
    (REQ-B4.2), or a fill to record (REQ-B4.3's decision only — the actual record attempt and its
    own runtime failure are NOT knowable here, so that half of REQ-B4.3 is handled by the
    effectful `reconcile()` loop, not this pure planner)."""
    steps = []
    stop_index = None
    for i, fill in enumerate(candidates):
        tid = fill.get("tid")
        if tid in already_recorded_tids:
            steps.append({"fill": fill, "action": "skip_duplicate"})
            continue
        if is_unprocessable(fill):
            stop_index = i
            break
        steps.append({"fill": fill, "action": "record"})
    return {"steps": steps, "stop_index": stop_index}


def acquire_lock(lock_path: str):
    """IMPURE (REQ-B10): exclusive, non-blocking flock on `lock_path`. Returns an open file
    handle (caller releases by closing it) or None if another invocation already holds it. Never
    blocks, never raises."""
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    fh = open(lock_path, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


def read_checkpoint(path: str) -> int:
    """IMPURE (REQ-B7): missing/empty/unparseable -> 0. Never raises."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        return int(raw)
    except (FileNotFoundError, ValueError):
        return 0


def write_checkpoint(path: str, value: int) -> None:
    """IMPURE (REQ-B6): atomic write — tempfile in the same directory + os.replace — so a crash
    mid-write can never leave a corrupt or partially-written checkpoint file."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=d, prefix=".tmp-checkpoint-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(value))
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def already_recorded_tids(ledger_path: str) -> set:
    """IMPURE, read-only (REQ-B4.1's dedup set): every `fill_tid` present in `ledger_path`'s
    JSONL lines. Missing ledger -> empty set."""
    tids = set()
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raw = ""
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and "fill_tid" in obj and obj["fill_tid"] is not None:
            tids.add(obj["fill_tid"])
    tids |= _recorded_tids_cache.get(ledger_path, set())
    return tids


def record_line(payload: dict, ledger_path: str) -> dict:
    """IMPURE (REQ-D1) — the ONLY ledger-mutating call in this feature's Python code. Delegates
    the identity guard, the P1 halt check, and the append itself entirely to record.mjs's own
    entrypoint; this module reimplements none of that guard logic directly."""
    result = subprocess.run(
        ["node", _RECORD_MJS, json.dumps(payload), ledger_path],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"record.mjs failed (exit {result.returncode}): {result.stderr[:300]}")
    return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def _build_payload(fill: dict, wallet: str, wake: str) -> dict:
    """REQ-C1 ledger-line payload for one well-formed candidate fill."""
    split = compute_realized_pnl(fill["closedPnl"], fill["fee"])
    coin = fill.get("coin", "")
    tid = fill["tid"]
    return {
        "source": "hl-trade",
        "chain": "hyperliquid",
        "fill_tid": tid,
        "confirmed": True,
        "external": True,
        "earn_usdc": split["earn_usdc"],
        "cost_usdc": split["cost_usdc"],
        "wallet": wallet,
        "task": f"hl-close {coin} tid={tid}".strip(),
        "wake": wake,
    }


def reconcile(info, address: str, ledger_path: str, checkpoint_path: str, lock_path: str,
              wallet: str, wake: str, now_ms: int, record_line_fn=None) -> dict:
    """Composition root (IMPURE). See module docstring + behavioral-spec.md Group B/REQ-E3."""
    if record_line_fn is None:
        record_line_fn = record_line

    lock = acquire_lock(lock_path)
    if lock is None:
        # REQ-B10: another invocation already in flight — touch nothing else, return immediately.
        return {"status": "locked", "recorded": 0}

    try:
        since_time_ms = read_checkpoint(checkpoint_path)

        try:
            # REQ-B8: INCLUSIVE boundary — passes the raw checkpoint value as-is, with no offset
            # added, so a fill sharing the checkpoint's own timestamp is re-fetched, not skipped.
            raw_fills = info.user_fills_by_time(
                address, since_time_ms, now_ms, aggregate_by_time=False
            )
        except Exception as e:  # noqa: BLE001 - REQ-B9: any API failure fails this pass closed
            return {"status": "api-error", "recorded": 0, "error": str(e)[:200]}

        candidates = select_close_fills(raw_fills, since_time_ms)
        already_recorded = already_recorded_tids(ledger_path)
        plan = plan_batch(candidates, already_recorded)

        recorded = 0
        last_handled_time = None
        for step in plan["steps"]:
            fill = step["fill"]
            if step["action"] == "skip_duplicate":
                last_handled_time = fill["time"]
                continue
            # action == "record"
            payload = _build_payload(fill, wallet, wake)
            try:
                record_line_fn(payload, ledger_path)
            except Exception:  # noqa: BLE001 - REQ-B4.3: a record failure STOPs the batch here
                break
            recorded += 1
            last_handled_time = fill["time"]
            _recorded_tids_cache.setdefault(ledger_path, set()).add(fill["tid"])

        # REQ-B5: advance the checkpoint to the LAST fill successfully recorded or confirmed-as-
        # already-recorded this pass, in strict order. Never advance past a STOP; never advance
        # at all if zero eligible fills were handled.
        if last_handled_time is not None:
            write_checkpoint(checkpoint_path, last_handled_time)

        return {"status": "ok", "recorded": recorded}
    finally:
        lock.close()
