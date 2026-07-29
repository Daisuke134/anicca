#!/usr/bin/env python3
"""Reconcile a sent paid-work artifact into its project ledger.

This is deliberately browser-free: it consumes a green paid-queue evidence
bundle, verifies the project-bound artifact/hash, and materializes buyer-visible
state.  Re-running it is idempotent and never sends another message.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import runpy
from pathlib import Path
from typing import Any

try:
    from paid_queue_evidence import validate_paid_queue
except ModuleNotFoundError:  # direct import from the repository's test loader
    _spec = importlib.util.spec_from_file_location(
        "paid_queue_evidence", Path(__file__).with_name("paid_queue_evidence.py")
    )
    assert _spec and _spec.loader
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    validate_paid_queue = _module.validate_paid_queue

try:
    from paid_work_evidence import validate_paid_work
except ModuleNotFoundError:  # direct import from the repository's test loader
    _spec = importlib.util.spec_from_file_location(
        "paid_work_evidence", Path(__file__).with_name("paid_work_evidence.py")
    )
    assert _spec and _spec.loader
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    validate_paid_work = _module.validate_paid_work


class ReconcileError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconcileError(f"invalid_json:{path}") from exc
    if not isinstance(value, dict):
        raise ReconcileError(f"json_not_object:{path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ReconcileError(f"artifact_unreadable:{path}") from exc
    return digest.hexdigest()


def _same_path(left: Any, right: Any) -> bool:
    try:
        return Path(str(left or "")).expanduser().resolve() == Path(str(right or "")).expanduser().resolve()
    except OSError:
        return False


def _pending_bundle_is_fully_bound(
    current: dict[str, Any],
    root: Path,
    evidence: Path,
    manifest: dict[str, Any],
) -> bool:
    """Allow same-version revalidation only for our exact pending bundle."""
    if (
        current.get("buyer_visible") is not False
        or current.get("artifact_ready_pending_browser") is not True
        or current.get("next_action") != "retry_buyer_visible_delivery"
    ):
        return False
    artifact = Path(str(manifest.get("artifact_path") or "")).expanduser().resolve()
    acceptance = Path(str(manifest.get("acceptance_evidence_path") or "")).expanduser().resolve()
    try:
        artifact.relative_to(root)
        acceptance.relative_to(root)
    except ValueError:
        return False
    package_hash = str(manifest.get("package_sha256") or "")
    bindings = (
        ("current_version", manifest.get("artifact_version")),
        ("current_artifact_path", artifact),
        ("current_package_sha256", package_hash),
        ("current_acceptance_evidence_path", acceptance),
        ("current_acceptance_status", manifest.get("acceptance_status")),
        ("current_acceptance_delta", manifest.get("acceptance_delta")),
    )
    for key, expected in bindings:
        actual = current.get(key)
        if key.endswith("_path"):
            if not _same_path(actual, expected):
                return False
        elif actual != expected:
            return False
    if not _same_path(current.get("current_delivery_evidence_path"), evidence):
        return False
    try:
        if evidence.stat().st_mtime < float(current.get("current_delivery_evidence_mtime")):
            return False
        if not artifact.is_file() or _sha256(artifact) != package_hash:
            return False
        stable = _load_json(evidence)
    except (OSError, TypeError, ValueError, ReconcileError):
        return False
    if stable.get("status") != "ok":
        return False
    for key in ("artifact_version", "acceptance_status", "package_sha256", "acceptance_delta"):
        if stable.get(key) != manifest.get(key):
            return False
    if not _same_path(stable.get("project_root"), root):
        return False
    if not _same_path(stable.get("artifact_path"), artifact):
        return False
    if not _same_path(stable.get("acceptance_evidence_path"), acceptance):
        return False
    return True


def mark_ready_for_browser(
    project_root: str | Path,
    delivery_evidence_path: str | Path,
    *,
    min_mtime: float = 0,
) -> dict[str, Any]:
    """Persist a validated artifact as browser-pending, without opening a browser.

    This is the recovery boundary after a builder succeeds but the browser
    helper fails.  The stable delivery evidence is revalidated and all fields
    are copied from the project manifest, so a later pass can reuse only the
    exact artifact/hash/acceptance bundle that was validated here.
    """
    root = Path(project_root).expanduser().resolve()
    evidence = Path(delivery_evidence_path).expanduser().resolve()
    manifest = _load_json(root / "delivery" / "paid-work-result.json")
    state_path = root / "state.json"
    try:
        current = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconcileError("project_state_invalid") from exc
    if not isinstance(current, dict) or not current.get("request_id") or not current.get("adapter"):
        raise ReconcileError("project_state_not_initialized")
    allow_current_version = _pending_bundle_is_fully_bound(current, root, evidence, manifest)
    ok, errors = validate_paid_work(
        root,
        evidence,
        min_mtime=min_mtime,
        allow_current_version=allow_current_version,
    )
    if not ok:
        raise ReconcileError("paid_work_evidence_not_green:" + ",".join(errors))
    try:
        artifact = Path(str(manifest["artifact_path"])).expanduser().resolve()
        artifact.relative_to(root)
        acceptance = Path(str(manifest["acceptance_evidence_path"])).expanduser().resolve()
        acceptance.relative_to(root)
    except (KeyError, OSError, ValueError) as exc:
        raise ReconcileError("paid_work_manifest_binding_invalid") from exc
    version = str(manifest.get("artifact_version") or "")
    package_hash = str(manifest.get("package_sha256") or "")
    acceptance_delta = manifest.get("acceptance_delta")
    if not version or not package_hash or not isinstance(acceptance_delta, list):
        raise ReconcileError("paid_work_manifest_fields_missing")
    ledger = runpy.run_path(str(Path(__file__).with_name("project_ledger.py")))
    if (
        current.get("buyer_visible") is True
        and current.get("current_version") == version
        and current.get("current_package_sha256") == package_hash
    ):
        raise ReconcileError("project_already_buyer_visible")
    try:
        delivery_evidence_mtime = evidence.stat().st_mtime
    except OSError as exc:
        raise ReconcileError("delivery_evidence_unreadable") from exc
    patch = {
        "current_version": version,
        "current_artifact_path": str(artifact),
        "current_package_sha256": package_hash,
        "current_acceptance_evidence_path": str(acceptance),
        "current_acceptance_status": "PASS",
        "current_acceptance_delta": acceptance_delta,
        "current_delivery_evidence_path": str(evidence),
        "current_delivery_evidence_mtime": delivery_evidence_mtime,
        "buyer_visible": False,
        "artifact_ready_pending_browser": True,
        "next_action": "retry_buyer_visible_delivery",
    }
    if all(current.get(key) == value for key, value in patch.items()):
        return {**current, "reconciled": False, "resend": False}
    merged = ledger["append"](root, patch, "paid_work_ready_for_browser")
    return {**merged, "reconciled": True, "resend": False}


def reconcile(
    project_root: str | Path,
    evidence_dir: str | Path,
    queue_item_path: str | Path,
    *,
    min_mtime: float = 0,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    expected = _load_json(Path(queue_item_path).expanduser().resolve())
    expected_evidence = expected.get("delivery_evidence")
    if not isinstance(expected_evidence, dict):
        raise ReconcileError("queue_delivery_evidence_missing")
    bound_root = Path(str(expected_evidence.get("project_root") or "")).expanduser().resolve()
    if not str(expected_evidence.get("project_root") or "") or bound_root != root:
        raise ReconcileError("project_root_not_bound_to_queue")

    ok, errors = validate_paid_queue(evidence_dir, expected, min_mtime)
    if not ok:
        raise ReconcileError("paid_queue_evidence_not_green:" + ",".join(errors))
    browser_evidence = _load_json(
        Path(evidence_dir).expanduser().resolve() / "paid-queue-evidence.json"
    )
    send_performed = browser_evidence.get("send_performed") is True

    artifact = Path(str(expected_evidence.get("artifact_path") or "")).expanduser().resolve()
    try:
        artifact.relative_to(root)
    except ValueError as exc:
        raise ReconcileError("artifact_outside_project_root") from exc
    if not artifact.is_file() or artifact.stat().st_size <= 0:
        raise ReconcileError("artifact_missing_or_empty")
    expected_hash = str(expected_evidence.get("package_sha256") or "")
    if _sha256(artifact) != expected_hash:
        raise ReconcileError("artifact_hash_mismatch")
    version = str(expected_evidence.get("artifact_version") or "")
    if not version:
        raise ReconcileError("artifact_version_missing")

    ledger = runpy.run_path(str(Path(__file__).with_name("project_ledger.py")))
    state_path = root / "state.json"
    try:
        current = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconcileError("project_state_invalid") from exc
    if not isinstance(current, dict) or not current.get("request_id") or not current.get("adapter"):
        raise ReconcileError("project_state_not_initialized")
    patch = {
        "current_version": version,
        "current_artifact_path": str(artifact),
        "current_package_sha256": expected_hash,
        "buyer_visible": True,
        "artifact_ready_pending_browser": False,
        "latest_buyer_visible_version": version,
        "latest_buyer_visible_package_sha256": expected_hash,
        "next_action": "await_buyer_feedback",
    }
    if all(current.get(key) == value for key, value in patch.items()):
        return {
            **current,
            "reconciled": False,
            "resend": False,
            "send_performed": send_performed,
        }
    merged = ledger["append"](root, patch, "paid_work_browser_sent_reconciled")
    return {
        **merged,
        "reconciled": True,
        "resend": False,
        "send_performed": send_performed,
    }


def reconcile_answer(
    project_root: str | Path,
    evidence_dir: str | Path,
    queue_item_path: str | Path,
    answer_file: str | Path,
    *,
    min_mtime: float = 0,
) -> dict[str, Any]:
    """Reconcile a verified buyer-visible text answer without inventing an artifact."""
    root = Path(project_root).expanduser().resolve()
    evidence_root = Path(evidence_dir).expanduser().resolve()
    expected = _load_json(Path(queue_item_path).expanduser().resolve())
    expected_evidence = expected.get("delivery_evidence")
    if not isinstance(expected_evidence, dict):
        raise ReconcileError("queue_delivery_evidence_missing")
    bound_root = Path(str(expected_evidence.get("project_root") or "")).expanduser().resolve()
    if not str(expected_evidence.get("project_root") or "") or bound_root != root:
        raise ReconcileError("project_root_not_bound_to_queue")

    answer_path = Path(answer_file).expanduser().resolve()
    if answer_path.name != "paid-answer.json" or answer_path.parent != evidence_root.parent:
        raise ReconcileError("paid_answer_not_bound_to_pass_evidence")
    if min_mtime and (
        not answer_path.is_file() or answer_path.stat().st_mtime < min_mtime
    ):
        raise ReconcileError("paid_answer_stale")
    answer = _load_json(answer_path)
    message = str(answer.get("message") or "")
    if answer.get("version") != 1 or answer.get("status") != "answer" or not message.strip():
        raise ReconcileError("paid_answer_invalid")

    ok, errors = validate_paid_queue(evidence_root, expected, min_mtime)
    if not ok:
        raise ReconcileError("paid_answer_evidence_not_green:" + ",".join(errors))
    browser_evidence = _load_json(evidence_root / "paid-queue-evidence.json")
    if browser_evidence.get("mode") != "answer":
        raise ReconcileError("paid_answer_browser_mode_missing")
    message_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()
    if browser_evidence.get("message_sha256") != message_hash:
        raise ReconcileError("paid_answer_not_bound_to_browser_evidence")

    feedback_hash = str(expected.get("buyer_feedback_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", feedback_hash):
        raise ReconcileError("buyer_feedback_hash_missing")
    state_path = root / "state.json"
    current = _load_json(state_path)
    if not current.get("request_id") or not current.get("adapter"):
        raise ReconcileError("project_state_not_initialized")
    patch = {
        "handled_buyer_feedback_sha256": feedback_hash,
        "material_event_outcome": "buyer_answer_sent",
        "last_buyer_answer_sha256": message_hash,
        "last_buyer_answer_at": str(browser_evidence.get("captured_at") or ""),
        "next_action": "await_buyer_feedback",
    }
    send_performed = browser_evidence.get("send_performed") is True
    if all(current.get(key) == value for key, value in patch.items()):
        merged = current
        reconciled = False
    else:
        ledger = runpy.run_path(str(Path(__file__).with_name("project_ledger.py")))
        merged = ledger["append"](root, patch, "paid_answer_browser_sent_reconciled")
        reconciled = True
    return {
        **merged,
        "reconciled": reconciled,
        "resend": False,
        "send_performed": send_performed,
        "buyer_visible_response": True,
    }


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--queue-item", type=Path)
    parser.add_argument("--delivery-evidence", type=Path)
    parser.add_argument("--answer-file", type=Path)
    parser.add_argument("--mark-ready", action="store_true")
    parser.add_argument("--min-mtime", type=float, default=0)
    args = parser.parse_args()
    try:
        if args.mark_ready:
            if args.delivery_evidence is None:
                raise ReconcileError("delivery_evidence_required_for_mark_ready")
            result = mark_ready_for_browser(
                args.project_root, args.delivery_evidence, min_mtime=args.min_mtime
            )
        else:
            if args.evidence_dir is None or args.queue_item is None:
                raise ReconcileError("evidence_dir_and_queue_item_required")
            if args.answer_file is not None:
                result = reconcile_answer(
                    args.project_root,
                    args.evidence_dir,
                    args.queue_item,
                    args.answer_file,
                    min_mtime=args.min_mtime,
                )
            else:
                result = reconcile(
                    args.project_root,
                    args.evidence_dir,
                    args.queue_item,
                    min_mtime=args.min_mtime,
                )
    except ReconcileError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, separators=(",", ":")))
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
