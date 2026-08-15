#!/usr/bin/env python3
"""Offline-safe planner and runner for the four Hermes Coconala revenue lanes.

The adapter deliberately owns no browser or marketplace implementation.  ``run``
only hands one forced step to the existing gig worker through its CDP lock.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from gig_paths import REPO_ROOT

try:  # direct execution has this directory on sys.path already
    from shared_commerce_snapshot import write_snapshot
except ImportError:  # pragma: no cover - import path is only needed by embedders
    from .shared_commerce_snapshot import write_snapshot  # type: ignore


DEFAULT_SNAPSHOT = Path.home() / "gig" / "shared-commerce-snapshot.json"
DEFAULT_REPO = REPO_ROOT
DEFAULT_BOARD = "gig-revenue"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_PROVIDER = "openai-codex"
DEFAULT_B0_COOLDOWN_MARKER = Path.home() / "gig" / ".b0-cooldown"
DEFAULT_STOREFRONT_WRITE_INTERVAL_SECONDS = 10_800
MIN_STOREFRONT_WRITE_INTERVAL_SECONDS = 3_600
MAX_STOREFRONT_WRITE_INTERVAL_SECONDS = 86_400
DEFAULT_RECEIPT_DIR = Path.home() / "gig" / "hermes-canary"
DEFAULT_APPLIED_LEDGER = Path.home() / "gig" / "applied.jsonl"
DEFAULT_SHUPPIN_LEDGER = Path.home() / "gig" / "shuppin.jsonl"
DEFAULT_TELEGRAM_DB = Path.home() / "gig" / "telegram-outbox.sqlite3"
AUDIT_CADENCE_SECONDS = 1_800
AUDIT_CRON_OFFSET_SECONDS = 300
AUDIT_ENQUEUE_GRACE_SECONDS = 600
AUDIT_MAX_RUNTIME_SECONDS = 7_200
AUDIT_MAX_JSON_BYTES = 1_048_576
HERMES_BIN = "hermes"

_LANES = ("paid", "reply", "apply", "storefront")
_RETIRED_RUNTIME_LANES = frozenset({"storefront"})
_ACTIVE_RUNTIME_LANES = tuple(lane for lane in _LANES if lane not in _RETIRED_RUNTIME_LANES)
_LANE_TO_STEP = {"paid": "PAID_WORK", "reply": "B1", "apply": "B2", "storefront": "B0"}
_LANE_TO_ASSIGNEE = {"paid": "gigpaid", "reply": "gigreply", "apply": "gigapply", "storefront": "gigstorefront"}
_LANE_TO_PRIORITY = {"paid": 40, "reply": 30, "apply": 20, "storefront": 10}
_TASK_KEY_RE = re.compile(r"^gig:coconala:(paid|reply|apply|storefront):([0-9]+)$")
_TASK_KEY_SEARCH_RE = re.compile(
    r"(?<![A-Za-z0-9_.:-])(gig:coconala:(?:paid|reply|apply|storefront):[0-9]+)(?![A-Za-z0-9_.:-])"
)
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")


class CanaryError(Exception):
    """A fail-closed, user-actionable canary contract error."""


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CanaryError("snapshot could not be read") from exc
    if not isinstance(value, dict):
        raise CanaryError("snapshot must be a JSON object")
    return value


def _required_snapshot(snapshot: Mapping[str, Any]) -> tuple[str, int, Mapping[str, Any]]:
    if snapshot.get("version") != 1:
        raise CanaryError("snapshot version is not supported")
    if snapshot.get("platform") != "coconala":
        raise CanaryError("snapshot platform is not coconala")
    if snapshot.get("ready") is not True:
        raise CanaryError("snapshot is not ready")
    missing = snapshot.get("missing_sources")
    if not isinstance(missing, list) or missing:
        raise CanaryError("snapshot has missing sources")
    snapshot_id = snapshot.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise CanaryError("snapshot_id is missing")
    if "/" in snapshot_id or "\\" in snapshot_id or "\x00" in snapshot_id:
        raise CanaryError("snapshot_id is unsafe")
    slot = snapshot.get("slot")
    if isinstance(slot, bool) or not isinstance(slot, int):
        raise CanaryError("snapshot slot is missing")
    lanes = snapshot.get("lanes")
    if not isinstance(lanes, dict) or not all(isinstance(lanes.get(lane), dict) for lane in _LANES):
        raise CanaryError("snapshot lanes are incomplete")
    return snapshot_id, slot, lanes


def _render_task_key(template: Any, lane: str, slot: int) -> str:
    if not isinstance(template, str) or not template:
        raise CanaryError("snapshot idempotency template is missing")
    try:
        rendered = template.format(platform="coconala", lane=lane, slot=slot)
    except (IndexError, KeyError, ValueError):
        raise CanaryError("snapshot idempotency template is invalid") from None
    expected = f"gig:coconala:{lane}:{slot}"
    if rendered != expected:
        raise CanaryError("snapshot idempotency template rendered an invalid key")
    return rendered


def _task_body(repo: Path, lane: str, task_key: str) -> str:
    command = shlex.join([
        "/opt/homebrew/bin/python3",
        str(repo / "skills/earn/gig/scripts/hermes_canary.py"),
        "run",
        "--lane",
        lane,
        "--task-key",
        task_key,
    ])
    return (
        "Run exactly the one command below for this task.\n"
        f"{command}\n\n"
        "Do not touch the browser or marketplace outside that command. "
        "Complete on receipt and rc0; block on a nonzero rc."
    )


def plan_snapshot(snapshot: Mapping[str, Any], *, repo: Path = DEFAULT_REPO) -> dict[str, Any]:
    """Validate a snapshot and return exactly four bounded task specifications."""
    snapshot_id, slot, _lanes = _required_snapshot(snapshot)
    idem = snapshot.get("idempotency")
    if not isinstance(idem, dict):
        raise CanaryError("snapshot idempotency data is missing")
    template = idem.get("task_template")
    tasks: list[dict[str, Any]] = []
    for lane in _LANES:
        key = _render_task_key(template, lane, slot)
        step = _LANE_TO_STEP[lane]
        tasks.append(
            {
                "lane": lane,
                "step": step,
                "assignee": _LANE_TO_ASSIGNEE[lane],
                "priority": _LANE_TO_PRIORITY[lane],
                "reserved_every_slot": lane == "storefront",
                "idempotency_key": key,
                "title": f"Coconala {lane} canary ({step}) slot {slot}",
                "body": _task_body(repo, lane, key),
            }
        )
    return {
        "action": "plan",
        "version": 1,
        "snapshot_id": snapshot_id,
        "slot": slot,
        "tasks": tasks,
    }


def plan_from_path(path: Path | str = DEFAULT_SNAPSHOT, *, repo: Path = DEFAULT_REPO) -> dict[str, Any]:
    return plan_snapshot(_read_json(Path(path)), repo=Path(repo))


def _hermes_create_argv(
    task: Mapping[str, Any],
    *,
    board: str,
    repo: Path,
    model: str,
    provider: str,
) -> list[str]:
    return [
        HERMES_BIN,
        "kanban",
        "--board",
        board,
        "create",
        str(task["title"]),
        "--body",
        str(task["body"]),
        "--assignee",
        str(task["assignee"]),
        "--workspace",
        f"dir:{repo}",
        "--priority",
        str(task["priority"]),
        "--idempotency-key",
        str(task["idempotency_key"]),
        "--max-runtime",
        "2h",
        "--max-retries",
        "2",
        "--json",
    ]


def _parse_hermes_json(stdout: str) -> Mapping[str, Any]:
    try:
        value = json.loads(stdout or "")
    except json.JSONDecodeError as exc:
        raise CanaryError("Hermes returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise CanaryError("Hermes returned an invalid result")
    return value


def _validated_excluded_lanes(exclude_lanes: Sequence[str] | None) -> frozenset[str]:
    excluded = frozenset(exclude_lanes or ())
    unknown = excluded.difference(_LANES)
    if unknown:
        raise CanaryError(f"unknown lane: {sorted(unknown)[0]}")
    return excluded


def enqueue_from_path(
    path: Path | str = DEFAULT_SNAPSHOT,
    *,
    repo: Path = DEFAULT_REPO,
    board: str = DEFAULT_BOARD,
    model: str = DEFAULT_MODEL,
    provider: str = DEFAULT_PROVIDER,
    exclude_lanes: Sequence[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Create each fresh planned card once; idempotency makes retries safe."""
    excluded_lanes = _validated_excluded_lanes(exclude_lanes) | _RETIRED_RUNTIME_LANES
    snapshot_path = Path(path)
    try:
        fresh = write_snapshot(output_path=snapshot_path)
    except Exception as exc:
        raise CanaryError("fresh snapshot could not be built") from exc
    if not isinstance(fresh, dict):
        raise CanaryError("fresh snapshot is invalid")
    plan = plan_snapshot(fresh, repo=Path(repo))
    run = runner or subprocess.run
    created: list[dict[str, Any]] = []
    for task in plan["tasks"]:
        if task["lane"] in excluded_lanes:
            continue
        argv = _hermes_create_argv(task, board=board, repo=Path(repo), model=model, provider=provider)
        try:
            result = run(argv, check=False, capture_output=True, text=True, shell=False)
        except OSError as exc:
            raise CanaryError("Hermes enqueue failed") from exc
        if result.returncode != 0:
            raise CanaryError("Hermes enqueue failed")
        payload = _parse_hermes_json(result.stdout)
        task_id = payload.get("id")
        if task_id is None:
            task_id = payload.get("task_id")
        created.append(
            {
                "lane": task["lane"],
                "idempotency_key": task["idempotency_key"],
                "task_id": task_id,
            }
        )
    return {
        "action": "enqueue",
        "version": 1,
        "snapshot_id": plan["snapshot_id"],
        "slot": plan["slot"],
        "created": created,
    }


