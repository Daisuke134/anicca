#!/usr/bin/env python3
"""Build and verify the deterministic conversation input for Gig B1.

The marketplace adapter owns discovery.  B1 receives only the canonical inbox
route plus a bounded union of current open-order, inquiry, and delivery-queue
talkrooms.  The model may decide what each conversation needs, but it cannot
silently substitute another inbox route or omit a discovered conversation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
    from project_effect_fence import (
        FenceError,
        active_fences_for_item,
        paid_order_talkroom_ids,
    )
except ModuleNotFoundError:
    _fence_spec = importlib.util.spec_from_file_location(
        "project_effect_fence", Path(__file__).with_name("project_effect_fence.py")
    )
    if _fence_spec is None or _fence_spec.loader is None:
        raise
    _fence_module = importlib.util.module_from_spec(_fence_spec)
    _fence_spec.loader.exec_module(_fence_module)
    FenceError = _fence_module.FenceError
    active_fences_for_item = _fence_module.active_fences_for_item
    paid_order_talkroom_ids = _fence_module.paid_order_talkroom_ids


INBOX_URL = "https://coconala.com/message?fromMyPage=true"
ALLOWED_OUTCOMES = frozenset({"observed_no_action", "replied", "submitted", "blocked"})


class ContractError(ValueError):
    """The deterministic B1 input is absent or cannot be trusted."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_inbox_url(value: Any) -> bool:
    parsed = urlsplit(str(value or ""))
    return (
        parsed.scheme == "https"
        and parsed.hostname == "coconala.com"
        and parsed.path == "/message"
        and parse_qs(parsed.query, keep_blank_values=True) == {"fromMyPage": ["true"]}
    )


def canonical_talkroom(row: dict[str, Any]) -> tuple[str, str] | None:
    raw_id = str(row.get("talkroom_id") or "").strip()
    raw_url = str(row.get("marketplace_url") or row.get("talkroom_url") or "").strip()
    parsed = urlsplit(raw_url) if raw_url else None
    url_id = None
    if parsed and parsed.hostname in {"coconala.com", "www.coconala.com"}:
        match = re.fullmatch(r"/talkrooms/(\d+)", parsed.path)
        url_id = match.group(1) if match else None
    if raw_id and not re.fullmatch(r"\d+", raw_id):
        raise ContractError("malformed_talkroom_id")
    if raw_id and raw_url and url_id != raw_id:
        raise ContractError("talkroom_identity_url_mismatch")
    talkroom_id = raw_id or url_id
    if not talkroom_id:
        return None
    return talkroom_id, f"https://coconala.com/talkrooms/{talkroom_id}"


