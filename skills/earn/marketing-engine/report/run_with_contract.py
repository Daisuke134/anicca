#!/usr/bin/env python3
"""Execute one bounded runner and emit exactly one truthful final report."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import pathlib
import secrets
import subprocess
import sys

import run_contract
import runner_report


HERE = pathlib.Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent


@dataclasses.dataclass(frozen=True)
class ExecutionResult:
    event: dict
    delivery: dict | None
    returncode: int


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def execute(*, runner_id: str, command: list[str], state_root: pathlib.Path,
            evidence_root: pathlib.Path, environment: str, dry_run: bool,
            product_ids: list[str], quarantine_reason: str | None,
            send: bool, timeout: int | None = None) -> ExecutionResult:
    if runner_id not in run_contract.RUNNERS:
        raise run_contract.ContractError(f"unknown runner_id: {runner_id}")
    if not command:
        raise run_contract.ContractError("command is required")
    if dry_run:
        environment = "test"
    run_id = secrets.token_hex(16)
    if run_id == "0" * 32:  # defensive; token_hex cannot intentionally return this
        run_id = "1" + run_id[1:]
    started_at = _now()
    run_dir = pathlib.Path(evidence_root) / started_at[:10] / runner_id / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    execution_path = run_dir / "execution.json"
    command_hash = hashlib.sha256(
        json.dumps(command, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()

    if quarantine_reason:
        stdout = b""
        stderr = b""
        returncode = 0
        status = "skipped"
        error = None
        effect = {
            "provider": "scheduler_guard",
            "action": "execute",
            "status": "blocked",
            "receipt": None,
            "evidence": str(execution_path),
            "null_reason": quarantine_reason,
            "simulated": False,
        }
        metric = {
            "name": "external_actions",
            "product_id": product_ids[0] if len(product_ids) == 1 else None,
            "value": 0,
            "unit": "count",
            "observed_at": _now(),
            "source": "scheduler_guard",
            "evidence": str(execution_path),
            "null_reason": None,
            "simulated": False,
        }
    else:
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
            status = "success" if returncode == 0 else "failed"
            error = None if returncode == 0 else f"process exited with exit {returncode}"
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
            returncode = 124
            status = "failed"
            error = f"process timed out after {timeout} seconds"
        effect = {
            "provider": "local_process",
            "action": "execute",
            "status": "observed" if status == "success" else "failed",
            "receipt": None,
            "evidence": str(execution_path),
            "null_reason": "no_external_effect_receipt",
            "simulated": dry_run,
        }
        metric = {
            "name": "process_exit_code",
            "product_id": product_ids[0] if len(product_ids) == 1 else None,
            "value": returncode,
            "unit": "count",
            "observed_at": _now(),
            "source": "local_process",
            "evidence": str(execution_path),
            "null_reason": None,
            "simulated": dry_run,
        }

    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    finished_at = _now()
    execution_path.write_text(json.dumps({
        "schema_version": "marketing.execution.v1",
        "run_id": run_id,
        "runner_id": runner_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "command_sha256": command_hash,
        "returncode": returncode,
        "quarantined": bool(quarantine_reason),
        "quarantine_reason": quarantine_reason,
        "dry_run": dry_run,
    }, ensure_ascii=False, sort_keys=True, indent=2) + "\n")

    event = run_contract.validate_event({
        "schema_version": "marketing.run.v1",
        "run_id": run_id,
        "runner_id": runner_id,
        "environment": environment,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "dry_run": dry_run,
        "product_ids": product_ids,
        "effects": [effect],
        "metrics": [metric],
        "evidence": [
            run_contract.evidence_item(stdout_path, "stdout"),
            run_contract.evidence_item(stderr_path, "stderr"),
            run_contract.evidence_item(execution_path, "execution"),
        ],
        "error": error,
    })
    store = run_contract.RunStore(
        pathlib.Path(state_root) / "run-reports.jsonl",
        pathlib.Path(state_root) / "run-deliveries.jsonl",
    )
    delivery = None
    if send:
        delivery = run_contract.record_and_deliver(event, store, runner_report._telegram_sender())
    else:
        store.record_final(event)
    return ExecutionResult(event, delivery, returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", required=True, choices=sorted(run_contract.RUNNERS))
    parser.add_argument("--state-root", type=pathlib.Path, default=ENGINE_ROOT / "state")
    parser.add_argument("--evidence-root", type=pathlib.Path,
                        default=ENGINE_ROOT / "evidence" / "runs")
    parser.add_argument("--environment", choices=sorted(run_contract.ENVIRONMENTS),
                        default="production")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--product", action="append", default=[])
    parser.add_argument("--quarantine-reason")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--no-send", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        result = execute(
            runner_id=args.runner,
            command=command,
            state_root=args.state_root,
            evidence_root=args.evidence_root,
            environment=args.environment,
            dry_run=args.dry_run,
            product_ids=args.product,
            quarantine_reason=args.quarantine_reason,
            send=not args.no_send,
            timeout=args.timeout,
        )
    except (OSError, run_contract.ContractError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1
    print(json.dumps({
        "runner_id": result.event["runner_id"],
        "run_id": result.event["run_id"],
        "status": result.event["status"],
        "returncode": result.returncode,
        "delivery": result.delivery,
    }, ensure_ascii=False, sort_keys=True))
    return result.returncode if result.event["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
