#!/usr/bin/env python3
"""Shared, receipt-first Ebook Seller runner (shadow stage)."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "brain"))
sys.path.insert(0, str(HERE / "gates"))
from script_ledger import ScriptLedger, preflight  # noqa: E402
from ebook_packs import load_ebook_packs  # noqa: E402


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def run(*, engine: Path, product: str, slot_at: str, script_id: str, ledger_path: Path,
        state_root: Path) -> dict:
    packs = load_ebook_packs(engine)
    pack = next((item for item in packs.values() if item["product_id"] == product), None)
    require(pack is not None, "ebook product pack missing")
    timestamp = dt.datetime.fromisoformat(slot_at.replace("Z", "+00:00"))
    require(timestamp.tzinfo is not None, "slot timestamp timezone required")
    require(timestamp.astimezone(dt.timezone(dt.timedelta(hours=9))).strftime("%H:%M") in pack["slots_jst"], "slot not allowed for product")
    script = ScriptLedger(ledger_path).get(script_id)
    preflight(script)
    require(script["product_id"] == product and script["account_id"] == f"product:{product}", "script product scope mismatch")
    key = hashlib.sha256(f"{product}|{slot_at}".encode()).hexdigest()[:24]
    receipt = {"schema_version": "marketing.ebook-run.v1", "run_id": f"ebook-run.{key}",
               "product_id": product, "slot_at": slot_at, "script_id": script_id,
               "creative_id": script["creative_id"], "renderer_id": script["renderer_id"],
               "state": "script_preflighted", "external_effects": [],
               "accounts": pack["accounts"], "recorded_at": slot_at}
    state_root.mkdir(parents=True, exist_ok=True)
    path = state_root / f"{receipt['run_id']}.json"
    encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path.exists():
        require(path.read_text(encoding="utf-8") == encoded, "conflicting run replay")
    else:
        path.write_text(encoded, encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", required=True, choices=("ebook-ja", "ebook-en"))
    parser.add_argument("--slot-at", required=True)
    parser.add_argument("--script-id", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(engine=HERE, product=args.product, slot_at=args.slot_at,
                         script_id=args.script_id, ledger_path=args.ledger,
                         state_root=args.state_root), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
