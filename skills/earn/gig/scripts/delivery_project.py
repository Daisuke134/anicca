"""Bridge queue selection to a generic, stable marketplace project ledger."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_ledger
import delivery_identity


def project_identity(item: dict[str, Any]) -> str:
    """Return the most stable marketplace identity available for the ledger."""
    return delivery_identity.stable_identity(item)


def record_queue_selection(base: str | Path, item: dict[str, Any], *, adapter: str) -> Path:
    request_id = project_identity(item)
    root = Path(base) / request_id
    observed = {
        "buyer": item.get("buyer"),
        "delivery_date": item.get("delivery_date"),
        "talkroom_id": item.get("talkroom_id"),
        "source_contract_id": item.get("contract_id"),
        "queue_class": item.get("queue_class"),
        "talkroom_state": item.get("talkroom_state"),
        "buyer_visible_artifact_observed": item.get("buyer_visible_artifact_observed") is True,
        "buyer_feedback_pending_artifact": item.get("buyer_feedback_pending_artifact") is True,
        "buyer_agreement_observed": item.get("buyer_agreement_observed") is True,
        "buyer_reply_after_artifact_observed": item.get("buyer_reply_after_artifact_observed") is True,
    }
    # Queue polling is an observation.  Only a positive numeric observation may
    # populate/update the durable contract price; absent or ambiguous DOM data
    # must never erase a previously recorded amount.
    price = item.get("price_jpy")
    if isinstance(price, (int, float)) and not isinstance(price, bool) and price > 0:
        observed["price_jpy"] = int(price)
    if (root / "state.json").exists():
        # Queue polling is an observation.  It must not overwrite durable
        # workflow state such as await_buyer_approval_for_publication.
        project_ledger.append(root, observed, "queue_selected")
        return root
    project_ledger.init_project(base, request_id, adapter, {**observed, "next_action": "delivery_evidence"})
    project_ledger.append(root, {"next_action": "delivery_evidence"}, "queue_selected")
    return root


def _same_path(left: Any, right: Any) -> bool:
    try:
        return Path(str(left or "")).expanduser().resolve() == Path(str(right or "")).expanduser().resolve()
    except OSError:
        return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_accepted_artifact(
    root: Path, item: dict[str, Any],
) -> tuple[dict[str, Any], Path] | None:
    evidence = item.get("delivery_evidence")
    if not isinstance(evidence, dict) or evidence.get("present") is not True or evidence.get("status") != "ok":
        return None
    evidence_path = Path(str(evidence.get("path") or "")).expanduser().resolve()
    try:
        stable = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(stable, dict) or stable.get("status") != "ok":
        return None
    for key in (
        "project_root", "artifact_path", "artifact_version", "acceptance_evidence_path",
        "acceptance_status", "acceptance_delta", "package_sha256",
    ):
        left = stable.get(key)
        right = evidence.get(key)
        if key.endswith("_path") or key == "project_root":
            if not _same_path(left, right):
                return None
        elif left != right:
            return None
    if not _same_path(stable.get("project_root"), root):
        return None
    try:
        artifact = Path(str(stable["artifact_path"])).expanduser().resolve()
        artifact.relative_to(root)
        acceptance = Path(str(stable["acceptance_evidence_path"])).expanduser().resolve()
        acceptance.relative_to(root)
    except (KeyError, OSError, ValueError):
        return None
    package_hash = str(stable.get("package_sha256") or "")
    version = str(stable.get("artifact_version") or "")
    if (
        stable.get("acceptance_status") != "PASS"
        or not acceptance.is_file()
        or not artifact.is_file()
        or not version
        or version not in artifact.name
        or not re.fullmatch(r"[0-9a-f]{64}", package_hash)
    ):
        return None
    try:
        if _sha256_file(artifact) != package_hash:
            return None
    except OSError:
        return None
    feedback_path = Path(
        str(item.get("buyer_feedback_requirements_path") or "")
    ).expanduser().resolve()
    try:
        feedback_path.relative_to(root / "requirements")
        stable_requirements = Path(
            str(stable.get("requirements_path") or "")
        ).expanduser().resolve()
        stable_requirements.relative_to(root / "requirements")
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        observed_at = datetime.fromisoformat(str(feedback["observed_at"]))
        if (
            observed_at.tzinfo is None
            or feedback.get("feedback_sha256") != item.get("buyer_feedback_sha256")
            or not stable_requirements.is_file()
            or artifact.stat().st_mtime < observed_at.timestamp()
            or acceptance.stat().st_mtime < observed_at.timestamp()
            or stable_requirements.stat().st_mtime < observed_at.timestamp()
        ):
            return None
    except (KeyError, OSError, ValueError, json.JSONDecodeError):
        return None
    return stable, evidence_path


def _state_bound_accepted_artifact(
    state: dict[str, Any], item: dict[str, Any], root: Path, *,
    verify_files: bool = True,
) -> bool:
    """Verify the accepted artifact already bound into durable project state."""
    evidence = item.get("delivery_evidence")
    if not isinstance(evidence, dict) or evidence.get("present") is not True or evidence.get("status") != "ok":
        return False
    evidence_path = Path(str(evidence.get("path") or "")).expanduser()
    try:
        stable = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(stable, dict) or stable.get("status") != "ok":
        return False
    for key in (
        "project_root", "artifact_version", "acceptance_status", "package_sha256", "acceptance_delta",
    ):
        if stable.get(key) != evidence.get(key):
            return False
    for key in ("artifact_path", "acceptance_evidence_path"):
        if not _same_path(stable.get(key), evidence.get(key)):
            return False
    if evidence.get("project_root") and not _same_path(evidence.get("project_root"), root):
        return False
    bindings = (
        ("current_version", "artifact_version"),
        ("current_artifact_path", "artifact_path"),
        ("current_package_sha256", "package_sha256"),
        ("current_acceptance_evidence_path", "acceptance_evidence_path"),
        ("current_acceptance_status", "acceptance_status"),
        ("current_acceptance_delta", "acceptance_delta"),
    )
    for state_key, evidence_key in bindings:
        if state_key.endswith("_path"):
            if not _same_path(state.get(state_key), evidence.get(evidence_key)):
                return False
        elif state.get(state_key) != evidence.get(evidence_key):
            return False
    if not _same_path(state.get("current_delivery_evidence_path"), evidence_path):
        return False
    try:
        if evidence_path.stat().st_mtime < float(state.get("current_delivery_evidence_mtime")):
            return False
    except (OSError, TypeError, ValueError):
        return False
    if not verify_files:
        return True
    try:
        artifact = Path(str(stable["artifact_path"])).expanduser().resolve()
        artifact.relative_to(root)
        acceptance = Path(str(stable["acceptance_evidence_path"])).expanduser().resolve()
        acceptance.relative_to(root)
    except (KeyError, OSError, ValueError):
        return False
    package_hash = str(stable.get("package_sha256") or "")
    version = str(stable.get("artifact_version") or "")
    if (
        stable.get("acceptance_status") != "PASS"
        or not acceptance.is_file()
        or not artifact.is_file()
        or not version
        or version not in artifact.name
        or not re.fullmatch(r"[0-9a-f]{64}", package_hash)
    ):
        return False
    try:
        return _sha256_file(artifact) == package_hash
    except OSError:
        return False


def _pending_browser_delivery_is_bound(state: dict[str, Any], item: dict[str, Any], root: Path) -> bool:
    """Return true only for a durable, stable-evidence-bound retry bundle."""
    if (
        state.get("buyer_visible") is not False
        or state.get("artifact_ready_pending_browser") is not True
        or state.get("next_action") != "retry_buyer_visible_delivery"
    ):
        return False
    if not _state_bound_accepted_artifact(state, item, root, verify_files=False):
        return False
    return True


def workflow_action(root: str | Path, item: dict[str, Any]) -> str:
    """Map durable buyer-wait state plus fresh live DOM to act/await_buyer."""
    state_path = Path(root) / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "act"
    if _pending_browser_delivery_is_bound(state, item, Path(root).expanduser().resolve()):
        return "deliver_existing"
    next_action = str(state.get("next_action") or "")
    awaiting_buyer = next_action.startswith("await_buyer_")
    if not awaiting_buyer or state.get("buyer_visible") is not True:
        return "act"
    if item.get("buyer_feedback_pending_artifact") is True:
        return "act"
    if item.get("buyer_agreement_observed") is True:
        return "act"
    if item.get("buyer_reply_after_artifact_observed") is True:
        return "act"
    if (
        item.get("buyer_visible_artifact_observed") is True
        and item.get("talkroom_state") == "取引中"
        and item.get("formal_delivery_observed") is not True
    ):
        # Dais ruling 2026-07-25: formal-eligible work is OUR pending action,
        # never a reason to wait for the buyer.
        if item.get("delivery_action") == "formal":
            return "act"
        return "await_buyer"
    return "act"


def resolve_workflow_action(root: str | Path, item: dict[str, Any]) -> str:
    """Reconcile an accepted artifact before deciding whether a model is needed."""
    project_root = Path(root).expanduser().resolve()
    state_path = project_root / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "act"
    feedback_hash = str(item.get("buyer_feedback_sha256") or "")
    handled_hash = str(state.get("handled_buyer_feedback_sha256") or "")
    if handled_hash and feedback_hash and handled_hash != feedback_hash:
        return "act"
    # A verified text answer is a completed response to this exact buyer event.
    # Artifact visibility can legitimately remain false when the buyer is asking
    # about a broken confirmation UI. Falling through to artifact reconciliation
    # would resend the old attachment (or rebuild) despite the answer already
    # being visible in the talkroom.
    answered_feedback = (
        re.fullmatch(r"[0-9a-f]{64}", feedback_hash)
        and handled_hash == feedback_hash
        and state.get("material_event_outcome") == "buyer_answer_sent"
        and re.fullmatch(r"[0-9a-f]{64}", str(state.get("last_buyer_answer_sha256") or ""))
    )
    requires_existing_delivery = (
        item.get("delivery_action") == "progress"
        and item.get("buyer_feedback_pending_artifact") is True
        and item.get("buyer_visible_artifact_observed") is not True
    )
    if answered_feedback:
        if not requires_existing_delivery:
            return "await_buyer"
        if _state_bound_accepted_artifact(state, item, project_root):
            patch = {
                "buyer_visible": False,
                "artifact_ready_pending_browser": True,
                "next_action": "retry_buyer_visible_delivery",
            }
            if not all(state.get(key) == value for key, value in patch.items()):
                project_ledger.append(
                    project_root, patch, "answered_feedback_existing_artifact_requeued",
                )
            return "deliver_existing"
    if not re.fullmatch(r"[0-9a-f]{64}", feedback_hash):
        return workflow_action(project_root, item)
    accepted = _validated_accepted_artifact(project_root, item)
    if accepted is None:
        return "act"
    stable, evidence_path = accepted
    package_hash = str(stable["package_sha256"])
    buyer_visible = (
        item.get("buyer_visible_artifact_observed") is True
        and (
            state.get("latest_buyer_visible_package_sha256") == package_hash
            or state.get("buyer_visible") is True
        )
    )
    try:
        evidence_mtime = evidence_path.stat().st_mtime
    except OSError:
        return "act"
    patch = {
        "current_version": str(stable["artifact_version"]),
        "current_artifact_path": str(Path(str(stable["artifact_path"])).expanduser().resolve()),
        "current_package_sha256": package_hash,
        "current_acceptance_evidence_path": str(
            Path(str(stable["acceptance_evidence_path"])).expanduser().resolve()
        ),
        "current_acceptance_status": "PASS",
        "current_acceptance_delta": stable["acceptance_delta"],
        "current_delivery_evidence_path": str(evidence_path),
        "current_delivery_evidence_mtime": evidence_mtime,
        "handled_buyer_feedback_sha256": feedback_hash,
        "material_event_outcome": "accepted_artifact_reconciled",
        "buyer_visible": buyer_visible,
        "artifact_ready_pending_browser": not buyer_visible,
        "next_action": "await_buyer_feedback" if buyer_visible else "retry_buyer_visible_delivery",
    }
    if not all(state.get(key) == value for key, value in patch.items()):
        project_ledger.append(project_root, patch, "feedback_idempotency_bootstrapped")
    return "await_buyer" if buyer_visible else "deliver_existing"
