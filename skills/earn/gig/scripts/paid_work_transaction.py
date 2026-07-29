#!/usr/bin/env python3
"""Rollback-safe boundary around a paid-work agent invocation."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from paid_work_evidence import validate_paid_work  # noqa: E402
from paid_work_validation_contract import (  # noqa: E402
    CONTRACT_RELATIVE_PATH,
    ContractError,
    parse_contract,
    run_contract,
    trusted_paths,
)


LEDGER_NAME = "paid-work-transaction.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _atomic_bytes(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(), 0o600)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def _snapshot(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    row: dict[str, Any] = {
        "path": str(resolved), "existed": False, "size_bytes": 0,
        "mode": None, "mtime_ns": None, "sha256": None, "content_b64": "",
    }
    if resolved.is_file():
        content = resolved.read_bytes()
        stat = resolved.stat()
        row.update({
            "existed": True, "size_bytes": len(content), "mode": stat.st_mode & 0o777,
            "mtime_ns": stat.st_mtime_ns, "sha256": _sha256_bytes(content),
            "content_b64": base64.b64encode(content).decode("ascii"),
        })
    return row


def _current_record(path: Path) -> dict[str, Any]:
    row = _snapshot(path)
    row.pop("content_b64", None)
    return row


def _latest_requirements_path(root: Path, manifest: Path) -> Path:
    try:
        prior = json.loads(manifest.read_text(encoding="utf-8"))
        candidate = Path(str(prior.get("requirements_path") or "")).expanduser().resolve()
        requirements_root = (root / "requirements").resolve()
        if candidate.is_file() and _inside(candidate, requirements_root):
            return candidate
    except (OSError, ValueError, json.JSONDecodeError, AttributeError):
        pass
    files = [path for path in (root / "requirements").glob("**/*") if path.is_file()]
    if files:
        return max(files, key=lambda path: (path.stat().st_mtime_ns, str(path)))
    return root / "requirements" / "latest-feedback.json"


def _baseline_files(root: Path, name: str) -> list[str]:
    directory = root / name
    return sorted(str(path.resolve()) for path in directory.glob("**/*") if path.is_file())


def begin_transaction(project_root: str | Path, delivery_evidence: str | Path,
                      evidence_dir: str | Path, min_mtime: float) -> Path:
    root = Path(project_root).expanduser().resolve()
    evidence = Path(evidence_dir).expanduser().resolve()
    manifest = root / "delivery" / "paid-work-result.json"
    requirements = _latest_requirements_path(root, manifest)
    contract_path = root / CONTRACT_RELATIVE_PATH
    try:
        contract_snapshot = _snapshot(contract_path)
        if not contract_snapshot["existed"]:
            raise ContractError("acceptance_contract_missing_or_invalid")
        contract = parse_contract(base64.b64decode(contract_snapshot["content_b64"]))
        contract_trusted_files = {
            relative: _snapshot(path)
            for relative, path in trusted_paths(contract, root).items()
        }
    except (OSError, ValueError, ContractError) as exc:
        raise ValueError(str(exc) or "acceptance_contract_missing_or_invalid") from exc
    ledger_path = evidence / LEDGER_NAME
    ledger = {
        "version": 1, "status": "active", "started_at": _now(),
        "project_root": str(root), "delivery_evidence": str(Path(delivery_evidence).expanduser().resolve()),
        "min_mtime": float(min_mtime),
        "snapshots": {
            "requirements_latest": _snapshot(requirements),
            "project_manifest": _snapshot(manifest),
            "stable_delivery_evidence": _snapshot(Path(delivery_evidence)),
            "validation_contract": contract_snapshot,
        },
        "contract_trusted_files": contract_trusted_files,
        "baseline": {
            "artifacts": _baseline_files(root, "artifacts"),
            "acceptance": _baseline_files(root, "acceptance"),
            "requirements": _baseline_files(root, "requirements"),
        },
        "actions": [], "restored": [], "quarantined": [],
    }
    _atomic_json(ledger_path, ledger)
    return ledger_path


def _load_ledger(ledger_path: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(ledger_path).expanduser().resolve()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("invalid paid-work transaction ledger")
    return path, value


def _candidate_manifest(ledger: dict[str, Any]) -> dict[str, Any]:
    path = Path(ledger["project_root"]) / "delivery" / "paid-work-result.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _quarantine_new_outputs(ledger_path: Path, ledger: dict[str, Any]) -> None:
    root = Path(ledger["project_root"]).resolve()
    rejected = ledger_path.parent / "rejected-output"
    specs = (
        ("artifact", root / "artifacts", set(ledger["baseline"].get("artifacts", []))),
        ("acceptance", root / "acceptance", set(ledger["baseline"].get("acceptance", []))),
        ("requirements", root / "requirements", set(ledger["baseline"].get("requirements", []))),
    )
    for label, owned_root, baseline in specs:
        candidates = sorted(
            (path for path in owned_root.glob("**/*") if path.is_file()),
            key=lambda path: (len(path.parts), str(path)),
            reverse=True,
        )
        for candidate in candidates:
            resolved = candidate.resolve()
            if not _inside(resolved, owned_root) or str(resolved) in baseline:
                continue
            rejected.mkdir(parents=True, exist_ok=True)
            relative = candidate.relative_to(owned_root)
            safe_name = "--".join(relative.parts)
            destination = rejected / f"{label}--{safe_name}"
            if destination.exists():
                destination = rejected / f"{label}--{_sha256_bytes(candidate.read_bytes())[:12]}--{safe_name}"
            os.replace(candidate, destination)
            row = {
                "kind": label,
                "from": str(resolved),
                "to": str(destination),
                "sha256": _sha256_bytes(destination.read_bytes()),
            }
            ledger["quarantined"].append(row)
            ledger["actions"].append({"action": "quarantine", **row})


def _restore_snapshot(ledger_path: Path, ledger: dict[str, Any], label: str, row: dict[str, Any]) -> None:
    path = Path(row["path"])
    if row["existed"]:
        content = base64.b64decode(row["content_b64"])
        _atomic_bytes(path, content, int(row["mode"]))
        if row.get("mtime_ns") is not None:
            os.utime(path, ns=(int(row["mtime_ns"]), int(row["mtime_ns"])))
    elif path.exists():
        discarded = ledger_path.parent / "rollback-discarded"
        discarded.mkdir(parents=True, exist_ok=True)
        destination = discarded / f"{label}--{path.name}"
        if destination.exists():
            destination = discarded / f"{label}--{os.getpid()}--{path.name}"
        os.replace(path, destination)
        ledger["actions"].append({"action": "remove_new_critical", "from": str(path), "to": str(destination)})
    current = _current_record(path)
    ledger["restored"].append({"label": label, **current})
    ledger["actions"].append({"action": "restore", "label": label, "path": str(path), "sha256": current["sha256"]})


def rollback_transaction(ledger_path: str | Path, reason: str) -> tuple[bool, list[str]]:
    try:
        path, ledger = _load_ledger(ledger_path)
        if ledger.get("status") == "rolled_back":
            return True, []
        _quarantine_new_outputs(path, ledger)
        for label, row in ledger["snapshots"].items():
            _restore_snapshot(path, ledger, label, row)
        for relative, row in ledger.get("contract_trusted_files", {}).items():
            _restore_snapshot(path, ledger, f"validation_input:{relative}", row)
        ledger["status"] = "rolled_back"
        ledger["failure_reason"] = reason
        ledger["finished_at"] = _now()
        ledger["after"] = {
            "project_manifest": _current_record(Path(ledger["project_root"]) / "delivery" / "paid-work-result.json"),
            "stable_delivery_evidence": _current_record(Path(ledger["delivery_evidence"])),
        }
        _atomic_json(path, ledger)
        return True, []
    except Exception as error:
        return False, [f"rollback_failed:{error}"]


def validate_and_promote(ledger_path: str | Path) -> tuple[bool, list[str]]:
    path, ledger = _load_ledger(ledger_path)
    root = Path(ledger["project_root"])
    stable = Path(ledger["delivery_evidence"])
    manifest = root / "delivery" / "paid-work-result.json"
    min_mtime = float(ledger["min_mtime"])
    ok, errors = validate_paid_work(
        root, stable, manifest, min_mtime, require_delivery_evidence=False,
    )
    if not ok:
        rollback_ok, rollback_errors = rollback_transaction(path, "project_validation_failed")
        return False, [*errors, *([] if rollback_ok else rollback_errors)]
    try:
        contract_snapshot = ledger["snapshots"]["validation_contract"]
        current_contract = _current_record(Path(contract_snapshot["path"]))
        if any(current_contract.get(key) != contract_snapshot.get(key) for key in ("existed", "sha256", "mode", "mtime_ns")):
            raise ContractError("acceptance_contract_missing_or_modified")
        contract = parse_contract(base64.b64decode(contract_snapshot["content_b64"]))
        for relative, snapshot in ledger.get("contract_trusted_files", {}).items():
            current = _current_record(Path(snapshot["path"]))
            if any(current.get(key) != snapshot.get(key) for key in ("existed", "sha256", "mode", "mtime_ns")):
                raise ContractError(f"acceptance_contract_trusted_file_modified:{relative}")
        payload = _candidate_manifest(ledger)
        artifact = Path(str(payload.get("artifact_path") or "")).expanduser().resolve()
        acceptance = Path(str(payload.get("acceptance_evidence_path") or "")).expanduser().resolve()
        requirements = Path(str(payload.get("requirements_path") or "")).expanduser().resolve()
        contract_ok, contract_errors, validation = run_contract(
            contract,
            root,
            artifact=artifact,
            artifact_version=str(payload.get("artifact_version") or ""),
            acceptance=acceptance,
            requirements=requirements,
        )
        ledger["validation"] = validation
        _atomic_json(path, ledger)
        if not contract_ok:
            infra_only = all(
                error.startswith("sandbox_infra_unavailable:") for error in contract_errors
            ) if contract_errors else False
            reason = "sandbox_infra_unavailable" if infra_only else "acceptance_contract_failed"
            rollback_ok, rollback_errors = rollback_transaction(path, reason)
            return False, [*contract_errors, *([] if rollback_ok else rollback_errors)]
        ok, errors = validate_paid_work(
            root, stable, manifest, min_mtime, require_delivery_evidence=False,
        )
        if not ok:
            rollback_ok, rollback_errors = rollback_transaction(path, "post_contract_validation_failed")
            return False, [*errors, *([] if rollback_ok else rollback_errors)]
        manifest_bytes = manifest.read_bytes()
        prior_mode = stable.stat().st_mode & 0o777 if stable.exists() else 0o600
        _atomic_bytes(stable, manifest_bytes, prior_mode)
        ledger["actions"].append({
            "action": "promote", "from": str(manifest), "to": str(stable),
            "sha256": _sha256_bytes(manifest_bytes),
        })
        _atomic_json(path, ledger)
    except ContractError as error:
        rollback_ok, rollback_errors = rollback_transaction(path, "acceptance_contract_failed")
        return False, [str(error), *([] if rollback_ok else rollback_errors)]
    except Exception as error:
        rollback_ok, rollback_errors = rollback_transaction(path, "promotion_failed")
        return False, [f"promotion_failed:{error}", *([] if rollback_ok else rollback_errors)]
    ok, errors = validate_paid_work(root, stable, manifest, min_mtime)
    if not ok:
        rollback_ok, rollback_errors = rollback_transaction(path, "full_validation_failed")
        return False, [*errors, *([] if rollback_ok else rollback_errors)]
    path, ledger = _load_ledger(path)
    ledger["status"] = "committed"
    ledger["finished_at"] = _now()
    ledger["after"] = {
        "project_manifest": _current_record(manifest),
        "stable_delivery_evidence": _current_record(stable),
    }
    _atomic_json(path, ledger)
    return True, []


def _main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    begin = sub.add_parser("begin")
    begin.add_argument("--project-root", required=True, type=Path)
    begin.add_argument("--delivery-evidence", required=True, type=Path)
    begin.add_argument("--evidence-dir", required=True, type=Path)
    begin.add_argument("--min-mtime", required=True, type=float)
    promote = sub.add_parser("validate-promote")
    promote.add_argument("--ledger", required=True, type=Path)
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--ledger", required=True, type=Path)
    rollback.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "begin":
        print(begin_transaction(args.project_root, args.delivery_evidence, args.evidence_dir, args.min_mtime))
        return 0
    if args.command == "validate-promote":
        ok, errors = validate_and_promote(args.ledger)
    else:
        ok, errors = rollback_transaction(args.ledger, args.reason)
    print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
