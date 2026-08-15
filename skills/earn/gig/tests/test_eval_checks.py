"""EV2: the three deterministic checks, against the real 2026-08-07 evidence.

★ The two classes at the top are the point. ★ A check that fires on a fixture and not on
the accident is worthless, and a check that fires on everything is worse than none, so
every check here is pinned in BOTH directions: on the real accident pass
(`gig-pass-1786075205-12532`) and on a real healthy pass (`gig-pass-1786107605-99603`),
before any constructed row appears.

The constructed trajectories that follow are negative controls, not coverage. Each one
carries exactly one defect, asserts the check fires on it, then removes that one defect
and asserts silence -- so a check that simply returned False would fail here.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "evals"))

import checks  # noqa: E402
import replay_evidence  # noqa: E402

EVIDENCE = Path("/workspace/gig/evidence")
ACCIDENT_PASS = EVIDENCE / "gig-pass-1786075205-12532"
HEALTHY_PASS = EVIDENCE / "gig-pass-1786107605-99603"

# The paid room both passes share: order 91000002, the room accident ③ happened in.
# ponytail: needs_accident/needs_healthy replay REAL evidence at EVIDENCE (machine-local,
# never in git); the room id there must match this constant's real value or those two
# guarded tests fail even though nothing is actually broken. $GIG_EVAL_PAID_ROOM lets a
# machine with real evidence on disk override the synthetic default.
PAID_ROOM = os.environ.get("GIG_EVAL_PAID_ROOM", "90000002")
# An ordinary enquiry thread. Not a paid room, so the reply lane owns it.
FREE_ROOM = "93000002"


def _row(lane, action, resource_key, result="ok", stage="TEST", **extra):
    """One trajectory line, built by the production builder so the schema stays honest."""
    import trajectory

    return trajectory.build_event(
        stage=stage, lane=lane, resource_key=resource_key, action=action,
        result=result, **extra,
    )


def _verdicts(rows, paid_rooms=(PAID_ROOM,)):
    return {verdict.check: verdict for verdict in checks.run_checks(rows, paid_rooms)}


# ── the real accident, and the real healthy pass ──────────────────────────────────────


needs_accident = pytest.mark.skipif(
    not ACCIDENT_PASS.is_dir(), reason=f"{ACCIDENT_PASS} has been garbage-collected"
)
needs_healthy = pytest.mark.skipif(
    not HEALTHY_PASS.is_dir(), reason=f"{HEALTHY_PASS} has been garbage-collected"
)


@pytest.fixture(scope="module")
def accident_rows():
    return list(replay_evidence.replay(ACCIDENT_PASS))


@pytest.fixture(scope="module")
def healthy_rows():
    return list(replay_evidence.replay(HEALTHY_PASS))


@needs_accident
def test_the_real_accident_pass_shows_a_second_lane_in_the_paid_room(accident_rows):
    """Accident ③, on the pass it happened on."""
    verdict = checks.paid_room_owned_by_one_lane(accident_rows, checks.paid_room_ids(ACCIDENT_PASS))
    assert verdict.ok is False
    assert [(finding.row["lane"], finding.row["action"], finding.row["resource_key"])
            for finding in verdict.findings] == [("reply", "write", f"talkroom:{PAID_ROOM}")]


@needs_accident
def test_the_counting_version_from_spec_4_2_stays_clean_on_the_same_rows(accident_rows):
    """★ The regression this whole check exists to prevent (spec §8.2). ★

    `single_owner_per_resource` counts the lanes that wrote to a resource. On these exact
    rows the delivery lane only read and judged the room -- it refused the artifact -- so
    `reply` is the only writer, one owner, and accident ③ passes clean. If someone ever
    replaces the identity check with a headcount, this test says what they lost.
    """
    owners: dict[str, set[str]] = {}
    for row in accident_rows:
        if row["action"] == "write":
            owners.setdefault(row["resource_key"], set()).add(row["lane"])
    assert owners[f"talkroom:{PAID_ROOM}"] == {"reply"}
    assert all(len(lanes) <= 1 for lanes in owners.values())  # the spec version: no violation


@needs_accident
def test_the_real_accident_pass_spoke_before_reading_the_posting_and_the_dm(accident_rows):
    """Accident ⑤: the buyer's 募集 and DM were never read, and we wrote anyway."""
    verdict = checks.sources_read_before_work(accident_rows)
    assert verdict.ok is False
    assert [finding.reason for finding in verdict.findings] == ["unread_posting_dm"]
    kinds_read = {checks.resource_kind(row["resource_key"]) for row in accident_rows
                  if row["action"] == "read"}
    assert kinds_read == {"project", "talkroom"}  # posting and dm genuinely absent


