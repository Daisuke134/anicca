#!/usr/bin/env python3
"""Low-cost Coconala reply detector used by push and five-minute fallback."""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gig_paths import BROWSER_DIR, HOST_STATE_DIR, RUNNER_DIR

try:
    from connector_outbox import ConnectorOutbox
except ModuleNotFoundError:
    _outbox_spec = importlib.util.spec_from_file_location(
        "reply_detector_outbox", Path(__file__).with_name("connector_outbox.py"),
    )
    if _outbox_spec is None or _outbox_spec.loader is None:
        raise
    _outbox_module = importlib.util.module_from_spec(_outbox_spec)
    _outbox_spec.loader.exec_module(_outbox_module)
    ConnectorOutbox = _outbox_module.ConnectorOutbox


class StepFailure(RuntimeError):
    def __init__(
        self, step: str, returncode: int, *, attempts: list[dict[str, Any]] | None = None,
    ):
        super().__init__(f"{step} exited {returncode}")
        self.step = step
        self.returncode = returncode
        self.attempts = list(attempts or [])


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


def _collect_snapshot_with_retry(
    args: Any, snapshot: Path, evidence: Path,
) -> list[dict[str, Any]]:
    """Retry the read-only source collection once, preserving each attempt's evidence."""
    attempts: list[dict[str, Any]] = []
    for number in (1, 2):
        attempt_evidence = evidence / (
            "live-dom" if number == 1 else f"live-dom-retry-{number}"
        )
        snapshot.unlink(missing_ok=True)
        try:
            collect_command = [
                sys.executable, str(args.snapshot_script),
                "--output", str(snapshot),
                "--evidence-dir", str(attempt_evidence),
                "--mode", "direct-inbox-only",
                "--hidden-no-screenshot",
                "--semantic-runner", str(args.runner),
                "--semantic-schema", str(args.semantic_schema),
                "--semantic-workdir", str(Path.home()),
                "--database", str(args.database),
                "--manifest", str(args.manifest),
            ]
            if args.semantic_effects_enabled:
                collect_command.append("--semantic-effects-enabled")
            _run("collect", collect_command)
        except StepFailure as error:
            attempts.append({
                "attempt": number, "status": "failed",
                "returncode": error.returncode,
                "evidence_dir": str(attempt_evidence),
            })
            if number == 2:
                raise StepFailure(
                    "collect", error.returncode, attempts=attempts,
                ) from error
            continue
        try:
            snapshot_value = json.loads(snapshot.read_text(encoding="utf-8"))
            if not isinstance(snapshot_value, dict):
                raise ValueError("collector snapshot must be an object")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            attempts.append({
                "attempt": number, "status": "failed",
                "returncode": 1, "error": "invalid_snapshot",
                "evidence_dir": str(attempt_evidence),
            })
            if number == 2:
                raise StepFailure("collect", 1, attempts=attempts) from error
            continue
        attempts.append({
            "attempt": number, "status": "completed",
            "returncode": 0, "evidence_dir": str(attempt_evidence),
        })
        return attempts
    raise AssertionError("unreachable collector retry state")


