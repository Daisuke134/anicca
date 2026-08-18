#!/usr/bin/env python3
"""The ledger row between "we built it" and "the buyer's world changed".

Measured 2026-08-07 on order 91000002: the builder produced v5, the acceptance
report said PASS, and the project ledger's last event was
``paid_work_ready_for_browser``.  There was no row saying the artifact was sent
and no row saying it could not be sent.  A pass that cannot read either fact has
only one option left -- build it again -- which is how the same order reached v5
and how 90000004 reached v17.

Two facts are therefore recorded here, and they are recorded the same way:

* ``delivery_attempt_failed`` -- we tried to put this exact artifact in front of
  this exact buyer request and did not succeed, for this reason.
* the confirmed half, ``confirmed_patch()`` -- merged into the caller's own
  "sent" row so one delivery produces one event rather than two.

A row that only exists on success reproduces the defect one level up, so the
failure half is as durable as the success half and carries a counter.  Without a
counter, "never tried" and "tried and failed nine times" are the same silence.

Channel-neutral by construction.  ``talkroom`` (a file in the marketplace room)
and ``live_system`` (90000004, where delivery means the buyer's own WordPress
changed) are both deliveries; neither is the definition.  Nothing in this module
reads a marketplace, an artifact format, or a browser.

Discipline for anything written here (both linked memories apply):

* State moves only through ``project_ledger.append``.  No file in this module
  writes ``state.json``.
* Nothing observed by a browser is copied in.  Every recorded value is
  re-derived from the project's own validated state or from a typed vocabulary
  owned by this repository; free text coming back from a page is dropped rather
  than stored.
* A count of zero says how it was counted.  Pruned history records that it was
  pruned instead of silently reading as "this never happened".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import runpy
import time
from pathlib import Path
from typing import Any

_HEX64 = re.compile(r"[0-9a-f]{64}")
# Our own failure vocabulary, not the browser's. Anything else is normalised
# away rather than persisted: an append-only row must not become a place where
# remote text lands.
_REASON = re.compile(r"[a-z0-9_]{1,64}")
_PASS_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_VERSION = re.compile(r"[A-Za-z0-9_.-]{1,32}")

CHANNEL_TALKROOM = "talkroom"
CHANNEL_LIVE_SYSTEM = "live_system"
CHANNELS = (CHANNEL_TALKROOM, CHANNEL_LIVE_SYSTEM)

UNKNOWN_REASON = "unknown_delivery_failure"

# History is for humans and for debugging; the counters below are the authority.
_HISTORY_LIMIT = 20
# One key per (buyer request, package) pair.  A project that keeps rebuilding
# creates a new key each time, so the map is bounded -- and the eviction is
# counted, because a zero that came from pruning is not a zero.
_COUNTS_LIMIT = 32

DEFAULT_MAX_ATTEMPTS = 3


def max_attempts() -> int:
    raw = str(os.environ.get("GIG_DELIVERY_MAX_ATTEMPTS") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_ATTEMPTS
    return value if value > 0 else DEFAULT_MAX_ATTEMPTS


def _hex(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if _HEX64.fullmatch(text) else ""


def normalize_channel(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in CHANNELS else CHANNEL_TALKROOM


def normalize_reason(value: Any) -> str:
    text = str(value or "").strip()
    return text if _REASON.fullmatch(text) else UNKNOWN_REASON


def _optional(pattern: re.Pattern[str], value: Any) -> str | None:
    text = str(value or "").strip()
    return text if pattern.fullmatch(text) else None


def attempt_key(buyer_feedback_sha256: Any = None, package_sha256: Any = None) -> str:
    """Identity of one delivery target: this buyer request, this package.

    Deliberately finer than the project.  Keying attempts per project would let
    a failure against v4 be read as a failure against v5, and keying them per
    buyer request alone would do the same across rebuilds.
    """
    return f"{_hex(buyer_feedback_sha256) or '-'}:{_hex(package_sha256) or '-'}"


def _rows(state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = state.get("delivery_attempts")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _counts(state: dict[str, Any]) -> dict[str, int]:
    counts = state.get("delivery_attempt_counts")
    if not isinstance(counts, dict):
        return {}
    clean: dict[str, int] = {}
    for key, value in counts.items():
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            clean[str(key)] = value
    return clean


def attempt_report(
    state: dict[str, Any],
    buyer_feedback_sha256: Any = None,
    package_sha256: Any = None,
) -> dict[str, Any]:
    """Answer "never tried" vs "tried and failed n times" for one target.

    ``verdict`` is the whole point of this module.  ``failed_attempts`` comes
    from the counter map rather than the bounded history, so a long-running
    project cannot lose attempts to the history window and read as fresh.
    """
    key = attempt_key(buyer_feedback_sha256, package_sha256)
    failed = _counts(state).get(key, 0)
    confirmed = _hex(state.get("delivery_confirmed_feedback_sha256")) == _hex(
        buyer_feedback_sha256
    ) and bool(_hex(buyer_feedback_sha256))
    history = [row for row in _rows(state) if str(row.get("key") or "") == key]
    last = history[-1] if history else None
    limit = max_attempts()
    if confirmed:
        verdict = "confirmed"
    elif failed:
        verdict = "tried_and_failed"
    else:
        verdict = "never_tried"
    return {
        "key": key,
        "verdict": verdict,
        "failed_attempts": failed,
        "max_attempts": limit,
        "exhausted": verdict == "tried_and_failed" and failed >= limit,
        "last_reason": str(last.get("reason")) if last else None,
        "last_channel": str(last.get("channel")) if last else None,
        "last_at": last.get("at") if last else None,
        # A zero here can mean "no attempt was ever made" or "the record was
        # pruned".  Say which, so the two never share a byte pattern.
        "counts_evicted": int(state.get("delivery_attempt_counts_evicted") or 0),
        "history_truncated": bool(state.get("delivery_attempts_truncated")),
    }


def confirmed_for_feedback(state: dict[str, Any], buyer_feedback_sha256: Any) -> bool:
    """Did a confirmed delivery answer this exact buyer request?

    Both scalars must agree.  ``handled_buyer_feedback_sha256`` alone is not
    enough: 90000004 carries one written by a hand-recorded row, and that row is
    known to be stale (task #21).  Requiring the confirmation scalar as well
    means only deliveries this module recorded can satisfy the question, so no
    pre-existing project is retroactively declared delivered.
    """
    digest = _hex(buyer_feedback_sha256)
    if not digest:
        return False
    if _hex(state.get("handled_buyer_feedback_sha256")) != digest:
        return False
    return _hex(state.get("delivery_confirmed_feedback_sha256")) == digest


def _history_patch(
    state: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    history = [*_rows(state), row]
    truncated = bool(state.get("delivery_attempts_truncated")) or len(history) > _HISTORY_LIMIT
    return {
        "delivery_attempts": history[-_HISTORY_LIMIT:],
        "delivery_attempts_truncated": truncated,
    }


def _counts_patch(state: dict[str, Any], key: str, value: int) -> dict[str, Any]:
    counts = {**_counts(state), key: value}
    evicted = int(state.get("delivery_attempt_counts_evicted") or 0)
    if len(counts) > _COUNTS_LIMIT:
        # Newest keys are the ones a live order is still working against; drop
        # the oldest and say how many were dropped.
        drop = len(counts) - _COUNTS_LIMIT
        for stale in list(counts)[:drop]:
            if stale != key:
                counts.pop(stale, None)
                evicted += 1
    return {"delivery_attempt_counts": counts, "delivery_attempt_counts_evicted": evicted}


def failed_patch(
    state: dict[str, Any],
    *,
    channel: str,
    reason: str,
    buyer_feedback_sha256: Any = None,
    package_sha256: Any = None,
    artifact_version: Any = None,
    pass_id: Any = None,
    at: float | None = None,
) -> dict[str, Any]:
    """The durable "attempted and failed, for this reason" record."""
    key = attempt_key(buyer_feedback_sha256, package_sha256)
    row = {
        "at": float(at if at is not None else time.time()),
        "key": key,
        "channel": normalize_channel(channel),
        "outcome": "failed",
        "reason": normalize_reason(reason),
        "artifact_version": _optional(_VERSION, artifact_version),
        "package_sha256": _hex(package_sha256) or None,
        "buyer_feedback_sha256": _hex(buyer_feedback_sha256) or None,
        "pass_id": _optional(_PASS_ID, pass_id),
    }
    return {
        **_history_patch(state, row),
        **_counts_patch(state, key, _counts(state).get(key, 0) + 1),
        "last_delivery_attempt_outcome": "failed",
        "last_delivery_attempt_reason": row["reason"],
        "last_delivery_attempt_key": key,
        "last_delivery_attempt_at": row["at"],
        "last_delivery_attempt_channel": row["channel"],
    }


def confirmed_patch(
    state: dict[str, Any],
    *,
    channel: str,
    buyer_feedback_sha256: Any = None,
    package_sha256: Any = None,
    artifact_version: Any = None,
    pass_id: Any = None,
    at: float | None = None,
) -> dict[str, Any]:
    """The confirmed half, for the caller to merge into its own "sent" row.

    ``handled_buyer_feedback_sha256`` advances HERE and nowhere earlier.  Moving
    it when the artifact is built would mark an unsent file as handled and the
    buyer would never receive it -- which is the failure this module exists to
    end, inverted.  Moving it only on a confirmed delivery is safe only because
    the failure half above bounds the retries; the two are one mechanism.

    When the caller cannot name the buyer request (no digest in the queue item),
    the digest is left alone and the omission is recorded.  Advancing to an
    empty value would claim to have handled something we cannot name.
    """
    digest = _hex(buyer_feedback_sha256)
    key = attempt_key(buyer_feedback_sha256, package_sha256)
    row = {
        "at": float(at if at is not None else time.time()),
        "key": key,
        "channel": normalize_channel(channel),
        "outcome": "confirmed",
        "reason": None,
        "artifact_version": _optional(_VERSION, artifact_version),
        "package_sha256": _hex(package_sha256) or None,
        "buyer_feedback_sha256": digest or None,
        "pass_id": _optional(_PASS_ID, pass_id),
    }
    patch: dict[str, Any] = {
        **_history_patch(state, row),
        **_counts_patch(state, key, 0),
        "last_delivery_attempt_outcome": "confirmed",
        "last_delivery_attempt_reason": None,
        "last_delivery_attempt_key": key,
        "last_delivery_attempt_at": row["at"],
        "last_delivery_attempt_channel": row["channel"],
        "delivery_channel": row["channel"],
    }
    if digest:
        patch["handled_buyer_feedback_sha256"] = digest
        patch["delivery_confirmed_feedback_sha256"] = digest
        patch["delivery_digest_unadvanced_reason"] = None
    else:
        patch["delivery_digest_unadvanced_reason"] = "buyer_request_not_named_by_queue_item"
    return patch


def _ledger() -> Any:
    return runpy.run_path(str(Path(__file__).with_name("project_ledger.py")))


def _read_state(root: Path) -> dict[str, Any]:
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not state.get("request_id") or not state.get("adapter"):
        raise ValueError("project_state_not_initialized")
    return state


def record_failed(
    project_root: str | Path,
    *,
    channel: str,
    reason: str,
    buyer_feedback_sha256: Any = None,
    package_sha256: Any = None,
    artifact_version: Any = None,
    pass_id: Any = None,
) -> dict[str, Any]:
    """Append the failure row and return the report the next pass will read."""
    root = Path(project_root).expanduser().resolve()
    state = _read_state(root)
    # Re-derived from the project's own validated state, never from whatever the
    # browser last printed. If the caller names a package the ledger does not
    # hold, the ledger wins -- the attempt was against what we actually built.
    package = _hex(package_sha256) or _hex(state.get("current_package_sha256"))
    version = _optional(_VERSION, artifact_version) or _optional(
        _VERSION, state.get("current_version")
    )
    patch = failed_patch(
        state,
        channel=channel,
        reason=reason,
        buyer_feedback_sha256=buyer_feedback_sha256,
        package_sha256=package,
        artifact_version=version,
        pass_id=pass_id,
    )
    merged = _ledger()["append"](root, patch, "delivery_attempt_failed")
    return attempt_report(merged, buyer_feedback_sha256, package)


def correction_patch(
    state: dict[str, Any],
    *,
    reason: str,
    buyer_feedback_sha256: Any = None,
    package_sha256: Any = None,
    pass_id: Any = None,
    at: float | None = None,
) -> dict[str, Any]:
    """Supersede failures that were never real attempts, without claiming a delivery.

    Order 91000002, 2026-08-08: a contract-validation bug (progress_blockers_invalid,
    fixed the same day) crashed the delivery browser before any tab opened, and each
    crash was booked as a delivery attempt -- 9/3 exhausted against an order the buyer
    was actively waiting on. The counter was right about what was recorded and wrong
    about what happened.

    This is the failure half's ERRATUM, not the success half: the count for the target
    resets to zero and the correction is itself a durable history row, but the handled/
    confirmed digests are untouched -- nothing was delivered and nothing claims to be.
    Same discipline as every row here: state moves only through project_ledger.append,
    and the reason is our own vocabulary, never remote text.
    """
    key = attempt_key(buyer_feedback_sha256, package_sha256)
    row = {
        "at": float(at if at is not None else time.time()),
        "key": key,
        "channel": None,
        "outcome": "corrected",
        "reason": normalize_reason(reason),
        "artifact_version": None,
        "package_sha256": _hex(package_sha256) or None,
        "buyer_feedback_sha256": _hex(buyer_feedback_sha256) or None,
        "pass_id": _optional(_PASS_ID, pass_id),
    }
    return {
        **_history_patch(state, row),
        **_counts_patch(state, key, 0),
        "last_delivery_attempt_outcome": "corrected",
        "last_delivery_attempt_reason": row["reason"],
        "last_delivery_attempt_key": key,
        "last_delivery_attempt_at": row["at"],
    }


def record_correction(
    project_root: str | Path,
    *,
    reason: str,
    buyer_feedback_sha256: Any = None,
    pass_id: Any = None,
) -> dict[str, Any]:
    """Append the correction and return the report the next pass will read."""
    root = Path(project_root).expanduser().resolve()
    state = _read_state(root)
    package = _hex(state.get("current_package_sha256"))
    patch = correction_patch(
        state,
        reason=reason,
        buyer_feedback_sha256=buyer_feedback_sha256,
        package_sha256=package,
        pass_id=pass_id,
    )
    # A distinct event name on purpose: paid_admission's INERT_EVENTS denylist does not
    # know it, so the correction reads as the order having moved -- which it has: a defect
    # in our own machinery was found and fixed, and the next pass may retry.
    merged = _ledger()["append"](root, patch, "delivery_attempt_correction")
    return attempt_report(merged, buyer_feedback_sha256, package)


def _queue_feedback_digest(path: str | Path | None) -> str:
    if not path:
        return ""
    try:
        item = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return _hex(item.get("buyer_feedback_sha256")) if isinstance(item, dict) else ""


def _main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    failed = sub.add_parser("record-failed")
    failed.add_argument("--project-root", required=True, type=Path)
    failed.add_argument("--channel", default=CHANNEL_TALKROOM)
    failed.add_argument("--reason", required=True)
    failed.add_argument("--queue-item", type=Path)
    failed.add_argument("--pass-id")
    report = sub.add_parser("report")
    report.add_argument("--project-root", required=True, type=Path)
    report.add_argument("--queue-item", type=Path)
    correct = sub.add_parser("correct")
    correct.add_argument("--project-root", required=True, type=Path)
    correct.add_argument("--queue-item", type=Path)
    correct.add_argument("--reason", required=True)
    correct.add_argument("--pass-id")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    digest = _queue_feedback_digest(args.queue_item)
    try:
        if args.command == "record-failed":
            payload = record_failed(
                root,
                channel=args.channel,
                reason=args.reason,
                buyer_feedback_sha256=digest,
                pass_id=args.pass_id,
            )
        elif args.command == "correct":
            payload = record_correction(
                root,
                reason=args.reason,
                buyer_feedback_sha256=digest,
                pass_id=args.pass_id,
            )
        else:
            state = _read_state(root)
            payload = attempt_report(state, digest, state.get("current_package_sha256"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, separators=(",", ":")))
        return 1
    print(json.dumps({"ok": True, **payload}, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