@needs_healthy
def test_the_healthy_pass_is_silent_on_both_checks(healthy_rows):
    """Same two checks, same rooms, a pass that behaved. Neither fires."""
    verdicts = _verdicts(healthy_rows, checks.paid_room_ids(HEALTHY_PASS))
    assert verdicts["paid_room_owned_by_one_lane"].ok is True
    assert verdicts["sources_read_before_work"].ok is not False
    assert {checks.resource_kind(row["resource_key"]) for row in healthy_rows
            if row["action"] == "read"} == {"project", "talkroom", "dm", "posting"}


@needs_healthy
def test_the_healthy_pass_stays_silent_once_it_actually_sends(healthy_rows):
    """★ The direct proof for ⑤. ★

    The healthy pass never sent anything (the fence refused the reply lane and the paid
    lane delivered nothing), so `sources_read_before_work` is undetermined there -- silence
    for want of an action, which proves nothing about the reading. Append the send it did
    not make and the check has to say True, because all four sources really were read.
    """
    assert checks.sources_read_before_work(healthy_rows).ok is None
    sent = healthy_rows + [_row("delivery", "deliver", f"talkroom:{PAID_ROOM}")]
    assert checks.sources_read_before_work(sent).ok is True


@needs_healthy
def test_a_fence_refusal_is_not_a_touch(healthy_rows):
    """The healthy pass's reply row for the paid room IS the fence working.

    reply_lane.py:355 never records a fence-refused room at all; the replay records it as
    `refused` so the fence stays visible. Either way it must not read as a claim on the
    room, or every correctly-fenced pass would look like the accident it prevented.
    """
    refusals = [row for row in healthy_rows
                if row["lane"] == "reply" and row["resource_key"] == f"talkroom:{PAID_ROOM}"]
    assert [row["result"] for row in refusals] == ["refused"]
    assert checks.paid_room_owned_by_one_lane(healthy_rows, {PAID_ROOM}).ok is True


@needs_accident
def test_the_paid_room_identity_comes_from_the_orders_not_from_the_rows():
    """★ Exit proof 4. ★ The accident pass predates project-fences.json, so membership is
    resolved through `project_effect_fence.paid_talkroom_ids` over the pass's own
    marketplace snapshot and delivery queue -- the same function that builds the registry
    the runtime enforces. Nothing here reads the trajectory to decide what is paid."""
    rooms = checks.paid_room_ids(ACCIDENT_PASS)
    assert rooms is not None and PAID_ROOM in rooms and FREE_ROOM not in rooms
    assert not (ACCIDENT_PASS / "project-fences.json").exists()


@needs_healthy
def test_the_registry_is_preferred_when_the_pass_wrote_one():
    """A pass that carries its own fence registry is scored against that registry."""
    registry = json.loads((HEALTHY_PASS / "project-fences.json").read_text(encoding="utf-8"))
    fenced = {fence["identities"]["talkroom_id"] for fence in registry["fences"]}
    assert checks.paid_room_ids(HEALTHY_PASS) == fenced


def test_paid_rooms_are_undetermined_rather_than_empty_when_nothing_can_be_read(tmp_path):
    """★ Absence must not read as safety. ★ No snapshot, no registry: None, not set()."""
    assert checks.paid_room_ids(tmp_path) is None
    verdict = checks.paid_room_owned_by_one_lane(
        [_row("reply", "write", f"talkroom:{PAID_ROOM}")], None
    )
    assert verdict.ok is None and verdict.note == "paid_rooms_undeterminable"


# ── negative controls: one defect each ────────────────────────────────────────────────


def test_a_delivery_with_no_gate_fires_and_the_same_delivery_gated_does_not():
    ungated = [_row("delivery", "deliver", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64)]
    assert checks.no_delivery_without_gate(ungated).ok is False
    assert [f.reason for f in checks.no_delivery_without_gate(ungated).findings] == [
        "delivered_without_gate"
    ]
    gated = [_row("delivery", "judge", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64)] + ungated
    assert checks.no_delivery_without_gate(gated).ok is True


