"""earnings-to-settle-mirror — sprint-4 (a2).

Bridges LAYER C's ~/gig/earnings.jsonl to ~/loops/<slot>/settle.jsonl.
Runs as a menu item ("settle-mirror") on 3600s cadence, ROI=0.

INV-1: no subprocess to <slot>-cli.sh.
INV-4: reads ~/gig/earnings.jsonl (READ-only); writes ONLY under ~/loops/<slot>/.
INV-J8: no human-touch surfaces.
Fail-closed: never fabricates a plausible pass_id; unmatched → sentinel.
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

SETTLED_STATUSES = frozenset({"検収", "支払", "検収完了", "completed", "paid"})
_PASS_ID_RE = re.compile(r"^p-\d+$")


def parse_earnings_line(line: str) -> Optional[dict]:
    s = line.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def is_settled_row(row: dict) -> bool:
    """PROP-E3: settled status AND positive int jpy."""
    if not isinstance(row, dict):
        return False
    if row.get("status") not in SETTLED_STATUSES:
        return False
    try:
        jpy = int(row.get("jpy", 0) or 0)
    except (TypeError, ValueError):
        return False
    return jpy > 0


def extract_pass_id_or_sentinel(row: dict) -> str:
    """REQ-R3(ii) direct field read + regex validation.

    Returns row.pass_id if it matches ^p-\\d+$; else the sentinel
    'unmatched-requestId-<X>' where X is the requestId (str-cast).
    """
    pid = row.get("pass_id")
    if isinstance(pid, str) and _PASS_ID_RE.match(pid):
        return pid
    return f"unmatched-requestId-{row.get('requestId')}"


def build_settle_row(
    *, pass_id: str, requestId, jpy: int, status: str, ts: int,
    slot: str, earnings_ts,
) -> dict:
    """REQ-R3(iii): top-level requestId + earnings_status for dedup."""
    return {
        "schema_version": 1,
        "ts": int(ts),
        "pass_id": pass_id,
        "slot": slot,
        "jpy": int(jpy),
        "source": "coconala-earnings-mirror",
        "requestId": str(requestId),
        "earnings_status": str(status),
        "evidence": {"earnings_ts": earnings_ts},
    }


def settle_row_dedup_key(row: dict) -> tuple:
    return (str(row.get("requestId")), str(row.get("earnings_status")))


def _read_offset(state_dir: Path) -> int:
    p = state_dir / "settle-mirror-offset.json"
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text()).get("last_earnings_line", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        return 0


def _write_offset_atomic(state_dir: Path, value: int) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    tmp = state_dir / ".settle-mirror-offset.json.tmp"
    tmp.write_text(json.dumps({"last_earnings_line": int(value)}, indent=2))
    os.replace(tmp, state_dir / "settle-mirror-offset.json")


def _load_settle_dedup_tail(settle_path: Path, n: int = 500) -> set:
    if not settle_path.exists():
        return set()
    try:
        lines = settle_path.read_text().splitlines()[-n:]
    except OSError:
        return set()
    keys = set()
    for l in lines:
        try:
            keys.add(settle_row_dedup_key(json.loads(l)))
        except (json.JSONDecodeError, ValueError):
            pass
    return keys


def mirror_earnings_to_settle(
    slot_dir: Path,
    earnings_path: Path,
    now_ts: int,
) -> dict:
    """REQ-R1 canonical entry. Read new earnings rows, append settle rows.

    NEVER writes to earnings.jsonl or anywhere outside slot_dir.
    """
    slot = Path(slot_dir)
    slot_name = slot.name
    state_dir = slot / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    settle_path = slot / "settle.jsonl"

    started_ms = int(time.time() * 1000)

    # (i) BUILD in-memory
    offset_before = _read_offset(state_dir)
    earnings_lines = []
    if earnings_path.exists():
        try:
            earnings_lines = earnings_path.read_text().splitlines()
        except OSError:
            earnings_lines = []
    # EDGE-E8: offset > file → reset to 0
    if offset_before > len(earnings_lines):
        offset_before = 0

    new_slice = earnings_lines[offset_before:]
    dedup_keys = _load_settle_dedup_tail(settle_path, n=500)

    to_append = []
    dup = 0
    unmatched = 0
    for line in new_slice:
        row = parse_earnings_line(line)
        if row is None:
            continue
        if not is_settled_row(row):
            continue
        pass_id = extract_pass_id_or_sentinel(row)
        settle_row = build_settle_row(
            pass_id=pass_id, requestId=row.get("requestId"),
            jpy=row.get("jpy"), status=row.get("status"),
            ts=now_ts, slot=slot_name,
            earnings_ts=row.get("ts"),
        )
        key = settle_row_dedup_key(settle_row)
        if key in dedup_keys:
            dup += 1
            continue
        dedup_keys.add(key)
        to_append.append(settle_row)
        if pass_id.startswith("unmatched-requestId-"):
            unmatched += 1

    # (ii) APPEND
    if to_append:
        with settle_path.open("a", encoding="utf-8") as f:
            for r in to_append:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = {
        "new": len(to_append),
        "dup": dup,
        "unmatched": unmatched,
        "elapsed_ms": int(time.time() * 1000) - started_ms,
    }

    # (iii) last-run marker
    tmp = state_dir / ".settle-mirror-last-run.json.tmp"
    tmp.write_text(json.dumps({**report, "ts": int(now_ts)}, indent=2))
    os.replace(tmp, state_dir / "settle-mirror-last-run.json")

    # (iv) offset LAST
    _write_offset_atomic(state_dir, len(earnings_lines))

    return report
