#!/usr/bin/env python3
"""Recover verified paid remote answers through existing delivery boundaries."""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0, str(HERE))
from gig_paths import BROWSER_DIR, REPO_ROOT, RUNNER_DIR  # noqa: E402
REPO = REPO_ROOT
import delivery_project  # noqa: E402
import delivery_queue  # noqa: E402
import paid_work_evidence  # noqa: E402
import paid_remote_result  # noqa: E402
import reconcile_paid_delivery  # noqa: E402
import step_result_status  # noqa: E402
from telegram_outbox import TelegramOutbox, dispatch_one  # noqa: E402
from telegram_report import OpenClawTelegramTransport  # noqa: E402

DEFAULT_TELEGRAM_DATABASE = Path.home() / "gig" / "telegram-outbox.sqlite3"
DEFAULT_TELEGRAM_RECEIPTS = Path.home() / "gig" / "telegram-delivery-receipts"
PAID_DECISION_SCHEMA_VERSION = 3
PAID_DECISION_PROMPT_VERSION = "paid-semantic-decision-v6"
PAID_DECISION_MODEL = "gpt-5.6-sol"
PAID_FILE_MODEL = "gpt-5.6-sol"
PAID_FILE_POLICY_VERSION = "paid-file-build-review-v17"
PAID_SOURCE_CENSUS_VERSION = "paid-source-census-v4"
PAID_SOURCE_CENSUS_SKILLS = ("music-score-omr",)
PAID_FILE_OPERATOR_POLICY = "paid-file-operator-policy.json"
PAID_DECISION_FIELDS = frozenset((
    "decision", "mode", "feedback_sha256", "requirements_sha256",
    "latest_message_identity", "required_output", "required_effect", "delivery_stage",
    "formal_approval_evidence", "unresolved",
))

class Failure(RuntimeError):
    def __init__(self, step: str): self.step = step

def _load(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)

def _text(value: Any) -> str: return str(value or "").strip()

def _comparison_key(value: str) -> str: return " ".join(value.split())

def _run(command: list[str], step: str) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode: raise Failure(step)
    return result.stdout

