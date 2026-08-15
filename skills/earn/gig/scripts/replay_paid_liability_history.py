#!/usr/bin/env python3
"""Replay the recorded pass history through the liability gate — spec §0.1.6 (P1a-6).

The done condition for the paid-buyer lane was never "the code runs". It was "the code
catches the failure that already happened". So this walks the real evidence directories in
chronological order, feeds each pass's marketplace snapshot through the enumerator, and
asks the gate what it would have said at the end of that pass.

Measured on 2026-08-05 against the live evidence root: 77 of 77 passes with a snapshot
would have failed the gate. Four separate silences on 90000004 (¥2,500 each, the oldest
surviving 47 passes) and one on 90000000 (¥40,000, 9 passes) — ¥50,000 of accepted work
sitting unanswered and unexplained while every pass log read clean.

That number is also why the gate ships report-only. A gate that fails 77 out of 77 passes
is not a gate, it is an outage. Blocking has to wait until a lane can actually dispose of a
liability, either by acting with a readback or by refusing with a typed code. The replay is
what proves the gate fires in the right places; it is not permission to switch it on.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_SNAPSHOT_NAMES = ("marketplace-snapshot.json", "marketplace-snapshot.after-reply.json")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pass_dirs(evidence_root: Path) -> list[Path]:
    """Pass directories in the order they actually ran.

    Sorted by the epoch embedded in the name rather than by mtime, because evidence dirs get
    touched by later tooling and mtime would silently reorder history.
    """
    dirs = []
    for path in evidence_root.glob("gig-pass-*"):
        match = re.search(r"gig-pass-(\d+)", path.name)
        if path.is_dir() and match:
            dirs.append((int(match.group(1)), path))
    return [path for _, path in sorted(dirs)]


def _snapshot_for(pass_dir: Path) -> Path | None:
    for name in _SNAPSHOT_NAMES:
        candidate = pass_dir / name
        if candidate.is_file():
            return candidate
    return None


def replay(evidence_root: Path | str, store: Path | str) -> dict[str, Any]:
    enumeration = _load("paid_talkroom_enumeration")
    liability = _load("silence_liability")
    gate = _load("paid_lane_pass_gate")

    evidence_root = Path(evidence_root)
    store = Path(store)

    passes_with_snapshot = 0
    passes_gate_would_fail = 0
    failures: list[dict[str, Any]] = []

    for pass_dir in _pass_dirs(evidence_root):
        snapshot_path = _snapshot_for(pass_dir)
        if snapshot_path is None:
            continue
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A snapshot we cannot read is a pass we cannot judge. Skipping it silently
            # would flatter the result, so it is counted separately below.
            continue
        passes_with_snapshot += 1
        pass_id = pass_dir.name
        result = enumeration.enumerate_paid_talkrooms(snapshot)
        liability.observe(store, result["rooms"], pass_id=pass_id)
        verdict = gate.check(store, pass_id=pass_id)
        if not verdict["ok"]:
            passes_gate_would_fail += 1
            failures.append({"pass_id": pass_id, "detail": verdict["detail"]})

    still_open = liability.open_liabilities(store)
    return {
        "evidence_root": str(evidence_root),
        "passes_with_snapshot": passes_with_snapshot,
        "passes_gate_would_fail": passes_gate_would_fail,
        "still_open": still_open,
        "owed_jpy": sum((row["order_value_jpy"] or 0) for row in still_open),
        "oldest_age_passes": max((row["age_passes"] for row in still_open), default=0),
        "first_failure": failures[0] if failures else None,
        "last_failure": failures[-1] if failures else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", default=str(Path.home() / "gig" / "evidence"))
    parser.add_argument("--store", required=True, help="scratch ledger; do not point at production")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = replay(args.evidence_root, args.store)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"snapshot を持つ pass: {report['passes_with_snapshot']}")
        print(f"ゲートが点灯する pass: {report['passes_gate_would_fail']}")
        print(f"未応答のまま滞留: ¥{report['owed_jpy']:,}")
        for row in report["still_open"]:
            print(
                f"  {row['talkroom_id']} ¥{row['order_value_jpy']} "
                f"{row['age_passes']} パス経過  {(row['title'] or '')[:30]}"
            )
    # Zero means the history contained no unanswered paying customer. It never has.
    return 0 if report["passes_gate_would_fail"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
