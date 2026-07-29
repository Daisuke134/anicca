"""Deterministic evidence gates for a paid-work revision run."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _owned_file(value: Any, root: Path) -> tuple[Path | None, str | None]:
    path = Path(str(value or "")).expanduser()
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None, "path_outside_project_root"
    if not resolved.is_file() or resolved.stat().st_size == 0:
        return None, "file_missing_or_empty"
    return resolved, None


def _require_fresh(path: Path | None, label: str, min_mtime: float, errors: list[str]) -> None:
    """Reject evidence records that predate the pass that requested them."""
    if path is None or min_mtime <= 0:
        return
    try:
        if path.stat().st_mtime < min_mtime:
            errors.append(f"{label}_stale")
    except OSError:
        errors.append(f"{label}_missing_or_empty")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_number(value: str) -> int | None:
    match = re.fullmatch(r"v(\d+)", value.strip(), re.IGNORECASE)
    return int(match.group(1)) if match else None


def validate_paid_work(
    project_root: str | Path,
    delivery_evidence_path: str | Path,
    manifest_path: str | Path | None = None,
    min_mtime: float = 0,
    allow_current_version: bool = False,
    require_delivery_evidence: bool = True,
) -> tuple[bool, list[str]]:
    """Validate a builder's versioned artifact before browser submission."""
    root = Path(project_root).expanduser().resolve()
    manifest = Path(manifest_path or root / "delivery" / "paid-work-result.json").expanduser()
    errors: list[str] = []
    try:
        freshness_floor = max(float(min_mtime or 0), 0.0)
    except (TypeError, ValueError):
        freshness_floor = 0.0
        errors.append("min_mtime_invalid")
    try:
        manifest.resolve().relative_to(root)
    except ValueError:
        errors.append("manifest_outside_project_root")
    if manifest.is_file():
        _require_fresh(manifest, "manifest", freshness_floor, errors)
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
        errors.append("paid_work_manifest_missing_or_invalid")
    if not isinstance(payload, dict):
        payload = {}
        errors.append("paid_work_manifest_not_object")
    if payload.get("status") != "ok":
        errors.append("paid_work_status_not_ok")
    recorded_root = Path(str(payload.get("project_root") or "")).expanduser()
    try:
        if recorded_root.resolve() != root:
            errors.append("project_root_binding_mismatch")
    except OSError:
        errors.append("project_root_binding_invalid")
    requirements, reason = _owned_file(payload.get("requirements_path"), root)
    if reason:
        errors.append(f"requirements_{reason}")
    _require_fresh(requirements, "requirements", freshness_floor, errors)
    artifact, reason = _owned_file(payload.get("artifact_path"), root)
    if reason:
        errors.append(f"artifact_{reason}")
    # Large existing artifacts may be repacked in place during this pass and
    # retain their filesystem mtime.  The manifest's SHA256 is the freshness
    # binding for that payload; the feedback, acceptance, manifest, and stable
    # delivery records above/below are the records that must be rewritten now.
    version = str(payload.get("artifact_version") or "").strip()
    if not version:
        errors.append("artifact_version_missing")
    elif artifact is not None and version not in artifact.name:
        errors.append("artifact_version_not_in_filename")
    acceptance, reason = _owned_file(payload.get("acceptance_evidence_path"), root)
    if reason:
        errors.append(f"acceptance_{reason}")
    _require_fresh(acceptance, "acceptance", freshness_floor, errors)
    if payload.get("acceptance_status") != "PASS":
        errors.append("acceptance_status_not_pass")
    acceptance_payload: dict[str, Any] = {}
    if acceptance is not None:
        try:
            loaded = json.loads(acceptance.read_text(encoding="utf-8"))
            acceptance_payload = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            errors.append("acceptance_evidence_invalid_json")
    if acceptance_payload.get("status") != "PASS":
        errors.append("acceptance_evidence_status_not_pass")
    acceptance_delta = acceptance_payload.get("acceptance_delta")
    if not isinstance(acceptance_delta, list) or not any(isinstance(item, str) and item.strip() for item in acceptance_delta):
        errors.append("acceptance_evidence_delta_empty")
    delta = payload.get("acceptance_delta")
    if not isinstance(delta, list) or not any(isinstance(item, str) and item.strip() for item in delta):
        errors.append("acceptance_delta_empty")
    elif acceptance_delta != delta:
        errors.append("acceptance_delta_manifest_mismatch")
    version_number = _version_number(version)
    if version_number is None:
        errors.append("artifact_version_not_vN")
    state_path = root / "state.json"
    current_version = ""
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                current_version = str(
                    state.get("current_version")
                    or state.get("latest_artifact_version")
                    or state.get("artifact_version")
                    or ""
                )
        except (OSError, json.JSONDecodeError):
            errors.append("project_state_invalid_json")
    current_number = _version_number(current_version) if current_version else None
    if (
        current_number is not None
        and version_number is not None
        and version_number <= current_number
        and not (allow_current_version and version_number == current_number)
    ):
        errors.append("artifact_version_not_newer_than_project_state")
    package_hash = str(payload.get("package_sha256") or "")
    if artifact is None or not re.fullmatch(r"[0-9a-f]{64}", package_hash) or _sha256(artifact) != package_hash:
        errors.append("package_sha256_mismatch")
    for candidate in (requirements, artifact, acceptance):
        if candidate is not None and "downloads" in str(candidate).casefold():
            errors.append("downloads_path_forbidden")

    if require_delivery_evidence:
        evidence = Path(delivery_evidence_path).expanduser()
        if not evidence.is_file() or evidence.stat().st_size == 0:
            errors.append("delivery_evidence_missing_or_empty")
        else:
            _require_fresh(evidence, "delivery_evidence", freshness_floor, errors)
            try:
                evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                evidence_payload = {}
                errors.append("delivery_evidence_invalid")
            if not isinstance(evidence_payload, dict):
                evidence_payload = {}
                errors.append("delivery_evidence_not_object")
            for key in ("artifact_path", "artifact_version", "acceptance_evidence_path", "acceptance_status", "package_sha256", "acceptance_delta"):
                if evidence_payload.get(key) != payload.get(key):
                    errors.append(f"delivery_evidence_{key}_mismatch")
            if evidence_payload.get("status") not in (None, "ok"):
                errors.append("delivery_evidence_status_not_ok")
    return not errors, errors


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--delivery-evidence", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--min-mtime", type=float, default=0)
    args = parser.parse_args()
    ok, errors = validate_paid_work(args.project_root, args.delivery_evidence, args.manifest, args.min_mtime)
    print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
