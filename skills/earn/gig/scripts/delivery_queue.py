#!/usr/bin/env python3
"""Build the Gig action queue from authenticated marketplace state plus delivery evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    from delivery_cadence import delivery_decision, progress_payload
    from delivery_identity import stable_identity
except ModuleNotFoundError:  # direct import through the test loader
    import importlib.util
    _cadence_spec = importlib.util.spec_from_file_location(
        "delivery_cadence", Path(__file__).with_name("delivery_cadence.py")
    )
    if _cadence_spec is None or _cadence_spec.loader is None:
        raise
    _cadence = importlib.util.module_from_spec(_cadence_spec)
    _cadence_spec.loader.exec_module(_cadence)
    delivery_decision = _cadence.delivery_decision
    progress_payload = _cadence.progress_payload
    _identity_spec = importlib.util.spec_from_file_location(
        "delivery_identity", Path(__file__).with_name("delivery_identity.py")
    )
    if _identity_spec is None or _identity_spec.loader is None:
        raise
    _identity = importlib.util.module_from_spec(_identity_spec)
    _identity_spec.loader.exec_module(_identity)
    stable_identity = _identity.stable_identity


QUEUE_PRIORITY = {
    "overdue_or_today_paid_deliverable": 0,
    "buyer_feedback_or_revision": 1,
    "quote_needing_proposal": 2,
    "other_paid_work": 3,
    "nurture": 4,
    "listing_apply_learn": 5,
}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def normalized(value: Any) -> str:
    return re.sub(r"\W+", "", str(value or "").casefold())


def duplicate_order_quote(order: dict[str, Any], quote: dict[str, Any]) -> bool:
    order_request = str(order.get("request_id") or "")
    quote_request = str(quote.get("request_id") or "")
    if order_request and quote_request:
        return order_request == quote_request
    if normalized(order.get("buyer")) != normalized(quote.get("buyer")):
        return False
    order_title = normalized(order.get("title"))
    quote_title = normalized(quote.get("title"))
    return bool(order_title and quote_title and (order_title == quote_title or order_title in quote_title or quote_title in order_title))


def evidence_path(root: Path, item: dict[str, Any]) -> Path:
    return root / f"{stable_identity(item)}.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_active_paid_order(order: dict[str, Any]) -> bool:
    """Keep a live returned/revision order when the card status is ambiguous.

    Coconala's received-orders card can omit the paid label after a formal
    delivery is returned.  The authenticated talkroom and structured order
    fields are the safe fallback; free-form card text is never enough.
    """
    if order.get("status") == "paid":
        return True
    if order.get("status") != "unknown":
        return False
    try:
        price = int(order.get("price_jpy"))
    except (TypeError, ValueError):
        return False
    live_revision = (
        order.get("buyer_feedback_pending_artifact") is True
        or order.get("buyer_reply_after_artifact_observed") is True
    )
    live_paid_state = (
        order.get("talkroom_state") == "取引中"
        or (
            order.get("talkroom_state") == "納品確認待ち"
            and order.get("formal_delivery_observed") is True
        )
    )
    return (
        price > 0
        and str(order.get("price_source") or "").startswith("structured")
        and bool(order.get("contract_id"))
        and bool(order.get("talkroom_id"))
        and live_paid_state
        and live_revision
    )


def delivery_gate(item: dict[str, Any], evidence_root: Path) -> tuple[dict[str, Any], list[str]]:
    path = evidence_path(evidence_root, item)
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict):
            evidence = {}
    except (OSError, json.JSONDecodeError):
        evidence = {}
    blockers: list[str] = []
    artifact_value = evidence.get("artifact_path")
    artifact = Path(os.path.expanduser(str(artifact_value))) if artifact_value else None
    version = str(evidence.get("artifact_version") or "")
    if not artifact or not artifact.is_file() or not version or version not in artifact.name:
        blockers.append("missing_versioned_artifact")
    acceptance_value = evidence.get("acceptance_evidence_path")
    acceptance = Path(os.path.expanduser(str(acceptance_value))) if acceptance_value else None
    if evidence.get("acceptance_status") != "PASS" or not acceptance or not acceptance.is_file():
        blockers.append("missing_acceptance_evidence")
    package_hash = str(evidence.get("package_sha256") or "")
    if not artifact or not artifact.is_file() or not re.fullmatch(r"[0-9a-f]{64}", package_hash) or sha256_file(artifact) != package_hash:
        blockers.append("missing_package_hash")
    snapshot_time = item.get("snapshot_captured_at")
    live_formal = (
        item.get("formal_delivery_observed") is True
        and item.get("buyer_visible_artifact_observed") is True
        and item.get("talkroom_state") == "納品確認待ち"
        and bool(snapshot_time)
        and item.get("talkroom_observed_at") == snapshot_time
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(item.get("talkroom_evidence_sha256") or "")))
        and bool(re.fullmatch(r"[0-9a-f]{64}", str(item.get("talkroom_screenshot_sha256") or "")))
    )
    if not live_formal:
        blockers.append("formal_delivery_not_confirmed")
    return {"path": str(path), "present": path.is_file(), **evidence}, blockers


def build(snapshot: dict[str, Any], evidence_root: Path, today: date) -> dict[str, Any]:
    quotes = [q for q in snapshot.get("quotes", []) if q.get("status") == "proposal_required"]
    paid = []
    for source in snapshot.get("orders", []):
        if not is_active_paid_order(source):
            continue
        item = dict(source)
        # Normalize the ambiguous card state before priority/cadence logic so
        # downstream workers cannot mistake a returned paid order for a quote.
        item["status"] = "paid"
        paid.append(item)
    # A stale proposal may remain visible during the quote -> purchased
    # transition. Paid is authoritative; remove only the stale quote.
    quotes = [quote for quote in quotes if not any(duplicate_order_quote(order, quote) for order in paid)]
    items: list[dict[str, Any]] = []
    for source in paid:
        item = dict(source)
        item["snapshot_captured_at"] = snapshot.get("captured_at")
        due = None
        try:
            due = date.fromisoformat(str(item.get("delivery_date")))
        except (TypeError, ValueError):
            pass
        if (
            item.get("buyer_feedback_pending_artifact")
            or item.get("buyer_reply_after_artifact_observed")
            or item.get("revision_requested")
        ):
            queue_class = "buyer_feedback_or_revision"
        elif due and due <= today:
            queue_class = "overdue_or_today_paid_deliverable"
        else:
            queue_class = "other_paid_work"
        delivery_evidence, blockers = delivery_gate(item, evidence_root)
        # Live talkroom facts are authoritative.  Local evidence may supply
        # only artifact/acceptance facts; it must never forge buyer consent,
        # formal state, visibility, timestamps, or live hashes.
        cadence_item = dict(item)
        for key in (
            "artifact_path", "artifact_version", "acceptance_evidence_path",
            "acceptance_status", "package_sha256", "acceptance_delta",
        ):
            if key in delivery_evidence:
                cadence_item[key] = delivery_evidence[key]
        cadence_item["blockers"] = blockers
        cadence = delivery_decision(cadence_item)
        item.update({
            "queue_class": queue_class,
            "priority": QUEUE_PRIORITY[queue_class],
            "delivery_evidence": delivery_evidence,
            "blockers": blockers,
            "delivery_ready": not blockers,
            # The worker may send an honest progress artifact for every
            # blocked paid item.  Formal delivery remains a separate state
            # and is never implied by a local evidence flag.
            "delivery_action": cadence["mode"],
            "formal_delivery_checkbox": cadence["formal_delivery_checkbox"],
            "progress_payload": progress_payload(cadence_item) if cadence["mode"] == "progress" else None,
        })
        items.append(item)
    for source in quotes:
        item = dict(source)
        item.update({
            "queue_class": "quote_needing_proposal",
            "priority": QUEUE_PRIORITY["quote_needing_proposal"],
            "blockers": [],
            "delivery_ready": False,
        })
        items.append(item)
    items.sort(key=lambda item: (
        item["priority"],
        item.get("delivery_date") or item.get("proposal_due") or "9999-12-31",
        -int(item.get("price_jpy") or 0),
        str(item.get("contract_id") or ""),
    ))
    return {
        "version": 1,
        "captured_at": snapshot.get("captured_at"),
        "today": today.isoformat(),
        "source": snapshot.get("source", "fixture_or_normalized_snapshot"),
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--snapshot", required=True, type=Path)
    build_parser.add_argument("--delivery-evidence-dir", required=True, type=Path)
    build_parser.add_argument("--today", default=date.today().isoformat())
    build_parser.add_argument("--output", required=True, type=Path)
    build_parser.add_argument("--require-live-source", action="store_true")
    build_parser.add_argument("--max-age-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if args.require_live_source:
            if snapshot.get("source") not in {
                "authenticated_coconala_default_context_dom",
                "authenticated_coconala_hidden_default_context_dom",
            } or snapshot.get("read_only") is not True:
                raise ValueError("production queue requires a read-only authenticated live DOM snapshot")
            captured = datetime.fromisoformat(str(snapshot.get("captured_at") or ""))
            if captured.tzinfo is None:
                raise ValueError("live DOM snapshot timestamp lacks timezone")
            age = (datetime.now(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds()
            if age < -30 or age > args.max_age_seconds:
                raise ValueError(f"live DOM snapshot is stale (age_seconds={age:.0f})")
        result = build(snapshot, args.delivery_evidence_dir, date.fromisoformat(args.today))
        atomic_json(args.output, result)
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "success", "items": len(result["items"]), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
