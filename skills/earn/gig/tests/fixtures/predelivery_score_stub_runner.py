#!/usr/bin/env python3
"""A stand-in for agent_runner.py, for predelivery_score.py's subprocess boundary.

Mirrors ``artifact_judge_stub_runner.py`` exactly, for the same reason: the real scorer
shells out to ``agent_runner.py``, which starts a real provider, and that must never happen
from a test. ``GIG_PREDELIVERY_SCORE_STUB`` selects the answer:

    high | low          score 90 / score 20, one dimension each, both well-formed
    out_of_range        score 140 -- parse_score must reject this to None
    malformed           a result file that is not JSON
    no_result           success claimed with no result file
    crash               nonzero exit, no summary at all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--task-label", required=True)
    parser.add_argument("--loop", default="unattributed")
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args()

    mode = os.environ.get("GIG_PREDELIVERY_SCORE_STUB", "high")
    if mode == "crash":
        print("stub scorer: provider unavailable", file=sys.stderr)
        return 1

    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    result_path = evidence / "attempt-01.result.json"

    if mode == "malformed":
        result_path.write_text('{"score": 9', encoding="utf-8")
    elif mode == "no_result":
        result_path.unlink(missing_ok=True)
    else:
        payload = {
            "high": {"score": 90, "dimensions": [{"name": "scope_match", "score": 90, "reason": "stub"}]},
            "low": {"score": 20, "dimensions": [{"name": "scope_match", "score": 20, "reason": "stub low"}]},
            "out_of_range": {"score": 140, "dimensions": [{"name": "scope_match", "score": 90, "reason": "stub"}]},
        }[mode]
        result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    summary = {
        "version": 1,
        "status": "success",
        "task_class": args.task_class,
        "task_label": args.task_label,
        "selected_provider": "stub",
        "result_path": str(result_path),
    }
    (evidence / "summary.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