def test_a_gate_recorded_after_the_send_does_not_authorise_it():
    """★ Order is the gate. ★ A set comparison (spec §4.2) would call this clean."""
    rows = [
        _row("delivery", "deliver", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64),
        _row("delivery", "judge", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64),
    ]
    assert {r["resource_key"] for r in rows if r["action"] == "deliver"} <= {
        r["resource_key"] for r in rows if r["action"] == "judge" and r["ok"]
    }  # the spec version: clean
    verdict = checks.no_delivery_without_gate(rows)
    assert verdict.ok is False and verdict.findings[0].reason == "delivered_without_gate"


def test_a_gate_on_a_different_artifact_does_not_authorise_this_one():
    """★ Exit proof against a stale judge. ★ Same room, earlier line, wrong package."""
    stale = [
        _row("delivery", "judge", f"talkroom:{PAID_ROOM}", artifact_sha256="b" * 64),
        _row("delivery", "deliver", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64),
    ]
    verdict = checks.no_delivery_without_gate(stale)
    assert verdict.ok is False
    assert verdict.findings[0].reason == "gate_judged_a_different_artifact"
    fresh = [
        _row("delivery", "judge", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64),
        stale[1],
    ]
    assert checks.no_delivery_without_gate(fresh).ok is True


def test_a_judge_from_another_stage_is_not_the_send_gate():
    """★ Spec §8.5, made structural. ★ If `validate_paid_work`'s promote-time judge is ever
    instrumented, its line lands under the PAID_WORK stage while the send gate and the
    delivery both carry PAID_QUEUE_DELIVERY -- so it still cannot authorise a send, and
    accident ④ cannot be re-hidden by adding instrumentation."""
    promote = _row("delivery", "judge", f"talkroom:{PAID_ROOM}", stage="PAID_WORK",
                   artifact_sha256="a" * 64)
    send = _row("delivery", "deliver", f"talkroom:{PAID_ROOM}", stage="PAID_QUEUE_DELIVERY",
                artifact_sha256="a" * 64)
    verdict = checks.no_delivery_without_gate([promote, send])
    assert verdict.ok is False and verdict.findings[0].reason == "gate_from_a_different_stage"
    gate = _row("delivery", "judge", f"talkroom:{PAID_ROOM}", stage="PAID_QUEUE_DELIVERY",
                artifact_sha256="a" * 64)
    assert checks.no_delivery_without_gate([promote, gate, send]).ok is True


def test_a_refused_gate_does_not_authorise_a_delivery():
    """`ok` is derived from `result`; a judge that refused has approved nothing."""
    rows = [
        _row("delivery", "judge", f"talkroom:{PAID_ROOM}", result="refused",
             reason="artifact_is_about_the_deal", artifact_sha256="a" * 64),
        _row("delivery", "deliver", f"talkroom:{PAID_ROOM}", artifact_sha256="a" * 64),
    ]
    assert checks.no_delivery_without_gate(rows).ok is False


def test_a_refused_delivery_needs_no_gate():
    """Nothing reached the buyer, so there was nothing to gate."""
    rows = [_row("delivery", "deliver", f"talkroom:{PAID_ROOM}", result="refused")]
    verdict = checks.no_delivery_without_gate(rows)
    assert verdict.ok is None and verdict.note == "no_delivery_in_this_pass"


def test_a_pass_with_no_delivery_at_all_is_undetermined_not_clean():
    verdict = checks.no_delivery_without_gate([_row("delivery", "read", "project:91000002")])
    assert verdict.ok is None


def test_the_wrong_lane_in_a_paid_room_fires_and_the_owner_lane_does_not():
    defect = [_row("reply", "write", f"talkroom:{PAID_ROOM}")]
    assert checks.paid_room_owned_by_one_lane(defect, {PAID_ROOM}).ok is False
    fixed = [_row("delivery", "write", f"talkroom:{PAID_ROOM}")]
    assert checks.paid_room_owned_by_one_lane(fixed, {PAID_ROOM}).ok is True


def test_the_wrong_lane_in_a_free_room_is_not_a_violation():
    """The reply lane answering an enquiry is the reply lane doing its job."""
    rows = [_row("reply", "write", f"talkroom:{FREE_ROOM}")]
    assert checks.paid_room_owned_by_one_lane(rows, {PAID_ROOM}).ok is True