def _require_rows(container: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = container.get(key)
    if not isinstance(value, list):
        raise ContractError(f"malformed_{owner}_{key}")
    if not all(isinstance(row, dict) for row in value):
        raise ContractError(f"malformed_{owner}_{key}_row")
    return value


def build_context(
    snapshot: dict[str, Any],
    queue: dict[str, Any],
    snapshot_path: Path,
    queue_path: Path,
    *,
    fence_registry: dict[str, Any] | None = None,
    projects_root: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ContractError("malformed_snapshot")
    if not isinstance(queue, dict):
        raise ContractError("malformed_queue")
    inbox = snapshot.get("inbox")
    if not isinstance(inbox, dict):
        raise ContractError("missing_snapshot_inbox")
    if inbox.get("not_found") is True:
        raise ContractError("inbox_not_found")
    if not valid_inbox_url(inbox.get("url")):
        raise ContractError("invalid_inbox_route")

    orders = _require_rows(snapshot, "orders", "snapshot")
    _require_rows(snapshot, "quotes", "snapshot")
    direct_inquiries = _require_rows(snapshot, "inquiries", "snapshot")
    inquiries = (
        _require_rows(snapshot, "b1_inquiries", "snapshot")
        if "b1_inquiries" in snapshot
        else direct_inquiries
    )
    queue_items = _require_rows(queue, "items", "queue")

    # TODO 3c: prevention is removing the capability, not guarding it.
    #
    # B1 is an agent with a shell and a CDP websocket. On 2026-08-07 it sent two ungrounded
    # messages into paid talkroom 90000002 by hand-writing websockets.connect + a click on
    # 送信 -- it called no module of ours, so no Python gate was ever in its path. The only
    # line that holds is the one that is never crossed: an agent that is not told the room
    # exists does not open it.
    #
    # Nothing is lost by taking these rooms away, and that is measured rather than assumed.
    # coconala_queue_snapshot writes live-dom/talkroom-<id>.json for every order at
    # gig_pass.sh:1041 -- deterministic, before any lane, no model -- and thread_freshness
    # and state_reconciler read exactly that file (glob "*/live-dom/talkroom-<id>.json").
    # NO consumer anywhere reads agent-B1/talkroom-*.live-dom.json; report_envelope, the one
    # reader of agent-B1/, reads attempt-01.result.json for ids and outcomes only. In
    # gig-pass-1786071605-53411 the collector's file for 90000002 is 649 bytes carrying
    # transaction_state, formal_delivery_confirmed and buyer_attachments; B1's copy of the
    # same room is 264 bytes carrying url, not_found, observed and title -- a receipt for a
    # visit and nothing else.
    #
    # The removal set is snapshot["orders"], NOT the wider fence set. It is the same list
    # the collector iterates, so "removed from B1" and "already observed by the pass" are
    # the same rooms by construction.
    try:
        forbidden = paid_order_talkroom_ids(snapshot)
    except FenceError as error:
        # Fail closed, and note which direction that is here: if the orders list cannot be
        # read, this pass cannot tell a paid room from an enquiry. Raising isolates the B1
        # lane for one pass. Continuing would hand B1 the paid rooms again, which is the
        # bug. paid_work_evidence.validate_paid_work, gig_pass.sh's paid_work_fresh_blocked
        # and delivery_cadence.delivery_decision all take the same direction on their own
        # "I could not look" answer.
        raise ContractError(f"paid_membership_undeterminable:{error}") from error

    discovered: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], *reasons: str, required: bool = True) -> None:
        identity = canonical_talkroom(row)
        if identity is None:
            if required:
                raise ContractError("missing_actionable_talkroom_identity")
            return
        talkroom_id, url = identity
        if talkroom_id in forbidden:
            # Not an omission the coverage check should punish -- see forbidden_talkrooms
            # in the returned context, which turns visiting this room into its own error.
            return
        target = discovered.setdefault(talkroom_id, {"talkroom_id": talkroom_id, "url": url, "reasons": []})
        if target["url"] != url:
            raise ContractError("talkroom_identity_url_mismatch")
        for reason in reasons:
            if reason and reason not in target["reasons"]:
                target["reasons"].append(reason)

    # Every open paid order and inbox conversation is a sweep target.  This is
    # intentionally broader than unread-only; a stale badge cannot hide work.
    for row in orders:
        add(row, "open_paid_order")
    for row in inquiries:
        reasons = ["open_inquiry"]
        if row.get("reply_required") is True:
            reasons.append("reply_required")
        add(row, *reasons)
    for row in queue_items:
        queue_class = str(row.get("queue_class") or "").strip()
        has_talkroom_hint = bool(row.get("talkroom_id")) or "/talkrooms/" in str(
            row.get("marketplace_url") or row.get("talkroom_url") or ""
        )
        add(row, f"queue:{queue_class}" if queue_class else "queue", required=has_talkroom_hint)

    if fence_registry is not None:
        now = datetime.now(timezone.utc)
        for row in discovered.values():
            matches = active_fences_for_item(
                row,
                fence_registry,
                capability="conversation_write",
                platform="coconala",
                now=now,
            )
            row["write_allowed"] = not matches
            if matches:
                row["write_blocked_by"] = [str(fence["id"]) for fence in matches]
    else:
        for row in discovered.values():
            row["write_allowed"] = True

    if projects_root is not None:
        for key, row in discovered.items():
            row["conversation"] = talkroom_conversation(key, projects_root=projects_root)

    return {
        "version": 1,
        "snapshot_path": str(snapshot_path.resolve()),
        "queue_path": str(queue_path.resolve()),
        "inbox_url": INBOX_URL,
        "actionable_talkrooms": [discovered[key] for key in sorted(discovered, key=int)],
        # The rooms this lane must not open. Stated rather than merely absent, so that the
        # coverage contract can run in both directions: the existing check catches a
        # supplied room B1 dropped, and validate_result now catches a room B1 visited that
        # was never supplied. Silence about them would leave "B1 went somewhere it was not
        # sent" indistinguishable from a stale context.
        "forbidden_talkrooms": sorted(forbidden, key=lambda value: (len(value), value)),
    }


# --- P1b: hand the lane what the buyer said, instead of telling it to go and look ----------
#
# b1-context was 570 bytes of URLs and reasons. The lane's evidence contract asked for a
# screenshot and never for a scroll, so it read the top of the thread, called it a purchase
# acknowledgement, and returned observed_no_action — while further down, unread, the buyer
# had written that the fix did not match the instructions and that they would not force us
# to continue. Twenty-four passes did nothing on top of that.
#
# The conversation was already on disk that entire time. This is not new collection; it is
# giving the lane what the loop already recorded.