def _operator_brake_status(
    script: Path | None = None, *, timeout: float = 5.0,
) -> str:
    """Return free/held, or fail closed when the operator gate is unknowable."""
    brake = script or Path(__file__).with_name("gig_brake.sh")
    environment = os.environ.copy()
    environment.setdefault(
        "GIG_OPERATOR_BRAKE_FILE",
        str(HOST_STATE_DIR / "gig-work" / "reply.operator.brake"),
    )
    try:
        if not brake.is_file():
            return "failed"
        completed = subprocess.run(
            [str(brake), "status"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
    except Exception:
        return "failed"
    return {0: "held", 1: "free"}.get(completed.returncode, "failed")


def _telegram_report(args: Any, events: Path, command: str) -> str:
    """Publish one report through the durable Telegram outbox, never fatally.

    Shared by the verified-reply report and the dead-letter alert: reporting is
    an obligation, but a Telegram outage must not turn a completed detector run
    into a failed one. The outbox itself is what makes the send durable and
    exactly-once, so 'deferred' here means 'queued, not yet acknowledged'.
    """
    try:
        report = subprocess.run(
            [
                sys.executable, str(args.telegram_report_script), command,
                "--events", str(events),
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
    except Exception:
        return "deferred"
    if report.returncode == 0:
        return "sent"
    if report.returncode == 2:
        return "delivery_unknown"
    return "deferred"


def _count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _snapshot_terminal_counts(snapshot: Any) -> dict[str, int | None]:
    """Project only bounded terminal classifications from one fresh snapshot."""
    unknown = {
        "officially_unrepliable_count": None,
        "stop_contact_count": None,
        "classification_failed_count": None,
        "semantic_judgement_failed_count": None,
        "semantic_migration_pending_count": None,
    }
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("inquiries"), list):
        return unknown
    inquiries = snapshot["inquiries"]
    if any(
        not isinstance(item, dict) or not isinstance(item.get("next_action"), str)
        for item in inquiries
    ):
        return unknown
    actions = [item.get("next_action") for item in inquiries]
    classification_failures = [
        item for item in inquiries
        if item.get("next_action") in (
            "estimate_failed", "semantic_failed", "semantic_pending",
        )
    ]
    migration_pending = sum(
        item.get("next_action") == "semantic_pending"
        and item.get("last_message_side") == "seller"
        and item.get("semantic_failure") == "semantic_receipt_pending"
        for item in classification_failures
    )
    return {
        "officially_unrepliable_count": actions.count("officially_unrepliable"),
        "stop_contact_count": actions.count("stop_contact"),
        "classification_failed_count": len(classification_failures),
        "semantic_judgement_failed_count": (
            len(classification_failures) - migration_pending
        ),
        "semantic_migration_pending_count": migration_pending,
    }


def close_officially_unrepliable_pending(
    snapshot: dict[str, Any], *, database: Path, manifest: Path, owner: str, now: int,
) -> dict[str, Any]:
    """Close old pre-click actions only when the fresh official UI forbids sending."""
    inquiries = {
        str(item.get("talkroom_id") or ""): item
        for item in snapshot.get("inquiries", []) if isinstance(item, dict)
    }
    db = ConnectorOutbox(database, manifest)
    closed: list[int] = []
    errors: list[str] = []
    for action in db.pending_actions():
        item = inquiries.get(str(action.get("thread_id") or ""))
        if not (
            isinstance(item, dict)
            and item.get("last_message_side") == "buyer"
            and item.get("sending_unavailable") is True
            and item.get("next_action") == "officially_unrepliable"
            and item.get("reply_required") is False
            and item.get("estimate_required") is False
        ):
            continue
        action_id = int(action["action_id"])
        try:
            claimed = db.claim(owner=owner, now=now, lease_seconds=30, action_id=action_id)
            if claimed is None:
                continue
            db.close_nothing_to_say(
                action_id, owner=owner, fencing_token=int(claimed["fencing_token"]),
                reason="officially_unrepliable", now=now,
            )
            closed.append(action_id)
        except Exception as error:
            errors.append(f"{action_id}:{type(error).__name__}")
    return {"closed_action_ids": closed, "errors": errors}


def _snapshot_activity_counts(snapshot: Any) -> dict[str, int | None]:
    keys = (
        "thread_changed_buyer_count", "thread_readback_count",
        "thread_revalidated_count",
    )
    receipt = snapshot.get("source_receipt") if isinstance(snapshot, dict) else None
    if not isinstance(receipt, dict):
        return {key: None for key in keys}
    return {key: _count(receipt.get(key)) for key in keys}


def _oldest_actionable(items: Any) -> str | None:
    if not isinstance(items, list) or not items:
        return None
    origins = [
        str(item.get("origin_at") or "")
        for item in items
        if isinstance(item, dict)
    ]
    if len(origins) != len(items) or any(not value for value in origins):
        return None
    try:
        return min(
            origins,
            key=lambda value: datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).astimezone(timezone.utc),
        )
    except (TypeError, ValueError):
        return None


def _verified_events(
    events: Any, expected_replied: int | None,
) -> list[dict[str, Any]] | None:
    if not isinstance(events, list) or expected_replied is None:
        return None
    identities: set[tuple[int, int, str]] = set()
    for event in events:
        if not isinstance(event, dict) or event.get("status") != "replied":
            return None
        action_id = _count(event.get("action_id"))
        revision = _count(event.get("revision"))
        if action_id is None or revision is None or action_id <= 0 or revision <= 0:
            return None
        if not isinstance(event.get("talkroom_id"), str) or not event["talkroom_id"].strip():
            return None
        identity = (action_id, revision, event["talkroom_id"].strip())
        if identity in identities:
            return None
        identities.add(identity)
        for key in ("origin_at", "seller_sent_at"):
            value = event.get(key)
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return None
            if parsed.tzinfo is None:
                return None
    return events if len(events) == expected_replied else None


def _wake_result(*, run_id: str, trigger: str, status: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "status": status,
        "trigger": trigger,
        "observed": None,
        "actionable": None,
        "oldest_actionable": None,
        "effect": None,
        "official_readback": None,
        "pending": None,
        "estimate_required": None,
        "estimate_effect": None,
        "estimate_readback": None,
        "estimate_pending": None,
        "estimate_failed": None,
        "estimate_events": [],
        "officially_unrepliable_count": None,
        "stop_contact_count": None,
        "classification_failed_count": None,
        "semantic_judgement_failed_count": None,
        "semantic_migration_pending_count": None,
        "thread_changed_buyer_count": None,
        "thread_readback_count": None,
        "thread_revalidated_count": None,
        "next_wake": None,
    }


def _persist_wake_report(args: Any, output: Path, result: dict[str, Any]) -> None:
    report_input = output
    fallback_dir: Path | None = None
    try:
        try:
            _atomic_json(output, result)
        except Exception as error:
            result["status"] = "failed"
            result.setdefault("failed_step", "output")
            result.setdefault("errors", []).append({
                "type": type(error).__name__, "message": str(error)[:300],
            })
            fallback_dir = Path(tempfile.mkdtemp(prefix="gig-reply-wake-"))
            report_input = fallback_dir / "detector-result.json"
            _atomic_json(report_input, result)
        result["telegram_report"] = _telegram_report(args, report_input, "reply-wake")
        if report_input != output:
            _atomic_json(report_input, result)
        else:
            try:
                _atomic_json(output, result)
            except Exception:
                pass
    finally:
        if fallback_dir is not None:
            try:
                (fallback_dir / "detector-result.json").unlink(missing_ok=True)
                fallback_dir.rmdir()
            except OSError:
                pass


def _owner_only(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.chmod(0o600)


def _requested_estimate_module() -> Any:
    path = Path(__file__).with_name("requested_estimate.py")
    spec = importlib.util.spec_from_file_location("gig_requested_estimate_detector", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("requested_estimate_module_missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_requested_estimate(snapshot: dict[str, Any], *, args: Any, owner: str, now: int) -> dict[str, Any]:
    """Run the estimate lane between collect and normal queue construction."""
    module = _requested_estimate_module()
    return module.process_snapshot(
        snapshot,
        database_path=args.database,
        manifest=args.manifest,
        runner=args.runner,
        schema=args.estimate_schema,
        workdir=Path.home(),
        helper=args.cdp_helper,
        owner=owner,
        hidden=False,
        now=now,
    )


def merge_estimate_metrics(result: dict[str, Any], estimate_result: dict[str, Any], *, normal_actionable: int | None) -> dict[str, Any]:
    """Project estimate outcomes into the one wake truth without relabelling them."""
    estimate_required = _count(estimate_result.get("estimate_required"))
    estimate_effect = _count(estimate_result.get("estimate_effect"))
    estimate_readback = _count(estimate_result.get("estimate_readback"))
    estimate_pending = _count(estimate_result.get("estimate_pending"))
    estimate_failed = _count(estimate_result.get("estimate_failed"))
    result.update({
        key: estimate_result.get(key)
        for key in (
            "estimate_required", "estimate_effect", "estimate_readback",
            "estimate_pending", "estimate_failed", "estimate_events",
        )
    })
    if isinstance(normal_actionable, int) and estimate_required is not None:
        result["actionable"] = normal_actionable + estimate_required
    for total_key, estimate_value, normal_key in (
        ("effect", estimate_effect, "effect"),
        ("official_readback", estimate_readback, "official_readback"),
        ("pending", estimate_pending, "pending"),
        ("failed", estimate_failed, "failed"),
    ):
        normal_value = result.get(normal_key)
        if isinstance(normal_value, int) and estimate_value is not None:
            result[total_key] = normal_value + estimate_value
        elif estimate_value is not None and normal_value is None:
            result[total_key] = None
    result.setdefault("errors", []).extend(list(estimate_result.get("errors") or []))
    if estimate_failed and result.get("status") in {"completed", "reconcile_pending"}:
        result["status"] = "failed"
    elif estimate_pending and result.get("status") == "completed":
        result["status"] = "reconcile_pending"
    return result


def install_token_budget(environ: dict[str, str], *, run_id: str) -> None:
    """Keep the direct Reply owner free of inherited ANICCA token caps."""
    del run_id
    for key in (
        "ANICCA_BUDGET_SCOPE_ID", "ANICCA_PASS_TOKEN_BUDGET",
        "ANICCA_LOOP_DAILY_TOKEN_BUDGET", "ANICCA_BUDGET_DAILY_SCOPE",
        "ANICCA_BUDGET_REQUIRED",
    ):
        environ.pop(key, None)
    environ.setdefault(
        "ANICCA_TOKEN_BUDGET_LEDGER",
        environ.get(
            "GIG_TOKEN_BUDGET_LEDGER",
            str(Path.home() / ".local/state/anicca/telemetry/token-budget.jsonl"),
        ),
    )


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
        default=RUNNER_DIR / "agent_runner.py",
    )
    parser.add_argument("--schema", type=Path, default=gig_root / "schemas/reply_composition.schema.json")
    parser.add_argument(
        "--semantic-schema", type=Path,
        default=gig_root / "schemas/reply_semantic_judgement.schema.json",
    )
    parser.add_argument(
        "--semantic-effects-enabled", action=argparse.BooleanOptionalAction, default=True,
    )
    parser.add_argument("--estimate-schema", type=Path, default=gig_root / "schemas/estimate_category_selection.schema.json")
    parser.add_argument(
        "--cdp-helper", type=Path,
        default=BROWSER_DIR / "scripts" / "cdp_default_tab.py",
    )
    parser.add_argument("--snapshot-script", type=Path, default=gig_root / "scripts/coconala_queue_snapshot.py")
    parser.add_argument("--queue-script", type=Path, default=gig_root / "scripts/reply_queue.py")
    parser.add_argument("--lane-script", type=Path, default=gig_root / "scripts/reply_lane.py")
    parser.add_argument(
        "--fence-script", type=Path, default=gig_root / "scripts/project_effect_fence.py",
    )
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
        default=RUNNER_DIR / "config.json",
    )
    parser.add_argument("--telegram-target", default=os.environ.get("GIG_REPORT_CHAT", ""))
    args = parser.parse_args()

    os.environ["CLOAK_BROWSER_OWNER"] = "gig-reply-detector"
    run_id = f"{int(time.time())}-{os.getpid()}"
    evidence = args.evidence_dir or home / f"gig/evidence/reply-detector-{run_id}"
    output = args.output or evidence / "detector-result.json"
    try:
        evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
        evidence.chmod(0o700)
    except Exception as error:
        failure = {
            **_wake_result(run_id=run_id, trigger=args.trigger, status="failed"),
            "failed_step": "evidence",
            "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
        }
        _persist_wake_report(args, output, failure)
        print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
        return 1
    lock_fd: int | None = None
    lock_handle = None
    try:
        try:
            args.lock_file.parent.mkdir(parents=True, exist_ok=True)
            lock_fd = os.open(args.lock_file, os.O_CREAT | os.O_RDWR, 0o600)
            os.fchmod(lock_fd, 0o600)
            lock_handle = os.fdopen(lock_fd, "r+")
            lock_fd = None
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            busy = _wake_result(
                run_id=run_id, trigger=args.trigger, status="busy",
            )
            busy["errors"] = []
            _persist_wake_report(args, output, busy)
            print(json.dumps(busy, ensure_ascii=False, separators=(",", ":")))
            return 0
        except Exception as error:
            failure = {
                **_wake_result(
                    run_id=run_id, trigger=args.trigger, status="failed",
                ),
                "failed_step": "lock",
                "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
            }
            _persist_wake_report(args, output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1

        brake_status = _operator_brake_status()
        if brake_status == "held":
            operator_brake = {
                **_wake_result(
                    run_id=run_id, trigger=args.trigger, status="operator_brake",
                ),
                "errors": [],
            }
            _persist_wake_report(args, output, operator_brake)
            print(json.dumps(operator_brake, ensure_ascii=False, separators=(",", ":")))
            return 0
        if brake_status == "failed":
            failure = {
                **_wake_result(
                    run_id=run_id, trigger=args.trigger, status="failed",
                ),
                "failed_step": "operator_brake",
                "errors": [{"code": "operator_brake_check_failed"}],
            }
            _persist_wake_report(args, output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1

        snapshot = evidence / "marketplace-snapshot.json"
        queue = evidence / "reply-queue.json"
        lane_result = evidence / "reply-lane-result.json"
        try:
            collect_attempts = _collect_snapshot_with_retry(args, snapshot, evidence)
            _owner_only(snapshot)
            snapshot_value = json.loads(snapshot.read_text(encoding="utf-8"))
            terminal_cleanup = close_officially_unrepliable_pending(
                snapshot_value, database=args.database, manifest=args.manifest,
                owner=f"gig-reply-terminal-{run_id}", now=int(time.time()),
            )
            _atomic_json(evidence / "terminal-action-cleanup.json", terminal_cleanup)
            try:
                estimate_result = run_requested_estimate(
                    snapshot_value, args=args,
                    owner=f"gig-estimate-detector-{run_id}", now=int(time.time()),
                )
            except Exception as error:
                # Estimates are additive: a bounded estimate failure is reported
                # in this wake while the normal-message lane continues.
                estimate_result = {
                    "estimate_required": None, "estimate_effect": 0,
                    "estimate_readback": 0, "estimate_pending": 0,
                    "estimate_failed": 1, "estimate_events": [],
                    "errors": [{"type": type(error).__name__, "code": "estimate_lane_failed"}],
                }
            estimate_output = evidence / "requested-estimate-result.json"
            _atomic_json(estimate_output, estimate_result)
            _owner_only(estimate_output)
            normal_snapshot = evidence / "normal-reply-snapshot.json"
            if isinstance(snapshot_value, dict) and isinstance(snapshot_value.get("inquiries"), list):
                normal_value = dict(snapshot_value)
                normal_value["inquiries"] = [
                    item for item in snapshot_value["inquiries"]
                    if not (isinstance(item, dict) and item.get("estimate_required") is True)
                ]
                _atomic_json(normal_snapshot, normal_value)
                _owner_only(normal_snapshot)
            else:
                normal_snapshot = snapshot
            _run("queue_build", [
                sys.executable, str(args.queue_script), "build",
                "--snapshot", str(normal_snapshot), "--output", str(queue),
            ])
            _owner_only(queue)
            _run("outbox_enqueue", [
                sys.executable, str(args.queue_script), "enqueue",
                "--queue", str(queue), "--database", str(args.database),
                "--manifest", str(args.manifest),
            ])
            # Build the paid-room fence from this wake's explicit official orders.
            # If that proof is unavailable, the reply lane refuses instead of guessing.
            fences = evidence / "project-fences.json"
            try:
                _run("fence_build", [
                    sys.executable, str(args.fence_script), "build-paid",
                    "--snapshot", str(snapshot),
                    "--now", time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                    "--output", str(fences),
                ])
                _owner_only(fences)
            except Exception:
                fences.unlink(missing_ok=True)
            _run("reply_lane", [
                sys.executable, str(args.lane_script),
                "--queue", str(queue), "--database", str(args.database),
                "--manifest", str(args.manifest), "--runner", str(args.runner),
                "--schema", str(args.schema), "--cdp-helper", str(args.cdp_helper),
                "--max-model-calls", "0",
                "--output", str(lane_result), "--workdir", str(home),
                "--owner-prefix", f"gig-reply-detector-{run_id}",
                "--fences", str(fences),
            ], accepted=(0, 2))
            lane = json.loads(lane_result.read_text(encoding="utf-8"))
            queue_value = json.loads(queue.read_text(encoding="utf-8"))
            events = lane.get("events")
            dlq_events = lane.get("dlq_events")
            counts = {
                key: _count(lane.get(key))
                for key in (
                    "replied", "reconciled", "requeued", "reconcile_pending",
                    "already_delivered", "pending_verify", "dlq", "nothing_to_say",
                    "failed", "blocked", "skipped", "deferred",
                )
            }
            replied = counts["replied"]
            reconciled = counts["reconciled"]
            dlq = counts["dlq"]
            verified_events = _verified_events(events, replied)
            newly_dlq = len(dlq_events) if isinstance(dlq_events, list) else None
            pending_verify = counts["pending_verify"]
            reconcile_pending = counts["reconcile_pending"]
            result = {
                "status": str(lane.get("status") or "failed"),
                "trigger": args.trigger,
                **counts,
                "errors": list(lane.get("errors") or []),
                "events": list(events or []) if isinstance(events, list) else [],
                "dlq_events": list(dlq_events or []) if isinstance(dlq_events, list) else [],
            }
            result.update({
                "run_id": run_id,
                **_snapshot_terminal_counts(snapshot_value),
                **_snapshot_activity_counts(snapshot_value),
                "observed": (
                    len(snapshot_value["inquiries"])
                    if isinstance(snapshot_value, dict)
                    and isinstance(snapshot_value.get("inquiries"), list)
                    else None
                ),
                "actionable": (
                    len(queue_value["items"])
                    if isinstance(queue_value, dict)
                    and isinstance(queue_value.get("items"), list)
                    else None
                ),
                "oldest_actionable": _oldest_actionable(
                    queue_value.get("items") if isinstance(queue_value, dict) else None
                ),
                "effect": (
                    max(0, replied - reconciled)
                    if (
                        replied is not None
                        and reconciled is not None
                        and reconciled <= replied
                    )
                    else None
                ),
                "official_readback": (
                    len(verified_events) if verified_events is not None else None
                ),
                "pending": (
                    pending_verify + reconcile_pending
                    if pending_verify is not None and reconcile_pending is not None
                    else None
                ),
                "historical_dlq": (
                    max(0, dlq - newly_dlq)
                    if (
                        dlq is not None
                        and newly_dlq is not None
                        and newly_dlq <= dlq
                    )
                    else None
                ),
                "newly_dlq": newly_dlq,
                "next_wake": None,
                "collect_attempts": len(collect_attempts),
                "collect_recovered": len(collect_attempts) > 1,
            })
            merge_estimate_metrics(
                result, estimate_result,
                normal_actionable=(
                    len(queue_value["items"])
                    if isinstance(queue_value, dict)
                    and isinstance(queue_value.get("items"), list)
                    else None
                ),
            )
            _persist_wake_report(args, output, result)
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
            return 0 if result["status"] == "completed" else 1
        except StepFailure as error:
            failure = {
                **_wake_result(
                    run_id=run_id, trigger=args.trigger, status="failed",
                ),
                "failed_step": error.step,
                "errors": [{"returncode": error.returncode}],
            }
            if error.step == "collect":
                failure.update({
                    "effect": 0, "official_readback": 0, "pending": 0,
                    "estimate_effect": 0, "estimate_readback": 0,
                    "estimate_pending": 0, "estimate_failed": 0,
                })
                failure["collect_attempts"] = len(error.attempts)
                failure["collect_recovered"] = False
                failure["collect_attempt_receipts"] = error.attempts
            _persist_wake_report(args, output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1
        except Exception as error:
            failure = {
                **_wake_result(
                    run_id=run_id, trigger=args.trigger, status="failed",
                ),
                "failed_step": "internal",
                "errors": [{"type": type(error).__name__, "message": str(error)[:300]}],
            }
            _persist_wake_report(args, output, failure)
            print(json.dumps(failure, ensure_ascii=False, separators=(",", ":")))
            return 1
    finally:
        if lock_handle is not None:
            lock_handle.close()
        elif lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
