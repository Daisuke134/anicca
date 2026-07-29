#!/usr/bin/env python3
"""Generic buyer-visible delivery and inquiry cadence decisions.

This module contains only deterministic policy.  Marketplace adapters collect
DOM facts and the model/browser worker performs the actual send.  No buyer,
request number, title, or marketplace is embedded here.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def _artifact_ready(item: dict[str, Any]) -> bool:
    path = str(item.get("artifact_path") or "").strip()
    version = str(item.get("artifact_version") or "").strip()
    if not path or not version or version not in Path(path).name:
        return False
    return Path(path).is_file()


def _hash_ready(item: dict[str, Any]) -> bool:
    digest = str(item.get("package_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        return False
    path = str(item.get("artifact_path") or "")
    if path and Path(path).is_file():
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return actual == digest
    return False


def _acceptance_ready(item: dict[str, Any]) -> bool:
    status = str(item.get("acceptance_status") or "").upper()
    # A boolean emitted by a model or local ledger is not evidence.  The
    # acceptance report must be a real file in the request-scoped workspace.
    evidence_path = str(item.get("acceptance_evidence_path") or "")
    return status == "PASS" and bool(evidence_path and Path(evidence_path).is_file())


def delivery_decision(item: dict[str, Any]) -> dict[str, Any]:
    """Return ``formal`` only when all independent delivery gates pass.

    A progress message is always allowed when work exists or feedback was
    observed.  It explicitly keeps the formal-delivery checkbox off, so an
    incomplete artifact can be shown to the buyer without falsely closing a
    transaction.
    """
    if (
        item.get("formal_delivery_observed") is True
        and item.get("talkroom_state") == "納品確認待ち"
        and item.get("buyer_feedback_pending_artifact") is not True
        and item.get("buyer_reply_after_artifact_observed") is not True
    ):
        return {
            "mode": "none",
            "formal_delivery_checkbox": False,
            "buyer_visible": True,
            "blockers": [],
        }
    # ``formal_delivery_not_confirmed`` is the action to perform, not a
    # prerequisite.  Once the artifact/acceptance/hash/agreement gates pass,
    # the worker may submit it and the next collector observes the durable
    # 納品確認待ち state.
    blockers = [
        str(x) for x in (item.get("blockers") or [])
        if str(x) and str(x) != "formal_delivery_not_confirmed"
    ]
    if not _artifact_ready(item) and "missing_versioned_artifact" not in blockers:
        blockers.append("missing_versioned_artifact")
    if not _acceptance_ready(item) and "missing_acceptance_evidence" not in blockers:
        blockers.append("missing_acceptance_evidence")
    if not _hash_ready(item) and "missing_package_hash" not in blockers:
        blockers.append("missing_package_hash")
    # Dais ruling 2026-07-25: never wait for explicit buyer agreement before
    # formal delivery. Once artifact/acceptance/hash gates pass we submit
    # formally and the buyer reviews (accept or request revision) — the ball
    # must always be in the buyer's court, never ours.
    # Unprocessed buyer feedback still blocks formal: a fresh buyer message
    # after our artifact means the current artifact may not answer it, so the
    # builder must process the feedback first (progress), then formal-deliver.
    if (
        item.get("buyer_feedback_pending_artifact") is True
        or item.get("buyer_reply_after_artifact_observed") is True
    ) and "buyer_feedback_unprocessed" not in blockers:
        blockers.append("buyer_feedback_unprocessed")
    mode = "formal" if not blockers else "progress"
    return {
        "mode": mode,
        "formal_delivery_checkbox": mode == "formal",
        "buyer_visible": True,
        "blockers": blockers,
    }


def progress_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Build a concise, buyer-visible progress update for the current pass.

    Buyer-facing text must read like a person wrote it. Internal blocker
    identifiers, ledger field names, and hashes never appear here — they stay
    in the evidence ledger (Dais ruling 2026-07-25 after
    "残課題: buyer_feedback_unprocessed" leaked to a real buyer).
    """
    decision = delivery_decision(item)
    version = str(item.get("artifact_version") or "未生成")
    delta = [str(x) for x in (item.get("acceptance_delta") or []) if str(x)]
    blockers = decision["blockers"]
    if delta:
        # Keep it scannable: lead with the update, list the changes plainly.
        changes = "\n".join(f"・{line}" for line in delta[:8])
        message = (
            f"お世話になっております。修正版 {version} をお送りします。\n"
            f"今回の主な変更点です。\n{changes}\n"
            "ご確認いただき、気になる点があれば遠慮なくお知らせください。"
        )
    else:
        message = (
            f"お世話になっております。{version} の内容を確認しながら調整を進めています。"
            "まとまり次第あらためてお送りしますので、少しお待ちください。"
        )
    # A progress payload is intentionally buyer-visible even when the formal
    # delivery gate is not met; the worker must attach only the artifact that
    # actually exists and must not tick the formal checkbox.
    return {
        "mode": "progress",
        "formal_delivery_checkbox": False,
        "buyer_visible": True,
        "artifact_version": version,
        "acceptance_delta": delta,
        "blockers": blockers,
        "message": message,
    }