def _json_line(stdout: str, step: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        try: value = json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(value, dict): return value
    raise Failure(step)

def _collector(args, mode, output, evidence, item_path=None, item=None):
    command = [sys.executable, str(args.collector), "--output", str(output), "--evidence-dir", str(evidence),
               "--mode", mode, "--projects-root", str(args.projects_root), "--cdp-helper", str(args.cdp_helper)]
    if mode == "selected-talkroom-only":
        room = _text((item or {}).get("talkroom_id"))
        if not item_path or not re.fullmatch(r"[0-9]+", room): raise Failure("remote_resume")
        command += ["--talkroom-id", room, "--project-id", delivery_project.resolve_project_root(args.projects_root, item).name,
                    "--selected-order-input", str(item_path)]
    return command

def _row(snapshot: dict[str, Any], room: str) -> dict[str, Any]:
    for value in snapshot.get("orders", []):
        if isinstance(value, dict) and _text(value.get("talkroom_id")) == room:
            talkroom = snapshot.get("talkroom")
            return {**talkroom, **value} if isinstance(talkroom, dict) else value
    talkroom = snapshot.get("talkroom")
    if isinstance(talkroom, dict) and _text(talkroom.get("talkroom_id")) == room: return talkroom
    raise Failure("remote_resume")

def _seller_last(row: dict[str, Any]) -> str:
    values = [row.get(key) for key in ("seller_last_message", "latest_seller_message", "last_seller_message")]
    values += row.get("seller_sent_messages") or row.get("seller_messages") or []
    for value in reversed(values):
        value = value.get("text") if isinstance(value, dict) else value
        if isinstance(value, str) and value.strip(): return value.strip()
    return ""


def _seller_last_sha256(row: dict[str, Any]) -> str:
    values = row.get("seller_sent_messages") or row.get("seller_messages") or []
    for value in reversed(values):
        if isinstance(value, dict) and re.fullmatch(r"[0-9a-f]{64}", _text(value.get("text_sha256"))):
            return _text(value.get("text_sha256"))
    message = _seller_last(row)
    return hashlib.sha256(_comparison_key(message).encode()).hexdigest() if message else ""


def _seller_message_with_attachment(row: dict[str, Any], message: str, filename: str) -> bool:
    expected = _comparison_key(message)
    expected_sha256 = hashlib.sha256(expected.encode()).hexdigest()
    for value in reversed(row.get("seller_sent_messages") or row.get("seller_messages") or []):
        if (isinstance(value, dict)
                and (_text(value.get("text_sha256")) == expected_sha256
                     or _comparison_key(_text(value.get("text"))) == expected)
                and filename in (value.get("attachments") or [])):
            return True
    return False


def _validated_customer_attachment(root: Path, value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"path", "filename", "sha256"}:
        raise ValueError("invalid customer attachment")
    raw = Path(_text(value.get("path")))
    filename, digest = _text(value.get("filename")), _text(value.get("sha256"))
    if (raw.is_symlink() or not _regular_file(raw) or Path(filename).name != filename
            or raw.name != filename or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        raise ValueError("invalid customer attachment")
    evidence_raw = root / "evidence"
    if evidence_raw.is_symlink() or not evidence_raw.is_dir():
        raise ValueError("invalid customer attachment root")
    path = raw.resolve(); evidence = evidence_raw.resolve()
    path.relative_to(evidence)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("customer attachment hash mismatch")
    return {"path": str(path), "filename": filename, "sha256": digest}


def _reported_remote_cycle(args, item: dict[str, Any]) -> Path | None:
    """Recognize a verified remote cycle already reported in the official room."""
    try:
        root = _paid_project_root(args, item)
        feedback = _text(item.get("buyer_feedback_sha256"))
        answer = _load(root / "delivery" / "paid-answer.json")
        if _answer_ready(root, item):
            _validate_consultation_authorization(root, feedback)
            message = _text(answer.get("message"))
            formal = item.get("formal_delivery_observed", item.get("formal_delivery_confirmed"))
            if (message and _seller_last_sha256(item) == hashlib.sha256(_comparison_key(message).encode()).hexdigest()
                    and formal is False
                    and _text(item.get("talkroom_state", item.get("transaction_state")))):
                return root
            return None
        result = _load(root / "delivery" / "paid-remote-result.json")
        message = _text(answer.get("message"))
        attachment = _validated_customer_attachment(root, result.get("customer_attachment"))
        seller_match = (_seller_message_with_attachment(item, message, attachment["filename"])
                        if attachment else
                        _seller_last_sha256(item) == hashlib.sha256(_comparison_key(message).encode()).hexdigest())
        formal = item.get("formal_delivery_observed", item.get("formal_delivery_confirmed"))
        if (result.get("status") == "ok" and result.get("verified_after") is True
                and result.get("buyer_feedback_sha256") == feedback
                and _comparison_key(_text(result.get("customer_message"))) == _comparison_key(message)
                and message and seller_match
                and formal is False
                and _text(item.get("talkroom_state", item.get("transaction_state")))):
            return root
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
        pass
    return None


def _reported_file_progress_cycle(args, item: dict[str, Any]) -> Path | None:
    """Recognize a reconciled review-stage file send without resending it."""
    try:
        root = _paid_project_root(args, item)
        manifest, snapshots = _file_bundle_snapshots(root, validate_source_census=False)
        receipt = _load(root / "context" / "paid-file-authorization.json")
        feedback = _text(item.get("buyer_feedback_sha256")) or _text(receipt.get("buyer_feedback_sha256"))
        requirements_sha256 = paid_remote_result.requirements_digest(root, feedback)
        if receipt.get("version") == 2:
            stable = delivery_queue.evidence_path(args.delivery_evidence_dir, item)
            _validate_file_authorization(root, stable, feedback, requirements_sha256)
        else:
            # Migration-only reconciliation: an already buyer-visible v1 send may
            # be recognized, but this receipt is never accepted by the writer.
            owner = root / "evidence" / "agent-PAID_FILE_OWNER"
            summary = _runner_summary(owner)
            result_path = _consultation_result_path(owner, summary)
            result = _load(result_path)
            if (not isinstance(receipt, dict) or receipt.get("version") != 1
                    or receipt.get("buyer_feedback_sha256") != feedback
                    or receipt.get("requirements_sha256") != requirements_sha256
                    or receipt.get("manifest_sha256") != snapshots["manifest"][1]
                    or receipt.get("artifact_sha256") != snapshots["artifact"][1]
                    or receipt.get("acceptance_sha256") != snapshots["acceptance"][1]
                    or receipt.get("owner_summary_sha256") != hashlib.sha256((owner / "summary.json").read_bytes()).hexdigest()
                    or receipt.get("owner_result_sha256") != hashlib.sha256(result_path.read_bytes()).hexdigest()
                    or result.get("status") != "ok"):
                return None
        state = _load(root / "state.json")
        artifact = Path(_text(manifest.get("artifact_path"))).resolve()
        artifact.relative_to(root.resolve())
        messages = item.get("seller_sent_messages") or item.get("seller_messages") or []
        latest = messages[-1] if isinstance(messages, list) and messages else None
        if (not isinstance(latest, dict) or artifact.name not in (latest.get("attachments") or [])
                or item.get("buyer_reply_after_artifact_observed") is True
                or item.get("formal_delivery_observed", item.get("formal_delivery_confirmed")) is not False
                or not _text(item.get("talkroom_state", item.get("transaction_state")))
                or state.get("handled_buyer_feedback_sha256") != feedback
                or state.get("delivery_confirmed_feedback_sha256") != feedback
                or state.get("current_version") != manifest.get("artifact_version")
                or state.get("latest_buyer_visible_version") != manifest.get("artifact_version")
                or state.get("current_package_sha256") != manifest.get("package_sha256")
                or state.get("work_state") != "DELIVERED"
                or state.get("next_action") != "await_buyer_feedback"
                or not _regular_file(artifact)
                or hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest.get("package_sha256")):
            return None
        return root
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
        return None


def _reported_handoff_cycle(args, item: dict[str, Any]) -> Path | None:
    """Trust an explicit out-of-loop handoff only while live seller-last still matches."""
    try:
        root = _paid_project_root(args, item)
        receipt_path = root / "delivery" / "paid-external-handoff.json"
        if receipt_path.is_symlink() or not _regular_file(receipt_path):
            return None
        receipt = _load(receipt_path)
        room = _text(item.get("talkroom_id"))
        feedback = _text(item.get("buyer_feedback_sha256"))
        message_sha256 = _text(receipt.get("message_sha256"))
        if (receipt.get("version") != 1 or receipt.get("status") != "awaiting_buyer"
                or _text(receipt.get("talkroom_id")) != room
                or _text(receipt.get("buyer_feedback_sha256")) != feedback
                or not re.fullmatch(r"[0-9a-f]{64}", message_sha256)
                or _seller_last_sha256(item) != message_sha256
                or item.get("formal_delivery_observed", item.get("formal_delivery_confirmed")) is not False
                or not _text(item.get("talkroom_state", item.get("transaction_state")))):
            return None
        evidence_root = (root / "evidence").resolve()
        official = Path(_text(receipt.get("official_readback"))).resolve()
        official.relative_to(evidence_root)
        if (official.is_symlink() or not _regular_file(official)
                or hashlib.sha256(official.read_bytes()).hexdigest()
                != _text(receipt.get("official_readback_sha256"))):
            return None
        official_row = _row(_load(official), room)
        if (_text(official_row.get("buyer_feedback_sha256")) != feedback
                or _seller_last_sha256(official_row) != message_sha256
                or official_row.get("formal_delivery_observed",
                                    official_row.get("formal_delivery_confirmed")) is not False):
            return None
        work_evidence = receipt.get("work_evidence")
        if not isinstance(work_evidence, list):
            return None
        for proof in work_evidence:
            if not isinstance(proof, dict) or set(proof) != {"path", "sha256"}:
                return None
            path = Path(_text(proof.get("path"))).resolve()
            path.relative_to(evidence_root)
            if (path.is_symlink() or not _regular_file(path)
                    or hashlib.sha256(path.read_bytes()).hexdigest() != _text(proof.get("sha256"))):
                return None
        return root
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
        return None

def _reported_formal_cycle(args, item: dict[str, Any]) -> Path | None:
    """Close only an official formal delivery backed by the same project artifact."""
    try:
        state = _text(item.get("talkroom_state", item.get("transaction_state")))
        formal = item.get("formal_delivery_observed", item.get("formal_delivery_confirmed"))
        if (formal is not True or state not in {"納品確認待ち", "取引完了"}
                or item.get("buyer_feedback_pending_artifact") is True):
            return None
        talkroom_identity = {key: value for key, value in item.items() if key not in {"request_id", "project_id"}}
        candidate = delivery_project.resolve_project_root(args.projects_root, talkroom_identity)
        if candidate.is_symlink():
            return None
        root = candidate.resolve()
        root.relative_to(args.projects_root.resolve())
        if not root.is_dir():
            return None
        attachments: set[str] = set()
        for message in item.get("seller_sent_messages") or item.get("seller_messages") or []:
            if not isinstance(message, dict):
                continue
            attachments.update(value for value in message.get("attachments") or []
                               if isinstance(value, str) and value and Path(value).name == value)
        ledgers = [root / "events.jsonl", *root.rglob("formal-delivery-ledger.jsonl")]
        for ledger in ledgers:
            if ledger.is_symlink() or not _regular_file(ledger):
                continue
            for line in ledger.read_text(encoding="utf-8").splitlines():
                try: record = json.loads(line)
                except json.JSONDecodeError: continue
                if (not isinstance(record, dict) or record.get("event") != "FORMAL_DELIVERY_CONFIRMED"
                        or _text(record.get("project_id")) != root.name
                        or _text(record.get("talkroom_id")) != _text(item.get("talkroom_id"))
                        or _text(record.get("seller_attachment_readback")) not in attachments):
                    continue
                artifact = Path(_text(record.get("artifact_path")))
                if artifact.is_symlink() or not _regular_file(artifact):
                    continue
                resolved = artifact.resolve()
                resolved.relative_to(root)
                content = resolved.read_bytes()
                if (resolved.name == record.get("seller_attachment_readback")
                        and len(content) == record.get("artifact_bytes")
                        and hashlib.sha256(content).hexdigest() == record.get("artifact_sha256")):
                    return root
    except (OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
        pass
    return None

def observe_orders(args, evidence_dir) -> list[dict[str, Any]]:
    snapshot = evidence_dir / "orders-only-snapshot.json"
    _run(_collector(args, "orders-only", snapshot, evidence_dir), "orders_observation")
    try: queue = delivery_queue.build_preliminary(_load(snapshot), date.fromisoformat(args.today))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error: raise Failure("orders_observation") from error
    return [dict(item) for item in queue.get("items", []) if isinstance(item, dict) and item.get("terminal") is not True
            and _text(item.get("talkroom_state")) not in {"取引完了", "completed", "closed", "terminal"}]

def _regular_file(path: Path) -> bool:
    try: return stat.S_ISREG(path.lstat().st_mode)
    except OSError: return False

def _runner_summary(managed: Path) -> dict[str, Any]:
    managed = managed.resolve()
    summary_path = managed / "summary.json"
    if not _regular_file(summary_path): raise ValueError("invalid verifier summary")
    summary = _load(summary_path)
    raw_result = summary.get("result_path") if isinstance(summary, dict) else None
    if not isinstance(raw_result, str) or not raw_result.strip(): raise ValueError("invalid verifier result path")
    result_candidate = managed / raw_result if not Path(raw_result).is_absolute() else Path(raw_result)
    if result_candidate.is_symlink() or not _regular_file(result_candidate): raise ValueError("invalid verifier result file")
    result_path = result_candidate.resolve()
    if result_path.parent != managed: raise ValueError("invalid verifier result file")
    return summary


def _official_content_sha256(row: dict[str, Any]) -> str:
    canonical = {
        "side": row.get("side"),
        "sent_at": row.get("sent_at"),
        "text": str(row.get("text") or ""),
        "attachments": row.get("attachments"),
    }
    return hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _latest_official_identity(root: Path, talkroom_id: str) -> dict[str, str]:
    path = root / "source" / "talkroom" / "messages.jsonl"
    if path.is_symlink() or not _regular_file(path):
        raise Failure("paid_work_decision")
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        row = json.loads(lines[-1]) if lines else None
    except (IndexError, OSError, json.JSONDecodeError) as error:
        raise Failure("paid_work_decision") from error
    if not isinstance(row, dict):
        raise Failure("paid_work_decision")
    required = {"version", "source", "talkroom_id", "message_id", "observed_at",
                "content_sha256", "side", "sent_at", "text", "attachments"}
    if (set(row) < required or row.get("version") != 1
            or row.get("source") != "coconala_live_talkroom"
            or _text(row.get("talkroom_id")) != talkroom_id
            or not _text(row.get("message_id"))
            or not _text(row.get("observed_at"))
            or row.get("side") not in {"buyer", "seller", "system"}
            or not isinstance(row.get("text"), str)
            or not isinstance(row.get("attachments"), list)
            or not re.fullmatch(r"[0-9a-f]{64}", _text(row.get("content_sha256")))
            or _official_content_sha256(row) != row.get("content_sha256")):
        raise Failure("paid_work_decision")
    for attachment in row["attachments"]:
        if not isinstance(attachment, dict) or set(attachment) < {
                "filename", "content_type", "size_text", "href", "reference"}:
            raise Failure("paid_work_decision")
    state = _load(root / "state.json")
    if _text(state.get("talkroom_id")) != talkroom_id:
        raise Failure("paid_work_decision")
    return {"message_id": _text(row["message_id"]),
            "content_sha256": _text(row["content_sha256"]), "side": _text(row["side"])}


def _validate_paid_decision(value: dict[str, Any], feedback: str, requirements: str,
                            identity: dict[str, str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != PAID_DECISION_FIELDS:
        raise ValueError("invalid paid semantic decision")
    decision, mode = value.get("decision"), value.get("mode")
    if decision not in {"actionable", "await_buyer", "satisfied_noop", "blocked"}:
        raise ValueError("invalid paid semantic decision")
    if decision == "actionable" and mode not in {"file", "remote", "answer"}:
        raise ValueError("actionable decision requires mode")
    if decision != "actionable" and mode is not None:
        raise ValueError("non-actionable decision requires null mode")
    delivery_stage = value.get("delivery_stage")
    if decision == "actionable" and mode == "file" and delivery_stage not in {"formal", "review"}:
        raise ValueError("file decision requires formal or review delivery stage")
    if (decision != "actionable" or mode != "file") and delivery_stage != "none":
        raise ValueError("non-file decision requires none delivery stage")
    approval = value.get("formal_approval_evidence")
    if delivery_stage == "formal":
        if identity.get("side") != "buyer" or approval != identity:
            raise ValueError("formal delivery requires current buyer approval evidence")
    elif approval is not None:
        raise ValueError("non-formal decision requires null approval evidence")
    if (not isinstance(value.get("feedback_sha256"), str)
            or not isinstance(value.get("requirements_sha256"), str)
            or not isinstance(value.get("required_output"), str)
            or not isinstance(value.get("required_effect"), str)
            or value.get("feedback_sha256") != feedback
            or value.get("requirements_sha256") != requirements
            or value.get("latest_message_identity") != identity
            or not _text(value.get("required_output"))
            or not _text(value.get("required_effect"))):
        raise ValueError("paid semantic decision identity mismatch")
    unresolved = value.get("unresolved")
    if not isinstance(unresolved, list) or any(not isinstance(item, str) for item in unresolved):
        raise ValueError("invalid paid semantic decision unresolved")
    return value


def _decision_runner_proof(evidence: Path) -> dict[str, Any]:
    summary = _runner_summary(evidence)
    expected = {"status": "success", "task_label": "paid-work-decision",
                "task_class": "escalation-agent", "escalated": True,
                "selected_provider": "codex", "selected_model": PAID_DECISION_MODEL}
    if any(summary.get(key) != value for key, value in expected.items()):
        raise Failure("paid_work_decision")
    result_path = _consultation_result_path(evidence, summary)
    summary_path = evidence / "summary.json"
    return {**expected,
            "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            "result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}


def _file_snapshot(path: Path) -> tuple[int, str]:
    if path.is_symlink() or not _regular_file(path):
        raise ValueError("bound input is not a regular file")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise ValueError("bound input cannot be read") from error
    return len(content), hashlib.sha256(content).hexdigest()


def _file_operator_policy(root: Path, feedback: str,
                          requirements_sha256: str) -> tuple[Path | None, dict[str, Any], str]:
    """Return one account-owner policy only when it is scoped to this exact cycle."""
    path = root / "context" / PAID_FILE_OPERATOR_POLICY
    if not path.exists():
        return None, {}, ""
    try:
        _size, digest = _file_snapshot(path)
        policy = _load(path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise Failure("operator_policy") from error
    if not isinstance(policy, dict):
        raise Failure("operator_policy")
    directives = policy.get("directives")
    if (policy.get("version") != 1
            or policy.get("authorized_by") != "account_owner"
            or _text(policy.get("request_id")) != root.name
            or not isinstance(directives, list) or not directives
            or any(not isinstance(value, str) or not value.strip() for value in directives)):
        raise Failure("operator_policy")
    if (policy.get("buyer_feedback_sha256") != feedback
            or policy.get("requirements_sha256") != requirements_sha256):
        return None, {}, ""
    return path, policy, digest


def _file_review_images(root: Path, artifact_sha256: str, finding: str = "",
                        limit: int = 12) -> list[Path]:
    """Create artifact-bound visual inputs for the fresh native-vision reviewer."""
    resolved_root = root.resolve()
    frames: list[Path] = []
    for receipt_path in sorted((root / "work").glob("**/receipt.json")):
        try:
            receipt = _load(receipt_path)
            if receipt.get("output", {}).get("sha256") != artifact_sha256:
                continue
            raw = receipt.get("qc", {}).get("output", {}).get("review_frames", {}).get("path")
            directory = Path(_text(raw)).resolve()
            directory.relative_to(resolved_root)
            candidates = sorted(path for path in directory.glob("*.jpg")
                                if not path.is_symlink() and path.is_file())
        except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if not candidates:
            continue
        cited: list[Path] = []
        for number in re.findall(r"(?:frame[- ]?)?(\d{4})", finding, flags=re.IGNORECASE):
            candidate = directory / f"frame-{number}.jpg"
            if candidate in candidates and candidate not in cited:
                cited.append(candidate)
        remaining = max(0, limit - len(cited))
        sampled: list[Path] = []
        if remaining == 1:
            sampled = [candidates[len(candidates) // 2]]
        elif remaining > 1:
            sampled = [candidates[round(index * (len(candidates) - 1) / (remaining - 1))]
                       for index in range(remaining)]
        frames = cited + [path for path in sampled if path not in cited]
        break
    if frames:
        return frames[:limit]

    try:
        manifest_path = root / "delivery" / "paid-work-result.json"
        manifest = _load(manifest_path)
        raw_artifact = Path(_text(manifest.get("artifact_path")))
        artifact = (resolved_root / raw_artifact if not raw_artifact.is_absolute()
                    else raw_artifact).resolve()
        artifact.relative_to(resolved_root)
        if (manifest.get("package_sha256") != artifact_sha256
                or _file_snapshot(artifact)[1] != artifact_sha256):
            return []
    except (AttributeError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return []

    suffix = artifact.suffix.casefold()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return [artifact]
    if suffix != ".pdf":
        return []

    review_dir = root / "evidence" / "controller-artifact-review" / artifact_sha256
    try:
        review_dir.mkdir(parents=True, exist_ok=True)
        for stale in review_dir.glob("candidate-page-*.png"):
            if not stale.is_symlink() and stale.is_file():
                stale.unlink()
        prefix = review_dir / "candidate-page"
        _run(["pdftoppm", "-png", "-r", "150", str(artifact), str(prefix)],
             "file_visual_evidence")
        pages = sorted(
            review_dir.glob("candidate-page-*.png"),
            key=lambda path: int(path.stem.rsplit("-", 1)[1]),
        )
        if not pages:
            raise Failure("file_visual_evidence")
        rows = [
            {"page": index, "path": str(page), "sha256": _file_snapshot(page)[1]}
            for index, page in enumerate(pages, start=1)
        ]
        _write(review_dir / "review-manifest.json", {
            "version": 1,
            "artifact_path": str(artifact),
            "artifact_sha256": artifact_sha256,
            "pages": rows,
        })
        return pages
    except Failure:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise Failure("file_visual_evidence") from error


def _prepare_blind_output_audit(
    args, root: Path, manifest: dict[str, Any], artifact_sha256: str,
    source_correspondence_sha256: str,
) -> tuple[Path | None, list[Path]]:
    """Blind-read owner-declared manual crops before the final reviewer sees expectations."""
    try:
        correspondence = _load(Path(_text(manifest.get("source_correspondence_path"))))
        exact = correspondence.get("exact_semantic_value_checks")
        evidence_path = Path(_text(exact.get("label_evidence_path"))).resolve()
        evidence_path.relative_to(root.resolve())
        if exact.get("label_evidence_sha256") != _file_snapshot(evidence_path)[1]:
            raise ValueError("stale label evidence")
        evidence = _load(evidence_path)
        manual = [row for row in evidence.get("checks", [])
                  if _text(row.get("verification_mode")).startswith("manual")]
        if not manual:
            return None, []
        crops: list[tuple[str, Path, str, str, str]] = []
        for index, row in enumerate(manual, start=1):
            path = Path(_text(row.get("output_crop_path"))).resolve()
            path.relative_to(root.resolve())
            sha256 = _file_snapshot(path)[1]
            if sha256 != row.get("output_crop_sha256"):
                raise ValueError("stale output crop")
            crops.append((f"blind-{index:04d}", path, sha256,
                          _text(row.get("expected_label_from_controller")), _text(row.get("role"))))
    except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise Failure("file_visual_evidence") from error

    with tempfile.TemporaryDirectory(prefix="paid-output-audit-") as temporary:
        isolated = Path(temporary)
        copied: list[Path] = []
        for blind_id, source, _sha256, _expected, _role in crops:
            target = isolated / "crops" / f"{blind_id}{source.suffix.casefold()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied.append(target)
        schema = isolated / "schema.json"
        _write(schema, {
            "type": "object", "additionalProperties": False,
            "required": ["status", "reads"],
            "properties": {
                "status": {"type": "string", "const": "ok"},
                "reads": {
                    "type": "array", "minItems": len(crops), "maxItems": len(crops),
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": ["id", "visible_label", "confidence"],
                        "properties": {
                            "id": {"type": "string"},
                            "visible_label": {"type": "string", "minLength": 1},
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        },
                    },
                },
            },
        })
        prompt = isolated / "prompt.txt"
        prompt.write_text(
            "You are a blind visual transcription reviewer. Work only in this isolated directory. "
            "The attached images correspond in order to IDs "
            f"{json.dumps([{'id': row[0], 'target_role': row[4]} for row in crops])}. Each target role names the "
            "colored note whose adjacent Japanese solfege label must be read; ignore labels belonging to other colored "
            "notes in the same crop. Read only that visible label glyph, including any flat sign. You are not given any "
            "expected value and must not search outside this directory. Return exactly one read per ID in the same order. "
            "Use confidence low rather than guessing when the glyph is unreadable.",
            encoding="utf-8",
        )
        runtime = isolated / "runtime"
        runtime.mkdir()
        runner_source = Path(args.agent_runner).resolve()
        isolated_runner = runtime / runner_source.name
        shutil.copyfile(runner_source, isolated_runner)
        for sibling in ("token_budget.py", "config.json"):
            source = runner_source.parent / sibling
            if source.is_file():
                shutil.copyfile(source, runtime / sibling)
        profile = isolated / "blind-only.sb"
        profile.write_text(
            "(version 1)\n(allow default)\n"
            f"(deny file-read* (subpath {json.dumps(str(root.resolve().parent))}))\n"
            f"(deny file-read* (subpath {json.dumps(str(HERE.parents[2].resolve()))}))\n"
            f"(deny file-read* (subpath {json.dumps(str(Path.home() / 'life-manager'))}))\n"
            f"(deny file-write* (subpath {json.dumps(str(root.resolve().parent))}))\n",
            encoding="utf-8",
        )
        evidence_dir = isolated / "evidence"
        started = time.time_ns()
        command = [
            "/usr/bin/sandbox-exec", "-f", str(profile), sys.executable, str(isolated_runner),
            "--task-class", "escalation-agent", "--candidate-model", PAID_FILE_MODEL,
            "--prompt-file", str(prompt), "--schema", str(schema),
            "--evidence-dir", str(evidence_dir), "--task-label", "paid-output-blind-audit",
            "--loop", "gig", "--workdir", str(isolated), "--timeout-seconds", "1800", "--read-only",
            "--escalation-reason", "Blind output crop readback before paid submission",
        ]
        for image in copied:
            command += ["--image", str(image)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode:
            attempts = evidence_dir / "attempts.jsonl"
            attempt_stdout = evidence_dir / "attempt-01.stdout.log"
            attempt_stderr = evidence_dir / "attempt-01.stderr.log"
            _write(root / "context" / "paid-output-audit-runner-error.json", {
                "version": 1, "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:], "stderr_tail": completed.stderr[-4000:],
                "attempts_tail": attempts.read_text(encoding="utf-8")[-8000:] if attempts.is_file() else "",
                "attempt_stdout_tail": attempt_stdout.read_text(encoding="utf-8")[-4000:] if attempt_stdout.is_file() else "",
                "attempt_stderr_tail": attempt_stderr.read_text(encoding="utf-8")[-4000:] if attempt_stderr.is_file() else "",
            })
            raise Failure("file_verifier")
        result, proof = _file_runner_result(
            evidence_dir, task_label="paid-output-blind-audit", started_ns=started,
        )
        reads = result.get("reads") if isinstance(result, dict) else None
        if (result.get("status") != "ok" or not isinstance(reads, list)
                or [row.get("id") for row in reads] != [row[0] for row in crops]):
            raise Failure("file_verifier")
        rows = [{
            "id": blind_id, "crop_path": str(path), "crop_sha256": sha256, "target_role": role,
            "blind_visible_label": _text(read.get("visible_label")),
            "confidence": read.get("confidence"), "expected_label": expected,
            "match": _text(read.get("visible_label")) == expected,
        } for (blind_id, path, sha256, expected, role), read in zip(crops, reads)]
        audit_path = root / "context" / "paid-output-visual-audit.json"
        _write(audit_path, {
            "version": 1, "policy_version": PAID_FILE_POLICY_VERSION,
            "artifact_sha256": artifact_sha256,
            "source_correspondence_sha256": source_correspondence_sha256,
            "label_evidence_path": str(evidence_path),
            "label_evidence_sha256": _file_snapshot(evidence_path)[1],
            "status": "PASS" if all(row["match"] for row in rows) else "FAIL",
            "reads": rows, **proof,
        })
    return audit_path, [row[1] for row in crops]


def _file_reference_images(root: Path, manifest: dict[str, Any], limit: int = 4) -> list[Path]:
    """Read explicit visual-reference paths from the artifact's bound acceptance evidence."""
    try:
        resolved_root = root.resolve()
        acceptance = Path(_text(manifest.get("acceptance_evidence_path"))).resolve()
        acceptance.relative_to(resolved_root)
        if acceptance.is_symlink() or not acceptance.is_file():
            return []
        value = _load(acceptance)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return []

    raw_paths: list[str] = []
    reference_key = re.compile(r"(?:visual_)?reference(?:_image|_frame|_sheet)?_paths?$")

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if isinstance(key, str) and reference_key.fullmatch(key.casefold()):
                    values = child if isinstance(child, list) else [child]
                    raw_paths.extend(item for item in values if isinstance(item, str))
                else:
                    collect(child)
        elif isinstance(node, list):
            for child in node:
                collect(child)

    collect(value)
    images: list[Path] = []
    for raw in raw_paths:
        try:
            path = Path(raw)
            path = (resolved_root / path if not path.is_absolute() else path).resolve()
            path.relative_to(resolved_root)
        except (OSError, ValueError):
            continue
        if (path.suffix.casefold() in {".jpg", ".jpeg", ".png", ".webp"}
                and not path.is_symlink() and path.is_file() and path not in images):
            images.append(path)
        if len(images) >= limit:
            break
    return images


def _file_review_disposition(verdict: Any) -> str:
    if verdict == "deliverable":
        return "approve"
    if verdict == "needs_revision":
        return "repair"
    return "block"


def _file_progress_payload(cadence: dict[str, Any]) -> dict[str, Any]:
    """Keep internal acceptance evidence out of the buyer-facing progress note."""
    payload = delivery_queue.progress_payload(cadence)
    revision = (cadence.get("buyer_feedback_stage") == "revision"
                or cadence.get("buyer_reply_after_artifact_observed") is True)
    payload["message"] = (
        "お世話になっております。修正版をお送りします。ご確認をお願いいたします。"
        if revision else
        "お世話になっております。成果物をお送りします。ご確認をお願いいたします。"
    )
    return payload


def _context_input_snapshot(root: Path, context: Path) -> dict[str, tuple[int, str]]:
    try:
        compiled = _load(context)
        source_refs = compiled["source_refs"]
        read_first = compiled["combined_context"]["read_these_first"]
    except (KeyError, TypeError, OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("invalid compiled context") from error
    if not isinstance(source_refs, list) or not isinstance(read_first, list):
        raise ValueError("invalid compiled context inputs")
    root = root.resolve()
    snapshots: dict[str, tuple[int, str]] = {}
    for ref in source_refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
            raise ValueError("invalid compiled source reference")
        raw = Path(ref["path"])
        if raw.is_absolute():
            raise ValueError("compiled source reference must be relative")
        path = (root / raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("compiled source reference escapes project") from error
        snapshot = _file_snapshot(path)
        if (ref.get("bytes"), ref.get("sha256")) != snapshot:
            raise ValueError("compiled source reference changed")
        snapshots[str(path)] = snapshot
    for raw in read_first:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("invalid compiled read path")
        candidate = Path(raw)
        path = (root / candidate if not candidate.is_absolute() else candidate).resolve()
        snapshots[str(path)] = _file_snapshot(path)
    return snapshots


def _revalidate_file_snapshots(snapshots: dict[str, tuple[int, str]]) -> None:
    for raw, expected in snapshots.items():
        if _file_snapshot(Path(raw)) != expected:
            raise ValueError("bound paid decision input changed")


def _decision_prompt(context: Path, context_sha256: str, feedback: str,
                    requirements: str, identity: dict[str, str]) -> bytes:
    return (
        f"Return one strict JSON semantic decision for the compiled cumulative context {context}. "
        f"context_sha256={context_sha256}; current feedback_sha256={feedback}; requirements_sha256={requirements}; "
        f"latest_message_identity={json.dumps(identity, sort_keys=True)}. "
        "Use decision actionable, await_buyer, satisfied_noop, or blocked. "
        "Actionable requires mode file, remote, or answer; every other decision requires mode null. "
        "Choose mode from the required effect: remote only for an authenticated system mutation outside the Coconala "
        "marketplace; remote is for a buyer-owned work target, never for any Coconala page or transaction control. "
        "Coconala cancellation, refund, dispute, and contract controls require their own code-owned adapter and must be "
        "blocked when no such adapter is present. Answer mode is for the Coconala talkroom: use it when a text response "
        "itself completely satisfies the request, or when one indispensable missing "
        "buyer input must be requested before work can continue. In the latter case ask one bounded question that names "
        "exactly what is missing. Use await_buyer only after that exact question has already been sent and no newer buyer "
        "reply exists. Use file whenever satisfying the request requires a seller-produced local artifact, "
        "including initial delivery, revision, and resubmission of an artifact already present on disk. A file delivery "
        "may also include an accompanying Coconala message. Do not choose remote merely because the response describes "
        "or acknowledges an action. "
        "For every initial file submission and every correction, set delivery_stage to review and "
        "formal_approval_evidence to null. Formal delivery is never inferred merely because an artifact is complete. "
        "Set delivery_stage to formal only after the buyer explicitly approves an already submitted artifact and permits "
        "the transaction to be completed; then formal_approval_evidence must exactly equal the current buyer-side "
        "latest_message_identity. Every non-formal decision uses formal_approval_evidence null. Every non-file decision "
        "uses delivery_stage none. Decide explicit approval from "
        "the complete semantic workflow, never from title or keyword matching. required_output and required_effect must "
        "state the bounded outcome; unresolved is an array of strings. "
        "Read the context and its read_these_first files. Do not use a browser or mutate anything."
    ).encode("utf-8")


def _cached_paid_decision(root: Path, receipt: Any, prompt: Path,
                          prompt_sha256: str, schema_sha256: str, context_sha256: str,
                          feedback: str, requirements: str, identity: dict[str, str]) -> dict[str, Any]:
    if (not isinstance(receipt, dict)
            or receipt.get("schema_version") != PAID_DECISION_SCHEMA_VERSION
            or receipt.get("prompt_version") != PAID_DECISION_PROMPT_VERSION
            or receipt.get("schema_sha256") != schema_sha256
            or receipt.get("context_sha256") != context_sha256
            or receipt.get("prompt_sha256") != prompt_sha256
            or not isinstance(receipt.get("runner"), dict)):
        raise ValueError("stale paid decision receipt")
    runner = receipt["runner"]
    if (set(runner) != {"status", "task_label", "task_class", "escalated",
                        "selected_provider", "selected_model", "summary_sha256", "result_sha256"}
            or runner.get("status") != "success"
            or runner.get("task_label") != "paid-work-decision"
            or runner.get("task_class") != "escalation-agent"
            or runner.get("escalated") is not True
            or runner.get("selected_provider") != "codex"
            or runner.get("selected_model") != PAID_DECISION_MODEL
            or any(not re.fullmatch(r"[0-9a-f]{64}", runner.get(key, ""))
                   for key in ("summary_sha256", "result_sha256"))):
        raise ValueError("invalid paid decision runner proof")
    if prompt.is_symlink() or not _regular_file(prompt) or _file_snapshot(prompt)[1] != prompt_sha256:
        raise ValueError("stale paid decision prompt")
    evidence_root = root / "evidence"
    evidence = evidence_root / "agent-PAID_WORK_DECISION"
    if (evidence_root.is_symlink() or not evidence_root.is_dir()
            or evidence.is_symlink() or not evidence.is_dir()):
        raise ValueError("missing paid decision evidence")
    proof = _decision_runner_proof(evidence)
    if proof != runner:
        raise ValueError("tampered paid decision evidence")
    result_path = _consultation_result_path(evidence)
    value = _load(result_path)
    validated = _validate_paid_decision(value, feedback, requirements, identity)
    cached_value = {key: receipt.get(key) for key in PAID_DECISION_FIELDS}
    if validated != cached_value:
        raise ValueError("paid decision result does not match receipt")
    return validated


def _paid_decision(args, item_path: Path, root: Path, base: Path) -> dict[str, Any]:
    item_snapshot = _file_snapshot(item_path)
    feedback = _text(_load(item_path).get("buyer_feedback_sha256"))
    requirements = paid_remote_result.requirements_digest(root, feedback)
    item = _load(item_path)
    talkroom_id = _text(item.get("talkroom_id"))
    identity = _latest_official_identity(root, talkroom_id)
    schema = args.decision_schema
    schema_snapshot = _file_snapshot(schema)
    schema_sha256 = schema_snapshot[1]
    context = root / "context" / "current.json"
    if context.parent.is_symlink() or (context.parent.exists() and not context.parent.is_dir()):
        raise Failure("context_compile")
    context.parent.mkdir(parents=True, exist_ok=True)
    _run([sys.executable, str(args.context_compiler), "--project-root", str(root),
          "--queue-item", str(item_path), "--output", str(context)], "context_compile")
    if context.is_symlink() or not _regular_file(context):
        raise Failure("context_compile")
    context_snapshot = context.read_bytes()
    context_sha256 = hashlib.sha256(context_snapshot).hexdigest()
    context_inputs = _context_input_snapshot(root, context)
    if (paid_remote_result.requirements_digest(root, feedback) != requirements
            or _latest_official_identity(root, talkroom_id) != identity):
        raise Failure("paid_work_decision")
    if context.parent.is_symlink() or not context.parent.is_dir():
        raise Failure("paid_work_decision")
    receipt_path = context.parent / "paid-work-decision.json"
    prompt = base / "mode" / "decision.prompt.txt"
    prompt_bytes = _decision_prompt(context, context_sha256, feedback, requirements, identity)
    prompt_sha256 = hashlib.sha256(prompt_bytes).hexdigest()
    try:
        receipt = None if receipt_path.is_symlink() or not _regular_file(receipt_path) else _load(receipt_path)
        return _cached_paid_decision(root, receipt, prompt, prompt_sha256,
                                     schema_sha256, context_sha256, feedback, requirements, identity)
    except (AttributeError, Failure, OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    if prompt.parent.is_symlink() or (prompt.parent.exists() and not prompt.parent.is_dir()):
        raise Failure("paid_work_decision")
    prompt.parent.mkdir(parents=True, exist_ok=True)
    if prompt.is_symlink():
        raise Failure("paid_work_decision")
    prompt.write_bytes(prompt_bytes)
    prompt_snapshot = _file_snapshot(prompt)
    evidence_root = root / "evidence"
    if evidence_root.is_symlink() or (evidence_root.exists() and not evidence_root.is_dir()):
        raise Failure("paid_work_decision")
    evidence_root.mkdir(parents=True, exist_ok=True)
    evidence = evidence_root / "agent-PAID_WORK_DECISION"
    if evidence.is_symlink():
        raise Failure("paid_work_decision")
    started_ns = time.time_ns()
    try:
        _run([sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
              "--candidate-model", PAID_DECISION_MODEL,
              "--prompt-file", str(prompt), "--schema", str(schema), "--evidence-dir", str(evidence),
              "--task-label", "paid-work-decision", "--escalation-reason",
              "Paid delivery routing must use the authorized Sol semantic decision model.",
              "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "1800", "--read-only"],
             "paid_work_decision")
        try:
            value = _consultation_runner_result(
                evidence, task_label="paid-work-decision", task_class="escalation-agent",
                model=PAID_DECISION_MODEL, started_ns=started_ns,
            )
        except Failure as error:
            raise Failure("paid_work_decision") from error
        runner_proof = _decision_runner_proof(evidence)
        value = _validate_paid_decision(value, feedback, requirements, identity)
        current_bound = {
            str(item_path): item_snapshot,
            str(schema): schema_snapshot,
            str(prompt): prompt_snapshot,
            str(context): (len(context_snapshot), context_sha256),
        }
        _revalidate_file_snapshots(current_bound)
        if (_context_input_snapshot(root, context) != context_inputs
                or paid_remote_result.requirements_digest(root, feedback) != requirements
                or _latest_official_identity(root, talkroom_id) != identity):
            raise ValueError("paid decision inputs changed")
        receipt = {"schema_version": PAID_DECISION_SCHEMA_VERSION,
                   "prompt_version": PAID_DECISION_PROMPT_VERSION, "schema_sha256": schema_sha256,
                   "prompt_sha256": prompt_sha256, "context_sha256": context_sha256,
                   "runner": runner_proof, **value}
        _write(receipt_path, receipt)
        return value
    except Failure:
        raise
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise Failure("paid_work_decision") from error


def _decision_only(args, item_path: Path, output: Path) -> int:
    try:
        item = _load(item_path)
        room = _text(item.get("talkroom_id"))
        if not re.fullmatch(r"[0-9]+", room):
            raise Failure("paid_work_decision")
        candidate = delivery_project.resolve_project_root(args.projects_root, item)
        projects = args.projects_root.resolve()
        if candidate.is_symlink() or candidate.parent.resolve() != projects:
            raise Failure("paid_work_decision")
        root = candidate.resolve()
        root.relative_to(projects)
        if not root.is_dir():
            raise Failure("paid_work_decision")
        state = _load(root / "state.json")
        if _text(state.get("talkroom_id")) != room:
            raise Failure("paid_work_decision")
        evidence_root = args.evidence_dir.resolve()
        paid_root = evidence_root / "paid-direct"
        if paid_root.is_symlink():
            raise Failure("paid_work_decision")
        base_root = paid_root.resolve()
        if base_root.parent != evidence_root:
            raise Failure("paid_work_decision")
        base = (base_root / room).resolve()
        if base.parent != base_root:
            raise Failure("paid_work_decision")
        value = _paid_decision(args, item_path, root, base)
        _write(output, {"status": "completed", **value})
        return 0
    except (AttributeError, Failure, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        _write(output, {"status": "failed", "failed_step": error.step if isinstance(error, Failure) else "paid_work_decision", "effect": 0})
        return 1

def _delivery_snapshot(root: Path) -> dict[str, tuple[Any, ...]]:
    snapshot = {}
    for name in ("paid-remote-intent.json", "paid-remote-result.json", "paid-answer.json"):
        path = root / "delivery" / name
        try: info = path.lstat()
        except FileNotFoundError:
            if name != "paid-answer.json": raise Failure("remote_verifier")
            snapshot[name] = (False, None, None, None, None); continue
        except OSError as error: raise Failure("remote_verifier") from error
        if not stat.S_ISREG(info.st_mode): raise Failure("remote_verifier")
        try: content = path.read_bytes()
        except OSError as error: raise Failure("remote_verifier") from error
        snapshot[name] = (True, info.st_dev, info.st_ino, info.st_mode, content)
    return snapshot

def _requirements_snapshot(root: Path) -> bytes:
    path = root / "requirements" / "live-buyer-reply.json"
    if path.is_symlink() or not _regular_file(path): raise Failure("context_compile")
    try: return path.read_bytes()
    except OSError as error: raise Failure("context_compile") from error

def _validate_verifier_runner(managed: Path, semantic_status: str,
                              min_mtime_ns: int | None = None) -> dict[str, Any]:
    summary = _runner_summary(managed)
    expected = {"status": "success", "task_label": "paid-remote-verifier", "task_class": "escalation-agent",
                "escalated": True, "selected_provider": "codex", "selected_model": "gpt-5.6-sol"}
    if not isinstance(summary, dict) or any(summary.get(key) != value for key, value in expected.items()):
        raise ValueError("verifier runner selection mismatch")
    if step_result_status.status_from_evidence(managed) != semantic_status:
        raise ValueError("verifier runner semantic status mismatch")
    if min_mtime_ns is not None:
        raw_result = summary["result_path"]
        result_path = (managed / raw_result if not Path(raw_result).is_absolute() else Path(raw_result)).resolve()
        now_ns = time.time_ns()
        for path in (managed / "summary.json", result_path):
            mtime_ns = path.stat().st_mtime_ns
            if mtime_ns <= min_mtime_ns or mtime_ns > now_ns + 1_000_000_000:
                raise ValueError("verifier runner proof is stale")
    return summary

def _validate_managed_verifier(verifier: Path, project_root: Path, intent: dict[str, Any], feedback: str, digest: str,
                               min_evidence_mtime_ns: int | None = None) -> Path:
    try:
        if not isinstance(intent, dict) or not isinstance(intent.get("desired_state"), dict) or not _text(intent.get("target")):
            raise ValueError("invalid remote intent")
        project_root = project_root.resolve(); evidence_root = project_root / "evidence"
        if evidence_root.is_symlink() or not evidence_root.is_dir():
            raise ValueError("invalid project evidence root")
        managed_path = evidence_root / "agent-PAID_REMOTE_VERIFY"
        if managed_path.is_symlink() or not managed_path.is_dir() or verifier.is_symlink():
            raise ValueError("invalid managed verifier root")
        verifier = verifier.resolve(); managed = managed_path.resolve()
        if (verifier.name != "remote-verifier-result.json" or verifier.parent != managed
                or not verifier.is_file()):
            raise ValueError("invalid managed verifier path")
        _validate_verifier_runner(managed, "ok", min_evidence_mtime_ns)
        delivery_result = _load(project_root / "delivery" / "paid-remote-result.json")
        requirements_sha256 = paid_remote_result.requirements_digest(project_root, feedback)
        message = delivery_result.get("customer_message") if isinstance(delivery_result, dict) else None
        if not isinstance(message, str) or not message.strip():
            raise ValueError("invalid customer message")
        message_sha256 = hashlib.sha256(message.encode()).hexdigest()
        if (intent.get("requirements_sha256") != requirements_sha256
                or delivery_result.get("requirements_sha256") != requirements_sha256
                or intent.get("message_sha256") != message_sha256
                or delivery_result.get("message_sha256") != message_sha256):
            raise ValueError("builder requirements contract mismatch")
        result = _load(verifier); desired = intent["desired_state"]; target = intent["target"]
        if (not isinstance(result, dict) or result.get("verified") is not True
                or result.get("buyer_feedback_sha256") != feedback or result.get("target") != target
                or result.get("desired_digest", result.get("desired_state_digest")) != digest
                or result.get("observed_digest") != digest
                or not paid_remote_result.canonical_equal(result.get("observed_state"), desired)
                or result.get("requirements_sha256") != requirements_sha256
                or result.get("message_sha256") != message_sha256):
            raise ValueError("verifier result mismatch")
        attachment = _validated_customer_attachment(project_root, delivery_result.get("customer_attachment"))
        if (intent.get("customer_attachment") != attachment or result.get("customer_attachment") != attachment):
            raise ValueError("customer attachment verifier mismatch")
        references = [(field, result.get(field)) for field in ("before_evidence", "after_evidence")
                      if isinstance(result.get(field), str) and result.get(field).strip()]
        if not references and isinstance(result.get("evidence"), list):
            references = [("evidence", value) for value in result["evidence"] if isinstance(value, str) and value.strip()]
        if not references:
            raise ValueError("verifier evidence missing")
        observed = False; now_ns = time.time_ns()
        for field, raw_path in references:
            evidence_path = (managed / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)).resolve()
            evidence_path.relative_to(managed)
            mtime_ns = evidence_path.stat().st_mtime_ns if evidence_path.is_file() else 0
            if (not evidence_path.is_file() or (min_evidence_mtime_ns is not None
                                                 and (mtime_ns <= min_evidence_mtime_ns or mtime_ns > now_ns + 1_000_000_000))):
                raise ValueError("verifier evidence is stale or missing")
            evidence = _load(evidence_path)
            if (not isinstance(evidence, dict) or evidence.get("target") != target
                    or evidence.get("authenticated") is not True
                    or evidence.get("requirements_sha256") != requirements_sha256
                    or evidence.get("message_sha256") != message_sha256):
                raise ValueError("verifier evidence identity mismatch")
            if not paid_remote_result.canonical_equal(evidence.get("observed_state"), desired):
                raise ValueError("verifier observed state mismatch")
            observed = True
        if not observed:
            raise ValueError("verifier observed evidence missing")
        return verifier
    except Failure:
        raise
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise Failure("remote_verifier") from error

def _review_failure(verifier: Path, project_root: Path, intent: dict[str, Any], feedback: str, digest: str,
                    min_mtime_ns: int | None = None) -> dict[str, Any]:
    """Read a Sol-owned rejection as repair input, never as effect authorization."""
    try:
        project_root = project_root.resolve(); managed = project_root / "evidence" / "agent-PAID_REMOTE_VERIFY"
        if managed.is_symlink() or not managed.is_dir() or verifier.is_symlink():
            raise ValueError("invalid managed verifier root")
        verifier = verifier.resolve()
        if verifier.parent != managed.resolve() or verifier.name != "remote-verifier-result.json" or not verifier.is_file():
            raise ValueError("invalid managed verifier result")
        _validate_verifier_runner(managed, "blocked", min_mtime_ns)
        mtime_ns, now_ns = verifier.stat().st_mtime_ns, time.time_ns()
        if min_mtime_ns is not None and (mtime_ns <= min_mtime_ns or mtime_ns > now_ns + 1_000_000_000):
            raise ValueError("stale verifier rejection")
        result = _load(verifier)
        delivery_result = _load(project_root / "delivery" / "paid-remote-result.json")
        requirements_sha256 = paid_remote_result.requirements_digest(project_root, feedback)
        message = delivery_result.get("customer_message") if isinstance(delivery_result, dict) else None
        if not isinstance(message, str) or not message.strip(): raise ValueError("invalid customer message")
        message_sha256 = hashlib.sha256(message.encode()).hexdigest()
        if (not isinstance(result, dict) or result.get("verified") is not False
                or result.get("buyer_feedback_sha256") != feedback
                or result.get("target") != intent.get("target")
                or result.get("desired_digest", result.get("desired_state_digest")) != digest
                or result.get("requirements_sha256") != requirements_sha256
                or result.get("message_sha256") != message_sha256):
            raise ValueError("verifier rejection identity mismatch")
        classification = result.get("classification")
        delta = result.get("delta")
        if classification == "quality_mismatch":
            if not isinstance(delta, list) or not 1 <= len(delta) <= 20:
                raise ValueError("invalid reviewer delta")
            for item in delta:
                fields = ("requirement", "expected", "observed", "evidence", "repair")
                if (not isinstance(item, dict) or set(item) != set(fields)
                        or any(not isinstance(item.get(key), str) or not item[key].strip() or len(item[key]) > 2000
                               for key in fields)):
                    raise ValueError("invalid reviewer delta")
        elif classification in {"auth_transient", "cdp_transient"}:
            if delta not in (None, []): raise ValueError("transient rejection cannot prescribe a repair")
        else:
            raise ValueError("unclassified verifier rejection")
        return {"classification": classification, "delta": delta or []}
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise Failure("remote_verifier") from error

def resolve_managed_verifier(project_root: Path, feedback: str, digest: str) -> Path:
    try:
        project_root = project_root.resolve()
        intent = _load(project_root / "delivery" / "paid-remote-intent.json")
        managed = project_root / "evidence" / "agent-PAID_REMOTE_VERIFY"
        if managed.is_symlink() or not managed.is_dir(): raise Failure("remote_resume")
        verifier = managed / "remote-verifier-result.json"
        return _validate_managed_verifier(verifier, project_root, intent, feedback, digest)
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    raise Failure("remote_resume")

def _targeted(args, item, index):
    room = _text(item.get("talkroom_id")); base = args.evidence_dir / "paid-direct" / "targeted" / room
    item_path, snapshot = base / "item.json", base / "snapshot.json"
    _write(item_path, item)
    for attempt in range(2):
        try:
            _run(_collector(args, "selected-talkroom-only", snapshot, base, item_path, item), "targeted_readback")
            break
        except Failure:
            if attempt:
                raise
    return {**item, **_row(_load(snapshot), room)}

def _recoverable(args, item):
    try:
        root = _paid_project_root(args, item)
        delivery = root / "delivery"
        if not root.is_dir() or not (root / "state.json").is_file(): return None
        feedback = _text(item.get("buyer_feedback_sha256")); intent_path = delivery / "paid-remote-intent.json"
        try:
            decision = _current_paid_decision(root, item)
        except (AttributeError, KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
            decision = None
        if decision is not None:
            if decision.get("decision") != "actionable":
                return None
            if decision.get("mode") in {"file", "answer"}:
                return root, None
            remote_mode = decision.get("mode") == "remote"
        else:
            if _answer_ready(root, item):
                return root, None
            remote_mode = (_legacy_paid_mode(root, feedback) == "remote"
                           or _remote_revision_required(root, feedback))
        if remote_mode and all((delivery / name).is_file()
                               for name in ("paid-remote-intent.json", "paid-remote-result.json")):
            intent = _load(intent_path)
            if isinstance(intent, dict) and intent.get("buyer_feedback_sha256") == feedback:
                try:
                    verifier = resolve_managed_verifier(
                        root, feedback, _text(intent.get("desired_state_sha256")),
                    )
                    paid_remote_result.resume(
                        root, feedback, _text(intent.get("desired_state_sha256")), verifier,
                    )
                    return root, verifier
                except Failure: pass
                except (OSError, ValueError, TypeError, json.JSONDecodeError): pass
        if remote_mode:
            return root, None
        return None
    except (Failure, OSError, ValueError, TypeError, json.JSONDecodeError): return None


def _paid_project_root(args, item: dict[str, Any]) -> Path:
    projects = args.projects_root.expanduser().resolve()
    candidate = delivery_project.resolve_project_root(args.projects_root, item)
    if candidate.is_symlink() or candidate.parent.resolve() != projects:
        raise Failure("context_compile")
    root = candidate.resolve()
    root.relative_to(projects)
    return root


def _current_paid_decision(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    receipt = _load(root / "context" / "paid-work-decision.json")
    value = {key: receipt[key] for key in PAID_DECISION_FIELDS}
    feedback = _text(item.get("buyer_feedback_sha256"))
    requirements = paid_remote_result.requirements_digest(root, feedback)
    identity = _latest_official_identity(root, _text(item.get("talkroom_id")))
    return _validate_paid_decision(value, feedback, requirements, identity)


def _file_mode(root: Path, item: dict[str, Any]) -> bool:
    decision = _current_paid_decision(root, item)
    return decision.get("decision") == "actionable" and decision.get("mode") == "file"


def _file_runner_result(evidence: Path, *, task_label: str,
                        started_ns: int | None) -> tuple[dict[str, Any], dict[str, str]]:
    summary = _runner_summary(evidence)
    expected = {
        "status": "success", "task_label": task_label, "task_class": "escalation-agent",
        "escalated": True, "selected_provider": "codex", "selected_model": PAID_FILE_MODEL,
    }
    if any(summary.get(key) != value for key, value in expected.items()):
        raise Failure("file_verifier" if "verifier" in task_label else "file_builder")
    result_path = _consultation_result_path(evidence, summary)
    if started_ns is not None:
        now_ns = time.time_ns()
        for path in (evidence / "summary.json", result_path):
            if path.stat().st_mtime_ns <= started_ns or path.stat().st_mtime_ns > now_ns + 1_000_000_000:
                raise Failure("file_verifier" if "verifier" in task_label else "file_builder")
    value = _load(result_path)
    if not isinstance(value, dict):
        raise Failure("file_verifier" if "verifier" in task_label else "file_builder")
    proof = {
        "summary_sha256": hashlib.sha256((evidence / "summary.json").read_bytes()).hexdigest(),
        "result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
    }
    return value, proof


def _source_census_inputs(root: Path) -> list[dict[str, str]]:
    requirements = _load(root / "requirements" / "live-buyer-reply.json")
    attachments = requirements.get("attachments") if isinstance(requirements, dict) else None
    result: list[dict[str, str]] = []
    for attachment in attachments if isinstance(attachments, list) else []:
        if not isinstance(attachment, dict) or not _text(attachment.get("source_path")):
            continue
        path = Path(_text(attachment["source_path"])).resolve()
        relative = path.relative_to(root.resolve())
        sha256 = _file_snapshot(path)[1]
        if attachment.get("sha256") != sha256:
            raise ValueError("stale source census input")
        result.append({"path": str(relative), "sha256": sha256})
    return result


def _trusted_source_census(root: Path, requirements_sha256: str) -> tuple[Path, dict[str, Any]] | None:
    trust_path = root / "context" / "paid-source-census.json"
    if not _regular_file(trust_path):
        return None
    trust = _load(trust_path)
    census_path = Path(_text(trust.get("census_path"))).resolve() if isinstance(trust, dict) else Path()
    expected_sources = _source_census_inputs(root)
    if (not isinstance(trust, dict) or trust.get("version") != 1
            or trust.get("policy_version") != PAID_SOURCE_CENSUS_VERSION
            or trust.get("requirements_sha256") != requirements_sha256
            or trust.get("sources") != expected_sources
            or census_path != (root / "acceptance" / "controller-source-census-v1.json").resolve()
            or trust.get("census_sha256") != _file_snapshot(census_path)[1]):
        return None
    visuals = trust.get("visual_sources")
    visual_suffixes = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
    if (not isinstance(visuals, list)
            or (any(Path(source["path"]).suffix.casefold() in visual_suffixes
                    for source in expected_sources) and not visuals)):
        return None
    try:
        for visual in visuals:
            path = Path(_text(visual.get("path"))).resolve()
            path.relative_to(root.resolve())
            if visual.get("sha256") != _file_snapshot(path)[1]:
                return None
        census_visuals = _load(census_path).get("visual_sources")
    except (AttributeError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if census_visuals != [{key: value for key, value in visual.items() if key != "path"}
                          for visual in visuals]:
        return None
    return census_path, trust


def _source_census_visual_inputs(
    isolated: Path, copied_sources: list[dict[str, str]],
) -> tuple[list[Path], list[dict[str, Any]]]:
    """Create controller-owned page images that the census model must actually see."""
    visual_dir = isolated / "visual-sources"
    visual_dir.mkdir(parents=True, exist_ok=True)
    images: list[Path] = []
    rows: list[dict[str, Any]] = []
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    for index, source in enumerate(copied_sources):
        copied = Path(source["isolated_path"])
        rendered: list[Path] = []
        if copied.suffix.casefold() == ".pdf":
            prefix = visual_dir / f"source-{index:04d}-page"
            _run(["pdftoppm", "-png", "-r", "150", str(copied), str(prefix)], "file_builder")
            rendered = sorted(visual_dir.glob(f"{prefix.name}-*.png"),
                              key=lambda path: int(path.stem.rsplit("-", 1)[1]))
            if not rendered:
                raise Failure("file_builder")
        elif copied.suffix.casefold() in image_suffixes:
            rendered = [copied]
        for page, image in enumerate(rendered, start=1):
            sha256 = _file_snapshot(image)[1]
            images.append(image)
            rows.append({
                "source_path": source["path"], "page": page, "sha256": sha256, "kind": "source",
            })
    return images, rows


def _prepare_source_census(args, root: Path, requirements_sha256: str, code_root: Path) -> Path | None:
    sources = _source_census_inputs(root)
    if not sources:
        return None
    existing = _trusted_source_census(root, requirements_sha256)
    if existing is not None:
        return existing[0]
    with tempfile.TemporaryDirectory(prefix="paid-source-census-") as temporary:
        isolated = Path(temporary)
        copied_sources: list[dict[str, str]] = []
        for index, source in enumerate(sources):
            original = (root / source["path"]).resolve()
            copied = isolated / "sources" / f"{index:04d}{original.suffix}"
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, copied)
            copied_sources.append({**source, "isolated_path": str(copied)})
        visual_images, expected_visuals = _source_census_visual_inputs(isolated, copied_sources)
        requirements_copy = isolated / "requirements.json"
        shutil.copyfile(root / "requirements" / "live-buyer-reply.json", requirements_copy)
        source_manifest = isolated / "source-manifest.json"
        _write(source_manifest, {
            "version": 1, "requirements_path": str(requirements_copy),
            "requirements_sha256": requirements_sha256, "sources": copied_sources,
        })
        approved_skills = isolated / "skills"
        for name in PAID_SOURCE_CENSUS_SKILLS:
            source_skill = code_root / "skills" / name
            if not (source_skill / "SKILL.md").is_file():
                raise Failure("file_builder")
            shutil.copytree(source_skill, approved_skills / name)
        coverage_sources = []
        overlay_cli = approved_skills / "music-score-omr" / "scripts" / "source_notehead_overlay.py"
        for index, source in enumerate(copied_sources):
            copied = Path(source["isolated_path"])
            if copied.suffix.casefold() != ".pdf" or not overlay_cli.is_file():
                continue
            coverage_dir = isolated / "source-coverage" / f"source-{index:04d}"
            _run([sys.executable, str(overlay_cli), "--source", str(copied),
                  "--output", str(coverage_dir)], "file_builder")
            detector_manifest_path = coverage_dir / "detector-manifest.json"
            detector_manifest = _load(detector_manifest_path)
            if (not isinstance(detector_manifest, dict)
                    or detector_manifest.get("source_sha256") != source["sha256"]):
                raise Failure("file_builder")
            detector_sha256 = _file_snapshot(detector_manifest_path)[1]
            coverage_sources.append({
                "source_path": source["path"], "detector_manifest_sha256": detector_sha256,
                "manifest": detector_manifest,
            })
            for page in detector_manifest.get("pages", []):
                for system in page.get("systems", []):
                    tile = coverage_dir / _text(system.get("coverage_tile"))
                    tile_sha256 = _file_snapshot(tile)[1]
                    if tile_sha256 != system.get("coverage_tile_sha256"):
                        raise Failure("file_builder")
                    visual_images.append(tile)
                    expected_visuals.append({
                        "source_path": source["path"], "page": page.get("page"),
                        "system": system.get("system"), "sha256": tile_sha256,
                        "kind": "recognized_system_tile",
                        "detector_manifest_sha256": detector_sha256,
                    })
        coverage_manifest = isolated / "coverage-manifest.json"
        _write(coverage_manifest, {"version": 1, "sources": coverage_sources})
        visual_manifest = isolated / "visual-manifest.json"
        _write(visual_manifest, {"version": 1, "visual_sources": expected_visuals})
        runtime = isolated / "controller-runtime"
        runtime.mkdir()
        runner_source = Path(args.agent_runner).resolve()
        isolated_runner = runtime / runner_source.name
        shutil.copyfile(runner_source, isolated_runner)
        for sibling in ("token_budget.py", "config.json"):
            source = runner_source.parent / sibling
            if source.is_file():
                shutil.copyfile(source, runtime / sibling)
        isolated_schema = runtime / "gig_step_result.schema.json"
        shutil.copyfile(args.runner_schema, isolated_schema)
        census = isolated / "source-census.json"
        prompt = isolated / "prompt.txt"
        prompt.write_text(
            "You are the Paid source-only census owner. Work only in this isolated workdir. Read source-manifest.json, "
            "the copied requirements, and every copied buyer source. You cannot read any candidate artifact, producer "
            "ledger, output manifest, project workspace, release tree, repository, docs, or spec. Inspect only the "
            "controller-approved skills copied under skills/, read an applicable SKILL.md fully when one applies, and "
            "use its proven local CLI. Never search outside this isolated workdir. "
            "Every image listed in visual-manifest.json is attached as native vision input; visually inspect every one. "
            "Read coverage-manifest.json. Inspect every kind=recognized_system_tile: its top half is the source and its "
            "bottom half has every Audiveris-recognized notehead filled fluorescent green. Any notehead that remains black "
            "in the bottom half is an omission; any green mark without a source notehead is a false positive. Add "
            "coverage_findings with exactly one object per tile: source_path, page, system, source_sha256, tile_sha256, "
            "omissions, false_positive_detector_ids. omissions is a list of complete census-item objects using the same "
            "source_locator, exact_semantic_value, modifiers, verification fields as items. A recognized count or repeated "
            "generic sentence is not coverage evidence. Every omission must also appear exactly in items. "
            "Create source-census.json with version=1, status=PASS, requirements_sha256, sources copied exactly from the "
            "source manifest using only path and sha256, visual_sources copied exactly from visual-manifest.json, and a "
            "nonempty items array. Enumerate the complete atomic source set "
            "needed to prove the requested transformation. Every item must contain nonempty source_locator, "
            "exact_semantic_value, modifiers, and verification strings. When visual_sources is nonempty, every item's "
            "verification must cite the exact sha256 of the attached page image used to adjudicate it. For notation, "
            "enumerate every notehead including "
            "chords, ties, written accidentals, and carried accidentals; OMR counts are corroboration only, so adjudicate "
            "all source-only detector disagreements from source pixels. Do not infer anything from a candidate count. "
            "Do not create or inspect any deliverable. Return gig_step_result status ok only after the census exists.",
            encoding="utf-8",
        )
        evidence = isolated / "evidence"
        profile = isolated / "source-only.sb"
        quoted_projects = json.dumps(str(root.resolve().parent))
        quoted_live_evidence = json.dumps(str(root.resolve().parent.parent / "evidence"))
        quoted_delivery_evidence = json.dumps(str(root.resolve().parent.parent / "delivery-evidence"))
        quoted_releases = json.dumps(str(code_root.resolve().parent))
        quoted_checkout = json.dumps(str(Path.home() / "life-manager"))
        profile.write_text(
            "(version 1)\n(allow default)\n"
            f"(deny file-read* (subpath {quoted_projects}))\n"
            f"(deny file-read* (subpath {quoted_live_evidence}))\n"
            f"(deny file-read* (subpath {quoted_delivery_evidence}))\n"
            f"(deny file-read* (subpath {quoted_releases}))\n"
            f"(deny file-read* (subpath {quoted_checkout}))\n"
            f"(deny file-write* (subpath {quoted_projects}))\n",
            encoding="utf-8",
        )
        started = time.time_ns()
        command = [
            "/usr/bin/sandbox-exec", "-f", str(profile), sys.executable, str(isolated_runner),
            "--task-class", "escalation-agent", "--candidate-model", PAID_FILE_MODEL,
            "--prompt-file", str(prompt), "--schema", str(isolated_schema),
            "--evidence-dir", str(evidence), "--task-label", "paid-source-census",
            "--loop", "gig", "--workdir", str(isolated), "--timeout-seconds", "3600",
            "--escalation-reason", "Independent source-only census before paid build",
        ]
        for image in visual_images:
            command += ["--image", str(image)]
        _run(command, "file_builder")
        result, proof = _file_runner_result(evidence, task_label="paid-source-census", started_ns=started)
        value = _load(census)
        items = value.get("items") if isinstance(value, dict) else None
        fields = ("source_locator", "exact_semantic_value", "modifiers", "verification")
        expected_sources = [{"path": row["path"], "sha256": row["sha256"]} for row in sources]
        overlay_rows = [row for row in expected_visuals if row.get("kind") == "recognized_system_tile"]
        source_rows = {row["path"]: row for row in expected_sources}
        source_image_rows = {(row["source_path"], row["page"]): row for row in expected_visuals
                             if row.get("kind") == "source"}
        findings = value.get("coverage_findings") if isinstance(value, dict) else None
        expected_findings = {(row["source_path"], row["page"], row["system"]): row for row in overlay_rows}
        findings_by_page = ({(row.get("source_path"), row.get("page"), row.get("system")): row for row in findings}
                            if isinstance(findings, list) and all(isinstance(row, dict) for row in findings) else {})
        coverage_valid = not overlay_rows or set(findings_by_page) == set(expected_findings)
        for key, overlay in expected_findings.items():
            finding = findings_by_page.get(key, {})
            source = source_rows.get(key[0], {})
            source_image = source_image_rows.get(key[:2], {})
            omissions = finding.get("omissions")
            false_positives = finding.get("false_positive_detector_ids")
            coverage_valid = coverage_valid and (
                finding.get("source_sha256") == source.get("sha256")
                and finding.get("tile_sha256") == overlay.get("sha256")
                and isinstance(omissions, list) and isinstance(false_positives, list)
                and all(isinstance(omission, dict)
                        and all(_text(omission.get(field)) for field in fields)
                        and source_image.get("sha256") in _text(omission.get("verification"))
                        and overlay.get("sha256") in _text(omission.get("verification"))
                        and any(all(item.get(field) == omission.get(field) for field in fields)
                                for item in items or []) for omission in omissions)
            )
        if (result.get("status") != "ok" or value.get("version") != 1 or value.get("status") != "PASS"
                or value.get("requirements_sha256") != requirements_sha256
                or value.get("sources") != expected_sources
                or value.get("visual_sources") != expected_visuals
                or not coverage_valid
                or not isinstance(items, list) or not items
                or any(not isinstance(item, dict) or any(not _text(item.get(field)) for field in fields)
                       or (expected_visuals and not any(
                           visual["sha256"] in _text(item.get("verification"))
                           for visual in expected_visuals)) for item in items)):
            raise Failure("file_builder")
        target = root / "acceptance" / "controller-source-census-v1.json"
        shutil.copyfile(census, target)
        durable_evidence = root / "evidence" / "agent-PAID_SOURCE_CENSUS" / requirements_sha256
        shutil.copytree(evidence, durable_evidence, dirs_exist_ok=True)
        durable_pages = durable_evidence / "source-pages"
        durable_pages.mkdir(parents=True, exist_ok=True)
        durable_visuals: list[dict[str, Any]] = []
        for image, visual in zip(visual_images, expected_visuals):
            durable = durable_pages / image.name
            shutil.copyfile(image, durable)
            durable_visuals.append({**visual, "path": str(durable)})
        _write(root / "context" / "paid-source-census.json", {
            "version": 1, "policy_version": PAID_SOURCE_CENSUS_VERSION,
            "requirements_sha256": requirements_sha256, "sources": sources,
            "visual_sources": durable_visuals,
            "census_path": str(target.resolve()), "census_sha256": _file_snapshot(target)[1],
            **proof,
        })
        return target


def _validated_source_census(root: Path, receipt: dict[str, Any],
                             sources: list[dict[str, Any]]) -> None:
    binding = receipt.get("independent_source_census")
    trust_path = root / "context" / "paid-source-census.json"
    trust = _load(trust_path) if _regular_file(trust_path) else None
    census_path = root / "acceptance" / "controller-source-census-v1.json"
    expected_sources = _source_census_inputs(root)
    if not expected_sources and binding is None and trust is None and not census_path.exists():
        return
    trusted_sources = trust.get("sources") if isinstance(trust, dict) else None
    receipt_sources = {(str(source.get("path")), source.get("sha256")) for source in sources if isinstance(source, dict)}
    controller_receipt_path = (binding.get("controller_receipt_path") if isinstance(binding, dict) else None) or receipt.get("controller_receipt_path")
    controller_receipt_sha256 = (binding.get("controller_receipt_sha256") if isinstance(binding, dict) else None) or receipt.get("controller_receipt_sha256")
    if (not isinstance(binding, dict) or not isinstance(trust, dict)
            or binding.get("path") != str(census_path.resolve())
            or binding.get("sha256") != _file_snapshot(census_path)[1]
            or controller_receipt_path != str(trust_path.resolve())
            or controller_receipt_sha256 != _file_snapshot(trust_path)[1]
            or trust.get("policy_version") != PAID_SOURCE_CENSUS_VERSION
            or not isinstance(trusted_sources, list)
            or any((source["path"], source["sha256"]) not in receipt_sources for source in trusted_sources)):
        raise ValueError("invalid controller-owned independent source census")


def _file_bundle_snapshots(
    root: Path, *, validate_source_census: bool = True,
) -> tuple[dict[str, Any], dict[str, tuple[int, str]]]:
    manifest_path = root / "delivery" / "paid-work-result.json"
    manifest = _load(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError("invalid file manifest")
    paths = {
        "manifest": manifest_path,
        "requirements": Path(_text(manifest.get("requirements_path"))),
        "artifact": Path(_text(manifest.get("artifact_path"))),
        "acceptance": Path(_text(manifest.get("acceptance_evidence_path"))),
    }
    correspondence = _text(manifest.get("source_correspondence_path"))
    if correspondence:
        paths["source_correspondence"] = Path(correspondence)
    resolved_root = root.resolve()
    snapshots: dict[str, tuple[int, str]] = {}
    for key, path in paths.items():
        resolved = path.resolve()
        resolved.relative_to(resolved_root)
        snapshots[key] = _file_snapshot(resolved)
    if correspondence:
        receipt = _load(paths["source_correspondence"])
        mappings = receipt.get("mappings") if isinstance(receipt, dict) else None
        sources = receipt.get("sources") if isinstance(receipt, dict) else None
        if (not isinstance(receipt, dict)
                or receipt.get("version") != 1 or receipt.get("status") != "PASS"
                or receipt.get("artifact_sha256") != snapshots["artifact"][1]
                or not isinstance(sources, list) or not sources
                or not isinstance(mappings, list) or not mappings):
            raise ValueError("invalid source correspondence receipt")
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("invalid source correspondence source")
            source_path = Path(_text(source.get("path")))
            source_path = (resolved_root / source_path if not source_path.is_absolute()
                           else source_path).resolve()
            source_path.relative_to(resolved_root)
            if source.get("sha256") != _file_snapshot(source_path)[1]:
                raise ValueError("stale source correspondence source")
        fields = ("source_locator", "output_locator", "correspondence", "verification")
        if any(not isinstance(mapping, dict) or any(not _text(mapping.get(field)) for field in fields)
               for mapping in mappings):
            raise ValueError("invalid source correspondence mapping")
        if validate_source_census:
            _validated_source_census(root, receipt, sources)
    return manifest, snapshots


def _normalize_acceptance_delta(root: Path) -> None:
    manifest_path = root / "delivery" / "paid-work-result.json"
    manifest = _load(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("status") != "ok":
        raise ValueError("invalid file manifest")
    acceptance_path = Path(_text(manifest.get("acceptance_evidence_path"))).resolve()
    acceptance_path.relative_to(root.resolve())
    acceptance = _load(acceptance_path)
    if not isinstance(acceptance, dict):
        raise ValueError("invalid acceptance delta")
    delta = acceptance.get("acceptance_delta")
    if (acceptance.get("status") != "PASS" or not isinstance(delta, list)
            or not delta or any(not isinstance(value, str) or not value.strip() for value in delta)):
        raise ValueError("invalid acceptance delta")
    if manifest.get("acceptance_delta") != delta:
        manifest["acceptance_delta"] = delta
        _write(manifest_path, manifest)


def _file_immutable_inputs(root: Path, context: Path) -> dict[str, tuple[int, str]]:
    compiled = _load(context)
    read_first = compiled.get("combined_context", {}).get("read_these_first")
    if not isinstance(read_first, list):
        raise ValueError("invalid file builder inputs")
    resolved_root = root.resolve()
    snapshots = {str(context.resolve()): _file_snapshot(context)}
    for raw in read_first:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("invalid file builder input")
        candidate = Path(raw)
        path = (resolved_root / candidate if not candidate.is_absolute() else candidate).resolve()
        path.relative_to(resolved_root)
        snapshots[str(path)] = _file_snapshot(path)
    snapshots[str((root / "context" / "paid-work-decision.json").resolve())] = _file_snapshot(
        root / "context" / "paid-work-decision.json"
    )
    snapshots[str((root / "state.json").resolve())] = _file_snapshot(root / "state.json")
    operator_policy = root / "context" / PAID_FILE_OPERATOR_POLICY
    if operator_policy.exists():
        snapshots[str(operator_policy.resolve())] = _file_snapshot(operator_policy)
    for path in (root / "context" / "paid-source-census.json",
                 root / "acceptance" / "controller-source-census-v1.json"):
        if path.is_file():
            snapshots[str(path.resolve())] = _file_snapshot(path)
    return snapshots


def _resumable_file_bundle(root: Path, stable: Path, feedback: str) -> tuple[dict[str, Any], dict[str, tuple[int, str]]] | None:
    try:
        _normalize_acceptance_delta(root)
        manifest, snapshots = _file_bundle_snapshots(root)
        requirements = _load(Path(_text(manifest.get("requirements_path"))))
        observed = _text(requirements.get("feedback_first_observed_at") or requirements.get("observed_at"))
        if requirements.get("feedback_sha256") != feedback or not observed:
            return None
        observed_at = datetime.fromisoformat(observed).timestamp()
        artifact_stat = Path(_text(manifest.get("artifact_path"))).stat()
        if max(artifact_stat.st_mtime, artifact_stat.st_ctime) < observed_at:
            return None
        ok, _ = paid_work_evidence.validate_paid_work(
            root, stable, require_delivery_evidence=False, artifact_judge=paid_work_evidence.STRUCTURE_ONLY,
            allow_fresh_blocked_for_review=True,
        )
        return (manifest, snapshots) if ok else None
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _blocked_file_bundle_for_recheck(
    root: Path,
    review_state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, tuple[int, str]]] | None:
    """Return the exact previously blocked artifact for review before any rebuild.

    New buyer context can resolve a blocker, add a repairable requirement, or merely add
    urgency.  None of those cases authorizes discarding the old safety decision and
    running the owner first.  A fresh reviewer must classify the same artifact against
    the new cumulative context; only a concrete ``needs_revision`` verdict may re-enter
    the builder.
    """
    if (not isinstance(review_state, dict)
            or review_state.get("state") != "REVIEW_BLOCKED"
            or review_state.get("mode") != "file"):
        return None
    try:
        manifest, snapshots = _file_bundle_snapshots(root, validate_source_census=False)
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return (manifest, snapshots) if review_state.get("artifact_sha256") == snapshots["artifact"][1] else None


def _validate_file_authorization(root: Path, stable: Path, feedback: str,
                                 requirements_sha256: str) -> dict[str, Any]:
    _policy_path, _policy, operator_policy_sha256 = _file_operator_policy(
        root, feedback, requirements_sha256,
    )
    receipt = _load(root / "context" / "paid-file-authorization.json")
    manifest, snapshots = _file_bundle_snapshots(root)
    verifier = root / "evidence" / "agent-PAID_FILE_VERIFY"
    summary = _runner_summary(verifier)
    result_path = _consultation_result_path(verifier, summary)
    result = _load(result_path)
    if (not isinstance(receipt, dict) or receipt.get("version") != 4
            or receipt.get("buyer_feedback_sha256") != feedback
            or receipt.get("requirements_sha256") != requirements_sha256
            or receipt.get("review_policy_version") != PAID_FILE_POLICY_VERSION
            or receipt.get("operator_policy_sha256") != operator_policy_sha256
            or receipt.get("manifest_sha256") != snapshots["manifest"][1]
            or receipt.get("artifact_sha256") != snapshots["artifact"][1]
            or receipt.get("acceptance_sha256") != snapshots["acceptance"][1]
            or ("source_correspondence" in snapshots and receipt.get("source_correspondence_sha256")
                != snapshots["source_correspondence"][1])
            or receipt.get("verifier_summary_sha256") != hashlib.sha256((verifier / "summary.json").read_bytes()).hexdigest()
            or receipt.get("verifier_result_sha256") != hashlib.sha256(result_path.read_bytes()).hexdigest()
            or receipt.get("reviewer_model") != PAID_FILE_MODEL
            or result.get("verdict") != "deliverable"
            or not _text(result.get("reason"))
            or summary.get("task_label") != "paid-file-verifier"
            or summary.get("task_class") != "escalation-agent"
            or summary.get("escalated") is not True
            or summary.get("selected_provider") != "codex"
            or summary.get("selected_model") != PAID_FILE_MODEL):
        raise ValueError("stale file authorization")
    ok, errors = paid_work_evidence.validate_paid_work(
        root, stable, artifact_judge=lambda *_: ("deliverable", _text(result.get("reason"))),
    )
    if not ok:
        raise ValueError("invalid authorized file bundle:" + ",".join(errors))
    return manifest


def _build_and_authorize_file(args, item_path: Path, root: Path, item: dict[str, Any],
                              feedback: str, requirements_sha256: str, base: Path,
                              stable: Path) -> dict[str, Any]:
    code_root = REPO_ROOT
    context = root / "context" / "current.json"
    _run([sys.executable, str(args.context_compiler), "--project-root", str(root),
          "--queue-item", str(item_path), "--output", str(context)], "context_compile")
    operator_policy_path, operator_policy, operator_policy_sha256 = _file_operator_policy(
        root, feedback, requirements_sha256,
    )
    resumed = _resumable_file_bundle(root, stable, feedback)
    review_state_path = root / "context" / "paid-review-state.json"
    review_state = _load(review_state_path) if _regular_file(review_state_path) else {}
    finding = ""
    blocked_recheck_finding = ""
    if (resumed is not None and isinstance(review_state, dict)
            and review_state.get("state") == "REPAIR_PENDING"
            and review_state.get("mode") == "file"
            and review_state.get("review_policy_version") == PAID_FILE_POLICY_VERSION
            and review_state.get("operator_policy_sha256") == operator_policy_sha256
            and review_state.get("buyer_feedback_sha256") == feedback
            and review_state.get("requirements_sha256") == requirements_sha256
            and review_state.get("artifact_sha256") == resumed[1]["artifact"][1]):
        finding = (_text(review_state.get("finding"))
                   or "The prior reviewer withheld deliverable authorization; rebuild and prove the corrected artifact.")
    if (resumed is not None and isinstance(review_state, dict)
            and review_state.get("state") == "REVIEW_BLOCKED"
            and review_state.get("mode") == "file"
            and review_state.get("review_policy_version") == PAID_FILE_POLICY_VERSION
            and review_state.get("operator_policy_sha256") == operator_policy_sha256
            and review_state.get("buyer_feedback_sha256") == feedback
            and review_state.get("requirements_sha256") == requirements_sha256
            and review_state.get("artifact_sha256") == resumed[1]["artifact"][1]):
        raise Failure("file_review_blocked")
    if resumed is None:
        blocked_bundle = _blocked_file_bundle_for_recheck(root, review_state)
        if blocked_bundle is not None:
            resumed = blocked_bundle
            blocked_recheck_finding = (_text(review_state.get("finding"))
                                       or "The prior fresh reviewer could not authorize this exact artifact.")
    source_census = (_prepare_source_census(args, root, requirements_sha256, code_root)
                     if resumed is None or finding else None)
    census_instruction = (
        "The controller has no source-census inputs for this revision. Set independent_source_census "
        "to null and do not invent a census, controller receipt, path, or hash."
        if source_census is None else
        f"The controller-owned source-only census is {source_census}. Bind independent_source_census "
        "to its exact absolute path and SHA256 plus the exact absolute controller_receipt_path and "
        "controller_receipt_sha256 of context/paid-source-census.json."
    )
    bound = _file_immutable_inputs(root, context)
    requirements_before = _requirements_snapshot(root)
    builder_prompt = base / "file" / "builder.prompt.txt"
    builder_prompt.parent.mkdir(parents=True, exist_ok=True)
    owner_instructions = (
        "You are the sole paid task owner. Work only inside PROJECT_ROOT. Read context/current.json, "
        "every combined_context.read_these_first file, requirements/live-buyer-reply.json, and state.json. "
        f"Before creating anything, search {code_root} with rg for existing relevant SKILL.md files and production CLIs, "
        "read the applicable skill fully, and use its proven CLI contract instead of reimplementing the workflow. "
        "Choose tools from the complete buyer context and required output, never from a hardcoded buyer name, category, or keyword router. "
        "Create the actual buyer-facing deliverable that satisfies the complete accumulated request, not a plan, "
        "status report, transaction summary, or promise. Create exactly the next vN artifact under delivery/, "
        "a JSON acceptance file with status PASS and a nonempty acceptance_delta, and delivery/paid-work-result.json "
        "binding project_root, requirements_path, artifact_path, artifact_version, acceptance_evidence_path, "
        "acceptance_status, acceptance_delta, and package_sha256; copy acceptance_delta exactly from the acceptance "
        "file without paraphrasing it. Self-check every accumulated requirement against the "
        "actual produced artifact, open/read it, and correct omissions before claiming PASS. "
        "When a prior review identifies one defect, derive its failure class, enumerate analogous instances across the "
        "complete source and output, repair every confirmed instance, and add class-wide regression evidence. Never patch "
        "only the named locator while leaving the same defect elsewhere. "
        "When the deliverable transforms, edits, annotates, transcribes, or restructures buyer-provided source material, "
        "also create a version-1 PASS JSON source-correspondence receipt under acceptance/ and bind its absolute path as "
        "source_correspondence_path in paid-work-result.json. The receipt must bind artifact_sha256, list every relied-on "
        "source as an in-project path plus exact sha256, and contain nonempty mappings with source_locator, output_locator, "
        "correspondence, and verification. Locators must identify real source/output regions precisely enough for a fresh "
        "reviewer to sample them. When completeness requires an independent source census, derive that census without reading "
        "or importing any candidate ledger, detector or classifier, producer selection logic, output manifest, or include/exclude "
        "decision used by the production path. Running shared logic earlier or under a different filename is circular proof, not "
        "independent evidence. Fix the complete set of source items from the source alone before reading the candidate output; "
        "candidate output pixels, annotations, or manifests must never select, filter, or confirm which source items count. "
        "Independently compare every source item's exact semantic value, including modifiers, with the actual output value; a "
        "derived expected natural value or nearby coloured mark is not proof of the value actually delivered. Never invent "
        f"correspondence from counts, layout, or an owner assertion. {census_instruction} "
        "The owner must not create a census generator, "
        "replace the controller census, embed a prior producer ledger, or claim manual independence. "
        "Distinguish buyer-visible deliverable requirements from application qualifications and preferred production tools. "
        "Never claim use of an unavailable tool. A named tool is a delivery blocker only when the contract explicitly requires "
        "that editable source/project or proof of that tool's use as a delivered output; otherwise use the proven available CLI "
        "to create the requested buyer-visible result. "
        "Do not use Docker, Hermes, gig_pass.sh, network submission, browser mutation, fake data, placeholders, or mocks. "
        "Return the gig_step_result schema only after those files exist."
    )
    if operator_policy_path is not None:
        owner_instructions += (
            f" Read the exact account-owner policy {operator_policy_path} (SHA256 "
            f"{operator_policy_sha256}) and obey its scoped directives: "
            f"{json.dumps(operator_policy['directives'], ensure_ascii=False)}. It may resolve workflow/tool conflicts, "
            "but it never permits a false provenance claim or waives buyer-visible quality."
        )
    verifier_prompt = base / "file" / "verifier.prompt.txt"
    verifier_evidence = root / "evidence" / "agent-PAID_FILE_VERIFY"
    verdict: dict[str, Any] = {}
    proof: dict[str, Any] = {}
    for review_round in range(1, 4):
        if resumed is None or finding:
            correction = (" A fresh reviewer rejected the prior artifact. Create a corrected next version that resolves "
                          f"this finding: {finding}" if finding else "")
            builder_prompt.write_text(owner_instructions + correction, encoding="utf-8")
            owner_evidence = root / "evidence" / "agent-PAID_FILE_OWNER"
            owner_started = time.time_ns()
            _run([sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
                  "--candidate-model", PAID_FILE_MODEL,
                  "--prompt-file", str(builder_prompt), "--schema", str(args.runner_schema),
                  "--evidence-dir", str(owner_evidence), "--task-label", "paid-file-owner",
                  "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "3600",
                  "--escalation-reason", "One Sol paid owner must build the buyer deliverable"], "file_builder")
            owner, _ = _file_runner_result(owner_evidence, task_label="paid-file-owner", started_ns=owner_started)
            if owner.get("status") != "ok" or step_result_status.status_from_evidence(owner_evidence) != "ok":
                raise Failure("file_builder")
            _normalize_acceptance_delta(root)
            manifest, snapshots = _file_bundle_snapshots(root)
            for key in ("manifest", "artifact", "acceptance"):
                path = (root / "delivery" / "paid-work-result.json" if key == "manifest" else
                        Path(manifest[f"{key}_path" if key == "artifact" else "acceptance_evidence_path"]))
                stat = path.stat()
                fresh_ns = max(stat.st_mtime_ns, stat.st_ctime_ns) if key == "artifact" else stat.st_mtime_ns
                if fresh_ns <= owner_started:
                    raise Failure("file_builder")
        else:
            manifest, snapshots = resumed
        if (_requirements_snapshot(root) != requirements_before
                or _file_immutable_inputs(root, context) != bound
                or paid_remote_result.requirements_digest(root, feedback) != requirements_sha256):
            raise Failure("requirements_toctou")
        ok, errors = paid_work_evidence.validate_paid_work(
            root, stable, require_delivery_evidence=False, artifact_judge=paid_work_evidence.STRUCTURE_ONLY,
            allow_fresh_blocked_for_review=True,
        )
        if not ok:
            raise Failure("file_validation")
        review_images = _file_review_images(root, snapshots["artifact"][1], finding)
        audit_path, audit_images = (None, [])
        if "source_correspondence" in snapshots:
            audit_path, audit_images = _prepare_blind_output_audit(
                args, root, manifest, snapshots["artifact"][1], snapshots["source_correspondence"][1],
            )
            review_images += [path for path in audit_images if path not in review_images]
        reference_images = _file_reference_images(root, manifest)
        if Path(manifest["artifact_path"]).suffix.casefold() in {".mp4", ".mov", ".m4v", ".webm"} and not review_images:
            raise Failure("file_visual_evidence")
        visual_snapshots = {
            str(path): _file_snapshot(path) for path in review_images + reference_images
        }
        audit_snapshot = _file_snapshot(audit_path) if audit_path is not None else None
        policy_instruction = (
            "No scoped account-owner policy exists."
            if operator_policy_path is None else
            f"The exact account-owner policy is {operator_policy_path} with SHA256 {operator_policy_sha256}. "
            f"Its scoped directives are {json.dumps(operator_policy['directives'], ensure_ascii=False)}. "
            "Honor those directives when they resolve workflow/tool conflicts; they do not waive buyer-visible quality "
            "and never authorize a false provenance claim."
        )
        blocked_recheck_instruction = (
            f"This exact artifact was previously REVIEW_BLOCKED for: {blocked_recheck_finding} "
            "The cumulative buyer context or policy has since changed. Decide first whether the new input actually resolves "
            "that blocker. Added urgency, repetition, or a request for explanation does not resolve missing proof. "
            if blocked_recheck_finding else ""
        )
        verifier_prompt.write_text(
            f"You are a fresh read-only Sol reviewer. Independently read the actual artifact {manifest['artifact_path']}, "
            f"the complete accumulated requirements {manifest['requirements_path']}, acceptance evidence "
            f"{manifest['acceptance_evidence_path']}, and compiled context {context}. The exact artifact SHA256 is "
            f"{snapshots['artifact'][1]}, the exact requirements file SHA256 is {snapshots['requirements'][1]}, and the "
            f"accumulated requirements digest is {requirements_sha256}. Inspect the buyer-visible output "
            "itself and every applicable raw domain/Skill receipt. Reject plans, owner assertions, placeholders, corrupt files, "
            "missing requirements, unsupported claims, visual or semantic defects, and unproved provenance. Distinguish "
            "buyer-visible deliverable requirements from application qualifications and preferred production tools. Never "
            "invent tool provenance; require a named tool only when the contract explicitly requires its editable source/project "
            "or proof of its use as a delivered output. current_state identifies the last buyer-visible artifact and may be older "
            "than this exact candidate; that is not a candidate provenance mismatch. Never mutate, "
            f"submit, send, or rewrite any project file. {policy_instruction} Candidate review images attached to this "
            f"invocation are exactly {json.dumps([str(path) for path in review_images], ensure_ascii=False)}. Visual "
            f"reference images attached to this invocation are exactly "
            f"{json.dumps([str(path) for path in reference_images], ensure_ascii=False)}. You MUST visually inspect every "
            "attached candidate and reference image. "
            f"The controller-owned blind output audit is {audit_path} with SHA256 "
            f"{audit_snapshot[1] if audit_snapshot else 'none'}; its vision agent saw only isolated hash-bound crops and no "
            "expected values. Verify that receipt and independently inspect the same attached crops. Never claim a visual "
            "defect in a frame that was not attached; use raw "
            "receipts only for nonvisual facts about the remaining frames. Return needs_revision only for a concrete, "
            "For any transformation, edit, annotation, transcription, or restructuring of buyer-provided source material, "
            "require a source-correspondence receipt bound by the manifest and independently sample its source/output locators. "
            "Counts, layout checks, and owner assertions do not prove semantic correspondence. A missing or false receipt must "
            "never be accepted. Trace the raw receipt generators: an alleged independent source census is circular and must be "
            "rejected when it shares a candidate ledger, detector or classifier, producer selection logic, output manifest, or "
            "include/exclude decision with the production path. Executing shared logic before the manifest or renaming it does not "
            "make it independent. Reject any census whose source-item set is selected, filtered, or confirmed using candidate "
            "output pixels, annotations, or manifests; the complete source set must be fixed from source-only evidence before the "
            "candidate is read. Verify modifiers and the actual output semantic value, not merely a derived natural value or a "
            "nearby coloured mark. When the exact buyer source and candidate are locally readable with existing available tools, "
            f"{blocked_recheck_instruction}"
            "a missing receipt is itself a concrete correctable defect: return needs_revision and require the owner to create "
            "the hash-bound locator mapping, independently verify it, and correct the artifact wherever the mapping exposes a "
            "mismatch. Return undeterminable instead only when producing or checking truthful correspondence requires an "
            "unavailable tool, paid license, signup, account change, or inaccessible source. "
            "correctable buyer-visible defect proved by an attached candidate/reference comparison or deterministic receipt, "
            "and state the requirement, evidence, and repair. Before returning one repairable finding, inspect the complete "
            "source and output for analogous instances of the same failure class and include every confirmed instance in one "
            "bounded finding when the available evidence permits it. A repair is correctable only when the project or release proves "
            "that every tool needed for that specific repair is currently available and the repair needs no new paid license, "
            "signup, account change, or false provenance claim. If a candidate has both a deterministic repairable defect and "
            "a separate unavailable-tool or provenance blocker, return needs_revision for the repairable defect first; inspect "
            "the corrected artifact in the next round, then return undeterminable only if the blocker remains. If required "
            "provenance is absent and no independently repairable defect remains, return undeterminable, never needs_revision. "
            "If visual evidence is insufficient, return undeterminable; "
            "undeterminable and the semantic refusal verdicts never authorize a rebuild. Return only artifact_judgement "
            "schema; verdict=deliverable only when every non-overridden accumulated requirement is proved by direct evidence.",
            encoding="utf-8",
        )
        verifier_started = time.time_ns()
        verifier_command = [
            sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
            "--candidate-model", PAID_FILE_MODEL,
            "--prompt-file", str(verifier_prompt), "--schema", str(args.artifact_schema),
            "--evidence-dir", str(verifier_evidence), "--task-label", "paid-file-verifier",
            "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "1800", "--read-only",
            "--escalation-reason", "Fresh independent Sol review before paid submission",
        ]
        for image in review_images + reference_images:
            verifier_command += ["--image", str(image)]
        _run(verifier_command, "file_verifier")
        verdict, proof = _file_runner_result(
            verifier_evidence, task_label="paid-file-verifier", started_ns=verifier_started,
        )
        disposition = _file_review_disposition(verdict.get("verdict"))
        if disposition == "approve" and _text(verdict.get("reason")):
            break
        finding = _text(verdict.get("reason")) or "The reviewer did not prove the artifact deliverable."
        if disposition != "repair":
            _write(root / "context" / "paid-review-state.json", {
                "version": 1, "state": "REVIEW_BLOCKED", "mode": "file",
                "review_policy_version": PAID_FILE_POLICY_VERSION,
                "operator_policy_sha256": operator_policy_sha256,
                "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
                "artifact_sha256": snapshots["artifact"][1], "round": review_round,
                "verdict": _text(verdict.get("verdict")), "finding": finding,
            })
            raise Failure("file_review_blocked")
        _write(root / "context" / "paid-review-state.json", {
            "version": 1, "state": "REPAIR_PENDING", "mode": "file",
            "review_policy_version": PAID_FILE_POLICY_VERSION,
            "operator_policy_sha256": operator_policy_sha256,
            "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
            "artifact_sha256": snapshots["artifact"][1], "round": review_round, "finding": finding,
        })
        resumed = None
    else:
        raise Failure("file_verifier")

    current_manifest, current_snapshots = _file_bundle_snapshots(root)
    if (current_manifest != manifest or current_snapshots != snapshots
            or _requirements_snapshot(root) != requirements_before
            or _file_immutable_inputs(root, context) != bound
            or (audit_path is not None and _file_snapshot(audit_path) != audit_snapshot)
            or {str(path): _file_snapshot(path) for path in review_images + reference_images}
            != visual_snapshots):
        raise Failure("file_toctou")
    _write(stable, manifest)
    ok, errors = paid_work_evidence.validate_paid_work(
        root, stable, artifact_judge=lambda *_: ("deliverable", _text(verdict.get("reason"))),
        allow_fresh_blocked_for_review=True,
    )
    if not ok:
        raise Failure("file_validation")
    paid_work_evidence.resolve_fresh_blocked_after_review(
        root, manifest["requirements_path"], feedback, snapshots["artifact"][1],
    )
    ok, errors = paid_work_evidence.validate_paid_work(
        root, stable, artifact_judge=lambda *_: ("deliverable", _text(verdict.get("reason"))),
    )
    if not ok:
        raise Failure("file_validation")
    _write(root / "context" / "paid-file-authorization.json", {
        "version": 4, "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
        "review_policy_version": PAID_FILE_POLICY_VERSION,
        "operator_policy_sha256": operator_policy_sha256,
        "manifest_sha256": snapshots["manifest"][1], "artifact_sha256": snapshots["artifact"][1],
        "acceptance_sha256": snapshots["acceptance"][1],
        **({"source_correspondence_sha256": snapshots["source_correspondence"][1]}
           if "source_correspondence" in snapshots else {}),
        "reviewer_model": PAID_FILE_MODEL,
        "verifier_summary_sha256": proof["summary_sha256"],
        "verifier_result_sha256": proof["result_sha256"],
    })
    _write(root / "context" / "paid-review-state.json", {
        "version": 1, "state": "APPROVED", "mode": "file",
        "review_policy_version": PAID_FILE_POLICY_VERSION,
        "operator_policy_sha256": operator_policy_sha256,
        "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
        "artifact_sha256": snapshots["artifact"][1], "round": review_round,
    })
    return manifest


def _prepare_file(args, item_path: Path, root: Path, item: dict[str, Any], base: Path,
                  feedback: str) -> dict[str, Any]:
    requirements_sha256 = paid_remote_result.requirements_digest(root, feedback)
    stable = delivery_queue.evidence_path(args.delivery_evidence_dir, item)
    try:
        manifest = _validate_file_authorization(root, stable, feedback, requirements_sha256)
        repaired = False
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
        manifest = _build_and_authorize_file(
            args, item_path, root, item, feedback, requirements_sha256, base, stable,
        )
        repaired = True
    evidence, blockers = delivery_queue.delivery_gate(item, args.delivery_evidence_dir, args.projects_root)
    semantic = _current_paid_decision(root, item)
    cadence = {**item, **{key: evidence[key] for key in (
        "project_root", "requirements_path", "artifact_path", "artifact_version",
        "acceptance_evidence_path", "acceptance_status", "package_sha256",
        "acceptance_delta", "recipient_access_required",
    ) if key in evidence}, "blockers": blockers,
        "buyer_formal_delivery_hold": semantic.get("delivery_stage") == "review"}
    decision = delivery_queue.delivery_decision(cadence)
    if decision.get("mode") not in {"formal", "progress"}:
        raise Failure("file_validation")
    prepared = {
        **cadence, "delivery_evidence": evidence, "delivery_action": decision["mode"],
        "formal_delivery_checkbox": decision["formal_delivery_checkbox"],
        "progress_payload": _file_progress_payload(cadence) if decision["mode"] == "progress" else None,
        "requirements_sha256": requirements_sha256, "_paid_mode": "file",
        "file_repaired": repaired, "file_manifest": str(root / "delivery" / "paid-work-result.json"),
    }
    if manifest.get("package_sha256") != evidence.get("package_sha256"):
        raise Failure("file_validation")
    return prepared


def _legacy_paid_mode(root: Path, feedback: str) -> str:
    mode = _load(root / "delivery" / "paid-work-mode.json")
    if (not isinstance(mode, dict) or mode.get("status") != "ok"
            or mode.get("feedback_sha256") != feedback
            or mode.get("mode") not in {"file", "remote", "answer"}):
        return ""
    return _text(mode.get("mode"))


def _answer_ready(root: Path, item: dict[str, Any]) -> bool:
    try:
        feedback = _text(item.get("buyer_feedback_sha256"))
        intent_path = root / "delivery" / "paid-remote-intent.json"
        intent_mode = _text(_load(intent_path).get("mode")) if intent_path.is_file() else ""
        try:
            decision = _current_paid_decision(root, item)
            answer_mode = decision.get("decision") == "actionable" and decision.get("mode") == "answer"
            semantic_current = True
        except (AttributeError, KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
            answer_mode = intent_mode == "consultation_answer" and _legacy_paid_mode(root, feedback) == "answer"
            semantic_current = False
        if (not answer_mode or (not semantic_current and intent_mode
                                and intent_mode not in {"answer", "consultation_answer"})):
            return False
        paid_remote_result.requirements_digest(root, feedback)
        if not semantic_current and _remote_revision_required(root, feedback):
            return False
        return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _remote_revision_required(root: Path, feedback: str) -> bool:
    state = _load(root / "state.json")
    cycle, live = state.get("active_feedback_cycle"), state.get("live_system_delivery")
    return (isinstance(cycle, dict) and isinstance(live, dict)
            and cycle.get("buyer_feedback_sha256") == feedback
            and cycle.get("action") == "resubmit" and cycle.get("phase") == "ACTIONABLE"
            and bool(_text(live.get("target_url"))))


def _remote_mode_required(root: Path, item: dict[str, Any], feedback: str) -> bool:
    """Use legacy remote state only when no current semantic decision is valid."""
    try:
        decision = _current_paid_decision(root, item)
        return decision.get("decision") == "actionable" and decision.get("mode") == "remote"
    except (AttributeError, KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return _legacy_paid_mode(root, feedback) == "remote" or _remote_revision_required(root, feedback)

def _repair_prompt(root: Path, item: Path, feedback: str, requirements_sha256: str,
                   verifier: bool, cdp_helper: Path,
                   review_delta: list[dict[str, str]] | None = None) -> str:
    code_root = REPO_ROOT
    role = "fresh read-only Sol remote reviewer" if verifier else "Sol paid remote owner"
    tab_owner = "paid-direct-remote-verifier" if verifier else "paid-direct-remote-builder"
    mutation = "Never mutate, click submit, or send anything." if verifier else "Mutate only the authenticated target when required, idempotently."
    target_contract = (
        f"Read builder-owned {root / 'delivery/paid-remote-intent.json'} and "
        f"{root / 'delivery/paid-remote-result.json'} without modifying them. Independently verify that live target, "
        "not the Coconala talkroom, and write only verifier-owned result/evidence."
        if verifier else
        f"Use {root / 'delivery/paid-remote-intent.json'} and {root / 'delivery/paid-remote-result.json'} when present; "
        "for a fresh cycle derive the remote target from full project context, then write both records and verify that target."
    )
    verifier_contract = (
        "Write version=1 remote-verifier-result.json under PROJECT_ROOT/evidence/agent-PAID_REMOTE_VERIFY/. "
        "On PASS write verified=true with matching feedback, target, desired/observed digest, canonical observed_state, "
        "requirements_sha256, message_sha256, customer_attachment, and fresh verifier evidence, then return runner status=ok. "
        "For a correctable mismatch write verified=false, classification=quality_mismatch, and a nonempty delta array whose "
        "objects contain only requirement, expected, observed, evidence, and repair strings, then return status=blocked. "
        "For a temporary browser failure use auth_transient or cdp_transient with no delta."
        if verifier else
        "Never write remote-verifier-result.json or verifier-owned evidence."
    )
    ownership = (
        "Never modify paid-remote-intent.json, paid-remote-result.json, paid-answer.json, or any buyer/client surface."
        if verifier else
        "Write project-owned intent/result, authenticated before/after evidence, and a natural Japanese customer_message; "
        "do not submit to Coconala or use formal delivery."
    )
    correction = ""
    if not verifier and review_delta:
        correction = ("A fresh Sol reviewer rejected the prior result. Correct every structured finding, then re-read the "
                      "live target and rewrite owner evidence: "
                      + json.dumps(review_delta, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + ". ")
    return (f"You are the {role}. PROJECT_ROOT={root}. Current queue item={item}. "
            f"Read {root / 'context/current.json'} and every read_these_first path, then read the live target. "
            f"Current buyer feedback SHA256={feedback}. {mutation} "
            f"The canonical accumulated buyer requirements are {root / 'requirements/live-buyer-reply.json'} "
            f"with accumulated requirements SHA256={requirements_sha256}. Independently read that file; its feedback_sha256 must match the current feedback. "
            f"{target_contract} "
            f"Before building raw browser automation, search {code_root} with rg for an existing production adapter and relevant SKILL.md that "
            "support the target and its live readback. Read the skill, use its CLI contract when applicable, and do not reimplement it. "
            "Choose skills from the complete project context and actual target capabilities, never from a hardcoded buyer-name or keyword router. "
            "An authenticated remote session is not proof that it is the correct account. Bind the observed account/member identity to project-owned "
            "account context before reading or mutating it, and fail closed rather than reuse another client's session or evidence. "
            "Never use Hermes or gig_pass.sh. "
            f"Use the existing CloakBrowser daily-driver with a self-owned default-context tab: "
            f"{cdp_helper} open <url> --background --owner {tab_owner}; close that exact target tab and never navigate an existing foreground tab. "
            "Invoke the helper with python3, never python. "
            "Keep the operation idempotent and skip a mutation when the desired state is already true. "
            "Use one canonical state contract: observed_state must exactly equal paid-remote-intent.json desired_state in "
            "paid-remote-result.json, authenticated after evidence, and remote-verifier-result.json; desired_state_sha256, "
            "after_state_digest, desired_digest, and observed_digest must be the SHA256 of that same canonical JSON object. "
            "Only arrays named tags or keywords are unordered; every other array is ordered, including image order. "
            f"Write requirements_sha256={requirements_sha256} into paid-remote-intent.json, paid-remote-result.json, and every owned evidence JSON. "
            "Write message_sha256 as the SHA256 of the exact customer_message into intent/result/evidence; reviewer independently checks it. "
            "Each evidence JSON must have top-level target, authenticated=true, requirements_sha256, message_sha256, and observed_state; "
            "after evidence observed_state must exactly equal the canonical desired_state. "
            "Never place credential values in commands, stdout, prompts, or evidence; read existing credential files only at runtime "
            "without echoing or hardcoding their values. "
            "Buyer-prohibited images must be compared by visual/content identity; absence of a filename is not proof. "
            "Content-identical duplicate images do not satisfy a request for another image; compare content hashes and visual identity, "
            "and never claim a replacement unless it is distinct and safe. "
            "For PDF attachments, render or extract every page with existing local PDF tools before deciding. "
            "If the buyer requires a screenshot/file, bind one exact customer_attachment with absolute path, basename, and SHA256; "
            "reviewer must inspect its real content. Otherwise it is null. "
            f"{ownership} {correction}{verifier_contract} Return only the runner schema result.")


def _normalize_builder_result(root: Path) -> None:
    intent_path, result_path = root / "delivery/paid-remote-intent.json", root / "delivery/paid-remote-result.json"
    intent, result = _load(intent_path), _load(result_path)
    raw_after = Path(_text(result.get("after_evidence")))
    after_path = (root / raw_after if not raw_after.is_absolute() else raw_after).resolve()
    after_path.relative_to(root)
    after = _load(after_path)
    if (after.get("authenticated") is True and after.get("target") == intent.get("target")
            and paid_remote_result.canonical_equal(after.get("observed_state"), intent.get("desired_state"))):
        result["observed_state"] = after["observed_state"]
        result["after_state_digest"] = intent.get("desired_state_sha256")
        _write(result_path, result)


def _consultation_attachments(root: Path) -> tuple[list[dict[str, str]], list[Path], list[Path]]:
    requirements = _load(root / "requirements" / "live-buyer-reply.json")
    rows = requirements.get("attachments") if isinstance(requirements, dict) else None
    if not isinstance(rows, list):
        raise Failure("context_compile")
    if not rows:
        return [], [], []
    expected, images, documents = [], [], []
    seen: set[tuple[str, str]] = set()
    source_parent = root / "source"
    source_dir = source_parent / "buyer-attachments"
    if (source_parent.is_symlink() or source_dir.is_symlink()
            or not source_parent.is_dir() or not source_dir.is_dir()):
        raise Failure("context_compile")
    source_root = source_dir.resolve()
    try: source_root.relative_to(root.resolve())
    except ValueError as error: raise Failure("context_compile") from error
    for row in rows:
        if not isinstance(row, dict):
            raise Failure("context_compile")
        filename, digest = _text(row.get("filename")), _text(row.get("sha256"))
        raw = Path(_text(row.get("source_path")))
        if not filename or Path(filename).name != filename or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise Failure("context_compile")
        if raw.is_symlink() or not _regular_file(raw):
            raise Failure("context_compile")
        image = raw.resolve()
        try: image.relative_to(source_root)
        except ValueError as error: raise Failure("context_compile") from error
        if image.name != f"{digest[:12]}-{filename}" or hashlib.sha256(image.read_bytes()).hexdigest() != digest:
            raise Failure("context_compile")
        identity = (filename, digest)
        if identity in seen:
            continue
        seen.add(identity)
        expected.append({"filename": filename, "sha256": digest})
        if _text(row.get("content_type")).startswith("image/") or image.suffix.lower() in {
                ".avif", ".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}:
            images.append(image)
        else:
            documents.append(image)
    return expected, images, documents


def _consultation_runner_result(evidence: Path, *, task_label: str, task_class: str,
                                model: str, started_ns: int) -> dict[str, Any]:
    summary = _runner_summary(evidence)
    expected = {"status": "success", "task_label": task_label, "task_class": task_class,
                "selected_provider": "codex", "selected_model": model}
    if task_class == "escalation-agent": expected["escalated"] = True
    if any(summary.get(key) != value for key, value in expected.items()):
        raise Failure("remote_verifier" if "verifier" in task_label else "remote_builder")
    result_path = _consultation_result_path(evidence, summary)
    now_ns = time.time_ns()
    mtimes = ((evidence / "summary.json").stat().st_mtime_ns, result_path.stat().st_mtime_ns)
    if min(mtimes) <= started_ns or max(mtimes) > now_ns + 1_000_000_000:
        raise Failure("remote_verifier" if "verifier" in task_label else "remote_builder")
    value = _load(result_path)
    if not isinstance(value, dict):
        raise Failure("remote_verifier" if "verifier" in task_label else "remote_builder")
    return value


def _consultation_result_path(evidence: Path, summary: dict[str, Any] | None = None) -> Path:
    summary = summary or _runner_summary(evidence)
    raw = Path(summary["result_path"])
    return (evidence / raw if not raw.is_absolute() else raw).resolve()


def _validate_consultation_result(value: dict[str, Any], expected: list[dict[str, str]],
                                  *, message: str | None = None) -> list[dict[str, str]]:
    reviewed = value.get("reviewed_attachments")
    if value.get("status") not in {"ok", "blocked"} or not isinstance(reviewed, list):
        raise ValueError("invalid consultation result")
    if [{"filename": row.get("filename"), "sha256": row.get("sha256")} for row in reviewed
            if isinstance(row, dict)] != expected:
        raise ValueError("consultation attachments mismatch")
    if any(not _text(row.get("observation")) for row in reviewed):
        raise ValueError("consultation observation missing")
    customer_message = _text(value.get("customer_message"))
    if not customer_message or (message is not None and customer_message != message):
        raise ValueError("consultation message mismatch")
    issues = value.get("issues")
    if not isinstance(issues, list) or any(not _text(issue) for issue in issues):
        raise ValueError("invalid consultation issues")
    return reviewed


def _validate_consultation_authorization(root: Path, feedback: str) -> dict[str, Any]:
    intent = _load(root / "delivery" / "paid-remote-intent.json")
    expected, _, _ = _consultation_attachments(root)
    requirements_sha256 = paid_remote_result.requirements_digest(root, feedback)
    desired = intent.get("desired_state") if isinstance(intent, dict) else None
    if (intent.get("version") != 2
            or intent.get("mode") not in {"answer", "consultation_answer"}
            or intent.get("buyer_feedback_sha256") != feedback
            or intent.get("requirements_sha256") != requirements_sha256 or not isinstance(desired, dict)):
        raise ValueError("invalid consultation authorization")
    message = _text(desired.get("customer_message"))
    if paid_remote_result.SECRET.search(message):
        raise ValueError("unsafe consultation answer")
    reviewed = _validate_consultation_result({"status": "ok", "customer_message": message,
        "reviewed_attachments": desired.get("reviewed_attachments"), "issues": []}, expected)
    digest = hashlib.sha256(json.dumps(desired, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    message_sha256 = hashlib.sha256(message.encode()).hexdigest()
    if (intent.get("desired_state_sha256") != digest or intent.get("message_sha256") != message_sha256
            or intent.get("target") != f"https://coconala.com/talkrooms/{_text(intent.get('talkroom_id'))}"):
        raise ValueError("invalid consultation authorization")
    owner_dir = root / "evidence" / "agent-PAID_ANSWER_OWNER"
    verifier_dir = root / "evidence" / "agent-PAID_ANSWER_VERIFY"
    owner = _consultation_runner_result(owner_dir, task_label="paid-answer-owner",
                                        task_class="escalation-agent", model=PAID_DECISION_MODEL,
                                        started_ns=0)
    verifier = _consultation_runner_result(verifier_dir, task_label="paid-answer-verifier",
                                           task_class="escalation-agent", model=PAID_DECISION_MODEL,
                                           started_ns=0)
    owner_result_path = _consultation_result_path(owner_dir)
    verifier_result_path = _consultation_result_path(verifier_dir)
    if (hashlib.sha256(owner_result_path.read_bytes()).hexdigest()
            != intent.get("owner_result_sha256")
            or hashlib.sha256((owner_dir / "summary.json").read_bytes()).hexdigest()
            != intent.get("owner_summary_sha256")
            or hashlib.sha256(verifier_result_path.read_bytes()).hexdigest()
            != intent.get("verifier_result_sha256")
            or hashlib.sha256((verifier_dir / "summary.json").read_bytes()).hexdigest()
            != intent.get("verifier_summary_sha256")
            or intent.get("reviewer_model") != PAID_DECISION_MODEL):
        raise ValueError("consultation review proof changed")
    _validate_consultation_result(owner, expected, message=message)
    _validate_consultation_result(verifier, expected, message=message)
    if (owner.get("status") != "ok"
            or verifier.get("status") != "ok" or verifier.get("issues")):
        raise ValueError("consultation review blocked")
    answer = _load(root / "delivery" / "paid-answer.json")
    if (answer.get("status") != "answer" or answer.get("message") != message
            or answer.get("requirements_sha256") != requirements_sha256
            or answer.get("message_sha256") != message_sha256):
        raise ValueError("consultation answer mismatch")
    return {**intent, "reviewed_attachments": reviewed}


def _run_consultation_review(args, item_path: Path, root: Path, feedback: str, base: Path) -> Path:
    context = root / "context" / "current.json"
    context.parent.mkdir(parents=True, exist_ok=True)
    _run([sys.executable, str(args.context_compiler), "--project-root", str(root),
          "--queue-item", str(item_path), "--output", str(context)], "context_compile")
    requirements_sha256 = paid_remote_result.requirements_digest(root, feedback)
    requirements_snapshot = _requirements_snapshot(root)
    expected, images, documents = _consultation_attachments(root)
    schema = HERE.parent / "schemas" / "paid_consultation_review.schema.json"
    owner_evidence = root / "evidence" / "agent-PAID_ANSWER_OWNER"
    verifier_evidence = root / "evidence" / "agent-PAID_ANSWER_VERIFY"
    review_state_path = root / "context" / "paid-review-state.json"
    review_state = _load(review_state_path) if _regular_file(review_state_path) else {}
    issues = ([_text(issue) for issue in review_state.get("findings", []) if _text(issue)]
              if isinstance(review_state, dict)
              and review_state.get("state") == "REPAIR_PENDING"
              and review_state.get("mode") == "answer"
              and review_state.get("buyer_feedback_sha256") == feedback
              and review_state.get("requirements_sha256") == requirements_sha256 else [])
    for review_round in range(1, 4):
        owner_prompt = base / "answer-review" / "owner.prompt.txt"
        owner_prompt.parent.mkdir(parents=True, exist_ok=True)
        if expected:
            attachment_instruction = (
                "Inspect every buyer attachment listed here, preserve its exact order, filename, and SHA256 in "
                f"reviewed_attachments, and record a concrete observation: {json.dumps(expected, ensure_ascii=False)}. "
                f"Visually inspect image inputs. Read non-image documents with local read-only tools from these paths: "
                f"{json.dumps([str(path) for path in documents], ensure_ascii=False)}."
            )
        else:
            attachment_instruction = "No buyer attachments are present; reviewed_attachments must be an empty array."
        owner_prompt.write_text(
            "You are the Sol paid answer owner. Read-only: never submit or send anything. "
            f"Read {context}, {root / 'requirements/live-buyer-reply.json'}, and the current semantic decision at "
            f"{root / 'context/paid-work-decision.json'}. The answer must satisfy that decision's required_output and "
            f"required_effect without contradicting primary evidence. {attachment_instruction} "
            "Write a concrete, safe Japanese answer to the exact current buyer request. Distinguish proved facts from "
            "uncertainty, invent nothing, and ask at most one genuinely necessary question. Resolve every previous "
            f"fresh-review issue: {json.dumps(issues, ensure_ascii=False)}. Return blocked only when no safe answer can be sent.",
            encoding="utf-8",
        )
        command = [sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
                   "--candidate-model", PAID_DECISION_MODEL,
                   "--prompt-file", str(owner_prompt), "--schema", str(schema),
                   "--evidence-dir", str(owner_evidence), "--task-label", "paid-answer-owner",
                   "--escalation-reason", "Sol owner composes the exact paid buyer answer",
                   "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "1800", "--read-only"]
        for image in images:
            command += ["--image", str(image)]
        owner_started_ns = time.time_ns()
        _run(command, "remote_builder")
        owner = _consultation_runner_result(
            owner_evidence, task_label="paid-answer-owner", task_class="escalation-agent",
            model=PAID_DECISION_MODEL, started_ns=owner_started_ns,
        )
        try:
            reviewed = _validate_consultation_result(owner, expected)
        except (AttributeError, ValueError, TypeError) as error:
            raise Failure("remote_builder") from error
        if owner.get("status") != "ok":
            raise Failure("remote_builder")

        (base / "answer-review").mkdir(parents=True, exist_ok=True)
        verifier_prompt = base / "answer-review" / "verifier.prompt.txt"
        verifier_prompt.write_text(
            "You are a fresh read-only Sol reviewer. Never mutate, submit, send, or write business state. "
            f"Independently read {context}, {root / 'requirements/live-buyer-reply.json'}, and the current semantic "
            f"decision at {root / 'context/paid-work-decision.json'}. Trace every claimed completed or verified effect "
            f"through {root / 'delivery/paid-remote-result.json'} and its referenced after_evidence when present; do not "
            f"infer live state from buyer-visible flags or an older request when primary execution evidence exists. Read "
            f"every attached image, and "
            f"each non-image buyer document with local read-only tools from "
            f"{json.dumps([str(path) for path in documents], ensure_ascii=False)}. "
            f"reviewed_attachments is internal review evidence: return exactly this list and no other project files: "
            f"{json.dumps(expected, ensure_ascii=False)}. It does not mean those files will be sent to the buyer. "
            "Attack omissions, unsafe instructions, invented facts, recipient/stage mistakes, failure to answer the exact "
            "latest request, and attachment mismatch. Return the exact candidate customer_message and attachments on PASS; "
            "otherwise status=blocked with concrete repair issues. Candidate: "
            + json.dumps(owner, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        command = [sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
                   "--candidate-model", PAID_DECISION_MODEL,
                   "--prompt-file", str(verifier_prompt), "--schema", str(schema),
                   "--evidence-dir", str(verifier_evidence), "--task-label", "paid-answer-verifier",
                   "--escalation-reason", "Fresh Sol review before a paid buyer answer",
                   "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "1800", "--read-only"]
        for image in images:
            command += ["--image", str(image)]
        verifier_started_ns = time.time_ns()
        _run(command, "remote_verifier")
        checked = _consultation_runner_result(
            verifier_evidence, task_label="paid-answer-verifier", task_class="escalation-agent",
            model=PAID_DECISION_MODEL, started_ns=verifier_started_ns,
        )
        try:
            _validate_consultation_result(
                checked, expected, message=_text(owner.get("customer_message")) if checked.get("status") == "ok" else None,
            )
        except (AttributeError, ValueError, TypeError) as error:
            raise Failure("remote_verifier") from error
        if checked.get("status") == "ok" and not checked.get("issues"):
            break
        issues = [_text(issue) for issue in checked.get("issues") or [] if _text(issue)]
        if not issues or review_round == 3:
            _write(root / "context" / "paid-review-state.json", {
                "version": 1, "state": "REPAIR_PENDING", "mode": "answer",
                "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
                "round": review_round, "findings": issues,
            })
            raise Failure("remote_verifier")

    if _requirements_snapshot(root) != requirements_snapshot or _consultation_attachments(root)[0] != expected:
        raise Failure("requirements_toctou")
    target = _text(_load(item_path).get("marketplace_url"))
    if target != f"https://coconala.com/talkrooms/{_text(_load(item_path).get('talkroom_id'))}":
        raise Failure("remote_builder")
    message = _text(owner["customer_message"])
    desired = {"customer_message": message, "reviewed_attachments": reviewed}
    digest = hashlib.sha256(json.dumps(desired, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    message_sha256 = hashlib.sha256(message.encode()).hexdigest()
    delivery = root / "delivery"; delivery.mkdir(parents=True, exist_ok=True)
    _write(delivery / "paid-remote-intent.json", {"version": 2, "mode": "answer",
           "buyer_feedback_sha256": feedback, "talkroom_id": _text(_load(item_path).get("talkroom_id")),
           "target": target, "desired_state": desired, "desired_state_sha256": digest,
           "requirements_sha256": requirements_sha256, "message_sha256": message_sha256,
           "owner_result_sha256": hashlib.sha256(_consultation_result_path(owner_evidence).read_bytes()).hexdigest(),
           "owner_summary_sha256": hashlib.sha256((owner_evidence / "summary.json").read_bytes()).hexdigest(),
           "verifier_result_sha256": hashlib.sha256(_consultation_result_path(verifier_evidence).read_bytes()).hexdigest(),
           "verifier_summary_sha256": hashlib.sha256((verifier_evidence / "summary.json").read_bytes()).hexdigest(),
           "reviewer_model": PAID_DECISION_MODEL})
    _write(delivery / "paid-answer.json", {"version": 1, "status": "answer", "message": message,
           "requirements_sha256": requirements_sha256, "message_sha256": message_sha256})
    _validate_consultation_authorization(root, feedback)
    _write(root / "context" / "paid-review-state.json", {
        "version": 1, "state": "APPROVED", "mode": "answer",
        "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
        "round": review_round, "message_sha256": message_sha256,
    })
    return _consultation_result_path(verifier_evidence)


def _run_remote_repair(args, item_path: Path, root: Path, feedback: str, base: Path) -> Path:
    context = root / "context" / "current.json"
    context.parent.mkdir(parents=True, exist_ok=True)
    _run([sys.executable, str(args.context_compiler), "--project-root", str(root), "--queue-item", str(item_path), "--output", str(context)], "context_compile")
    try: requirements_sha256 = paid_remote_result.requirements_digest(root, feedback)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error: raise Failure("context_compile") from error
    requirements_snapshot = _requirements_snapshot(root)
    repair = base / "remote-repair"
    repair.mkdir(parents=True, exist_ok=True)
    pass_start = time.time()
    verifier_evidence = root / "evidence" / "agent-PAID_REMOTE_VERIFY"
    review_delta: list[dict[str, str]] | None = None
    builder_required, validation_start = True, pass_start
    try:
        intent = _load(root / "delivery" / "paid-remote-intent.json")
        digest = _text(intent.get("desired_state_sha256"))
        paid_remote_result.validate_builder(root, feedback, digest, resume=True)
        builder_required, validation_start = False, 0
        try:
            previous = _review_failure(
                verifier_evidence / "remote-verifier-result.json", root, intent, feedback, digest,
            )
            if previous["classification"] == "quality_mismatch":
                review_delta, builder_required = previous["delta"], True
        except Failure:
            pass
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    verifier_path = None
    for review_round in range(1, 4):
        if builder_required:
            prompt = repair / "owner.prompt.txt"
            prompt.write_text(
                _repair_prompt(root, item_path, feedback, requirements_sha256, False,
                               args.cdp_helper, review_delta),
                encoding="utf-8",
            )
            owner_evidence = root / "evidence" / "agent-PAID_REMOTE_OWNER"
            owner_started_ns = time.time_ns()
            _run([sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
                  "--candidate-model", PAID_DECISION_MODEL,
                  "--prompt-file", str(prompt), "--schema", str(args.runner_schema),
                  "--evidence-dir", str(owner_evidence), "--task-label", "paid-remote-owner",
                  "--escalation-reason", "Sol owner mutates the authenticated paid target",
                  "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "1800"],
                 "remote_builder")
            _consultation_runner_result(
                owner_evidence, task_label="paid-remote-owner", task_class="escalation-agent",
                model=PAID_DECISION_MODEL, started_ns=owner_started_ns,
            )
            if (_requirements_snapshot(root) != requirements_snapshot
                    or step_result_status.status_from_evidence(owner_evidence) != "ok"):
                raise Failure("remote_builder")
            if not all((root / "delivery" / name).is_file()
                       for name in ("paid-remote-intent.json", "paid-remote-result.json")):
                raise Failure("remote_builder")
            _normalize_builder_result(root)
            try:
                intent = _load(root / "delivery" / "paid-remote-intent.json")
                digest = _text(intent.get("desired_state_sha256"))
                paid_remote_result.validate_builder(root, feedback, digest, pass_start)
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                raise Failure("remote_builder") from error
            builder_required, validation_start = False, pass_start

        if verifier_evidence.is_symlink():
            raise Failure("remote_verifier")
        verifier_evidence.mkdir(parents=True, exist_ok=True)
        for stale in verifier_evidence.rglob("*.json"):
            if stale.name in {"summary.json", "runner-result.json"} or re.fullmatch(r"attempt-[0-9]+\.result\.json", stale.name):
                continue
            if stale.is_file():
                stale.unlink()
        verifier_path = verifier_evidence / "remote-verifier-result.json"
        verifier_path.unlink(missing_ok=True)
        repair.mkdir(parents=True, exist_ok=True)
        prompt = repair / "verifier.prompt.txt"
        prompt.write_text(
            _repair_prompt(root, item_path, feedback, requirements_sha256, True, args.cdp_helper),
            encoding="utf-8",
        )
        delivery_snapshot, verifier_started_ns = _delivery_snapshot(root), time.time_ns()
        _run([sys.executable, str(args.agent_runner), "--task-class", "escalation-agent",
              "--candidate-model", PAID_DECISION_MODEL,
              "--prompt-file", str(prompt), "--schema", str(args.runner_schema),
              "--evidence-dir", str(verifier_evidence), "--task-label", "paid-remote-verifier",
              "--escalation-reason", "Fresh Sol independently verifies the paid live target",
              "--loop", "gig", "--workdir", str(root), "--timeout-seconds", "1800", "--read-only"],
             "remote_verifier")
        if (_requirements_snapshot(root) != requirements_snapshot
                or _delivery_snapshot(root) != delivery_snapshot):
            raise Failure("remote_verifier")
        semantic_status = step_result_status.status_from_evidence(verifier_evidence)
        if semantic_status == "ok":
            verifier_path = _validate_managed_verifier(
                verifier_path, root, intent, feedback, digest, verifier_started_ns,
            )
            break
        if semantic_status != "blocked":
            raise Failure("remote_verifier")
        rejected = _review_failure(
            verifier_path, root, intent, feedback, digest, verifier_started_ns,
        )
        if review_round == 3:
            _write(root / "context" / "paid-review-state.json", {
                "version": 1, "state": "REPAIR_PENDING", "mode": "remote",
                "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
                "round": review_round, "findings": rejected.get("delta") or [],
            })
            raise Failure("remote_verifier")
        if rejected["classification"] == "quality_mismatch":
            review_delta, builder_required = rejected["delta"], True
        else:
            review_delta, builder_required = None, False

    if verifier_path is None:
        raise Failure("remote_verifier")
    try:
        intent = _load(root / "delivery" / "paid-remote-intent.json")
        digest = _text(intent.get("desired_state_sha256"))
        verifier_path = resolve_managed_verifier(root, feedback, digest)
        paid_remote_result.write_answer(root, feedback, digest, validation_start, verifier_path)
        paid_remote_result.record(root, feedback, digest, validation_start, verifier_path)
        paid_remote_result.resume(root, feedback, digest, verifier_path)
        _write(root / "context" / "paid-review-state.json", {
            "version": 1, "state": "APPROVED", "mode": "remote",
            "buyer_feedback_sha256": feedback, "requirements_sha256": requirements_sha256,
            "round": review_round, "desired_state_sha256": digest,
        })
        return verifier_path
    except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure) as error:
        raise Failure("remote_resume") from error

def _prepare_one(args, item_path: Path, output: Path) -> int:
    room = ""
    try:
        item = _load(item_path); room, feedback = _text(item.get("talkroom_id")), _text(item.get("buyer_feedback_sha256"))
        root = _paid_project_root(args, item)
        base = args.evidence_dir / "paid-direct" / room
        preflight = base / "preflight" / "selected-talkroom-snapshot.json"
        _run(_collector(args, "selected-talkroom-only", preflight, preflight.parent, item_path, item), "remote_resume")
        preflight_row = _row(_load(preflight), room)
        if _text(preflight_row.get("buyer_feedback_sha256")) != feedback: raise Failure("remote_resume")
        try:
            file_mode = _file_mode(root, item)
        except (AttributeError, KeyError, OSError, ValueError, TypeError, json.JSONDecodeError):
            file_mode = False
        if file_mode:
            try:
                prepared = _prepare_file(args, item_path, root, item, base, feedback)
            except ValueError as error:
                raise Failure("file_validation") from error
            _write(output, {**prepared, "project_root": str(root), "_paid_prepare_status": "prepared"})
            return 0
        delivery = root / "delivery"; intent_path = delivery / "paid-remote-intent.json"
        consultation_answer = _answer_ready(root, item)
        verifier = None; repaired = False
        if consultation_answer:
            try:
                _validate_consultation_authorization(root, feedback)
                verifier = _consultation_result_path(root / "evidence" / "agent-PAID_ANSWER_VERIFY")
            except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
                verifier = _run_consultation_review(args, item_path, root, feedback, base)
                repaired = True
        else:
            try:
                intent = _load(intent_path); digest = _text(intent.get("desired_state_sha256"))
                _normalize_builder_result(root)
                verifier = resolve_managed_verifier(root, feedback, digest)
                try:
                    paid_remote_result.resume(root, feedback, digest, verifier)
                except ValueError:
                    paid_remote_result.write_answer(root, feedback, digest, 0, verifier)
                    paid_remote_result.record(root, feedback, digest, 0, verifier)
                    paid_remote_result.resume(root, feedback, digest, verifier)
            except (AttributeError, OSError, ValueError, TypeError, json.JSONDecodeError, Failure):
                if not _remote_mode_required(root, item, feedback):
                    raise Failure("remote_resume")
                verifier = _run_remote_repair(args, item_path, root, feedback, base)
                repaired = True
        intent = _load(intent_path); digest = _text(intent.get("desired_state_sha256"))
        prepared = {**item, "project_root": str(root), "remote_repaired": repaired,
                    "requirements_sha256": paid_remote_result.requirements_digest(root, feedback)}
        _write(output, {**prepared, "_paid_prepare_status": "prepared"})
        return 0
    except (AttributeError, Failure, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        _write(output, {"status": "failed", "talkroom_id": room, "failed": 1, "failed_step": error.step if isinstance(error, Failure) else "remote_resume", "effect": 0, "readback": 0}); return 1


def _write_file_effect(args, item_path: Path, output: Path, prepared: dict[str, Any]) -> int:
    room = _text(prepared.get("talkroom_id")); sent_effect = 0
    try:
        feedback = _text(prepared.get("buyer_feedback_sha256"))
        root = _paid_project_root(args, prepared)
        requirements_sha256 = _text(prepared.get("requirements_sha256"))
        if (not _file_mode(root, prepared)
                or paid_remote_result.requirements_digest(root, feedback) != requirements_sha256):
            raise Failure("requirements_toctou")
        stable = delivery_queue.evidence_path(args.delivery_evidence_dir, prepared)
        manifest = _validate_file_authorization(root, stable, feedback, requirements_sha256)
        base = args.evidence_dir / "paid-direct" / room
        presend = base / "presend" / "selected-talkroom-snapshot.json"
        _run(_collector(args, "selected-talkroom-only", presend, presend.parent, item_path, prepared), "presend_readback")
        row = _row(_load(presend), room)
        if (_text(row.get("buyer_feedback_sha256")) != feedback
                or paid_remote_result.requirements_digest(root, feedback) != requirements_sha256):
            raise Failure("presend_readback")
        evidence, blockers = delivery_queue.delivery_gate(row, args.delivery_evidence_dir, args.projects_root)
        cadence = {**prepared, **row, **{key: evidence[key] for key in (
            "project_root", "requirements_path", "artifact_path", "artifact_version",
            "acceptance_evidence_path", "acceptance_status", "package_sha256",
            "acceptance_delta", "recipient_access_required",
        ) if key in evidence}, "delivery_evidence": evidence, "blockers": blockers}
        # A targeted DOM readback is intentionally sparse.  It may discover a new
        # reason to downgrade/cancel a send, but it must not erase a buyer hold
        # already derived from the complete project context.
        if prepared.get("buyer_formal_delivery_hold") is True:
            cadence["buyer_formal_delivery_hold"] = True
            cadence["buyer_formal_delivery_hold_reason"] = prepared.get(
                "buyer_formal_delivery_hold_reason"
            )
        decision = delivery_queue.delivery_decision(cadence)
        action = _text(decision.get("mode"))
        if action not in {"formal", "progress"}:
            raise Failure("presend_readback")
        prepared_action = _text(prepared.get("delivery_action"))
        if action == "formal" and prepared_action != "formal":
            raise Failure("presend_action_escalation")
        cadence.update(
            delivery_action=action,
            formal_delivery_checkbox=decision.get("formal_delivery_checkbox") is True,
            progress_payload=_file_progress_payload(cadence) if action == "progress" else None,
        )
        browser_item = base / "file" / f"queue-{os.getpid()}-{time.time_ns()}.json"
        _write(browser_item, cadence)
        browser_evidence = base / "file-browser" / f"{manifest['artifact_version']}-{manifest['package_sha256'][:12]}"
        browser_started = time.time()
        revision_after_formal = (
            action == "progress" and row.get("formal_delivery_observed") is True
            and _text(row.get("talkroom_state", row.get("transaction_state"))) == "納品確認待ち"
        )
        if revision_after_formal:
            cadence["revision_after_formal"] = True
            _write(browser_item, cadence)
        if action == "formal":
            command = [sys.executable, str(args.formal_browser), "--queue-item", str(browser_item),
                       "--manifest", str(root / "delivery" / "paid-work-result.json"),
                       "--project-root", str(root), "--evidence-dir", str(browser_evidence),
                       "--ledger", str(root / "events.jsonl"), "--default-tab-helper", str(args.cdp_helper)]
        else:
            command = [sys.executable, str(args.answer_browser), "--queue-item", str(browser_item),
                       "--manifest", str(root / "delivery" / "paid-work-result.json"),
                       "--evidence-dir", str(browser_evidence), "--default-tab-helper", str(args.cdp_helper)]
            if revision_after_formal:
                command.append("--revision-after-formal")
        browser = _json_line(_run(command, "file_browser"), "file_browser")
        if browser.get("ok") is not True or not isinstance(browser.get("evidence"), dict):
            raise Failure("file_browser")
        sent_effect = int(browser["evidence"].get("send_performed") is True)
        reconcile_paid_delivery.reconcile(root, browser_evidence, browser_item, min_mtime=browser_started)
        final = base / "official-readback" / "selected-talkroom-snapshot.json"
        _run(_collector(args, "selected-talkroom-only", final, final.parent, browser_item, cadence), "official_readback")
        official = _row(_load(final), room)
        if _text(official.get("buyer_feedback_sha256")) != feedback:
            raise Failure("official_readback")
        if action == "formal":
            if _reported_formal_cycle(args, official) != root:
                raise Failure("official_readback")
        else:
            payload = cadence.get("progress_payload") or {}
            binding = f"添付: {Path(_text(manifest.get('artifact_path'))).name}（{_text(manifest.get('artifact_version'))}）"
            message = _text(payload.get("message"))
            sent_message = message if binding in message else f"{message}\n\n{binding}"
            if not _seller_message_with_attachment(
                    official, sent_message, Path(_text(manifest.get("artifact_path"))).name):
                raise Failure("official_readback")
        result = {
            "talkroom_id": room, "send_performed": browser["evidence"].get("send_performed") is True,
            "deduplicated": browser["evidence"].get("deduplicated") is True,
            "formal_delivery_checkbox": action == "formal", "file_repaired": prepared.get("file_repaired") is True,
            "evidence_paths": {"manifest": str(root / "delivery" / "paid-work-result.json"),
                               "presend_readback": str(presend), "browser": str(browser_evidence),
                               "official_readback": str(final)},
        }
        _write(output, {"status": "completed", "effect": int(result["send_performed"]),
                        "readback": 1, "failed": 0, "item": result})
        return 0
    except (AttributeError, Failure, OSError, ValueError, TypeError, json.JSONDecodeError,
            reconcile_paid_delivery.ReconcileError) as error:
        _write(output, {"status": "failed", "talkroom_id": room, "failed": 1,
                        "failed_step": error.step if isinstance(error, Failure) else "file_delivery",
                        "effect": sent_effect, "readback": 0})
        return 1

def _write_one(args, item_path: Path, output: Path) -> int:
    lock_dir = _text(os.environ.get("CDP_LOCK_DIR"))
    expected_lock = args.cdp_lock_dir.expanduser().resolve()
    try:
        meta = Path(lock_dir).expanduser().resolve() / "meta" if lock_dir else None
        owner = meta.read_text(encoding="utf-8").split()[0] if meta else ""
    except (OSError, IndexError):
        owner = ""
    if (os.environ.get("GIG_CDP_LOCK_HELD") != "1" or not lock_dir
            or Path(lock_dir).expanduser().resolve() != expected_lock
            or owner != f"paid-direct-{item_path.stem}"):
        _write(output, {"status": "failed", "talkroom_id": "", "failed": 1, "failed_step": "writer_lock", "effect": 0, "readback": 0})
        return 1
    room = ""
    sent_effect = 0
    try:
        prepared = _load(item_path); item = prepared
        if prepared.get("_paid_mode") == "file":
            return _write_file_effect(args, item_path, output, prepared)
        room, feedback = _text(item.get("talkroom_id")), _text(item.get("buyer_feedback_sha256"))
        root = _paid_project_root(args, item)
        base = args.evidence_dir / "paid-direct" / room
        requirements_sha256 = _text(prepared.get("requirements_sha256"))
        if paid_remote_result.requirements_digest(root, feedback) != requirements_sha256:
            raise Failure("requirements_toctou")
        answer_path = root / "delivery" / "paid-answer.json"
        answer_before = answer_path.read_bytes()
        delivery = root / "delivery"; intent_path = delivery / "paid-remote-intent.json"
        intent = _load(intent_path); digest = _text(intent.get("desired_state_sha256"))
        consultation_expected = None
        if _answer_ready(root, item):
            expected, _, _ = _consultation_attachments(root)
            consultation_expected = expected
            reviewed = intent.get("desired_state", {}).get("reviewed_attachments")
            if ([{"filename": row.get("filename"), "sha256": row.get("sha256")}
                 for row in reviewed if isinstance(row, dict)] if isinstance(reviewed, list) else []) != expected:
                raise Failure("requirements_toctou")
        if consultation_expected is not None:
            _validate_consultation_authorization(root, feedback)
        else:
            verifier = resolve_managed_verifier(root, feedback, digest)
            paid_remote_result.resume(root, feedback, digest, verifier)
        if answer_path.read_bytes() != answer_before: raise Failure("answer_toctou")
        try: answer_payload = json.loads(answer_before.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error: raise Failure("answer_snapshot") from error
        if not isinstance(answer_payload, dict) or not _text(answer_payload.get("message")): raise Failure("answer_snapshot")
        customer_attachment = None
        if consultation_expected is None:
            remote_result = _load(root / "delivery" / "paid-remote-result.json")
            customer_attachment = _validated_customer_attachment(root, remote_result.get("customer_attachment"))
            if customer_attachment is not None:
                answer_payload["attachment"] = customer_attachment
        answer_dir = base / "answer"; answer_snapshot = answer_dir / f"paid-answer-{os.getpid()}-{time.time_ns()}.json"
        _write(answer_snapshot, answer_payload)
        if _load(answer_snapshot) != answer_payload: raise Failure("answer_snapshot")
        repaired = prepared.get("remote_repaired") is True if isinstance(prepared, dict) else False
        presend = base / "presend" / "selected-talkroom-snapshot.json"
        _run(_collector(args, "selected-talkroom-only", presend, presend.parent, item_path, item), "presend_readback")
        presend_row = _row(_load(presend), room)
        if (_text(presend_row.get("buyer_feedback_sha256")) != feedback
                or paid_remote_result.requirements_digest(root, feedback) != requirements_sha256):
            raise Failure("presend_readback")
        if consultation_expected is not None:
            try:
                current_attachments = _consultation_attachments(root)[0]
            except Failure as error:
                raise Failure("requirements_toctou") from error
            if current_attachments != consultation_expected:
                raise Failure("requirements_toctou")
        message = _text(answer_payload.get("message"))
        seller_matches = (_seller_message_with_attachment(presend_row, message, customer_attachment["filename"])
                          if customer_attachment else
                          _seller_last_sha256(presend_row) == hashlib.sha256(_comparison_key(message).encode()).hexdigest())
        if (message and _text(presend_row.get("talkroom_state", presend_row.get("transaction_state")))
                and presend_row.get("formal_delivery_observed", presend_row.get("formal_delivery_confirmed")) is False
                and seller_matches):
            result = {"talkroom_id": room, "send_performed": False, "deduplicated": True,
                      "formal_delivery_checkbox": False, "evidence_paths": {"answer_snapshot": str(answer_snapshot), "official_readback": str(presend), "presend_readback": str(presend)}}
            _write(output, {"status": "completed", "effect": 0, "readback": 1, "failed": 0, "item": result}); return 0
        browser = _json_line(_run([sys.executable, str(args.answer_browser), "--queue-item", str(item_path), "--answer-file", str(answer_snapshot),
                                   "--evidence-dir", str(answer_dir), "--default-tab-helper", str(args.cdp_helper)], "answer_browser"), "answer_browser")
        if browser.get("ok") is not True or not isinstance(browser.get("evidence"), dict): raise Failure("answer_browser")
        evidence = browser["evidence"]; sent_effect = int(evidence.get("send_performed") is True)
        final = base / "official-readback" / "selected-talkroom-snapshot.json"
        _run(_collector(args, "selected-talkroom-only", final, final.parent, item_path, item), "official_readback")
        row = _row(_load(final), room)
        official_matches = (_seller_message_with_attachment(row, message, customer_attachment["filename"])
                            if customer_attachment else
                            _seller_last_sha256(row) == hashlib.sha256(_comparison_key(message).encode()).hexdigest())
        if (_text(row.get("buyer_feedback_sha256")) != feedback
                or not _text(row.get("talkroom_state", row.get("transaction_state")))
                or row.get("formal_delivery_observed", row.get("formal_delivery_confirmed")) is not False
                or not official_matches):
            raise Failure("official_readback")
        result = {"talkroom_id": room, "send_performed": evidence.get("send_performed") is True, "deduplicated": evidence.get("deduplicated") is True,
                  "formal_delivery_checkbox": evidence.get("formal_delivery_checkbox") is True, "remote_repaired": repaired,
                  "evidence_paths": {"answer_snapshot": str(answer_snapshot), "pre_readback": str(base / "preflight" / "selected-talkroom-snapshot.json"), "presend_readback": str(presend), "official_readback": str(final)}}
        _write(output, {"status": "completed", "effect": int(result["send_performed"]), "readback": 1, "failed": 0, "item": result}); return 0
    except (AttributeError, Failure, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        _write(output, {"status": "failed", "talkroom_id": room, "failed": 1, "failed_step": error.step if isinstance(error, Failure) else "remote_resume", "effect": sent_effect, "readback": 0}); return 1

def _child_command(args, phase, item, output):
    return [sys.executable, str(HERE / "paid_direct.py"), phase, str(item), "--output", str(output),
            "--evidence-dir", str(args.evidence_dir), "--projects-root", str(args.projects_root), "--collector", str(args.collector), "--run-with-cdp-lock", str(args.run_with_cdp_lock),
            "--answer-browser", str(args.answer_browser), "--formal-browser", str(args.formal_browser),
            "--delivery-evidence-dir", str(args.delivery_evidence_dir),
            "--cdp-helper", str(args.cdp_helper), "--context-compiler", str(args.context_compiler),
            "--agent-runner", str(args.agent_runner), "--runner-schema", str(args.runner_schema),
            "--artifact-schema", str(args.artifact_schema), "--cdp-lock-dir", str(args.cdp_lock_dir), "--today", args.today]

def _prepare_command(args, item, output):
    return _child_command(args, "--effect-item", item, output)

def _effect_command(args, item, output):
    return [str(args.run_with_cdp_lock), f"paid-direct-{item.stem}", "0", "--"] + _child_command(args, "--write-item", item, output)

def _fresh_child_env(args):
    env = {key: value for key, value in os.environ.items() if key != "GIG_CDP_LOCK_HELD"}
    env["CDP_LOCK_DIR"] = str(args.cdp_lock_dir)
    return env


def _paid_report(run_id: str, result: dict[str, Any]) -> str:
    items = ", ".join(
        f"{_text(row.get('talkroom_id'))}={_text(row.get('status'))}"
        for row in result.get("items", []) if isinstance(row, dict)
    ) or "なし"
    next_action = ("案件別failureをbounded repair" if int(result.get("failed") or 0)
                   else "未完案件を次wakeでresume" if int(result.get("pending") or 0)
                   else "新しいbuyer feedbackを待つ")
    return "\n".join((
        "[ココナラ][納品] Codex:::",
        f"observed: {int(result.get('observed') or 0)}件",
        f"actionable: {int(result.get('actionable') or 0)}件",
        f"effect: {int(result.get('effect') or 0)}件",
        f"readback: {int(result.get('readback') or 0)}件",
        f"failed: {int(result.get('failed') or 0)}件",
        f"pending: {int(result.get('pending') or 0)}件",
        f"oldest: {_text(result.get('oldest')) or '不明'}",
        f"案件: {items}",
        f"次の一手: {next_action}",
        f"run_id: {run_id}",
    ))


def _report_paid_wake(args, result: dict[str, Any], run_id: str) -> dict[str, Any]:
    message = _paid_report(run_id, result)
    event_key = f"gig:telegram:paid-direct:v1:{run_id}"
    outbox = TelegramOutbox(args.telegram_database)
    row = outbox.enqueue(event_key=event_key, kind="paid-direct", message=message,
                         created_at=int(time.time()), suppress_identical_body=False)
    if row["state"] == "sent":
        return {"status": "sent", "message_id": row.get("message_id")}
    if row["state"] == "delivery_unknown":
        return {"status": "delivery_unknown", "message_id": row.get("message_id")}
    delivered = dispatch_one(
        outbox, owner=f"gig-paid-direct:{run_id}", now=lambda: int(time.time()),
        transport=OpenClawTelegramTransport(target=args.telegram_target, executable=args.openclaw,
                                            receipt_dir=args.telegram_receipt_dir),
        report_id=int(row["report_id"]),
    )
    return {"status": delivered["status"], "message_id": delivered.get("message_id")}

@contextmanager
def _lock(path: Path) -> Iterator[bool]:
    path.parent.mkdir(parents=True, exist_ok=True); handle = path.open("a+")
    try:
        try: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: yield False; return
        yield True
    finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN); handle.close()

def _unique_orders(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Keep only the freshest observation for each structural talkroom identity."""
    by_room: dict[str, dict[str, Any]] = {}
    for item in items:
        room = _text(item.get("talkroom_id"))
        if not room:
            raise Failure("orders_parse")
        previous = by_room.get(room)
        freshness = (
            _text(item.get("snapshot_captured_at")),
            _text(item.get("talkroom_observed_at")),
            _text(item.get("buyer_feedback_sha256")),
        )
        previous_freshness = (
            _text(previous.get("snapshot_captured_at")),
            _text(previous.get("talkroom_observed_at")),
            _text(previous.get("buyer_feedback_sha256")),
        ) if previous else ("", "", "")
        if previous is None or freshness > previous_freshness:
            by_room[room] = item
    return list(by_room.values()), len(items) - len(by_room)


def run_once(args, output: Path) -> int:
    with _lock(args.lock_file) as acquired:
        if not acquired:
            _write(output, {"status": "busy", "observed": 0, "actionable": 0, "effect": 0, "readback": 0, "failed": 0, "pending": 0, "oldest": None, "items": []}); return 0
        try:
            observed_items = observe_orders(args, args.evidence_dir / "orders")
            items, duplicate_dropped = _unique_orders(observed_items)
        except Failure as error:
            _write(output, {"status": "failed", "observed": 0, "actionable": 0, "effect": 0, "readback": 0, "failed": 1, "pending": 0, "oldest": None, "failed_step": error.step, "items": []}); return 1
        items.sort(key=lambda item: (_text(item.get("delivery_date")) or "9999-12-31", _text(item.get("talkroom_id"))))
        rows: dict[str, dict[str, Any]] = {}
        actionable = 0
        failed = effect = readback = 0; failed_step = ""
        for item in items:
            room = _text(item.get("talkroom_id"))
            try: item = _targeted(args, item, room)
            except (Failure, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                step = error.step if isinstance(error, Failure) else "targeted_readback"
                failed, failed_step = failed + 1, step; rows[room] = {"talkroom_id": room, "status": "failed", "failed_step": step}; continue
            handoff = _reported_handoff_cycle(args, item)
            if handoff is not None:
                rows[room] = {"talkroom_id": room, "status": "awaiting_buyer",
                              "send_performed": False, "deduplicated": True,
                              "formal_delivery_checkbox": False,
                              "evidence_paths": {"official_readback": str(
                                  handoff / "delivery" / "paid-external-handoff.json")}}
                readback += 1
                continue
            if _reported_formal_cycle(args, item) is not None:
                official = _text(item.get("talkroom_evidence_file"))
                rows[room] = {"talkroom_id": room, "status": "awaiting_buyer", "send_performed": False,
                              "deduplicated": True, "formal_delivery_checkbox": True,
                              "evidence_paths": {"official_readback": official}}
                readback += 1
                continue
            if _reported_file_progress_cycle(args, item) is not None:
                official = _text(item.get("talkroom_evidence_file"))
                rows[room] = {"talkroom_id": room, "status": "awaiting_buyer", "send_performed": False,
                              "deduplicated": True, "formal_delivery_checkbox": False,
                              "evidence_paths": {"official_readback": official}}
                readback += 1
                continue
            if _reported_remote_cycle(args, item) is not None:
                official = _text(item.get("talkroom_evidence_file"))
                rows[room] = {"talkroom_id": room, "status": "completed", "send_performed": False,
                              "deduplicated": True, "formal_delivery_checkbox": False,
                              "evidence_paths": {"official_readback": official}}
                readback += 1
                continue
            room, resolved = _text(item.get("talkroom_id")), _recoverable(args, item)
            if resolved is None:
                try:
                    root = _paid_project_root(args, item)
                    if _answer_ready(root, item):
                        delivery_project.record_queue_selection(args.projects_root, item, adapter="coconala")
                        resolved = _recoverable(args, item)
                    elif (root.is_dir() and not root.is_symlink()
                          and (root / "requirements" / "live-buyer-reply.json").is_file()
                          and re.fullmatch(r"[0-9a-f]{64}", _text(item.get("buyer_feedback_sha256")))):
                        root.resolve().relative_to(args.projects_root.resolve())
                        if not (root / "state.json").is_file():
                            delivery_project.record_queue_selection(args.projects_root, item, adapter="coconala")
                        bootstrap_item = args.evidence_dir / "paid-direct" / "bootstrap" / f"item-{room}.json"
                        _write(bootstrap_item, item)
                        _paid_decision(args, bootstrap_item, root.resolve(),
                                       args.evidence_dir / "paid-direct" / room)
                        resolved = _recoverable(args, item)
                except (Failure, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                    step = error.step if isinstance(error, Failure) else "context_compile"
                    failed, failed_step = failed + 1, step
                    rows[room] = {"talkroom_id": room, "status": "failed", "failed_step": step}
                    continue
            if resolved is None: rows[room] = {"talkroom_id": room, "status": "pending"}; continue
            root, _ = resolved; private = {key: item[key] for key in (
                "request_id", "contract_id", "talkroom_id", "title", "marketplace_url", "talkroom_url",
                "buyer_feedback_sha256", "buyer_feedback_stage", "buyer_feedback_pending_artifact",
                "buyer_feedback_requirements_path", "buyer_reply_after_artifact_observed",
                "buyer_formal_delivery_hold", "delivery_date", "status", "talkroom_state",
                "talkroom_evidence_file", "talkroom_observed_at", "snapshot_captured_at",
                "talkroom_evidence_sha256", "talkroom_screenshot_sha256", "formal_delivery_observed",
                "formal_delivery_confirmed", "formal_delivery_control_checked",
                "formal_delivery_control_disabled", "buyer_visible_artifact_observed",
                "room_contract_kind", "price_jpy", "price_source", "buyer",
            ) if key in item}
            private.update(project_root=str(root))
            item_file = args.evidence_dir / "paid-direct" / "items" / f"item-{room}.json"
            effect_file = item_file.with_name(item_file.stem + "-result.json")
            _write(item_file, private)
            actionable += 1
            prepared_file = item_file.with_name(item_file.stem + "-prepared.json")
            effect_file.unlink(missing_ok=True); prepared_file.unlink(missing_ok=True)
            prepare = subprocess.run(_prepare_command(args, item_file, prepared_file), capture_output=True, text=True, env=_fresh_child_env(args))
            try: prepared = _load(prepared_file)
            except (OSError, json.JSONDecodeError): prepared = {"status": "failed", "failed_step": "remote_resume", "effect": 0, "readback": 0}
            if prepare.returncode or prepared.get("_paid_prepare_status") != "prepared":
                failed, failed_step = failed + 1, _text(prepared.get("failed_step")) or "remote_resume"; rows[room] = {"talkroom_id": room, "status": "failed", "failed_step": failed_step}; continue
            process = subprocess.run(_effect_command(args, prepared_file, effect_file), capture_output=True, text=True, env=_fresh_child_env(args))
            try: value = _load(effect_file)
            except (OSError, json.JSONDecodeError): value = {"status": "failed", "failed_step": "writer_lock", "effect": 0, "readback": 0}
            if process.returncode or value.get("status") != "completed":
                effect += int(value.get("effect") == 1); readback += int(value.get("readback") == 1)
                failed, failed_step = failed + 1, _text(value.get("failed_step")) or "writer_lock"; rows[room] = {"talkroom_id": room, "status": "failed", "failed_step": failed_step}; continue
            item_result = value.get("item") or {}; effect, readback = effect + int(item_result.get("send_performed") is True), readback + int(value.get("readback") == 1)
            rows[room] = {"talkroom_id": room, "status": "completed", **{key: item_result[key] for key in ("send_performed", "deduplicated", "formal_delivery_checkbox", "remote_repaired", "file_repaired", "evidence_paths") if key in item_result}}
        dates = [_text(item.get("delivery_date")) for item in items if _text(item.get("delivery_date"))]
        result = {"status": "failed" if failed else "completed", "observed": len(items),
                  "duplicate_dropped": duplicate_dropped, "actionable": actionable,
                  "effect": effect, "readback": readback, "failed": failed,
                  "pending": sum(rows[_text(item["talkroom_id"])].get("status") == "pending" for item in items),
                  "oldest": min(dates, default=None),
                  "items": [rows[_text(item["talkroom_id"])] for item in items]}
        if failed_step: result["failed_step"] = failed_step
        _write(output, result); return int(bool(failed))

def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("output", "evidence-dir"): parser.add_argument(f"--{flag}", required=True, type=Path)
    parser.add_argument("--projects-root", type=Path, default=Path.home() / "gig/projects"); parser.add_argument("--collector", type=Path, default=HERE / "coconala_queue_snapshot.py")
    parser.add_argument("--run-with-cdp-lock", type=Path, default=HERE / "run_with_cdp_lock.sh"); parser.add_argument("--answer-browser", type=Path, default=HERE / "coconala_paid_progress_browser.py")
    parser.add_argument("--formal-browser", type=Path, default=HERE / "coconala_formal_delivery_browser.py")
    parser.add_argument("--delivery-evidence-dir", type=Path, default=Path.home() / "gig" / "delivery-evidence")
    parser.add_argument("--cdp-lock-dir", type=Path, default=Path.home() / "gig" / ".cdp-gig.lock")
    parser.add_argument("--cdp-helper", type=Path, default=BROWSER_DIR / "scripts" / "cdp_default_tab.py"); parser.add_argument("--lock-file", type=Path)
    parser.add_argument("--context-compiler", type=Path, default=HERE / "project_context_compiler.py"); parser.add_argument("--agent-runner", type=Path, default=RUNNER_DIR / "agent_runner.py")
    parser.add_argument("--runner-schema", type=Path, default=HERE.parent / "schemas/gig_step_result.schema.json")
    parser.add_argument("--artifact-schema", type=Path, default=HERE.parent / "schemas/paid_file_judgement.schema.json")
    parser.add_argument("--decision-schema", type=Path, default=HERE.parent / "schemas/paid_work_decision.schema.json")
    parser.add_argument("--telegram-database", type=Path, default=DEFAULT_TELEGRAM_DATABASE)
    parser.add_argument("--telegram-receipt-dir", type=Path, default=DEFAULT_TELEGRAM_RECEIPTS)
    parser.add_argument("--telegram-target", default=os.environ.get("GIG_REPORT_CHAT", ""))
    parser.add_argument("--openclaw", type=Path, default=Path("/opt/homebrew/bin/openclaw"))
    parser.add_argument("--today", default=date.today().isoformat()); parser.add_argument("--effect-item", type=Path); parser.add_argument("--write-item", type=Path); parser.add_argument("--decision-item", type=Path); return parser

def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    for name in ("output", "evidence_dir", "projects_root", "collector", "run_with_cdp_lock", "answer_browser", "formal_browser", "delivery_evidence_dir", "cdp_lock_dir", "context_compiler", "agent_runner", "runner_schema", "artifact_schema", "decision_schema"): setattr(args, name, getattr(args, name).expanduser().resolve())
    args.cdp_helper = args.cdp_helper.expanduser(); args.lock_file = args.lock_file.expanduser().resolve() if args.lock_file else args.evidence_dir / ".paid-direct.lock"
    if args.write_item: return _write_one(args, args.write_item.expanduser().resolve(), args.output)
    if args.effect_item: return _prepare_one(args, args.effect_item.expanduser().resolve(), args.output)
    if args.decision_item: return _decision_only(args, args.decision_item.expanduser().resolve(), args.output)
    run_id = f"{time.time_ns()}-{os.getpid()}"
    try:
        rc = run_once(args, args.output)
        result = _load(args.output)
    except Exception as error:
        rc = 1
        result = {"status": "failed", "observed": 0, "actionable": 0, "effect": 0,
                  "readback": 0, "failed": 1, "pending": 0, "oldest": None,
                  "failed_step": "paid_direct", "error": type(error).__name__, "items": []}
    try:
        result["telegram"] = _report_paid_wake(args, result, run_id)
    except Exception as error:
        result["telegram"] = {"status": "failed", "error": type(error).__name__}
    _write(args.output, result)
    return rc

if __name__ == "__main__": raise SystemExit(main())
