#!/usr/bin/env python3
"""A stand-in for agent_runner.py, for buyer_reaction_classify.py's subprocess boundary.

Mirrors ``predelivery_score_stub_runner.py`` exactly, for the same reason: the real
classifier shells out to ``agent_runner.py``, which starts a real provider, and that
must never happen from a test. ``GIG_BUYER_REACTION_STUB`` selects the answer:

    positive | revision_request | negative | neutral | unclear   that reaction
    invalid_enum        a reaction value outside the fixed enum
    malformed            a result file that is not JSON
    no_result             success claimed with no result file
    crash                  nonzero exit, no summary at all
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

    mode = os.environ.get("GIG_BUYER_REACTION_STUB", "positive")
    if mode == "crash":
        print("stub classifier: provider unavailable", file=sys.stderr)
        return 1

    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    result_path = evidence / "attempt-01.result.json"

    if mode == "malformed":
        result_path.write_text('{"reaction": "pos', encoding="utf-8")
    elif mode == "no_result":
        result_path.unlink(missing_ok=True)
    else:
        reaction = "not_a_real_reaction" if mode == "invalid_enum" else mode
        result_path.write_text(
            json.dumps({"reaction": reaction}, ensure_ascii=False), encoding="utf-8"
        )

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
