#!/usr/bin/env python3
"""Validate, persist, and deliver one runner-authored factual result payload."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import run_contract


HERE = pathlib.Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent
DEFAULT_STATE = ENGINE_ROOT / "state"


def build_event(payload: dict) -> dict:
    evidence_paths = payload.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths:
        raise run_contract.ContractError("evidence_paths must be a non-empty array")
    evidence = []
    for item in evidence_paths:
        if not isinstance(item, dict) or not item.get("path") or not item.get("kind"):
            raise run_contract.ContractError("each evidence path requires path and kind")
        evidence.append(run_contract.evidence_item(pathlib.Path(item["path"]), item["kind"]))
    event = {
        "schema_version": "marketing.run.v1",
        "run_id": payload.get("run_id"),
        "runner_id": payload.get("runner_id"),
        "environment": payload.get("environment"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "status": payload.get("status"),
        "dry_run": payload.get("dry_run"),
        "product_ids": payload.get("product_ids"),
        "effects": payload.get("effects"),
        "metrics": payload.get("metrics"),
        "evidence": evidence,
        "error": payload.get("error"),
    }
    return run_contract.validate_event(event)


def _telegram_sender():
    shared = ENGINE_ROOT.parents[1] / "_shared"
    sys.path.insert(0, str(shared))
    from telegram import TelegramClient
    return TelegramClient.from_env().send_text


def emit_payload(payload_path: pathlib.Path, state_root: pathlib.Path,
                 *, send: bool = True) -> dict:
    payload_path = pathlib.Path(payload_path)
    payload = json.loads(payload_path.read_text())
    event = build_event(payload)
    state_root = pathlib.Path(state_root)
    store = run_contract.RunStore(
        state_root / "run-reports.jsonl",
        state_root / "run-deliveries.jsonl",
    )
    recorded = store.record_final(event)
    delivery = None
    if send:
        delivery = store.delivery_for(event["runner_id"], event["run_id"])
        if delivery is None:
            receipt = _telegram_sender()(run_contract.render_telegram(event))
            delivery = store.record_delivery(event["runner_id"], event["run_id"], receipt)
    return {
        "runner_id": event["runner_id"],
        "run_id": event["run_id"],
        "created": recorded.created,
        "delivery": delivery,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=pathlib.Path)
    parser.add_argument("--state-root", type=pathlib.Path, default=DEFAULT_STATE)
    parser.add_argument("--no-send", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = emit_payload(args.payload, args.state_root, send=not args.no_send)
    except (OSError, json.JSONDecodeError, run_contract.ContractError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