# Buyer messages are kept whole: there are few of them and they are the entire point. Ours
# are capped, because every branch of every lane pays for this context and our own prose is
# not what the pass needs to reason about.
_SELLER_TEXT_CAP = 400
_MAX_MESSAGES = 40


def talkroom_conversation(talkroom_id: str, *, projects_root: Path) -> dict[str, Any]:
    """The recorded conversation for one room, bounded, with absence made visible."""
    path = Path(projects_root) / str(talkroom_id) / "source" / "talkroom" / "messages.jsonl"
    if not path.is_file():
        # Never an empty list. "No messages" reads as "nothing to answer", which is the
        # original bug; the lane is told the record was missing.
        return {
            "source_missing": True,
            "messages": [],
            "counts": {},
            "buyer_last_said": None,
            "unreadable_lines": 0,
        }

    rows: list[dict[str, Any]] = []
    unreadable = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # One broken line must not hide the conversation around it.
            unreadable += 1

    counts: dict[str, int] = {}
    for row in rows:
        side = str(row.get("side") or "unknown")
        counts[side] = counts.get(side, 0) + 1

    kept = rows[-_MAX_MESSAGES:]
    messages = []
    for row in kept:
        text = str(row.get("text") or "")
        if row.get("side") != "buyer" and len(text) > _SELLER_TEXT_CAP:
            text = text[:_SELLER_TEXT_CAP] + "…"
        messages.append({"side": row.get("side"), "text": text, "sent_at": row.get("sent_at")})

    buyer_last = next(
        (str(row.get("text") or "") for row in reversed(rows) if row.get("side") == "buyer"),
        None,
    )
    return {
        "source_missing": False,
        "messages": messages,
        "counts": counts,
        # Called out separately: buried in a list of twenty, the decisive sentence is easy to
        # skim past, and skimming past it is exactly what happened.
        "buyer_last_said": buyer_last,
        "unreadable_lines": unreadable,
    }


def _owned_fresh_file(path_value: Any, root: Path, min_mtime: float) -> tuple[Path | None, str | None]:
    try:
        path = Path(str(path_value or "")).resolve()
        path.relative_to(root.resolve())
    except (OSError, ValueError):
        return None, "not_owned"
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return None, "missing"
        if path.stat().st_mtime < min_mtime:
            return None, "stale"
    except OSError:
        return None, "missing"
    return path, None


