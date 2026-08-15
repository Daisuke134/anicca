#!/usr/bin/env python3
"""A stand-in for agent_runner.py that never launches a provider.

The real judge in ``scripts/artifact_judge.py`` shells out to
``skills/agent-runner/agent_runner.py``, which starts ``codex exec`` or ``claude -p``.
That must never happen from a test: it costs money and it takes minutes.

This reproduces the only part of the runner's contract the judge depends on -- an
``--evidence-dir`` holding ``summary.json`` with ``status`` and ``result_path``, and a
result file at that path -- so the subprocess boundary, the summary read and the verdict
parse are all exercised for real. What the "model" says is chosen by
``GIG_ARTIFACT_JUDGE_STUB``:

    deliverable | about_the_deal | undeterminable   that verdict
    unknown                                         a verdict string outside the enum
    malformed                                       a result file that is not JSON
    no_result                                       success claimed with no result file
    crash                                           nonzero exit, no summary at all
    hang                                            sleeps past any sane timeout
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--prompt-stdin", action="store_true")
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--task-label", required=True)
    parser.add_argument("--loop", default="unattributed")
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--candidate-profile")
    parser.add_argument("--escalation-reason")
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args()

    mode = os.environ.get("GIG_ARTIFACT_JUDGE_STUB", "deliverable")
    if mode == "hang":
        time.sleep(3600)
        return 0
    if mode == "crash":
        print("stub judge: provider unavailable", file=sys.stderr)
        return 1

    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    result_path = evidence / "attempt-01.result.json"

    if mode == "malformed":
        result_path.write_text('{"verdict": "deliver', encoding="utf-8")
    elif mode == "no_result":
        result_path.unlink(missing_ok=True)
    else:
        verdict = "probably fine" if mode == "unknown" else mode
        result_path.write_text(
            json.dumps({"verdict": verdict, "reason": "stub judge"}, ensure_ascii=False),
            encoding="utf-8",
        )

    summary = {
        "version": 1,
        "status": "success",
        "task_class": args.task_class,
        "task_label": args.task_label,
        "selected_provider": "stub",
        "result_path": str(result_path),
    }
    (evidence / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
