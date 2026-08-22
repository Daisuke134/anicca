from __future__ import annotations

import argparse
import os
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
    active_provider: str,
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
    environment = os.environ.copy()
    if active_provider == "all":
        environment.pop("JOB_SEARCH_ACTIVE_APPLICATION_PROVIDER", None)
    else:
        environment["JOB_SEARCH_ACTIVE_APPLICATION_PROVIDER"] = active_provider
    return subprocess.run(command, check=False, env=environment).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument(
        "--active-provider", choices=("workday", "ashby", "all"), required=True
    )
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
        active_provider=args.active_provider,
    )


if __name__ == "__main__":
    raise SystemExit(main())