def _json_file(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def validate_result(
    context_path: Path,
    summary_path: Path,
    evidence_dir: Path,
    min_mtime: float,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        context = json.loads(context_path.read_text(encoding="utf-8"))
        if not isinstance(context, dict):
            raise ValueError("context is not an object")
        expected_rows = context["actionable_talkrooms"]
        if not isinstance(expected_rows, list):
            raise ValueError("actionable_talkrooms is not an array")
        # A context written before TODO 3c has no such key. Treated as unreadable rather
        # than as an empty forbidden set: an old context cannot prove B1 stayed out of a
        # paid room, and "I could not look" must not read as "there was nothing to find".
        forbidden_rows = context["forbidden_talkrooms"]
        if not isinstance(forbidden_rows, list):
            raise ValueError("forbidden_talkrooms is not an array")
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return False, ["b1_context_unreadable"]
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, ["b1_runner_summary_unreadable"]
    if (
        not isinstance(summary, dict)
        or summary.get("status") != "success"
        or summary.get("task_label") != "gig-B1"
    ):
        return False, ["b1_runner_summary_not_success"]
    result_path, result_path_error = _owned_fresh_file(summary.get("result_path"), evidence_dir, min_mtime)
    if result_path_error:
        return False, [f"b1_result_{result_path_error}"]
    result = _json_file(result_path)
    if not result or result.get("status") != "ok":
        return False, ["b1_result_invalid"]
    current = result.get("current_b1")
    if not isinstance(current, dict):
        return False, ["current_b1_missing"]

    try:
        bound_context = Path(str(current.get("context_path") or "")).resolve()
        if bound_context != context_path.resolve():
            errors.append("context_path_mismatch")
        if current.get("context_sha256") != sha256_file(context_path):
            errors.append("context_sha256_mismatch")
    except OSError:
        errors.append("context_binding_unreadable")
    if current.get("inbox_url") != INBOX_URL or current.get("inbox_status") != "ok":
        errors.append("inbox_result_route_or_status_invalid")

    inbox_shot, shot_error = _owned_fresh_file(current.get("inbox_screenshot_path"), evidence_dir, min_mtime)
    if shot_error:
        errors.append(f"inbox_screenshot_{shot_error}")
    inbox_dom_path, dom_error = _owned_fresh_file(current.get("inbox_live_dom_path"), evidence_dir, min_mtime)
    if dom_error:
        errors.append(f"inbox_live_dom_{dom_error}")
    inbox_dom = _json_file(inbox_dom_path)
    if inbox_dom:
        if inbox_dom.get("not_found") is True:
            errors.append("inbox_not_found")
        if not valid_inbox_url(inbox_dom.get("url")):
            errors.append("inbox_live_dom_route_mismatch")
        if inbox_dom.get("observed") is not True:
            errors.append("inbox_not_observed")
    elif inbox_dom_path is not None:
        errors.append("inbox_live_dom_invalid_json")

    expected = {str(row.get("talkroom_id")): row for row in expected_rows if isinstance(row, dict)}
    inspected = current.get("inspected_talkrooms")
    if not isinstance(inspected, list) or not all(isinstance(row, dict) for row in inspected):
        return False, errors + ["inspected_talkrooms_malformed"]
    actual_ids = [str(row.get("talkroom_id") or "") for row in inspected]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(expected):
        errors.append("talkroom_coverage_mismatch")
    # TODO 3c: the coverage contract, run the other way. Above catches a supplied room B1
    # dropped; this catches a room B1 reached that it was never given. A paid talkroom in
    # this result means the lane went looking for work that belongs to PAID_WORK, and it is
    # named rather than folded into talkroom_coverage_mismatch, because "you visited order
    # 91000002's room" and "your room list is stale" need different fixes.
    forbidden = {str(value) for value in forbidden_rows}
    for talkroom_id in sorted(set(actual_ids) & forbidden):
        errors.append(f"talkroom_visit_forbidden:{talkroom_id}")
    for row in inspected:
        talkroom_id = str(row.get("talkroom_id") or "")
        expected_row = expected.get(talkroom_id)
        if not expected_row:
            continue
        expected_url = str(expected_row.get("url") or "")
        if row.get("url") != expected_url:
            errors.append(f"talkroom_result_url_mismatch:{talkroom_id}")
        if row.get("outcome") not in ALLOWED_OUTCOMES:
            errors.append(f"talkroom_outcome_invalid:{talkroom_id}")
        if expected_row.get("write_allowed") is False and row.get("outcome") in {"replied", "submitted"}:
            errors.append(f"talkroom_write_forbidden:{talkroom_id}")
        screenshot, screenshot_error = _owned_fresh_file(row.get("screenshot_path"), evidence_dir, min_mtime)
        if screenshot_error:
            errors.append(f"talkroom_screenshot_{screenshot_error}:{talkroom_id}")
        live_path, live_error = _owned_fresh_file(row.get("live_dom_path"), evidence_dir, min_mtime)
        if live_error:
            errors.append(f"talkroom_live_dom_{live_error}:{talkroom_id}")
        live_dom = _json_file(live_path)
        if live_dom:
            if live_dom.get("url") != expected_url:
                errors.append(f"talkroom_live_dom_url_mismatch:{talkroom_id}")
            if live_dom.get("observed") is not True:
                errors.append(f"talkroom_not_observed:{talkroom_id}")
            if live_dom.get("not_found") is True:
                errors.append(f"talkroom_not_found:{talkroom_id}")
        elif live_path is not None:
            errors.append(f"talkroom_live_dom_invalid_json:{talkroom_id}")
    return not errors, errors


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"malformed_{label}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--snapshot", required=True, type=Path)
    build.add_argument("--queue", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--fences", type=Path)
    build.add_argument(
        "--projects-root",
        type=Path,
        default=None,
        help="where <talkroom_id>/source/talkroom/messages.jsonl lives; without it the lane "
             "is told to go and look instead of being handed what the buyer said",
    )
    validate = subparsers.add_parser("validate")
    validate.add_argument("--context", required=True, type=Path)
    validate.add_argument("--runner-summary", required=True, type=Path)
    validate.add_argument("--evidence-dir", required=True, type=Path)
    validate.add_argument("--min-mtime", required=True, type=float)
    args = parser.parse_args()
    try:
        if args.command == "build":
            fence_registry = (
                _load_object(args.fences, "fences") if args.fences is not None else None
            )
            context = build_context(
                _load_object(args.snapshot, "snapshot"),
                _load_object(args.queue, "queue"),
                args.snapshot,
                args.queue,
                fence_registry=fence_registry,
                projects_root=args.projects_root,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            print(json.dumps({"ok": True, "count": len(context["actionable_talkrooms"]), "output": str(args.output)}, separators=(",", ":")))
            return 0
        ok, errors = validate_result(args.context, args.runner_summary, args.evidence_dir, args.min_mtime)
        print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, separators=(",", ":")))
        return 0 if ok else 1
    except ContractError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
