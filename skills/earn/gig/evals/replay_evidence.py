#!/usr/bin/env python3
"""Show the trajectory lines a pass that already ran WOULD have produced.

★ This is the EV1 proof, and it is a proof about the schema, not about the code. ★ The
writer is easy; the risk is that the schema in spec §4.1 cannot express what the real
lanes actually do. So this reads a finished evidence directory -- the artefacts the pass
left behind on its own -- and derives one trajectory line per action from them, using the
same ``trajectory.build_event`` the live call sites use. If a real pass cannot be
expressed, it fails here rather than in production.

It is also how spec §6 done-condition 1 is met: feed it ``gig-pass-1786075205-12532`` (the
2026-08-07 incident pass) and the lines it emits are the input the §4.2 checks will read.

★ Refuses to write inside ~/gig/evidence. ★ Replay is for sandbox copies. A live evidence
directory is the record of what happened, and a replay is a reconstruction of what would
have happened; writing the second into the place reserved for the first would make the
pass's own history unfalsifiable.

    python3 evals/replay_evidence.py --evidence-dir /tmp/replay/gig-pass-XXXX \\
        [--out /tmp/replay/trajectory.jsonl]

Mapping from evidence file to trajectory line
---------------------------------------------

| evidence                          | action    | lane     | stage               |
|-----------------------------------|-----------|----------|---------------------|
| context-read-receipt.json         | read (xN) | delivery | PAID_WORK           |
| paid-work-transaction.json        | judge     | delivery | PAID_WORK           |
| formal-delivery/paid-progress row | deliver   | delivery | PAID_QUEUE_DELIVERY |
| reply-lane-result.json events     | write     | reply    | INQUIRY_REPLY       |
| reply-lane-result.json errors     | write     | reply    | INQUIRY_REPLY       |

The last row is the one that matters. A reply-lane ERROR against a talkroom is still a
lane touching that room, and accident ③ (2026-08-07: a second lane wrote into a paid room
the delivery lane owned) is only visible if the reconstruction counts it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import trajectory  # noqa: E402
# ★ One classifier, not two. ★ The replay must sort sources into resource kinds exactly the
# way the live compiler does, or this tool would prove a schema that production does not
# actually write.
from project_context_compiler import source_resource_key  # noqa: E402

LIVE_EVIDENCE_ROOT = Path(os.environ.get("GIG_EVIDENCE_ROOT", "~/gig/evidence")).expanduser()

_DIGITS = re.compile(r"\A[0-9]+\Z")

# The status reply_lane.py:426 files a fence-refused room under. Not imported: reply_lane
# pulls in the browser stack, and this is a one-word wire format.
PAID_TALKROOM_REFUSED = "paid_talkroom_refused"


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _identity(evidence: Path) -> tuple[str, str]:
    """(request_id, talkroom_id) for the order this pass worked, from its own queue item."""
    queue = _json(evidence / "project-context-queue-item.json") or {}
    request_id = str(queue.get("request_id") or "").strip()
    talkroom_id = str(queue.get("talkroom_id") or "").strip()
    if not request_id and talkroom_id:
        # A direct service purchase has no 募集; its identity is its talkroom. Same fallback
        # as coconala_formal_delivery_browser.validate_queue_contract.
        request_id = talkroom_id
    receipt = _json(evidence / "context-read-receipt.json") or {}
    thread = str(receipt.get("thread_id") or "")
    if (not request_id or not talkroom_id) and thread.count(":") == 2:
        _, request_id, talkroom_id = thread.split(":")
    return request_id, talkroom_id


def replay(evidence: Path) -> Iterator[dict[str, Any]]:
    request_id, talkroom_id = _identity(evidence)

    # ── read: the three context sources, from B1's own receipt (commit 26701105) ────────
    receipt = _json(evidence / "context-read-receipt.json") or {}
    for source in receipt.get("sources_read") or []:
        if not isinstance(source, dict):
            continue
        key = source_resource_key(source.get("path") or "", request_id, talkroom_id)
        if key is None:
            continue
        digest = str(source.get("sha256") or "").lower()
        yield trajectory.build_event(
            stage="PAID_WORK", lane="delivery", resource_key=key, action="read",
            result="ok", artifact_sha256=digest if len(digest) == 64 else None,
        )

    # ── judge: the artifact verdict the paid-work transaction recorded ──────────────────
    txn = _json(evidence / "paid-work-transaction.json") or {}
    artifact = ((txn.get("validation") or {}).get("artifact")) or {}
    digest = str(artifact.get("sha256") or "").lower()
    if talkroom_id and len(digest) == 64:
        committed = str(txn.get("status") or "") == "committed"
        yield trajectory.build_event(
            stage="PAID_WORK", lane="delivery", resource_key=f"talkroom:{talkroom_id}",
            action="judge", result="ok" if committed else "refused",
            reason="" if committed else f"transaction_{txn.get('status') or 'unknown'}",
            artifact_sha256=digest,
        )

    # ── deliver: whatever actually reached a buyer-visible message ─────────────────────
    for name in ("formal-delivery.json", "paid-progress.json", "paid-answer.json"):
        row = _json(evidence / name)
        if not isinstance(row, dict):
            continue
        room = str(row.get("talkroom_id") or talkroom_id or "").strip()
        sent = bool(row.get("sent") or row.get("verified") or row.get("send_performed"))
        digest = str(row.get("package_sha256") or row.get("artifact_sha256") or "").lower()
        if not _DIGITS.fullmatch(room):
            continue
        yield trajectory.build_event(
            stage="PAID_QUEUE_DELIVERY", lane="delivery", resource_key=f"talkroom:{room}",
            action="ask" if name == "paid-answer.json" else "deliver",
            result="ok" if sent else "refused",
            artifact_sha256=digest if len(digest) == 64 else None,
        )

    # ── write: every room the reply lane touched, success or failure ───────────────────
    #
    # ★ A refusal is not a touch. ★ Corrected 2026-08-07 (EV2) on measurement: the live
    # writer at reply_lane.py:355 documents that a fence-refused room raises inside
    # execute_reply and never reaches the record call, so live trajectories carry NO row
    # for it -- while this reconstruction filed every `errors` entry as `error`, i.e. as a
    # claim on the room. Pass gig-pass-1786107605-99603 is the proof: its 18095433 row is
    # `paid_talkroom_refused`, the fence working exactly as commit a2161d03 intended, and
    # the reconstruction reported it as the reply lane touching a paid room -- the same
    # shape as the accident it prevented. Recorded as `refused` rather than dropped so the
    # fence's own work stays visible; the ownership check ignores `refused` either way.
    reply = _json(evidence / "reply-lane-result.json") or {}
    for bucket, result in (("events", "ok"), ("errors", "error")):
        for row in reply.get(bucket) or []:
            if not isinstance(row, dict):
                continue
            room = str(row.get("talkroom_id") or "").strip()
            if not _DIGITS.fullmatch(room):
                continue
            refused = str(row.get("status") or "") == PAID_TALKROOM_REFUSED
            yield trajectory.build_event(
                stage="INQUIRY_REPLY", lane="reply", resource_key=f"talkroom:{room}",
                action="write", result="refused" if refused else result,
                reason=PAID_TALKROOM_REFUSED if refused else "",
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    evidence = args.evidence_dir.expanduser().resolve()
    out = (args.out or evidence / "trajectory.jsonl").expanduser().resolve()
    try:
        out.relative_to(LIVE_EVIDENCE_ROOT.resolve())
    except (ValueError, OSError):
        pass
    else:
        print(f"refusing to write a reconstruction into live evidence: {out}", file=sys.stderr)
        return 2

    events = list(replay(evidence))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"ok": True, "events": len(events), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
