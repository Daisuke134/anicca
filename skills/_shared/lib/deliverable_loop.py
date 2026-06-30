"""deliverable_loop — REQ-I2 Deliverable Verify Loop (B1 NURTURE pre-納品 gate).

PROP-I2-deliverable-loop (required:true, Tier 1 integration).
NO 納品 until artifact passes fresh-context adversary across 5 dimensions:
brief_completeness / factual_correctness / usefulness / presentation_quality / safety_surface.
Cap reached → DO NOT 納品 + polite scope-clarification msg to buyer + lesson row.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from lib._common import append_jsonl, is_verdict_pass, sha256_file


@dataclass
class DeliverableLoopResult:
    delivered: bool
    rounds_to_pass: int
    stalled: bool = False


def deliver_with_verify(
    *,
    request_id: str,
    artifact_path: Path | str,
    brief_path: Path | str,
    buyer_messages_path: Path | str,
    loop_dir: Path | str,
    adversary_stub: Callable[..., dict],
    deliver_fn: Callable[[Path], str],
    send_buyer_msg_fn: Callable[[str], None] | None = None,
    max_rounds: int = 3,
    lessons_path: Path | str | None = None,
) -> DeliverableLoopResult:
    """Run the deliverable verify loop. Returns DeliverableLoopResult.

    On cap reached: send_buyer_msg_fn is invoked with a polite scope-clarification
    message (buyer is the platform-side counterparty, NOT a human reviewer; per
    REQ-J8 NO HUMAN, buyer messages are platform-to-platform via Coconala talk-room
    or equivalent).
    """
    loop_dir = Path(loop_dir)
    artifact_path = Path(artifact_path)
    deliveries_root = loop_dir / "deliveries" / str(request_id)

    for round_n in range(1, max_rounds + 1):
        round_dir = deliveries_root / f"round-{round_n}"
        round_dir.mkdir(parents=True, exist_ok=True)
        # Persist a manifest (= what was reviewed at this round)
        manifest = {
            "round": round_n,
            "artifact_sha256": sha256_file(artifact_path),
            "brief_path": str(brief_path),
            "buyer_messages_path": str(buyer_messages_path),
        }
        (round_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        verdict = adversary_stub(
            request_id=request_id,
            artifact_path=str(artifact_path),
            brief_path=str(brief_path),
            buyer_messages_path=str(buyer_messages_path),
            round=round_n,
            review_type="deliverable-quality",
        )

        if is_verdict_pass(verdict):
            deliver_fn(artifact_path)
            return DeliverableLoopResult(
                delivered=True, rounds_to_pass=round_n, stalled=False
            )

        # FAIL → would revise artifact (real impl writes new version);
        # tests treat round-N as a fresh review of the same artifact path.

    # Cap reached → polite buyer clarification + lesson row + DO NOT 納品
    if send_buyer_msg_fn is not None:
        send_buyer_msg_fn(_clarification_template(request_id, max_rounds))
    if lessons_path is not None:
        append_jsonl(Path(lessons_path), {
            "ts": int(time.time()),
            "requestId": request_id,
            "category": "deliverable-verify",
            "outcome": "deliverable-stalled",
            "reason": f"all {max_rounds} rounds FAIL",
            "evidence_id": None,
            "rounds_attempted": max_rounds,
        })
    return DeliverableLoopResult(delivered=False, rounds_to_pass=0, stalled=True)


def _clarification_template(request_id: str, rounds: int) -> str:
    return (
        f"お世話になっております。納品物の準備を進めておりますが、"
        f"いくつか scope の確認が必要な箇所が出てまいりました。"
        f"納期 / 範囲 について再度 すり合わせを させていただけますでしょうか。"
        f"(request {request_id}; 内部検証 {rounds} round 経過後の確認依頼)"
    )