def inquiries_from_dom(dom: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize open conversation cards into a generic reply queue.

    Buyer identity and raw message text are deliberately excluded.  The
    talkroom URL and bounded title are enough for the browser worker to reopen
    the conversation and compose a context-aware response from the live DOM.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in dom.get("cards", []):
        if not isinstance(card, dict):
            continue
        href = str(card.get("talkroom_url") or "")
        parsed = urlsplit(href)
        match = re.fullmatch(r"/(talkrooms|mypage/direct_message)/([A-Za-z0-9_-]+)", parsed.path.rstrip("/"))
        if not match:
            continue
        route, talkroom_id = match.groups()
        if talkroom_id in seen:
            continue
        seen.add(talkroom_id)
        title = re.sub(r"\s+", " ", str(card.get("title") or "")).strip()[:200]
        last_side = str(card.get("last_message_side") or "").lower()
        reply_required = (
            last_side == "buyer"
            if last_side in {"buyer", "seller"}
            else bool(card.get("unread"))
        )
        rows.append({
            "talkroom_id": talkroom_id,
            "talkroom_url": f"https://coconala.com/{route}/{talkroom_id}",
            "title": title,
            "reply_required": reply_required,
            "next_action": "reply" if reply_required else "observe",
        })
    return rows


def inquiry_reply_instruction(row: dict[str, Any]) -> dict[str, Any]:
    """Return a generic bounded instruction for one live conversation."""
    return {
        "talkroom_id": str(row.get("talkroom_id") or ""),
        "talkroom_url": str(row.get("talkroom_url") or ""),
        "mode": "reply",
        "message": "ご連絡ありがとうございます。内容を確認し、対応可能な範囲・納期・次の確認事項を具体的にご案内します。",
    }


def validate_inquiry_evidence(evidence_dir: str | Path, expected_ids: list[str]) -> tuple[bool, list[str]]:
    """Validate machine-readable post-send proof for every reply action.

    The browser worker must write ``inquiry-actions.json``.  A model's JSON
    acknowledgement is not enough: each expected room needs a real screenshot,
    a canonical talkroom URL, and a bounded live-DOM observation captured
    after the send.
    """
    root = Path(evidence_dir)
    manifest = root / "inquiry-actions.json"
    try:
        rows = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ["missing_inquiry_actions_manifest"]
    if not isinstance(rows, list):
        return False, ["inquiry_actions_manifest_not_array"]
    by_id = {str(row.get("talkroom_id")): row for row in rows if isinstance(row, dict)}
    errors: list[str] = []
    root_resolved = root.resolve()
    for room_id in expected_ids:
        row = by_id.get(str(room_id))
        if not row:
            errors.append(f"missing_inquiry_action:{room_id}")
            continue
        url = str(row.get("url") or "")
        if url != f"https://coconala.com/talkrooms/{room_id}":
            errors.append(f"invalid_inquiry_url:{room_id}")
        screenshot = Path(str(row.get("screenshot_path") or ""))
        try:
            screenshot.resolve().relative_to(root_resolved)
            screenshot_owned = True
        except ValueError:
            screenshot_owned = False
        if not screenshot_owned or not screenshot.is_file() or screenshot.stat().st_size == 0:
            errors.append(f"missing_inquiry_screenshot:{room_id}")
        live_dom_path = Path(str(row.get("live_dom_path") or ""))
        try:
            live_dom_path.resolve().relative_to(root_resolved)
            live_dom_owned = True
        except ValueError:
            live_dom_owned = False
        try:
            live_dom = json.loads(live_dom_path.read_text(encoding="utf-8")) if live_dom_owned else None
        except (OSError, json.JSONDecodeError):
            live_dom = None
        if not isinstance(live_dom, dict) or live_dom.get("url") != url or live_dom.get("reply_sent") is not True:
            errors.append(f"missing_post_send_live_dom:{room_id}")
        if row.get("sent") is not True:
            errors.append(f"reply_not_observed_sent:{room_id}")
    return not errors, errors


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-inquiry")
    validate.add_argument("--evidence-dir", required=True, type=Path)
    validate.add_argument("--expected-ids", required=True, type=Path)
    args = parser.parse_args()
    expected = json.loads(args.expected_ids.read_text(encoding="utf-8"))
    ok, errors = validate_inquiry_evidence(args.evidence_dir, [str(x) for x in expected])
    print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, separators=(",", ":")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
