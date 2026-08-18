#!/usr/bin/env python3
"""A stand-in for agent_runner.py for the first-contact decision.

Same contract as tests/fixtures/artifact_judge_stub_runner.py and for the same reason: the
real decider shells out to skills/agent-runner/agent_runner.py, which starts a provider.
That must never happen from a test.

The answer is chosen by ``GIG_FIRST_CONTACT_STUB``:

    build                  decision=build, nothing missing
    ask                    decision=ask with three concrete Japanese questions
    ask_without_missing    decision=ask but an empty ``missing`` -- a question that
                           cannot say what it is asking for
    unknown                a decision string outside the enum
    malformed              a result file that is not JSON
    no_result              success claimed with no result file
    crash                  nonzero exit, no summary at all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ASK_MISSING = [
    "動画は何本必要でしょうか。1本あたりの尺（分数）もあわせて教えてください。",
    "投稿先はYouTubeの通常動画とショートのどちらでしょうか。",
    "台本はナレーション原稿まで書き起こす形と、構成案までの形のどちらをご希望でしょうか。",
]


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
    parser.add_argument("--timeout-seconds", type=int)
    args = parser.parse_args()

    mode = os.environ.get("GIG_FIRST_CONTACT_STUB", "build")
    if mode == "crash":
        print("stub decider: provider unavailable", file=sys.stderr)
        return 1

    evidence = args.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    result_path = evidence / "attempt-01.result.json"

    if mode == "malformed":
        result_path.write_text('{"decision": "as', encoding="utf-8")
    elif mode == "no_result":
        result_path.unlink(missing_ok=True)
    else:
        if mode == "ask":
            payload = {
                "decision": "ask",
                "missing": ASK_MISSING,
                "blocker": "ご注文は動画の企画・台本ですが、本数・尺・投稿先が決まっていないため",
            }
        elif mode == "ask_without_missing":
            payload = {"decision": "ask", "missing": [], "blocker": "よく分かりません"}
        elif mode == "unknown":
            payload = {"decision": "probably fine", "missing": [], "blocker": ""}
        else:
            payload = {"decision": "build", "missing": [], "blocker": ""}
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