def _validated_lane_key(lane: str, task_key: str) -> int:
    if not isinstance(lane, str) or not isinstance(task_key, str):
        raise CanaryError("lane and task key are required")
    match = _TASK_KEY_RE.fullmatch(task_key)
    if match is None or match.group(1) != lane:
        raise CanaryError("lane and task key do not match the canary contract")
    return int(match.group(2))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_receipt_name(task_key: str) -> str:
    value = _SAFE_ID_RE.sub("_", task_key).strip("._")
    if not value:
        raise CanaryError("task key cannot name a receipt")
    return f"{value}.json"


def _write_receipt(receipt_dir: Path, task_key: str, payload: Mapping[str, Any]) -> Path:
    try:
        receipt_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = receipt_dir / _safe_receipt_name(task_key)
        fd, temporary = tempfile.mkstemp(prefix=f".{destination.stem}.", suffix=".tmp", dir=receipt_dir)
        try:
            os.fchmod(fd, 0o600)
            encoded = (json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            os.chmod(destination, 0o600)
        finally:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass
    except OSError as exc:
        raise CanaryError("canary receipt could not be written") from exc
    return destination


def _storefront_write_interval(value: Any = None) -> int:
    raw = (
        os.environ.get(
            "GIG_HERMES_STOREFRONT_WRITE_INTERVAL_SECONDS",
            str(DEFAULT_STOREFRONT_WRITE_INTERVAL_SECONDS),
        )
        if value is None
        else value
    )
    try:
        interval = int(raw)
    except (TypeError, ValueError):
        raise CanaryError("storefront write interval is invalid") from None
    if not MIN_STOREFRONT_WRITE_INTERVAL_SECONDS <= interval <= MAX_STOREFRONT_WRITE_INTERVAL_SECONDS:
        raise CanaryError("storefront write interval is invalid")
    return interval


def _has_recent_b0_success(
    marker_path: Path, *, now_epoch: Callable[[], float], interval_seconds: int
) -> bool:
    try:
        marked = int(marker_path.read_text(encoding="utf-8").strip())
        now = float(now_epoch())
    except (OSError, TypeError, ValueError):
        return False
    age = now - marked
    return marked >= 0 and age >= 0 and age < interval_seconds


def _storefront_observation_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("observation is not an object")
    digest, live, services = (value.get(key) for key in ("content_sha256", "live_listings_count", "service_count"))
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("observation hash is invalid")
    if any(type(count) is not int or count < 0 for count in (live, services)):
        raise ValueError("observation counts are invalid")
    return {"status": "ok", "content_sha256": digest, "live_listings_count": live, "service_count": services}


def _default_storefront_observer() -> Mapping[str, Any]:
    from listing_inventory import observe_storefront
    return observe_storefront()


def _write_truth(path: Path, payload: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(
            json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(path, 0o600)
    except OSError as exc:
        raise CanaryError("forced lane truth could not be written") from exc


def _forced_lane_truth(path: Path, *, lane: str, step: str) -> tuple[bool, str]:
    """Validate the structured receipt emitted by the forced worker run."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, "forced_lane_receipt_missing_or_invalid"
    if not isinstance(value, dict) or value.get("lane") != lane or value.get("step") != step:
        return False, "forced_lane_receipt_ambiguous"
    for field in (
        "blocked", "turns_exhausted", "incomplete", "unclosed",
        "coverage_complete", "collector_complete",
    ):
        if field in value and not isinstance(value[field], bool):
            return False, f"forced_lane_{field}_invalid"
    status = value.get("status")
    if status == "blocked" or value.get("blocked") is True:
        return False, "forced_lane_blocked"
    if status in ("failed", "failure", "error"):
        return False, "forced_lane_not_success"
    if status not in ("success", "verified", "completed"):
        return False, "forced_lane_not_success"
    if value.get("turns_exhausted") is True:
        return False, "forced_lane_turns_exhausted"
    if value.get("incomplete") is True or value.get("collector_complete") is not True:
        return False, "forced_lane_incomplete"
    if value.get("coverage_complete") is not True:
        return False, "forced_lane_coverage_incomplete"
    if value.get("unclosed") is True:
        return False, "forced_lane_unclosed"
    outcome = value.get("outcome")
    if outcome in ("failed", "blocked", "incomplete", "unclosed", "turns_exhausted"):
        return False, f"forced_lane_{outcome}"
    external_expected = value.get("external_effect_expected")
    if external_expected is not None and not isinstance(external_expected, bool):
        return False, "forced_lane_external_effect_expected_invalid"
    send_verified = value.get("send_verified")
    if send_verified is not None and not isinstance(send_verified, bool):
        return False, "forced_lane_send_verified_invalid"
    closure = value.get("lane_closure")
    if closure is None:
        closure = value.get("closure")
    if closure is not None and not (
        closure is True
        or closure == "closed"
        or isinstance(closure, dict) and closure.get("closed") is True
    ):
        return False, "forced_lane_external_effect_unclosed"
    no_action = value.get("no_action_reason")
    if no_action is None:
        no_action = value.get("no_action")
    if no_action is not None:
        if not isinstance(no_action, str) or not no_action.strip():
            return False, "forced_lane_no_action_reason_missing"
        readback_count = value.get("official_readback_count")
        if isinstance(readback_count, bool) or not isinstance(readback_count, int) or readback_count != 0:
            return False, "forced_lane_no_action_readback_nonzero"
        if value.get("external_effect_expected") is True:
            return False, "forced_lane_no_action_effect_expected"
        return True, "verified_noop"
    if external_expected is True and send_verified is not True:
        return False, "forced_lane_effect_not_verified"
    if external_expected is not False and send_verified is not True:
        return False, "forced_lane_effect_not_verified"
    return True, "verified_send"


def run_lane(
    *,
    lane: str,
    task_key: str,
    repo: Path = DEFAULT_REPO,
    snapshot_path: Path | str = DEFAULT_SNAPSHOT,
    receipt_dir: Path | str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    now_epoch: Callable[[], float] | None = None,
    marker_path: Path | str | None = None,
    interval_seconds: int | str | None = None,
    truth_path: Path | str | None = None,
    storefront_observer: Callable[[], Mapping[str, Any]] | None = None,
) -> int:
    """Run exactly one forced pass and persist a bounded receipt."""
    _validated_lane_key(lane, task_key)
    storefront_interval = (
        _storefront_write_interval(interval_seconds) if lane == "storefront" else None
    )
    snapshot_file = Path(snapshot_path)
    try:
        fresh = write_snapshot(output_path=snapshot_file)
    except Exception as exc:
        raise CanaryError("fresh snapshot could not be built") from exc
    if not isinstance(fresh, dict):
        raise CanaryError("fresh snapshot is invalid")
    snapshot_id, _slot, _lanes = _required_snapshot(fresh)

    step = _LANE_TO_STEP[lane]
    slot = _validated_lane_key(lane, task_key)
    repo_path = Path(repo)
    receipt_root = Path(receipt_dir) if receipt_dir is not None else Path.home() / "gig" / "hermes-canary"
    truth_file = (
        Path(truth_path)
        if truth_path is not None
        else receipt_root / ".truth" / f"{_safe_receipt_name(task_key)}.truth.json"
    )
    try:
        receipt_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        truth_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if truth_path is None:
            truth_file.unlink(missing_ok=True)
    except OSError as exc:
        raise CanaryError("forced lane truth path could not be prepared") from exc
    lock_script = repo_path / "skills/earn/gig/scripts/run_with_cdp_lock.sh"
    launcher = repo_path / "skills/earn/gig/scripts/launch_gig_worker.sh"
    argv = [
        str(lock_script),
        f"hermes-{lane}-{slot}",
        "7200",
        "--",
        "/usr/bin/env",
        f"GIG_HERMES_FORCED_STEP={step}",
        f"GIG_HERMES_TASK_KEY={task_key}",
        f"GIG_HERMES_SNAPSHOT_ID={snapshot_id}",
        f"GIG_HERMES_TRUTH_PATH={truth_file}",
        "GIG_WORKER_REPORTS_ENABLED=1",
        "/bin/bash",
        str(launcher),
    ]
    child_env = {
        name: value for name, value in os.environ.items()
        if not name.startswith("HERMES_KANBAN_")
    }
    child_env["CDP_LOCK_DIR"] = str(Path.home() / "gig" / f".cdp-gig-{lane}.lock")
    child_env["CLOAK_BROWSER_OWNER"] = f"gig-{lane}"
    child_env["GIG_LOCK_DIR"] = str(Path.home() / "gig" / f".gig-pass-{lane}.lock.d")
    child_env["GIG_HERMES_TRUTH_PATH"] = str(truth_file)
    started = _utc_now()
    receipt_payload = {
        "version": 1,
        "task_key": task_key,
        "lane": lane,
        "step": step,
        "snapshot_id": snapshot_id,
        "started_at": started,
        "truth_path": str(truth_file),
    }
    observation_failed = False
    if lane == "storefront":
        try:
            receipt_payload["observation"] = _storefront_observation_summary(
                (storefront_observer or _default_storefront_observer)()
            )
        except Exception:
            observation_failed = True
            receipt_payload["observation"] = {
                "status": "failed", "content_sha256": None,
                "live_listings_count": None, "service_count": None,
            }
    recent = lane == "storefront" and _has_recent_b0_success(
        Path(marker_path) if marker_path is not None else DEFAULT_B0_COOLDOWN_MARKER,
        now_epoch=now_epoch or time.time,
        interval_seconds=storefront_interval,
    )
    if observation_failed and not recent:
        receipt_payload.update(finished_at=_utc_now(), rc=1, outcome="failed", reason="storefront_observation_failed")
        _write_receipt(receipt_root, task_key, receipt_payload)
        return 1
    if recent:
        _write_truth(
            truth_file,
            {
                "lane": lane,
                "step": step,
                "status": "success",
                "coverage_complete": True,
                "collector_complete": True,
                "no_action_reason": "storefront_write_interval",
                "official_readback_count": 0,
            },
        )
        truth_ok, truth_reason = _forced_lane_truth(truth_file, lane=lane, step=step)
        deferred_rc = 0 if truth_ok else 1
        receipt_payload.update(
            finished_at=_utc_now(), rc=deferred_rc,
            outcome="deferred" if deferred_rc == 0 else "failed",
            reason="storefront_write_interval", no_action_reason="storefront_write_interval",
            collector_complete=True, official_readback_count=0,
            truth_verified=truth_ok, truth_reason=truth_reason,
        )
        _write_receipt(receipt_root, task_key, receipt_payload)
        return deferred_rc
    child_rc = 127
    run = runner or subprocess.run
    try:
        result = run(
            argv,
            check=False,
            shell=False,
            env=child_env,
        )
        child_rc = int(result.returncode)
    except OSError:
        child_rc = 127
    finished = _utc_now()
    truth_ok, truth_reason = _forced_lane_truth(truth_file, lane=lane, step=step)
    if child_rc == 0 and not truth_ok:
        child_rc = 1
    receipt_payload.update(
        finished_at=finished, rc=child_rc, outcome="executed" if child_rc == 0 else "failed"
    )
    receipt_payload.update(truth_verified=truth_ok, truth_reason=truth_reason)
    _write_receipt(receipt_root, task_key, receipt_payload)
    return child_rc


def _audit_epoch(value: Any) -> float | None:
    """Return a finite epoch from the small set of ledger timestamp shapes."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        number = parsed.timestamp()
    return number if math.isfinite(number) else None


def _audit_row_epoch(row: Mapping[str, Any]) -> float | None:
    for field in ("ts", "timestamp", "applied_at", "created_at", "createdAt", "updated_at"):
        if field in row:
            value = _audit_epoch(row.get(field))
            if value is not None:
                return value
    return None


def _audit_numeric_id(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if math.isfinite(value) and value.is_integer() else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        return str(int(value.strip()))
    return None


def _audit_jsonl(path: Path) -> list[Mapping[str, Any]]:
    if not path.exists():
        return []
    rows: list[Mapping[str, Any]] = []
    try:
        with path.open("rb") as handle:
            for raw in handle:
                if len(raw) > AUDIT_MAX_JSON_BYTES:
                    continue
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError):
                    continue
                if isinstance(value, dict):
                    rows.append(value)
    except OSError as exc:
        raise CanaryError("audit ledger could not be read") from exc
    return rows


def _audit_task_key(task: Mapping[str, Any]) -> str | None:
    found: set[str] = set()
    for field in ("title", "body"):
        value = task.get(field)
        if isinstance(value, str):
            found.update(match.group(1) for match in _TASK_KEY_SEARCH_RE.finditer(value))
    if len(found) != 1:
        return None
    key = next(iter(found))
    return key if _TASK_KEY_RE.fullmatch(key) is not None else None


def _audit_task_status(task: Mapping[str, Any]) -> str:
    value: Any = task.get("status") or task.get("state", "")
    if isinstance(value, Mapping):
        value = value.get("name", value.get("status", ""))
    status = str(value or "").strip().lower()
    return status if status in {"done", "running", "ready", "blocked"} else "unknown"


def _audit_due_slots(since: float, horizon: float) -> list[tuple[int, int]]:
    first = math.floor((since - AUDIT_CRON_OFFSET_SECONDS) / AUDIT_CADENCE_SECONDS) + 1
    due: list[tuple[int, int]] = []
    scheduled = first * AUDIT_CADENCE_SECONDS + AUDIT_CRON_OFFSET_SECONDS
    while scheduled <= horizon:
        due.append((scheduled // AUDIT_CADENCE_SECONDS, scheduled))
        scheduled += AUDIT_CADENCE_SECONDS
    return due


def _audit_tasks(
    *,
    board: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None,
) -> list[Mapping[str, Any]]:
    argv = [HERMES_BIN, "kanban", "--board", board, "list", "--archived", "--json"]
    run = runner or subprocess.run
    try:
        result = run(argv, check=False, capture_output=True, text=True, shell=False)
    except OSError as exc:
        raise CanaryError("Hermes audit query failed") from exc
    if result.returncode != 0:
        raise CanaryError("Hermes audit query failed")
    stdout = result.stdout or ""
    try:
        payload = json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CanaryError("Hermes audit returned invalid JSON") from exc
    if isinstance(payload, list):
        values = payload
    elif isinstance(payload, dict):
        values = payload.get("tasks", payload.get("items", payload.get("data", [])))
    else:
        values = []
    if not isinstance(values, list) or not all(isinstance(value, dict) for value in values):
        raise CanaryError("Hermes audit returned invalid tasks")
    return values


def _audit_receipts(receipt_dir: Path) -> dict[str, Mapping[str, Any]]:
    receipts: dict[str, Mapping[str, Any]] = {}
    if not receipt_dir.exists():
        return receipts
    try:
        paths = sorted(receipt_dir.glob("*.json"))
    except OSError as exc:
        raise CanaryError("audit receipts could not be read") from exc
    for path in paths:
        try:
            if not path.is_file() or path.stat().st_size > AUDIT_MAX_JSON_BYTES:
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        key = value.get("task_key")
        if not isinstance(key, str) or _TASK_KEY_RE.fullmatch(key) is None:
            continue
        receipts[key] = value
    return receipts


def _audit_receipt_outcome(value: Mapping[str, Any]) -> str | None:
    rc = value.get("rc")
    if isinstance(rc, bool) or not isinstance(rc, int) or rc != 0:
        return None
    outcome = value.get("outcome", "executed")
    return outcome if outcome in {"executed", "deferred"} else None


def _audit_applications(path: Path, since: float, horizon: float) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in _audit_jsonl(path):
        if row.get("status") != "applied":
            continue
        if row.get("submit_verified") is not True or row.get("applied_page_verified") is not True:
            continue
        timestamp = _audit_row_epoch(row)
        request_id = _audit_numeric_id(row.get("requestId"))
        if timestamp is None or request_id is None or not since <= timestamp <= horizon:
            continue
        counts[request_id] = counts.get(request_id, 0) + 1
    duplicate_ids = sorted((key for key, count in counts.items() if count > 1), key=int)
    return {
        "verified_count": sum(counts.values()),
        "unique_ids_count": len(counts),
        "duplicate_request_ids": duplicate_ids,
        "_request_ids": set(counts),
    }


def _audit_telegram_ids(path: Path, since: float) -> set[str]:
    if not path.exists():
        return set()
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT event_key,kind,state,created_at,message_id FROM telegram_reports"
        ).fetchall()
    except (OSError, sqlite3.Error):
        return set()
    finally:
        try:
            connection.close()
        except (UnboundLocalError, sqlite3.Error):
            pass
    reported: set[str] = set()
    for row in rows:
        if row["kind"] != "application" or row["state"] != "sent" or not str(row["message_id"] or "").strip():
            continue
        timestamp = _audit_epoch(row["created_at"])
        if timestamp is None or timestamp < since:
            continue
        event_key = row["event_key"]
        if not isinstance(event_key, str) or ":" not in event_key:
            continue
        request_id = _audit_numeric_id(event_key.rsplit(":", 1)[1])
        if request_id is not None:
            reported.add(request_id)
    return reported


def _audit_storefront_effects(path: Path, since: float, horizon: float) -> int:
    actions = {"shuppin_edited", "shuppin_published", "shuppin_created", "created", "published", "updated"}
    count = 0
    for row in _audit_jsonl(path):
        if row.get("action") not in actions or _audit_numeric_id(row.get("service_id")) is None:
            continue
        timestamp = _audit_row_epoch(row)
        if timestamp is not None and since <= timestamp <= horizon:
            count += 1
    return count


def audit_canary(
    *,
    since: float,
    until: float,
    now: float | None = None,
    board: str = DEFAULT_BOARD,
    receipt_dir: Path | str = DEFAULT_RECEIPT_DIR,
    applied_ledger: Path | str = DEFAULT_APPLIED_LEDGER,
    shuppin_ledger: Path | str = DEFAULT_SHUPPIN_LEDGER,
    telegram_db: Path | str = DEFAULT_TELEGRAM_DB,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Read-only audit for all four Hermes revenue lanes."""
    try:
        current = float(time.time() if now is None else now)
        since = float(since)
        until = float(until)
    except (TypeError, ValueError):
        raise CanaryError("invalid audit window") from None
    if not all(math.isfinite(value) for value in (since, until, current)) or not (0 <= since < until) or current < since:
        raise CanaryError("invalid audit window")
    horizon = min(current, until)
    tasks = _audit_tasks(board=board, runner=runner)
    receipts = _audit_receipts(Path(receipt_dir))
    due_by_lane = {lane: _audit_due_slots(since, horizon) for lane in _LANES}
    expected_keys = {
        lane: {f"gig:coconala:{lane}:{slot_id}": slot_id for slot_id, _scheduled in due}
        for lane, due in due_by_lane.items()
    }
    task_by_key: dict[str, Mapping[str, Any]] = {}
    for task in tasks:
        key = _audit_task_key(task)
        if key is not None and key in expected_keys.get(key.split(":")[2], {}):
            task_by_key.setdefault(key, task)

    lane_results: dict[str, dict[str, Any]] = {}
    stale_active = 0
    grace_pending = 0
    for lane, due in due_by_lane.items():
        metrics: dict[str, Any] = {
            "expected_due": len(due),
            "enqueued": 0,
            "done": 0,
            "running": 0,
            "ready": 0,
            "blocked": 0,
            "executed": 0,
            "deferred": 0,
            "missing_slots": 0,
            "nonzero_or_invalid_receipts": 0,
            "stale_active": 0,
            "_grace_pending": 0,
        }
        for slot_id, scheduled in due:
            key = f"gig:coconala:{lane}:{slot_id}"
            task = task_by_key.get(key)
            if task is None:
                if current >= scheduled + AUDIT_ENQUEUE_GRACE_SECONDS:
                    metrics["missing_slots"] += 1
                else:
                    metrics["_grace_pending"] += 1
                    grace_pending += 1
                continue
            metrics["enqueued"] += 1
            status = _audit_task_status(task)
            if status in {"done", "running", "ready", "blocked"}:
                metrics[status] += 1
            if status in {"running", "ready"}:
                task_epoch = _audit_row_epoch(task)
                if task_epoch is None or current - task_epoch <= AUDIT_MAX_RUNTIME_SECONDS:
                    continue
                metrics["stale_active"] += 1
                stale_active += 1
            outcome = _audit_receipt_outcome(receipts[key]) if key in receipts else None
            if outcome == "executed":
                metrics["executed"] += 1
            elif outcome == "deferred":
                metrics["deferred"] += 1
            if key in receipts and outcome is None:
                metrics["nonzero_or_invalid_receipts"] += 1
            elif status == "done" and key not in receipts:
                metrics["nonzero_or_invalid_receipts"] += 1
        lane_results[lane] = metrics

    applications = _audit_applications(Path(applied_ledger), since, horizon)
    reported_ids = _audit_telegram_ids(Path(telegram_db), since)
    request_ids = applications.pop("_request_ids")
    unreported_ids = sorted(request_ids - reported_ids, key=int)
    effect_count = _audit_storefront_effects(Path(shuppin_ledger), since, horizon)
    window_complete = current >= until
    all_nonstarved: bool | None = None
    if window_complete:
        all_nonstarved = all(lane_results[lane]["executed"] > 0 for lane in _LANES)
    else:
        all_nonstarved = None
    invariants: dict[str, bool | None] = {
        "no_missing_due": all(metrics["missing_slots"] == 0 for metrics in lane_results.values()),
        "no_bad_receipts": all(
            metrics["nonzero_or_invalid_receipts"] == 0 for metrics in lane_results.values()
        ),
        "no_blocked_tasks": all(metrics["blocked"] == 0 for metrics in lane_results.values()),
        "no_stale_active": stale_active == 0,
        "no_duplicate_applications": not applications["duplicate_request_ids"],
        "all_applications_reported": not unreported_ids,
        "no_excess_storefront_effects": effect_count <= lane_results["storefront"]["executed"],
        "all_lanes_nonstarved": all_nonstarved,
    }
    proven_red = any(value is False for value in invariants.values())
    active_pending = any(
        lane_results[lane]["running"] + lane_results[lane]["ready"] > lane_results[lane]["stale_active"]
        for lane in _LANES
    )
    if proven_red:
        verdict = "RED"
    elif not window_complete or active_pending or grace_pending:
        verdict = "PENDING"
    else:
        verdict = "GREEN" if all(value is True for value in invariants.values()) else "PENDING"
    for metrics in lane_results.values():
        metrics.pop("_grace_pending", None)
    return {
        "version": 1,
        "since": since,
        "until": until,
        "now": current,
        "window_complete": window_complete,
        "verdict": verdict,
        "lanes": lane_results,
        "applications": applications,
        "telegram": {"unreported_application_ids": unreported_ids},
        "storefront": {"effect_count": effect_count},
        "invariants": invariants,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes Coconala four-lane revenue adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    plan.add_argument("--repo", type=Path, default=DEFAULT_REPO)

    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    enqueue.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    enqueue.add_argument("--board", default=DEFAULT_BOARD)
    enqueue.add_argument("--model", default=DEFAULT_MODEL)
    enqueue.add_argument("--provider", default=DEFAULT_PROVIDER)
    enqueue.add_argument("--exclude-lane", action="append", choices=_LANES, default=[])

    run = sub.add_parser("run")
    run.add_argument("--lane", required=True, choices=_ACTIVE_RUNTIME_LANES)
    run.add_argument("--task-key", required=True)
    run.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    run.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    run.add_argument("--receipt-dir", type=Path, default=None)

    audit = sub.add_parser("audit")
    audit.add_argument("--since", type=float, required=True)
    audit.add_argument("--until", type=float, required=True)
    audit.add_argument("--now", type=float, default=None)
    audit.add_argument("--board", default=DEFAULT_BOARD)
    audit.add_argument("--receipt-dir", type=Path, default=DEFAULT_RECEIPT_DIR)
    audit.add_argument("--applied-ledger", type=Path, default=DEFAULT_APPLIED_LEDGER)
    audit.add_argument("--shuppin-ledger", type=Path, default=DEFAULT_SHUPPIN_LEDGER)
    audit.add_argument("--telegram-db", type=Path, default=DEFAULT_TELEGRAM_DB)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "plan":
            result = plan_from_path(args.snapshot, repo=args.repo)
            rc = 0
        elif args.command == "enqueue":
            result = enqueue_from_path(
                args.snapshot,
                repo=args.repo,
                board=args.board,
                model=args.model,
                provider=args.provider,
                exclude_lanes=args.exclude_lane,
            )
            rc = 0
        elif args.command == "audit":
            result = audit_canary(
                since=args.since,
                until=args.until,
                now=args.now,
                board=args.board,
                receipt_dir=args.receipt_dir,
                applied_ledger=args.applied_ledger,
                shuppin_ledger=args.shuppin_ledger,
                telegram_db=args.telegram_db,
            )
            rc = 1 if result["verdict"] == "RED" else 0
        else:
            rc = run_lane(
                lane=args.lane,
                task_key=args.task_key,
                repo=args.repo,
                snapshot_path=args.snapshot,
                receipt_dir=args.receipt_dir,
            )
            result = {
                "action": "run",
                "version": 1,
                "lane": args.lane,
                "task_key": args.task_key,
                "rc": rc,
            }
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return rc
    except CanaryError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
