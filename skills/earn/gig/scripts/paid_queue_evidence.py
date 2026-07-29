"""Deterministic post-send proof gate for browser delivery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


_FORMAL_CHECKBOX_KEYS = ("formal_delivery_checkbox", "formal_delivery_control_checked")


def _formal_checkbox(live_dom: Any) -> tuple[bool, Any]:
    """Read the rendered formal-delivery control, never a model-only claim."""
    if not isinstance(live_dom, dict):
        return False, None
    for key in _FORMAL_CHECKBOX_KEYS:
        if key in live_dom:
            return True, live_dom[key]
    return False, None


def _live_dom_url(live_dom: Any) -> tuple[str, str | None]:
    """Read canonical ``url``; accept ``talkroom_url`` only for legacy recovery."""
    if not isinstance(live_dom, dict):
        return "", None
    canonical = str(live_dom.get("url") or "").strip()
    legacy = str(live_dom.get("talkroom_url") or "").strip()
    if canonical and legacy and canonical != legacy:
        return "", "post_send_url_fields_conflict"
    return canonical or legacy, None


def validate_paid_queue(
    evidence_dir: str | Path,
    expected_item: dict[str, Any] | None = None,
    min_mtime: float = 0,
) -> tuple[bool, list[str]]:
    root = Path(evidence_dir).expanduser().resolve()
    manifest_path = root / "paid-queue-evidence.json"
    errors: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
        errors.append("paid_queue_manifest_missing_or_invalid")
    if manifest_path.is_file() and min_mtime and manifest_path.stat().st_mtime < min_mtime:
        errors.append("paid_queue_manifest_stale")
    if not isinstance(payload, dict):
        payload = {}
        errors.append("paid_queue_manifest_not_object")
    answer_mode = payload.get("mode") == "answer"
    observe_only = bool(isinstance(expected_item, dict) and expected_item.get("delivery_action") == "none")
    if observe_only:
        if payload.get("observed") is not True:
            errors.append("paid_queue_observation_not_observed")
    elif payload.get("sent") is not True:
        errors.append("paid_queue_send_not_observed")
    # The outer field is a useful duplicate for new sends, but the fresh DOM is
    # authoritative.  Runs17 omitted this duplicate while the DOM proved it was
    # off; do not reject that safe, recoverable evidence.  A present true value
    # remains fail-closed.
    if "formal_delivery_checkbox" in payload and payload.get("formal_delivery_checkbox") is not False:
        errors.append("formal_delivery_checkbox_not_off")
    if not str(payload.get("captured_at") or "").strip():
        errors.append("post_send_capture_time_missing")
    screenshot = Path(str(payload.get("screenshot_path") or "")).expanduser()
    live_dom_path = Path(str(payload.get("live_dom_path") or "")).expanduser()
    for name, path in (("screenshot", screenshot), ("live_dom", live_dom_path)):
        try:
            path.resolve().relative_to(root)
        except ValueError:
            errors.append(f"{name}_outside_evidence_dir")
            continue
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"{name}_missing_or_empty")
        elif min_mtime and path.stat().st_mtime < min_mtime:
            errors.append(f"{name}_stale")
    try:
        live_dom: Any = json.loads(live_dom_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        live_dom = {}
        errors.append("post_send_live_dom_invalid")
    live_dom_url, live_dom_url_error = _live_dom_url(live_dom)
    if live_dom_url_error:
        errors.append(live_dom_url_error)
    if not live_dom_url.startswith("https://"):
        errors.append("post_send_live_dom_url_missing")
    if not isinstance(live_dom, dict) or (not observe_only and live_dom.get("sent") is not True):
        errors.append("post_send_live_dom_send_not_observed")
    if answer_mode and live_dom.get("mode") != "answer":
        errors.append("post_send_answer_mode_missing")
    formal_present, formal_value = _formal_checkbox(live_dom)
    if not formal_present:
        errors.append("formal_delivery_checkbox_missing")
    elif formal_value is True:
        errors.append("formal_delivery_checkbox_on")
    elif formal_value is not False:
        errors.append("formal_delivery_checkbox_not_off")
    artifact_version = str(payload.get("artifact_version") or "")
    package_hash = str(payload.get("package_sha256") or "")
    delta = payload.get("acceptance_delta")
    if not observe_only and not answer_mode:
        if not artifact_version.strip():
            errors.append("sent_artifact_version_missing")
        if not package_hash.strip():
            errors.append("sent_package_hash_missing")
        if not isinstance(delta, list) or not any(isinstance(item, str) and item.strip() for item in delta):
            errors.append("sent_acceptance_delta_empty")
    expected_url = str(payload.get("expected_url") or "")
    expected_talkroom_id = str(payload.get("talkroom_id") or "")
    expected_evidence = expected_item.get("delivery_evidence") if isinstance(expected_item, dict) else None
    if not isinstance(expected_evidence, dict):
        expected_evidence = {}
    if expected_item:
        expected_talkroom_id = str(expected_item.get("talkroom_id") or expected_talkroom_id)
        expected_url = str(expected_item.get("marketplace_url") or expected_item.get("talkroom_url") or expected_url)
        if not expected_url and expected_talkroom_id:
            expected_url = f"https://coconala.com/talkrooms/{expected_talkroom_id}"
    if expected_url and live_dom_url != expected_url:
        errors.append("post_send_url_not_bound_to_queue")
    if expected_talkroom_id and str(payload.get("talkroom_id") or "") != expected_talkroom_id:
        errors.append("post_send_talkroom_not_bound_to_queue")
    attachment = live_dom.get("latest_seller_attachment") if isinstance(live_dom, dict) else None
    artifact_basename = str(payload.get("artifact_basename") or "")
    expected_artifact = Path(str(expected_evidence.get("artifact_path") or "")).name
    expected_artifact_path = Path(str(expected_evidence.get("artifact_path") or "")).expanduser()
    expected_version = str(expected_evidence.get("artifact_version") or "")
    expected_hash = str(expected_evidence.get("package_sha256") or "")
    expected_delta = expected_evidence.get("acceptance_delta")
    if not observe_only and not answer_mode and expected_artifact and artifact_basename != expected_artifact:
        errors.append("sent_artifact_not_bound_to_queue_manifest")
    if not observe_only and not answer_mode and expected_version and artifact_version != expected_version:
        errors.append("sent_version_not_bound_to_queue_manifest")
    if not observe_only and not answer_mode and expected_hash and package_hash != expected_hash:
        errors.append("sent_hash_not_bound_to_queue_manifest")
    if not observe_only and not answer_mode and expected_delta and delta != expected_delta:
        errors.append("sent_delta_not_bound_to_queue_manifest")
    if observe_only:
        return not errors, errors
    if answer_mode:
        message_hash = str(payload.get("message_sha256") or "")
        seller_message = str(live_dom.get("latest_seller_message") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", message_hash):
            errors.append("paid_answer_message_hash_invalid")
        if not seller_message.strip():
            errors.append("paid_answer_seller_message_missing")
        elif hashlib.sha256(seller_message.encode("utf-8")).hexdigest() != message_hash:
            errors.append("paid_answer_message_hash_mismatch")
        return not errors, errors
    if not isinstance(attachment, dict):
        errors.append("latest_seller_attachment_missing")
    else:
        if artifact_basename and attachment.get("filename") != artifact_basename:
            errors.append("latest_seller_attachment_filename_mismatch")
        try:
            attachment_size = int(attachment.get("size_bytes"))
            if attachment_size <= 0:
                raise ValueError
        except (TypeError, ValueError):
            attachment_size = 0
            errors.append("latest_seller_attachment_size_missing")
        if expected_artifact_path.is_file() and attachment_size != expected_artifact_path.stat().st_size:
            errors.append("latest_seller_attachment_size_mismatch")
        message = str(attachment.get("message") or live_dom.get("message") or "")
        if artifact_version and artifact_version not in message:
            errors.append("latest_seller_message_version_missing")
        if package_hash and package_hash not in message:
            errors.append("latest_seller_message_hash_missing")
    return not errors, errors


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--queue-item", type=Path)
    parser.add_argument("--min-mtime", type=float, default=0)
    args = parser.parse_args()
    expected = json.loads(args.queue_item.read_text(encoding="utf-8")) if args.queue_item else None
    ok, errors = validate_paid_queue(args.evidence_dir, expected, args.min_mtime)
    print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
