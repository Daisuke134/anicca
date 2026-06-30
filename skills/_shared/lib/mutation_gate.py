"""mutation_gate — INV-10 fresh-context adversary gate for strategy mutations.

PROP-C3-mutation-gate (required:true, Tier 1 integration) — REQ-C3.
Apply strategy.json.next only if reviews/strategy-mutation-<sha>/output/verdict.json
exists with overallVerdict=PASS. Otherwise discard + append a "mutation-rejected"
lesson row so the next pass learns from the failed proposal.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from lib._common import append_jsonl  # 2c refactor extension (FIND-016 fix)


@dataclass(frozen=True)
class MutationResult:
    applied: bool
    reason: str | None = None


def apply_strategy_mutation(
    *,
    slot_dir: Path | str,
    strategy_path: Path | str,
    next_path: Path | str,
    sha: str,
    lessons_path: Path | str,
) -> MutationResult:
    """Apply strategy.json.next over strategy.json IFF verdict file exists with PASS.

    On FAIL or missing verdict (= INV-10 fail-closed): discard next_path, append
    {category: self-mutation, outcome: mutation-rejected, ...} to lessons.jsonl.
    """
    slot_dir = Path(slot_dir)
    strategy_path = Path(strategy_path)
    next_path = Path(next_path)
    lessons_path = Path(lessons_path)

    verdict_path = (
        slot_dir / "reviews" / f"strategy-mutation-{sha}" / "output" / "verdict.json"
    )

    if not verdict_path.exists():
        _log_rejection(lessons_path, sha, "verdict-missing", None)
        if next_path.exists():
            next_path.unlink()
        return MutationResult(applied=False, reason="verdict-missing")

    try:
        verdict = json.loads(verdict_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        _log_rejection(lessons_path, sha, f"verdict-unreadable:{e.__class__.__name__}", None)
        if next_path.exists():
            next_path.unlink()
        return MutationResult(applied=False, reason="verdict-unreadable")

    overall = verdict.get("overallVerdict")
    if overall != "PASS":
        finding_summary = verdict.get("convergenceSignals", {}).get("findingCount", "?")
        _log_rejection(lessons_path, sha, f"verdict-fail:findings={finding_summary}", verdict_path)
        if next_path.exists():
            next_path.unlink()
        return MutationResult(applied=False, reason="verdict-fail")

    # PASS — rename next over strategy.
    next_path.replace(strategy_path)
    return MutationResult(applied=True)


def _log_rejection(
    lessons_path: Path, sha: str, reason: str, evidence_id: Path | None
) -> None:
    append_jsonl(lessons_path, {
        "ts": int(time.time()),
        "requestId": None,
        "category": "self-mutation",
        "outcome": "mutation-rejected",
        "reason": reason,
        "sha": sha,
        "evidence_id": str(evidence_id) if evidence_id else None,
    })
