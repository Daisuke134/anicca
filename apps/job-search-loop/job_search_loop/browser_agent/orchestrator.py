from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ESCALATION_REASON = "mandatory-model-browser-loop"


def invoke_runner(
    *,
    runner: Path,
    prompt: Path,
    schema: Path,
    evidence_dir: Path,
    workdir: Path,
    timeout_seconds: int,
    python: str,
) -> int:
    """Delegate one wake to the existing bounded model runner."""
    command = [
        python,
        str(runner),
        "--task-class",
        "browser-lane-agent",
        "--escalation-reason",
        ESCALATION_REASON,
        "--timeout-seconds",
        str(timeout_seconds),
        "--prompt-file",
        str(prompt),
        "--schema",
        str(schema),
        "--evidence-dir",
        str(evidence_dir),
        "--task-label",
        "job-search-daily",
        "--loop",
        "job-search",
        "--workdir",
        str(workdir),
    ]
    return subprocess.run(command, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--python", required=True)
    args = parser.parse_args(argv)
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be positive")
    return invoke_runner(
        runner=args.runner,
        prompt=args.prompt,
        schema=args.schema,
        evidence_dir=args.evidence_dir,
        workdir=args.workdir,
        timeout_seconds=args.timeout_seconds,
        python=args.python,
    )


if __name__ == "__main__":
    raise SystemExit(main())
