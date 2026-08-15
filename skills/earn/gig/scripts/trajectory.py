#!/usr/bin/env python3
"""One append-only line per action: which lane touched which resource, and what happened.

★ This file's deliverable is the schema, not the code. ★ Every later check in the eval
layer (spec 4.2) reads what this writes, so the vocabularies below are the contract and
the writing is incidental.

Placement follows spec 2026-08-07-gig-eval-layer-design.md §4.1/§5:

    ~/gig/evidence/gig-pass-<id>/trajectory.jsonl

★ Not to be confused with ~/gig/trajectory/<pass_id>/trajectory.jsonl ★, which
cdp_snapshot.py and cdp_nav_snapshot.py have written since before this existed. That one
is a browser navigation trail (one row per screenshot). This one is a semantic action
trail (one row per read/write/deliver/judge/ask). Different directory, different schema,
same unfortunate name -- the name here is fixed by the spec.

Two invariants that the callers depend on
-----------------------------------------

★ 1. A trajectory write may never fail its caller. ★ Instrumentation that can break
earning is worse than no instrumentation. ``record()`` therefore has exactly one
``return`` path for every failure mode: a full disk, an unwritable directory, a read-only
filesystem, a bad vocabulary, a value that will not serialise. It returns None and the
caller carries on. Only ``BaseException`` that is not ``Exception`` (KeyboardInterrupt,
SystemExit) is allowed through, because a Ctrl-C must still stop the pass.

★ 2. Nothing that is not an identifier or a digest may enter a line. ★ There is an active
plaintext-credential incident in this repository, so this is enforced by shape rather than
by care at the call sites: every field is either a fixed enum, an identifier constrained to
``[A-Za-z0-9_.:-]``, or a 64-character hex digest. ``reason`` is a reason CODE, not prose --
a Japanese buyer sentence, a password, a URL with a query string and an API key in it all
fail the charset and are replaced by ``reason_unprintable``. A call site that passes the
wrong thing leaks nothing; it only loses its own reason code.

Ordering
--------

``ts`` carries milliseconds, but ★ the authoritative order is the order of the lines in the
file ★. Appends are serialised with ``fcntl.flock`` and written with a single ``write()``
into a handle opened ``"a"``, matching ``work_event_projector._append_unique``, so parallel
lanes cannot interleave a partial line and file order is real write order. Checks that care
about "did the read happen before the write" (spec 4.2 ``sources_read_before_work``) should
read line order, not ``ts``.

Calling it
----------

From bash, the same idiom as every other script in this directory, plus the ``|| true``
that gig_pass.sh already uses for side-channel writes (see gig_pass.sh:198):

    python3 "$G/scripts/trajectory.py" --stage PAID_QUEUE_DELIVERY --lane delivery \\
        --resource-key "talkroom:90000002" --action deliver --result ok >/dev/null 2>&1 || true

From Python, an import and one call:

    import trajectory
    trajectory.record(stage="PAID_QUEUE_DELIVERY", lane="delivery",
                      resource_key="talkroom:90000002", action="deliver", result="ok")

Neither form needs to know where the file is. gig_pass.sh exports ``GIG_TRAJECTORY_FILE``
once per pass and every child process inherits it, the same way ``ANICCA_BUDGET_SCOPE_ID``
and friends are exported at gig_pass.sh:319-335. ★ With the variable unset the writer is a
silent no-op ★, which is what makes the test suite and ad-hoc runs write nothing.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# ── The vocabularies. These are the deliverable. ──────────────────────────────────────
#
# Fixed and minimal, per spec §4.1. A value outside them is REJECTED, never written: a
# check that reads this file must be able to treat "action" as a closed set, and one
# silently-accepted typo would make every membership test quietly wrong.

ACTIONS = ("read", "write", "deliver", "judge", "ask")

# spec §4.1 names three shapes. ``dm`` is the fourth, added on measurement: B1
# (commit 26701105) reads posting, DM, talkroom and our own commitments as four distinct
# sources, and spec §4.2 ``sources_read_before_work`` has to tell a DM read from a talkroom
# read. Folding DM under ``project:`` would collapse exactly the distinction the check
# needs. See the schema note at the bottom of this docstring block.
RESOURCE_KINDS = ("talkroom", "project", "posting", "dm")

# Not fixed by the spec. ``ok`` in spec §4.2's no_delivery_without_gate is a boolean field,
# while the §4.1 example line carries a string ``result`` -- so a line carries both, and
# ``ok`` is DERIVED from ``result`` here so the two can never disagree.
RESULTS = ("ok", "refused", "error", "skipped")

_IDENT = re.compile(r"\A[A-Za-z0-9_.:-]{1,64}\Z")
_REASON = re.compile(r"\A[A-Za-z0-9_.:-]{1,120}\Z")
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")
_RESOURCE_KEY = re.compile(r"\A(%s):[A-Za-z0-9_.-]{1,64}\Z" % "|".join(RESOURCE_KINDS))

REASON_UNPRINTABLE = "reason_unprintable"

ENV_FILE = "GIG_TRAJECTORY_FILE"
ENV_STAGE = "GIG_TRAJECTORY_STAGE"


class InvalidTrajectoryEvent(ValueError):
    """A value outside a fixed vocabulary.

    ★ Raised by build_event(), never by record(). ★ Tests and the CLI want to be told
    loudly; the production call sites must not be able to die of their own instrumentation.
    """


def trajectory_path(path: str | os.PathLike[str] | None = None) -> Path | None:
    """Where the line goes, or None meaning 'write nothing'."""
    if path is not None:
        text = str(path).strip()
        return Path(text).expanduser() if text else None
    text = str(os.environ.get(ENV_FILE) or "").strip()
    return Path(text).expanduser() if text else None


def _ident(value: Any, field: str) -> str:
    text = str(value if value is not None else "").strip()
    if not _IDENT.fullmatch(text):
        raise InvalidTrajectoryEvent(f"{field}_invalid")
    return text


def build_event(
    *,
    stage: str,
    lane: str,
    resource_key: str,
    action: str,
    result: str = "ok",
    reason: str = "",
    artifact_sha256: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """The whole schema, in one function. Raises InvalidTrajectoryEvent on bad vocabulary."""
    if action not in ACTIONS:
        raise InvalidTrajectoryEvent(f"action_not_in_vocabulary:{action!r}")
    if result not in RESULTS:
        raise InvalidTrajectoryEvent(f"result_not_in_vocabulary:{result!r}")
    key = str(resource_key or "").strip()
    if not _RESOURCE_KEY.fullmatch(key):
        raise InvalidTrajectoryEvent(f"resource_key_not_in_vocabulary:{key!r}")

    event: dict[str, Any] = {
        "ts": round(time.time() if now is None else float(now), 3),
        "stage": _ident(stage, "stage"),
        "lane": _ident(lane, "lane"),
        "resource_key": key,
        "action": action,
        "result": result,
        # spec §4.2 reads e.get("ok"); spec §4.1 shows result. Derived, so never contradictory.
        "ok": result == "ok",
    }
    if artifact_sha256 is not None:
        digest = str(artifact_sha256).strip().lower()
        if not _SHA256.fullmatch(digest):
            raise InvalidTrajectoryEvent("artifact_sha256_invalid")
        event["artifact_sha256"] = digest
    text = str(reason or "").strip()
    if text:
        # ★ Not raised on. ★ A call site that hands over the judge's prose instead of the
        # error id has made a mistake, and the correct outcome of that mistake is a line
        # that still records what happened with the prose thrown away -- not an exception
        # inside a delivery gate, and not buyer text on disk.
        event["reason"] = text if _REASON.fullmatch(text) else REASON_UNPRINTABLE
    return event


def _append(path: Path, line: str) -> None:
    """Append one whole line under an exclusive lock.

    Same shape as work_event_projector._append_unique: open "a" (so every write goes to
    the current end of file regardless of what another process did), take LOCK_EX, write
    the line in ONE call, flush. flock serialises the write() calls, O_APPEND makes the
    offset atomic; between them a parallel lane cannot land inside another lane's line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(line)
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def record(
    *,
    stage: str | None = None,
    lane: str,
    resource_key: str,
    action: str,
    result: str = "ok",
    reason: str = "",
    artifact_sha256: str | None = None,
    path: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    """Write one line. ★ Returns None instead of raising, for every failure there is. ★

    Returns the event that was written, or None when nothing was written -- because no
    destination is configured, because the vocabulary was wrong, or because the disk said
    no. The caller is not expected to check the return value; the tests are.
    """
    try:
        target = trajectory_path(path)
        if target is None:
            return None
        event = build_event(
            stage=stage if stage is not None else os.environ.get(ENV_STAGE, "UNKNOWN"),
            lane=lane,
            resource_key=resource_key,
            action=action,
            result=result,
            reason=reason,
            artifact_sha256=artifact_sha256,
        )
        _append(target, json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        return event
    except Exception as error:  # noqa: BLE001 - see invariant 1 in the module docstring
        # Never to stdout: several callers parse their own stdout as JSON.
        try:
            print(f"trajectory_write_skipped:{type(error).__name__}", file=sys.stderr)
        except Exception:  # noqa: BLE001 - even the diagnostic must not raise
            pass
        return None


def read_trajectory(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    """Every well-formed line, in file order. ★ File order is the authoritative order. ★"""
    rows: list[dict[str, Any]] = []
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8")
    except OSError:
        return rows
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append one line to the pass trajectory.")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--resource-key", required=True)
    parser.add_argument("--action", required=True, choices=list(ACTIONS))
    parser.add_argument("--result", default="ok", choices=list(RESULTS))
    parser.add_argument("--reason", default="")
    parser.add_argument("--artifact-sha256", default=None)
    parser.add_argument("--file", default=None, help=f"defaults to ${ENV_FILE}")
    args = parser.parse_args(argv)

    target = trajectory_path(args.file)
    if target is None:
        # Not an error: a pass that did not export the variable simply has no trajectory.
        print(json.dumps({"ok": True, "written": False, "reason": "no_trajectory_file"}))
        return 0
    try:
        event = build_event(
            stage=args.stage if args.stage is not None else os.environ.get(ENV_STAGE, "UNKNOWN"),
            lane=args.lane,
            resource_key=args.resource_key,
            action=args.action,
            result=args.result,
            reason=args.reason,
            artifact_sha256=args.artifact_sha256,
        )
    except InvalidTrajectoryEvent as error:
        # ★ Rejected, loudly, and not written. ★ Non-zero so a human running this by hand
        # sees it; the bash call sites end in `|| true`, so the pass is still unaffected.
        print(json.dumps({"ok": False, "written": False, "error": str(error)}), file=sys.stderr)
        return 2
    try:
        _append(target, json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    except Exception as error:  # noqa: BLE001 - invariant 1
        print(json.dumps({"ok": True, "written": False,
                          "reason": f"trajectory_write_skipped:{type(error).__name__}"}))
        return 0
    print(json.dumps({"ok": True, "written": True, "event": event}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
