from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path


ESCALATION_REASON = "mandatory-model-browser-loop"


def _is_duplicate_runtime_module_typo(command: str) -> bool:
    if any(
        marker in command
        for marker in ("$(", "`", ";", "&&", "||", "|", ">", "<", "\n")
    ):
        return False
    try:
        parts = shlex.split(command)
        if parts[:2] == ["/bin/zsh", "-lc"] and len(parts) == 3:
            parts = shlex.split(parts[2])
    except ValueError:
        return False
    return (
        len(parts) >= 3
        and parts[0]
        in {
            "/opt/homebrew/bin/python3",
            "/opt/homebrew/opt/python@3.14/bin/python3.14",
        }
        and parts[1:3]
        == ["-m", "job_search_loop.browser_agent.browser_agent.runtime"]
    )


def validate_pass_result(evidence_dir: Path) -> str | None:
    summary_path = evidence_dir / "summary.json"
    if not summary_path.is_file():
        return None
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_path = Path(str(summary.get("result_path") or ""))
        attempts_path = Path(str(summary.get("attempts_path") or ""))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        result_path.parent != evidence_dir
        or attempts_path.parent != evidence_dir
        or not result_path.is_file()
        or not attempts_path.is_file()
    ):
        return None
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if result.get("status") != "transport_failed":
        return None
    try:
        attempt = json.loads(attempts_path.read_text(encoding="utf-8").splitlines()[-1])
        stdout_path = Path(str(attempt.get("stdout_path") or ""))
    except (OSError, json.JSONDecodeError, IndexError):
        return "transport_failed_without_command_failure"
    if stdout_path.parent != evidence_dir or not stdout_path.is_file():
        return "transport_failed_without_command_failure"
    for line in stdout_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if (
            event.get("type") == "item.completed"
            and isinstance(item, dict)
            and item.get("type") == "command_execution"
            and isinstance(item.get("exit_code"), int)
            and item["exit_code"] != 0
        ):
            output = str(item.get("aggregated_output") or "")
            if output.startswith("zsh:") and "unmatched" in output:
                continue
            command = str(item.get("command") or "")
            if (
                "job_search_loop.runtime" in command
                and "job_search_loop.browser_agent.runtime" not in command
                and "following arguments are required: command" in output
            ):
                continue
            if (
                _is_duplicate_runtime_module_typo(command)
                and "ModuleNotFoundError" in output
            ):
                continue
            return None
    return "transport_failed_without_command_failure"


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
    returncode = subprocess.run(command, check=False, env=environment).returncode
    if returncode != 0:
        return returncode
    reason = validate_pass_result(evidence_dir)
    if reason is None:
        return 0
    receipt = evidence_dir / "semantic-validation.json"
    receipt.write_text(
        json.dumps({"status": "failed", "reason": reason}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(receipt, 0o600)
    return 2


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
