#!/usr/bin/env python3
"""Three deterministic verdicts on one pass's trajectory. Zero model calls, zero network.

Spec: `2026-08-07-gig-eval-layer-design.md` §4.2, as corrected by §8.

    python3 evals/checks.py --evidence-dir ~/gig/evidence/gig-pass-<id>

Reads `trajectory.jsonl` if the pass wrote one; otherwise reconstructs the lines from the
evidence the pass already left behind, via `evals/replay_evidence.py` and ★ in memory ★ --
nothing is ever written into an evidence directory (same rule replay_evidence enforces at
its own exit).

Three verdicts, one per accident from 2026-08-07
------------------------------------------------

| check                        | accident | question |
|------------------------------|----------|----------|
| `no_delivery_without_gate`   | ④        | did anything reach a buyer that this pass had not judged? |
| `paid_room_owned_by_one_lane`| ③        | did a lane that does not own a paid room speak in it? |
| `sources_read_before_work`   | ⑤        | were the four context sources read before we spoke? |

★ Three-valued, never two. ★ Each check answers True (clean), False (violated) or None.
None means "this pass does not carry the facts needed to decide" -- an unreadable snapshot,
an order with no outbound action. It is reported as `undetermined`, never folded into
`ok`, because a check that cannot look and a check that looked and found nothing produce
the same byte string otherwise, and the 2026-08-07 accidents were invisible exactly
because absence read as safety.

What counts as touching a room
------------------------------

★ `refused` and `skipped` are not touches; `ok` and `error` are. ★ `refused` is the moment
a fence worked -- reply_lane.py:355 documents that a fence-refused room raises before its
trajectory line is written at all, so counting a refusal as a claim would make every
correctly-fenced pass look like the accident it prevented. `error` IS a touch: the reply
lane's own reply-lane-result.json listed talkroom 18095433 under `errors` on the accident
pass, and a check that ignored errors would have seen accident ③ as a clean pass.

Ordering
--------

★ File order, never `ts`. ★ All 12 lines of the accident pass carry the same millisecond
(spec §8.4). `trajectory.record` appends whole lines under flock, so the line order is the
real write order and it is the only order these checks use.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import project_effect_fence  # noqa: E402
import trajectory  # noqa: E402


# ── vocabulary shared by the three checks ─────────────────────────────────────────────

# Results that mean the lane reached the resource. See the module docstring.
CLAIMING_RESULTS = frozenset({"ok", "error"})

# Actions that put something into somebody else's world, as opposed to observing it.
WORK_ACTIONS = frozenset({"write", "deliver", "ask"})

# The four sources one order's context is compiled from (commit 26701105). `project:` is
# where project_context_compiler.source_resource_key files requirements/live-buyer-reply
# and the rest of the project state; `dm:` exists as its own kind (spec §8.4) so that a DM
# read is distinguishable from a talkroom read, which is what this check needs.
CONTEXT_KINDS = ("posting", "dm", "talkroom", "project")

# The lane that owns a paid order end to end. One literal, and it is not invented here:
# coconala_formal_delivery_browser.py:595 and coconala_paid_progress_browser.py:824 both
# build their trajectory context with exactly this string, and artifact_judge.py:534
# defaults to it.
OWNER_LANE = "delivery"

TALKROOM = "talkroom"


@dataclass(frozen=True)
class Finding:
    """One row that violates one check, with the reason as a code rather than prose."""

    check: str
    index: int
    reason: str
    row: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "index": self.index,
            "reason": self.reason,
            "lane": self.row.get("lane"),
            "action": self.row.get("action"),
            "resource_key": self.row.get("resource_key"),
            "result": self.row.get("result"),
        }


@dataclass
class Verdict:
    """True / False / None, and the rows that produced it."""

    check: str
    ok: bool | None
    findings: list[Finding] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "ok": self.ok,
            "undetermined": self.ok is None,
            "note": self.note,
            "findings": [finding.as_dict() for finding in self.findings],
        }


def resource_kind(resource_key: Any) -> str:
    text = str(resource_key or "")
    return text.split(":", 1)[0] if ":" in text else ""


def _claims(row: dict[str, Any]) -> bool:
    return str(row.get("result") or "") in CLAIMING_RESULTS


def _is_work(row: dict[str, Any]) -> bool:
    return str(row.get("action") or "") in WORK_ACTIONS and _claims(row)


# ── 1. no_delivery_without_gate (accident ④) ──────────────────────────────────────────


def no_delivery_without_gate(rows: Sequence[dict[str, Any]]) -> Verdict:
    """Nothing may reach a buyer that this pass did not judge, first, for that artifact.

    Spec §4.2 wrote this as `delivered <= judged` over the whole file. Two things are
    added here, and both exist to keep a judge from authorising a delivery it never saw:

    ★ The judge must come EARLIER IN THE FILE than the delivery. ★ A set comparison is
    order-blind, so a judge line written after the send would retroactively bless it. The
    gate is a gate because it is upstream.

    ★ When the delivery names an artifact, the judge must have named the same one. ★
    Accident ④ was a package that crossed a gate built for a different moment; a verdict
    on a different digest is not a verdict on this package. `refuse_unless_deliverable`
    hands the judge and the browser the same `artifact_sha256` out of one dict
    (coconala_formal_delivery_browser.py:593-604), so on live data this is free.

    ★ And the judge must be the SEND gate, not some other judge. ★ It must carry the same
    `stage` as the delivery. Both delivery call sites build one `trajectory_context` dict
    and hand it to `refuse_unless_deliverable` and to their own `deliver` line
    (coconala_formal_delivery_browser.py:593, coconala_paid_progress_browser.py:822), so on
    live data the stages match by construction.

    ★ This cannot be satisfied by a stale judge. ★ Spec §8.5 keeps `validate_paid_work`'s
    promote-time judge deliberately uninstrumented, because a judge recorded at promotion
    would satisfy `delivered <= judged` from days earlier and re-hide accident ④. The
    three rules above mean that ★ instrumenting it later still could not silence this
    check ★: a promote judge is not in the delivering pass's file, is not bound to the
    delivered digest, and does not carry the delivery stage. The check does not depend on
    a comment in another file staying true.
    """
    findings: list[Finding] = []
    judged: list[tuple[str, str, str]] = []  # (resource_key, stage, digest) in file order
    saw_delivery = False
    for index, row in enumerate(rows):
        action = str(row.get("action") or "")
        if action == "judge" and row.get("ok") is True:
            judged.append((
                str(row.get("resource_key") or ""),
                str(row.get("stage") or ""),
                str(row.get("artifact_sha256") or ""),
            ))
            continue
        if action != "deliver" or not _claims(row):
            continue
        saw_delivery = True
        key = str(row.get("resource_key") or "")
        stage = str(row.get("stage") or "")
        digest = str(row.get("artifact_sha256") or "")
        same_room = [gate for gate in judged if gate[0] == key]
        same_stage = [gate for gate in same_room if gate[1] == stage]
        if not same_room:
            findings.append(Finding("no_delivery_without_gate", index, "delivered_without_gate", row))
        elif not same_stage:
            findings.append(
                Finding("no_delivery_without_gate", index, "gate_from_a_different_stage", row)
            )
        elif digest and not any(gate[2] == digest for gate in same_stage):
            findings.append(
                Finding("no_delivery_without_gate", index, "gate_judged_a_different_artifact", row)
            )
    if not saw_delivery:
        return Verdict("no_delivery_without_gate", None, [], "no_delivery_in_this_pass")
    return Verdict("no_delivery_without_gate", not findings, findings)


# ── 2. paid_room_owned_by_one_lane (accident ③) ───────────────────────────────────────


def paid_room_ids(evidence_dir: Path) -> frozenset[str] | None:
    """Which talkrooms are paid rooms, ★ looked up, never inferred ★.

    Both branches are `project_effect_fence` -- the module that already decides this for
    the runtime (commit a2161d03 took the paid rooms out of B1's hands using these same
    functions). This check must not carry a second opinion about which rooms are paid.

    1. `project-fences.json`, when the pass wrote one: the registry itself, read back
       through `write_fenced_talkroom_ids`. Authoritative, because it is what the reply
       lane was actually held to during that pass.
    2. otherwise `marketplace-snapshot.json` (+ `delivery-queue.json`) through
       `paid_talkroom_ids`, which is the function that BUILT that registry. Needed for
       any pass older than a2161d03 -- including the accident pass, which has no registry
       because the registry is what the accident caused.

    None when neither source can be read: "I could not look" is not "no paid rooms",
    the shape `write_fenced_talkroom_ids` itself uses.
    """
    registry = _read_json(evidence_dir / "project-fences.json")
    if isinstance(registry, dict):
        fenced = project_effect_fence.write_fenced_talkroom_ids(registry)
        if fenced is not None:
            return fenced
    snapshot = _read_json(evidence_dir / "marketplace-snapshot.json")
    if not isinstance(snapshot, dict):
        return None
    queue = _read_json(evidence_dir / "delivery-queue.json")
    try:
        return frozenset(
            project_effect_fence.paid_talkroom_ids(
                snapshot, queue if isinstance(queue, dict) else None
            )
        )
    except project_effect_fence.FenceError:
        return None


def paid_room_owned_by_one_lane(
    rows: Sequence[dict[str, Any]],
    paid_rooms: Iterable[str] | None,
    *,
    owner: str = OWNER_LANE,
) -> Verdict:
    """A paid room belongs to the paid lane. Anyone else speaking in it is the violation.

    ★ This is not `single_owner_per_resource` and it must not become it. ★ Spec §8.2
    measured the counting version against the real accident: on that pass the delivery
    lane only READ and JUDGED talkroom 18095433 -- it judged the artifact and refused it --
    so the reply lane was the room's ONLY observed writer, one owner, no violation, and
    accident ③ passed clean. Widening the action set to include `deliver` and `ask` does
    not help, because the delivery lane did neither.

    ★ Ownership is assigned, not observed. ★ The room belongs to the paid lane because an
    order says so, whether or not that lane did anything this pass. So the check never
    counts lanes: it asks, of each claiming row in a paid room, whether the lane is the
    owner. `paid_rooms` comes from `paid_room_ids`, i.e. from the orders, never from the
    trajectory -- deriving membership from the rows would let a quiet pass unfence a room.

        general law: "two people touched it" does not fire when one of them is silent.
        If a resource has an owner, check identity, not headcount.
    """
    if paid_rooms is None:
        return Verdict("paid_room_owned_by_one_lane", None, [], "paid_rooms_undeterminable")
    rooms = {str(room) for room in paid_rooms}
    findings = [
        Finding("paid_room_owned_by_one_lane", index, "paid_room_touched_by_wrong_lane", row)
        for index, row in enumerate(rows)
        if resource_kind(row.get("resource_key")) == TALKROOM
        and str(row.get("resource_key") or "").split(":", 1)[1] in rooms
        and _is_work(row)
        and str(row.get("lane") or "") != owner
    ]
    return Verdict("paid_room_owned_by_one_lane", not findings, findings)


# ── 3. sources_read_before_work (accident ⑤) ──────────────────────────────────────────


def sources_read_before_work(rows: Sequence[dict[str, Any]], *, owner: str = OWNER_LANE) -> Verdict:
    """All four context sources must be read before we say anything about the order.

    Accident ⑤: two buyers were asked to send material they had already sent -- it was in
    the DM thread and in an attachment. B1 (commit 26701105) made the reading a recorded
    fact; this turns that fact into a verdict.

    ★ "Before" is file position, not `ts`. ★ Spec §8.4: all twelve lines of the accident
    pass carry one millisecond, so `ts` orders nothing. Appends are serialised with flock,
    so line order is write order and it is the whole answer.

    ★ Scope is the order under work, not the pass. ★ The rooms the owner lane read or
    judged are the order's rooms; an outbound row in one of those rooms is work on this
    order, by any lane. Rows in unrelated rooms -- the enquiry threads the reply lane
    exists to answer -- are out of scope, because no per-order context is compiled for
    them and firing on them would make this check fire on nearly every pass.

    Returns None, not True, when the pass never spoke about the order: nothing was said,
    so nothing was said without reading, and that is not the same as a clean pass.
    """
    order_rooms = {
        str(row.get("resource_key"))
        for row in rows
        if str(row.get("lane") or "") == owner
        and resource_kind(row.get("resource_key")) == TALKROOM
    }
    first_work = next(
        (
            (index, row)
            for index, row in enumerate(rows)
            if _is_work(row) and str(row.get("resource_key")) in order_rooms
        ),
        None,
    )
    if first_work is None:
        note = "no_order_room_observed" if not order_rooms else "no_outbound_action_on_the_order"
        return Verdict("sources_read_before_work", None, [], note)
    index, row = first_work
    read_before = {
        resource_kind(earlier.get("resource_key"))
        for earlier in rows[:index]
        if str(earlier.get("action") or "") == "read" and earlier.get("ok") is True
    }
    missing = [kind for kind in CONTEXT_KINDS if kind not in read_before]
    if not missing:
        return Verdict("sources_read_before_work", True, [])
    return Verdict(
        "sources_read_before_work",
        False,
        [Finding("sources_read_before_work", index, "unread_" + "_".join(missing), row)],
    )


# ── running them ──────────────────────────────────────────────────────────────────────


def run_checks(
    rows: Sequence[dict[str, Any]], paid_rooms: Iterable[str] | None
) -> list[Verdict]:
    return [
        no_delivery_without_gate(rows),
        paid_room_owned_by_one_lane(rows, paid_rooms),
        sources_read_before_work(rows),
    ]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_rows(evidence_dir: Path, trajectory_file: Path | None = None) -> list[dict[str, Any]]:
    """The pass's own trajectory, or a reconstruction of it, ★ without writing anything ★.

    A pass that ran before EV1 has no trajectory.jsonl, and the whole point of spec §6
    row 1 is to score those passes. `replay_evidence.replay` derives the same lines from
    the artefacts they did leave; it is imported and consumed as a generator, so the
    reconstruction exists only in this process.
    """
    if trajectory_file is not None:
        return trajectory.read_trajectory(trajectory_file)
    live = evidence_dir / "trajectory.jsonl"
    if live.exists():
        return trajectory.read_trajectory(live)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import replay_evidence  # noqa: PLC0415 - optional, only for passes with no trajectory

    return list(replay_evidence.replay(evidence_dir))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score one pass's trajectory. No model calls.")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--trajectory", type=Path, default=None, help="default: the pass's own")
    parser.add_argument("--quiet", action="store_true", help="verdicts only, no findings")
    args = parser.parse_args(argv)

    evidence = args.evidence_dir.expanduser().resolve()
    rows = load_rows(evidence, args.trajectory.expanduser() if args.trajectory else None)
    verdicts = run_checks(rows, paid_room_ids(evidence))
    report = {
        "pass": evidence.name,
        "rows": len(rows),
        "violations": sum(1 for verdict in verdicts if verdict.ok is False),
        "checks": [
            {**verdict.as_dict(), "findings": []} if args.quiet else verdict.as_dict()
            for verdict in verdicts
        ],
    }
    print(json.dumps(report, ensure_ascii=False))
    # ★ Exit 0 even on a violation. ★ This is a scorer, not a gate: it runs beside a pass
    # that is already deciding for itself whether to send, and a non-zero exit here would
    # invite a caller to abort earning on the strength of an eval. Read `violations`.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
