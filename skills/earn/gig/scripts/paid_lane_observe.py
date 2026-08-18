#!/usr/bin/env python3
"""Record who is waiting, immediately after reply_queue decides not to look — §0.1.6 (P1a-5).

One command for the pass to call. It reads the marketplace snapshot, enumerates the paid
talkrooms, and writes a liability row for every buyer left waiting.

Its position in the pass is the point. `reply_queue.py build` gathers the paid talkroom ids
and then skips all of them; this runs on the next line and picks up exactly what was just
put down. Keeping the two halves adjacent means nobody can later read the pass and believe
paid rooms are handled somewhere else.

Non-zero exit is reserved for the enumerator being blind — a missing snapshot, or an order
that could not be keyed. Those are the conditions under which a waiting customer becomes
invisible, and invisibility is what produced 24 silent passes. Having open liabilities is
not itself an error here; that is the pass gate's judgement at the end, not this one's.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--store", required=True)
    parser.add_argument("--pass-id", required=True)
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "snapshot_missing": True,
                    "snapshot": str(snapshot_path),
                    "reason": "no snapshot means no enumeration, and an unenumerated paid "
                    "room cannot grow a liability",
                },
                ensure_ascii=False,
            )
        )
        return 2

    enumeration = _load("paid_talkroom_enumeration")
    liability = _load("silence_liability")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    result = enumeration.enumerate_paid_talkrooms(snapshot)
    liability.observe(Path(args.store), result["rooms"], pass_id=args.pass_id)

    open_rows = liability.open_liabilities(Path(args.store))
    payload = {
        "ok": not result["errors"] and result["dropped"] == 0,
        "snapshot_missing": False,
        "pass_id": args.pass_id,
        "orders_seen": result["orders_seen"],
        "rooms_enumerated": result["rooms_enumerated"],
        "dropped": result["dropped"],
        "collector_suspect": result["collector_suspect"],
        "errors": result["errors"],
        "open_liabilities": len(open_rows),
        "oldest_age_passes": max((row["age_passes"] for row in open_rows), default=0),
        "owed_jpy": sum((row["order_value_jpy"] or 0) for row in open_rows),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
