#!/usr/bin/env python3
"""The pass may not end while a paying customer is unanswered and unexplained — §0.1.6 (P1a-5).

This is what makes the previous four steps load-bearing. A liability that ages in a file
nobody reads is the same as no liability, and this loop has already demonstrated it will
exit zero forever regardless: 24 clean passes, ¥0 earned, one customer waiting throughout.

The gate does not demand a reply. Replying is often genuinely impossible in a given pass —
the artifact is not ready, the browser session is dead, the quota is gone. It demands that
the pass answer "why not" in a form that can be counted later. The only outcome it refuses
is silence, because silence is indistinguishable from everything being fine, and that
indistinguishability is the whole incident.

A disposition from an earlier pass does not excuse this one. Otherwise one refusal on
Monday buys silence for the rest of the week, which is the same failure with a slower clock.

`--expect-store` exists because an absent ledger is what a broken enumerator produces, and
reading "no file" as "nothing owed" would restore exactly the confidence that let two dozen
passes report success. When the caller knows the paid lane ran, it should pass that flag.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

_LIABILITY_PATH = Path(__file__).resolve().parent / "silence_liability.py"


def _liability_module():
    spec = importlib.util.spec_from_file_location("silence_liability", _LIABILITY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(store: Path | str, *, pass_id: str) -> dict[str, Any]:
    """Return the verdict for this pass.

    `detail` carries the customer and the money, not just a key. A gate that fails with a
    hash is useless at 3am, and the amount is what decides whether it can wait.
    """
    module = _liability_module()
    store = Path(store)

    undisposed = module.undisposed(store, pass_id=pass_id)
    open_rows = {row["liability_key"]: row for row in module.open_liabilities(store)}
    detail = [
        {
            "liability_key": key,
            "talkroom_id": open_rows.get(key, {}).get("talkroom_id"),
            "title": open_rows.get(key, {}).get("title"),
            "order_value_jpy": open_rows.get(key, {}).get("order_value_jpy"),
            "age_passes": open_rows.get(key, {}).get("age_passes"),
            "last_refusal": open_rows.get(key, {}).get("last_refusal"),
        }
        for key in undisposed
    ]
    return {
        "ok": not undisposed,
        "pass_id": pass_id,
        "undisposed": undisposed,
        "detail": detail,
        "store": str(store),
        "store_missing": not store.is_file(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--pass-id", required=True)
    parser.add_argument(
        "--expect-store",
        action="store_true",
        help="fail when the ledger is absent instead of reading it as nothing owed",
    )
    args = parser.parse_args(argv)

    verdict = check(args.store, pass_id=args.pass_id)
    if args.expect_store and verdict["store_missing"]:
        verdict["ok"] = False
        verdict["reason"] = (
            "the paid lane ran but wrote no liability ledger — an absent ledger is what a "
            "broken enumerator produces, and it must not read as 'nothing owed'"
        )
    print(json.dumps(verdict, ensure_ascii=False))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
