#!/usr/bin/env python3
"""Verify durable Gate 11 renderer evidence without making external calls."""

from __future__ import annotations

import json
import pathlib

from renderer_eval import HERE, read_jsonl, verify_outputs


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_gate11(*, engine: pathlib.Path = HERE.parent,
                  evidence_root: pathlib.Path | None = None) -> dict:
    engine = pathlib.Path(engine)
    root = pathlib.Path(evidence_root) if evidence_root is not None else engine / "evidence/renderers/gate11"
    fixtures = engine / "render_eval/renderer-fixtures.json"
    receipts_path = root / "attempts.jsonl"
    output = verify_outputs(fixtures, receipts_path)
    receipts = read_jsonl(receipts_path)
    require(all(row["publication_effects"] == [] for row in receipts), "external effect found")
    require(all(row["cost_usd"] == 0 for row in receipts), "non-zero cost found")
    unavailable = {row["renderer_id"] for row in receipts if row["status"] == "unavailable"}
    require({"omniavatar-monk", "musetalk", "longcat-video-avatar"} <= unavailable,
            "challenger blocker receipts missing")
    evaluator_path = root / "visual-evaluation.json"
    require(evaluator_path.is_file(), "visual evaluation evidence missing")
    evaluator = json.loads(evaluator_path.read_text(encoding="utf-8"))
    require(evaluator.get("status") in {"accepted", "failed", "unavailable"},
            "visual evaluation status invalid")
    result = {**output, "receipts": len(receipts),
              "publication_effects": 0, "cost_usd": 0,
              "visual_evaluation_status": evaluator["status"]}
    verification_path = root / "verification.json"
    verification_path.parent.mkdir(parents=True, exist_ok=True)
    verification_path.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                            sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(verify_gate11(), ensure_ascii=False, sort_keys=True))
