#!/usr/bin/env python3
"""Low-cost Coconala reply detector used by push and five-minute fallback."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


class StepFailure(RuntimeError):
    def __init__(self, step: str, returncode: int):
        super().__init__(f"{step} exited {returncode}")
        self.step = step
        self.returncode = returncode


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _run(step: str, arguments: list[str], *, accepted: tuple[int, ...] = (0,)) -> None:
    completed = subprocess.run(
        arguments,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode not in accepted:
        raise StepFailure(step, completed.returncode)


def _owner_only(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.chmod(0o600)


def install_token_budget(environ: dict[str, str], *, run_id: str) -> None:
    """Give this detector run its own token budget before it can call a model.

    The detector composes buyer replies on its own 300s timer, outside any pass.
    It never exported the budget env, so every one of those model calls reached
    agent_runner with budget_not_configured and was silently uncharged: 47 such
    calls in the ledger between 07-23 and 07-25. The scope id must be per run,
    not a fixed plist value, or the per-pass limit would accumulate all day.
    """
    environ.setdefault("ANICCA_BUDGET_SCOPE_ID", run_id)
    environ.setdefault(
        "ANICCA_PASS_TOKEN_BUDGET",
        environ.get("GIG_REPLY_PASS_TOKEN_BUDGET", "65536"),
    )
    # 1Mi/day is ~2x the measured peak of 527,499 charged tokens (07-24) for
    # gig-reply-compose across all callers: a breaker, not a throttle.
    environ.setdefault(
        "ANICCA_LOOP_DAILY_TOKEN_BUDGET",
        environ.get("GIG_DAILY_TOKEN_BUDGET", "1048576"),
    )
    environ.setdefault(
        "ANICCA_BUDGET_DAILY_SCOPE",
        environ.get("GIG_BUDGET_DAILY_SCOPE", "gig-reply-detector"),
    )
    environ.setdefault(
        "ANICCA_TOKEN_BUDGET_LEDGER",
        environ.get(
            "GIG_TOKEN_BUDGET_LEDGER",
            str(Path.home() / ".local/state/anicca/telemetry/token-budget.jsonl"),
        ),
    )
    environ.setdefault("ANICCA_BUDGET_REQUIRED", "1")


def main() -> int:
    gig_root = Path(__file__).resolve().parents[1]
    home = Path.home()
    install_token_budget(os.environ, run_id=f"reply-detector-{int(time.time())}-{os.getpid()}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger", choices=("fallback", "gmail_push", "manual"), default="fallback")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--lock-file", type=Path, default=home / "gig/reply-detector.lock")
    parser.add_argument("--database", type=Path, default=home / "gig/connector-outbox.sqlite3")
    parser.add_argument("--manifest", type=Path, default=gig_root / "config/connectors/coconala.json")
    parser.add_argument(
        "--runner", type=Path,
        default=home / "profitable-claude/skills/agent-runner/agent_runner.py",
    )
    parser.add_argument("--schema", type=Path, default=gig_root / "schemas/reply_composition.schema.json")
    parser.add_argument(
        "--cdp-helper", type=Path,
        default=home / "anicca/skills/browser/scripts/cdp_default_tab.py",
    )
    parser.add_argument("--snapshot-script", type=Path, default=gig_root / "scripts/coconala_queue_snapshot.py")
    parser.add_argument("--queue-script", type=Path, default=gig_root / "scripts/reply_queue.py")
    parser.add_argument("--lane-script", type=Path, default=gig_root / "scripts/reply_lane.py")
    parser.add_argument(
        "--telegram-report-script", type=Path,
        default=gig_root / "scripts/telegram_report.py",
    )
    parser.add_argument(
        "--telegram-database", type=Path,
        default=home / "gig/telegram-outbox.sqlite3",
    )
    parser.add_argument(
        "--runner-config", type=Path,
        default=home / "profitable-claude/skills/agent-runner/config.json",
    )
    parser.add_argument("--telegram-target", default="8547730585")
    args = parser.parse_args()

    os.environ["CLOAK_BROWSER_OWNER"] = "gig-reply-detector"
    run_id = f"{int(time.time())}-{os.getpid()}"
    evidence = args.evidence_dir or home / f"gig/evidence/reply-detector-{run_id}"
    output = args.output or evidence / "detector-result.json"
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence.chmod(0o700)
    args.lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(args.lock_file, os.O_CREAT | os.O_RDWR, 0o600)
    os.fchmod(lock_fd, 0o600)
    lock_handle = os.fdopen(lock_fd, "r+")
    try:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            busy = {"status": "busy", "trigger": args.trigger, "errors": []}
            _atomic_json(output, busy)
            print(json.dumps(busy, ensure_ascii=False, separators=(",", ":")))
            return 0

        snapshot = evidence / "marketplace-snapshot.json"
        queue = evidence / "reply-queue.json"
        lane_result = evidence / "reply-lane-result.json"
        try:
            _run("collect", [
                sys.executable, str(args.snapshot_script),
                "--output", str(snapshot),
                "--evidence-dir", str(evidence / "live-dom"),
                "--hidden-no-screenshot",
            ])
            _owner_only(snapshot)
            _run("queue_build", [
                sys.executable, str(args.queue_script), "build",
                "--snapshot", str(snapshot), "--output", str(queue),
            ])
            _owner_only(queue)
            _run("outbox_enqueue", [
                sys.executable, str(args.queue_script), "enqueue",
                "--queue", str(queue), "--database", str(args.database),
                "--manifest", str(args.manifest),
            ])
            _run("reply_lane", [
                sys.executable, str(args.lane_script),
                "--queue", str(queue), "--database", str(args.database),
                "--manifest", str(args.manifest), "--runner", str(args.runner),
                "--schema", str(args.schema), "--cdp-helper", str(args.cdp_helper),
                "--output", str(lane_result), "--workdir", str(home),
                "--owner-prefix", f"gig-reply-detector-{run_id}",
            ], accepted=(0, 2))
            lane = json.loads(lane_result.read_text(encoding="utf-8"))
            result = {
                "status": str(lane.get("status") or "failed"),
                "trigger": args.trigger,
                "replied": int(lane.get("replied") or 0),
                "reconciled": int(lane.get("reconciled") or 0),
                "requeued": int(lane.get("requeued") or 0),
                "reconcile_pending": int(lane.get("reconcile_pending") or 0),
                "blocked": int(lane.get("blocked") or 0),
                "skipped": int(lane.get("skipped") or 0),
                "errors": list(lane.get("errors") or []),
                "events": list(lane.get("events") or []),
            }
            _atomic_json(output, result)
            if result["events"]:
                try:
                    report = subprocess.run(
                        [
                            sys.executable, str(args.telegram_report_script), "reply",
                            "--events", str(output),
                            "--connector-database", str(args.database),
                            "--telegram-database", str(args.telegram_database),
                            "--runner-config", str(args.runner_config),
                            "--target", str(args.telegram_target),
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=90,
                        check=False,
                    )
                    if report.returncode == 0:
                        result["telegram_report"] = "sent"
                    elif report.returncode == 2:
                        result["telegram_report"] = "delivery_unknown"
                    else:
                        result["telegram_report"] = "deferred"
                except (OSError, subprocess.TimeoutExpired):
                    result["telegram_report"] = "deferred"
                _atomic_json(output, result)
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
            return 0 if result["status"] in {"completed", "reconcile_pending"} else 1
        except StepFailure as error:
            failure = {
                "status": "failed",
                "trigger": args.trigger,
                "failed_step": error.step,
                "errors": [{"returncode": error.returncode}],
            }
            _atomic_json(output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1
        except Exception as error:
            failure = {
                "status": "failed",
                "trigger": args.trigger,
                "failed_step": "internal",
                "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
            }
            _atomic_json(output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1
    finally:
        lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