@pytest.mark.parametrize("action", ["read", "judge"])
def test_observing_a_paid_room_is_allowed(action):
    """a2161d03: "other lanes observe this room and do not speak in it"."""
    rows = [_row("reply", action, f"talkroom:{PAID_ROOM}")]
    assert checks.paid_room_owned_by_one_lane(rows, {PAID_ROOM}).ok is True


@pytest.mark.parametrize("action", ["write", "deliver", "ask"])
def test_every_outbound_action_by_a_foreign_lane_counts(action):
    rows = [_row("reply", action, f"talkroom:{PAID_ROOM}")]
    assert checks.paid_room_owned_by_one_lane(rows, {PAID_ROOM}).ok is False


def test_an_errored_write_still_claims_the_room():
    """The accident's own row was an error, not a success."""
    rows = [_row("reply", "write", f"talkroom:{PAID_ROOM}", result="error")]
    assert checks.paid_room_owned_by_one_lane(rows, {PAID_ROOM}).ok is False


def test_a_missing_source_fires_and_reading_it_first_does_not():
    order = f"talkroom:{PAID_ROOM}"
    def context(kinds):
        return [_row("delivery", "read", key) for key in kinds]

    all_four = ["posting:91000002", "dm:91000002", order, "project:91000002"]
    work = _row("delivery", "deliver", order)
    assert checks.sources_read_before_work(context(all_four) + [work]).ok is True
    without_dm = [key for key in all_four if not key.startswith("dm:")]
    verdict = checks.sources_read_before_work(context(without_dm) + [work])
    assert verdict.ok is False and verdict.findings[0].reason == "unread_dm"


def test_a_source_read_after_the_send_does_not_count_even_at_the_same_millisecond():
    """★ File order, not `ts` (spec §8.4). ★ Every row below carries one timestamp."""
    order = f"talkroom:{PAID_ROOM}"
    before = [_row("delivery", "read", key, now=1786075205.0)
              for key in ("posting:91000002", order, "project:91000002")]
    dm = _row("delivery", "read", "dm:91000002", now=1786075205.0)
    work = _row("delivery", "deliver", order, now=1786075205.0)
    assert len({row["ts"] for row in before + [dm, work]}) == 1
    assert checks.sources_read_before_work(before + [work, dm]).ok is False
    assert checks.sources_read_before_work(before + [dm, work]).ok is True


def test_a_failed_read_is_not_a_read():
    order = f"talkroom:{PAID_ROOM}"
    rows = [
        _row("delivery", "read", "posting:91000002"),
        _row("delivery", "read", "dm:91000002", result="error"),
        _row("delivery", "read", order),
        _row("delivery", "read", "project:91000002"),
        _row("delivery", "deliver", order),
    ]
    assert checks.sources_read_before_work(rows).ok is False


def test_work_in_an_unrelated_room_is_out_of_scope():
    """No per-order context is compiled for an enquiry thread; firing on one would make
    this check fire on nearly every pass."""
    rows = [
        _row("delivery", "read", f"talkroom:{PAID_ROOM}"),
        _row("reply", "write", f"talkroom:{FREE_ROOM}"),
    ]
    verdict = checks.sources_read_before_work(rows)
    assert verdict.ok is None and verdict.note == "no_outbound_action_on_the_order"


# ── the runner ────────────────────────────────────────────────────────────────────────


@needs_accident
def test_the_cli_scores_a_real_pass_without_writing_into_its_evidence(capsys):
    before = sorted(path.name for path in ACCIDENT_PASS.iterdir())
    assert checks.main(["--evidence-dir", str(ACCIDENT_PASS)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["violations"] == 2
    assert sorted(path.name for path in ACCIDENT_PASS.iterdir()) == before
    assert "trajectory.jsonl" not in before


def test_the_cli_prefers_a_real_trajectory_over_a_reconstruction(tmp_path):
    """A live pass writes trajectory.jsonl; the replay is only for passes that did not."""
    import trajectory

    written = trajectory.record(
        stage="TEST", lane="reply", resource_key=f"talkroom:{PAID_ROOM}", action="write",
        path=tmp_path / "trajectory.jsonl",
    )
    assert written is not None
    assert checks.load_rows(tmp_path) == [written]
