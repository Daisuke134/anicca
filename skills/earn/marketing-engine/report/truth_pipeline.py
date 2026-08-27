#!/usr/bin/env python3
"""Serialized free-only publication truth, metrics, and owner-report sweep."""

from __future__ import annotations

import argparse
import fcntl
import json
import pathlib
import subprocess
import sys
from collections.abc import Callable


HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
ENGINE_ROOT = HERE.parent


def build_commands(
    repo_root: pathlib.Path, home: pathlib.Path, *, python: str = sys.executable
) -> list[list[str]]:
    repo_root = pathlib.Path(repo_root)
    home = pathlib.Path(home)
    engine = repo_root / "skills/earn/marketing-engine"
    state = engine / "state"
    evidence = engine / "evidence/metrics"
    env = home / "anicca/.env"
    commands = [
        [
            python,
            str(engine / "identity/publication_ledger.py"),
            "--days",
            "8",
            "--env-file",
            str(env),
            "--report",
            str(evidence / "publication-reconcile-latest.json"),
        ],
        [
            python,
            str(engine / "measure/native_metrics.py"),
            "--env",
            str(env),
            "collect",
            "--report",
            str(evidence / "native-metrics-latest.json"),
        ],
    ]
    owner_cli = engine / "report/owner_report_cli.py"
    for kind in ("action", "checkpoint", "incident", "experiment"):
        commands.append(
            [
                python,
                str(owner_cli),
                "sweep",
                "--kind",
                kind,
                "--state-root",
                str(state),
            ]
        )
    return commands


def _stage_name(command: list[str]) -> str:
    rendered = " ".join(command)
    if "publication_ledger.py" in rendered:
        return "reconcile"
    if "native_metrics.py" in rendered:
        return "collect"
    if "owner_report_cli.py" in rendered and "--kind" in command:
        return "report:" + command[command.index("--kind") + 1]
    return command[0]


def run_pipeline(
    commands: list[list[str]],
    *,
    lock_path: pathlib.Path,
    run_command: Callable[[list[str]], int] | None = None,
) -> dict:
    lock_path = pathlib.Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    run_command = run_command or (
        lambda command: subprocess.run(command, check=False).returncode
    )
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "locked", "failed_stages": [], "stages": []}
        stages = []
        failed = []
        for command in commands:
            stage = _stage_name(command)
            returncode = int(run_command(command))
            stages.append({"stage": stage, "returncode": returncode})
            if returncode != 0:
                failed.append(stage)
        return {
            "status": "failed" if failed else "completed",
            "failed_stages": failed,
            "stages": stages,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=pathlib.Path, default=REPO_ROOT)
    parser.add_argument("--home", type=pathlib.Path, default=pathlib.Path.home())
    parser.add_argument(
        "--lock-path", type=pathlib.Path, default=ENGINE_ROOT / "state/.truth-pipeline.lock"
    )
    args = parser.parse_args(argv)
    result = run_pipeline(
        build_commands(args.repo_root, args.home), lock_path=args.lock_path
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
