"""proposal_loop — REQ-I1 Proposal Verify Loop (B2 APPLY pre-submit gate).

PROP-I1-proposal-loop (required:true, Tier 1 integration).
NO submit until proposal passes a fresh-context adversary review across 5 dimensions:
brief_alignment / sample_relevance / price_realism / delivery_realism / red_flags.
≤3 round iter; cap reached → SKIP request (protects account rating).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from lib._common import append_jsonl, is_verdict_pass


@dataclass
class ProposalLoopResult:
    submitted: bool
    rounds_to_pass: int          # rounds it took to pass; 0 if never passed
    stalled: bool = False        # True iff cap reached without PASS


def propose_with_verify(
    *,
    request: dict,
    draft: dict,
    loop_dir: Path | str,
    adversary_stub: Callable[..., dict],
    submit_fn: Callable[[dict], str],
    max_rounds: int = 3,
    lessons_path: Path | str | None = None,
) -> ProposalLoopResult:
    """Run the proposal verify loop. Returns ProposalLoopResult.

    Args:
      request: dict with requestId + brief_text + budget_range_jpy
      draft:   the initial proposal {title, body, sample_deliverable, price_jpy, delivery_date}
      loop_dir: per-slot loop directory (used to persist round-N/draft.json)
      adversary_stub: callable returning a verdict dict per call (tests inject canned verdicts;
                     production wires this to a real fresh-context Opus subagent spawn)
      submit_fn: callable that performs the actual submit on PASS
      max_rounds: int, default 3 (lean)
      lessons_path: optional path to append the stalled-outcome lesson row
    """
    loop_dir = Path(loop_dir)
    request_id = str(request.get("requestId", "unknown"))
    proposals_root = loop_dir / "proposals" / request_id

    current_draft = dict(draft)

    for round_n in range(1, max_rounds + 1):
        round_dir = proposals_root / f"round-{round_n}"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "draft.json").write_text(json.dumps(current_draft, ensure_ascii=False, indent=2))

        verdict = adversary_stub(
            request=request,
            draft=current_draft,
            round=round_n,
            review_type="proposal-quality",
        )

        if is_verdict_pass(verdict):
            submit_fn(current_draft)
            return ProposalLoopResult(submitted=True, rounds_to_pass=round_n, stalled=False)

        # FAIL → revise for next round
        if round_n < max_rounds:
            current_draft = _revise_draft(current_draft, verdict)

    # Cap reached without PASS: log + SKIP (protect account)
    if lessons_path is not None:
        append_jsonl(Path(lessons_path), {
            "ts": int(time.time()),
            "requestId": request_id,
            "category": "proposal-verify",
            "outcome": "proposal-stalled",
            "reason": f"all {max_rounds} rounds FAIL",
            "evidence_id": None,
            "rounds_attempted": max_rounds,
        })
    return ProposalLoopResult(submitted=False, rounds_to_pass=0, stalled=True)


def _revise_draft(draft: dict, verdict: dict) -> dict:
    """Minimal revise: pass through (production wires this to an LLM call that
    rewrites the draft against the findings; tests treat round-2 as a fresh
    draft and only verify the LOOP STRUCTURE responds to PASS/FAIL correctly).
    """
    return dict(draft)
