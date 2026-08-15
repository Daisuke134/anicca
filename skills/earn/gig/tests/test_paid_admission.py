"""A13: an order that cannot proceed is skipped, and the next one is worked.

The shapes below are the live 2026-08-08 06:02 state, reduced:

    91000001  eight trailing ``queue_selected`` rows and nothing else -- picked by
             twelve consecutive passes, moved by none of them
    91000002  a real event as its last non-bookkeeping row -- a different paying
             customer whose finished v5 sat eight hours behind the jam
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load():
    spec = importlib.util.spec_from_file_location(
        "paid_admission_under_test", SCRIPTS / "paid_admission.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project(root: Path, identity: str, events: list[str], *, state: dict | None = None) -> None:
    """A project ledger whose event column is exactly ``events``."""
    directory = root / identity
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"request_id": identity, "adapter": "coconala", **(state or {})}
    (directory / "state.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    (directory / "events.jsonl").write_text(
        "".join(
            json.dumps({"ts": 1.0 + index, "request_id": identity, "adapter": "coconala",
                        "event": event, "state": payload}) + "\n"
            for index, event in enumerate(events)
        ),
        encoding="utf-8",
    )


def item(identity: str, buyer: str, **over) -> dict:
    base = {
        "request_id": identity,
        "buyer": buyer,
        "talkroom_id": f"tr-{identity}",
        "queue_class": "buyer_feedback_or_revision",
    }
    base.update(over)
    return base


JAMMED = ["project_initialized"] + ["queue_selected"] * 8
MOVED = ["project_initialized", "queue_selected", "paid_work_ready_for_browser"]


def risk_ledger(
    root: Path,
    identity: str,
    *,
    spent: int,
    stalled_before: int = 10,
    deadline_hours: float = 6,
    window_hours: float = 24,
) -> None:
    """A stuck ledger holding ``spent`` selections dated INSIDE the deadline window.

    ``stalled_before`` barren selections are dated well before window entry: they make
    the order stuck without spending the override allowance, which is the whole
    distinction. The default 10 is the live ``selections_without_progress`` measured on
    91000001 -- the value that made a bound counted off that counter unreachable.
    """
    entry = time.time() + deadline_hours * 3600 - window_hours * 3600
    rows = [(entry - 86400, "project_initialized")]
    rows += [(entry - 3600 * (stalled_before - i), "queue_selected") for i in range(stalled_before)]
    rows += [(entry + 60 * (i + 1), "queue_selected") for i in range(spent)]
    directory = root / identity
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"request_id": identity, "adapter": "coconala"}
    (directory / "state.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    (directory / "events.jsonl").write_text(
        "".join(
            json.dumps({"ts": ts, "request_id": identity, "adapter": "coconala",
                        "event": event, "state": payload}) + "\n"
            for ts, event in rows
        ),
        encoding="utf-8",
    )


# ── rule 1: skip the one that cannot move, work the next ──────────────────────────────


def test_the_jammed_head_is_skipped_and_the_next_order_is_worked(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    project(root, "91000002", MOVED)
    plan = m.plan(
        [item("91000001", "買い手A", priority=-1), item("91000002", "買い手B", priority=1)],
        projects_root=root,
    )
    assert plan["admitted"] == ["91000002"]
    assert plan["skipped"] == ["91000001"]
    head = plan["decisions"][0]
    assert head["reason"] == m.REASON_NO_PROGRESS
    assert head["selections_without_progress"] == 8


def test_new_buyer_feedback_hash_clears_stale_stall_for_this_plan(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", ["project_initialized"] + ["queue_selected"] * 23,
            state={"buyer_feedback_sha256": "a" * 64})
    planned = m.plan([item("91000001", "買い手A", buyer_feedback_sha256="b" * 64)], projects_root=root)
    assert planned["admitted"] == ["91000001"]
    assert planned["decisions"][0]["selections_without_progress"] == 0
    assert planned["decisions"][0]["consecutive_skips"] == 0


def test_same_observed_buyer_feedback_hash_keeps_stall_skip(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", ["project_initialized"] + ["queue_selected"] * 23,
            state={"buyer_feedback_sha256": "a" * 64})
    planned = m.plan([item("91000001", "買い手A", buyer_feedback_sha256="a" * 64)], projects_root=root)
    assert planned["skipped"] == ["91000001"]


@pytest.mark.parametrize("feedback", [None, "not-a-hash"])
def test_invalid_or_missing_current_feedback_hash_keeps_old_stall_behavior(tmp_path, feedback) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", ["project_initialized"] + ["queue_selected"] * 23,
            state={"buyer_feedback_sha256": "a" * 64})
    current = {"buyer_feedback_sha256": feedback} if feedback is not None else {}
    planned = m.plan([item("91000001", "買い手A", **current)], projects_root=root)
    assert planned["skipped"] == ["91000001"]


def test_must_action_candidates_beat_ordinary_head_and_rotate(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "ordinary", ["project_initialized"])
    project(root, "retry", ["project_initialized"],
            state={"next_action": "retry_buyer_visible_delivery"})
    project(root, "jammed", JAMMED,
            state={"buyer_feedback_sha256": "a" * 64,
                   "handled_buyer_feedback_sha256": "b" * 64})
    orders = [
        item("ordinary", "買い手A", priority=-1),
        item("retry", "買い手B", priority=1),
        item("jammed", "買い手C", priority=2),
    ]

    first = m.plan(orders, projects_root=root)
    assert len(first["admitted"]) == 1
    assert first["admitted"] == ["retry"]
    by_identity = {row["identity"]: row for row in first["decisions"]}
    assert by_identity["ordinary"]["must_action"] is False
    assert by_identity["retry"]["must_action"] is True
    assert by_identity["jammed"]["must_action"] is True

    _append_event(root, "retry", "queue_selected", ts=100.0)
    second = m.plan(orders, projects_root=root)
    assert len(second["admitted"]) == 1
    assert second["admitted"] == ["jammed"]
    assert {row["identity"] for row in second["decisions"]
            if row["must_action"]} == {"retry", "jammed"}


def test_must_action_uses_durable_talkroom_binding_when_request_id_is_missing(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "5204226", ["project_initialized"],
            state={"talkroom_id": "18115694",
                   "next_action": "retry_buyer_visible_delivery"})
    project(root, "18102795", ["project_initialized"])
    talkroom_only = item("18115694", "retry buyer", priority=1)
    talkroom_only["request_id"] = None
    talkroom_only["talkroom_id"] = "18115694"
    orders = [
        item("18102795", "ordinary buyer", priority=-1),
        talkroom_only,
    ]

    planned = m.plan(orders, projects_root=root)
    assert planned["admitted"] == ["18115694"]
    by_identity = {row["identity"]: row for row in planned["decisions"]}
    assert by_identity["18102795"]["must_action"] is False
    assert by_identity["18115694"]["must_action"] is True


@pytest.mark.parametrize("required_state", [{"next_action": "WORK_REQUIRED"}, {"work_state": "WORK_REQUIRED"}])
def test_work_required_state_outranks_ordinary_head(tmp_path, required_state) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "5204226", ["project_initialized"],
            state={"talkroom_id": "18115694", **required_state})
    project(root, "18102795", ["project_initialized"])
    work_required = item("18115694", "work-required buyer", priority=1)
    work_required.update(request_id=None, talkroom_id="18115694")
    planned = m.plan(
        [item("18102795", "ordinary buyer", priority=-1), work_required],
        projects_root=root,
    )
    assert planned["admitted"] == ["18115694"]
    assert planned["decisions"][1]["must_action"] is True


@pytest.mark.parametrize(
    "state",
    [
        {"buyer_feedback_sha256": "a" * 64,
         "handled_buyer_feedback_sha256": "a" * 64},
        {"active_feedback_cycle": {"phase": "AWAITING_BUYER"}},
        {"active_feedback_cycle": {"phase": "COMPLETE"}},
    ],
    ids=["equal-feedback", "awaiting", "complete"],
)
def test_equal_hash_and_terminal_feedback_phases_are_ordinary(tmp_path, state) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "ordinary-state", ["project_initialized"], state=state)
    planned = m.plan([item("ordinary-state", "買い手A")], projects_root=root)
    assert planned["decisions"][0]["must_action"] is False


def test_malformed_state_fails_safe_without_raising(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "malformed-state", ["project_initialized"])
    (root / "malformed-state" / "state.json").write_text("[]\n", encoding="utf-8")
    planned = m.plan([item("malformed-state", "買い手A")], projects_root=root)
    assert planned["admitted"] == ["malformed-state"]
    assert planned["decisions"][0]["must_action"] is False


def test_a_deadline_on_the_jammed_head_does_not_restore_the_blockage(tmp_path) -> None:
    """★ The regression an unbounded deadline override would reintroduce. ★

    The head is at first-contact risk AND permanently stuck, so delivery_queue puts it
    at priority -1 and it is decisions[0]. An override with no bound hands it the only
    max_orders slot on every pass for the whole width of the window, and the second
    customer's finished artifact -- the exact incident in this module's docstring at
    lines 18-28 -- sits untouched, with only the STARVED order escalating twelve hours
    later. Once it has spent its allowance INSIDE the window, the deadline stops
    buying passes and the other customer is served.
    """
    m = load()
    root = tmp_path / "projects"
    risk_ledger(root, "91000001", spent=m.DEADLINE_OVERRIDE_SELECTIONS)
    project(root, "91000002", MOVED)
    plan = m.plan(
        [
            item(
                "91000001",
                "買い手A",
                priority=-1,
                first_contact_at_risk=True,
                contact_deadline=(
                    datetime.now(timezone.utc) + timedelta(hours=6)
                ).isoformat(),
            ),
            item("91000002", "買い手B", priority=1),
        ],
        projects_root=root,
    )
    assert plan["admitted"] == ["91000002"]
    assert plan["skipped"] == ["91000001"]
    assert plan["decisions"][0]["deadline_override"] is False
    assert plan["decisions"][0]["reason"] == m.REASON_NO_PROGRESS


def test_priority_still_decides_fetch_order_and_never_progress(tmp_path) -> None:
    # The jammed order is priority -1 (A5's contact-deadline promotion, correct) and is
    # still looked at first: it is decisions[0]. What changed is that being first no
    # longer means being the only thing considered.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    project(root, "91000002", MOVED)
    plan = m.plan(
        [item("91000001", "買い手A", priority=-1), item("91000002", "買い手B", priority=1)],
        projects_root=root,
    )
    assert [row["identity"] for row in plan["decisions"]] == ["91000001", "91000002"]


def test_an_order_with_no_ledger_at_all_is_admitted(tmp_path) -> None:
    # A brand new order has never been selected, so it cannot be stuck.
    m = load()
    plan = m.plan([item("92000000", "newcomer")], projects_root=tmp_path / "projects")
    assert plan["admitted"] == ["92000000"]


@pytest.mark.parametrize("stalled", [0, 1])
def test_below_the_threshold_the_order_is_still_worked(tmp_path, stalled: int) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", ["project_initialized"] + ["queue_selected"] * stalled)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["admitted"] == ["91000001"]


# ── which events count as progress ────────────────────────────────────────────────────


def test_an_unknown_event_counts_as_progress(tmp_path) -> None:
    """★ The denylist direction. ★

    Skipping an order that was fine is a paying customer left unserved; continuing to
    work one that is stuck is only today's behaviour. So an event this module has never
    heard of keeps the order eligible.
    """
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED + ["some_future_event_nobody_told_us_about"])
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["admitted"] == ["91000001"]


def test_out_of_band_reconciliation_is_not_progress(tmp_path) -> None:
    # 91000002 carried nine consecutive state_reconciled rows while starved. They are
    # written by the reply detector reading the live DOM, not by working the order.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED + ["state_reconciled", "state_reconciled"])
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["skipped"] == ["91000001"]


def test_a_delivery_attempt_that_failed_is_progress_and_resets_the_count(tmp_path) -> None:
    # An attempt that failed is an attempt: the pass reached the browser and did
    # something different from doing nothing.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED + ["delivery_attempt_failed"])
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["admitted"] == ["91000001"]


def failures(root: Path, identity: str, reasons: list[str | None]) -> None:
    """A ledger of select-then-fail cycles, each carrying its own failure reason."""
    directory = root / identity
    directory.mkdir(parents=True, exist_ok=True)
    base = {"request_id": identity, "adapter": "coconala"}
    (directory / "state.json").write_text(json.dumps(base) + "\n", encoding="utf-8")
    lines = [json.dumps({"event": "project_initialized", "state": base})]
    for reason in reasons:
        lines.append(json.dumps({"event": "queue_selected", "state": base}))
        lines.append(
            json.dumps(
                {
                    "event": "delivery_attempt_failed",
                    "state": {**base, "last_delivery_attempt_reason": reason},
                }
            )
        )
    (directory / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_the_same_failure_twice_running_is_not_progress(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    failures(root, "91000001", ["paid_queue_delivery_failed"] * 3)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["skipped"] == ["91000001"]
    assert plan["decisions"][0]["selections_without_progress"] == 2


def test_a_changing_failure_reason_keeps_the_order_eligible(tmp_path) -> None:
    # Different reasons each pass means the loop is still getting somewhere new.
    m = load()
    root = tmp_path / "projects"
    failures(root, "91000001", ["reason_a", "reason_b", "reason_c"])
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["admitted"] == ["91000001"]


def test_a_failure_with_no_recorded_reason_keeps_the_order_eligible(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    failures(root, "91000001", [None, None, None])
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["admitted"] == ["91000001"]


# ── rule 2: the concurrency limit, partitioned per customer ───────────────────────────


def test_one_order_in_flight_per_customer(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "A1", MOVED)
    project(root, "A2", MOVED)
    project(root, "B1", MOVED)
    plan = m.plan(
        [item("A1", "same buyer"), item("A2", "Same  Buyer"), item("B1", "other")],
        projects_root=root,
        max_orders=3,
    )
    assert plan["admitted"] == ["A1", "B1"]
    assert plan["decisions"][1]["reason"] == m.REASON_CUSTOMER_SLOT


def test_a_missing_buyer_never_merges_two_customers(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "A1", MOVED)
    project(root, "A2", MOVED)
    plan = m.plan(
        [item("A1", ""), item("A2", None)], projects_root=root, max_orders=3
    )
    assert plan["admitted"] == ["A1", "A2"]


# ── D1: round robin, so the top of the queue does not win every pass forever ──────────
#
# docs/loop-engineering/26-gig-loop-asis-tobe-plan.md D1: "today max_orders=1
# head-of-line blocking means ONE order monopolizes the paid lane while others wait."
# Rule 1 above (skip a STUCK order) does not cover this: an order that keeps making
# real progress every pass is never "stuck" by selections_without_progress, so before
# this change it kept winning the single slot every pass, forever, with a second,
# equally-eligible customer never once admitted. These tests simulate the passes
# gig_pass.sh actually runs -- plan(), then grow the winner's ledger the way
# record_queue_selection + real work would -- and assert the slot alternates.


def _append_event(root: Path, identity: str, event: str, ts: float) -> None:
    """Append one ledger row with an explicit ``ts``, the way a real pass would."""
    directory = root / identity
    with (directory / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"ts": ts, "request_id": identity, "adapter": "coconala", "event": event})
            + "\n"
        )


def test_two_progressing_customers_alternate_across_passes(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "A1", ["project_initialized"])
    project(root, "B1", ["project_initialized"])
    order = [item("A1", "alice", priority=1), item("B1", "bob", priority=2)]

    # Pass 1: neither has ever won the slot -- tied at last_admitted_ts == 0.0, so
    # priority breaks the tie exactly like the old strict-priority behaviour.
    plan1 = m.plan(order, projects_root=root, max_orders=1)
    assert plan1["admitted"] == ["A1"]
    _append_event(root, "A1", "queue_selected", ts=10.0)
    _append_event(root, "A1", "paid_work_ready_for_browser", ts=10.1)

    # Pass 2: A1 has now won once (last_admitted_ts=10.0); B1 still never has (0.0).
    # B1 -- lower priority, but longer-waiting -- gets the slot. Old code would have
    # handed A1 the slot again forever; this is the regression this task closes.
    plan2 = m.plan(order, projects_root=root, max_orders=1)
    assert plan2["admitted"] == ["B1"]
    _append_event(root, "B1", "queue_selected", ts=20.0)
    _append_event(root, "B1", "paid_work_ready_for_browser", ts=20.1)

    # Pass 3: both have won exactly once. A1's win (ts=10.0) is older than B1's
    # (ts=20.0), so A1 -- the longer-waiting one now -- gets the slot back.
    plan3 = m.plan(order, projects_root=root, max_orders=1)
    assert plan3["admitted"] == ["A1"]


def test_a_genuinely_stuck_order_is_never_saved_by_round_robin(tmp_path) -> None:
    # Round robin only decides who wins among orders that could otherwise proceed.
    # A stuck order is skipped for REASON_NO_PROGRESS regardless of how long it has
    # waited for the slot -- an empty last_admitted_ts (never won) must not let it
    # jump the stuck check.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)  # 8 barren queue_selected rows, never a real event
    project(root, "91000002", ["project_initialized"])  # never admitted either
    plan = m.plan(
        [item("91000001", "stuck customer"), item("91000002", "new customer")],
        projects_root=root,
        max_orders=1,
    )
    assert plan["admitted"] == ["91000002"]
    assert plan["skipped"] == ["91000001"]
    assert plan["decisions"][0]["reason"] == m.REASON_NO_PROGRESS


def test_the_global_cap_holds_and_is_the_shipped_default(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    for identity in ("A1", "B1", "C1"):
        project(root, identity, MOVED)
    assert m.DEFAULT_MAX_ORDERS == 1
    plan = m.plan(
        [item("A1", "a"), item("B1", "b"), item("C1", "c")], projects_root=root
    )
    assert plan["admitted"] == ["A1"]
    assert [row["reason"] for row in plan["decisions"][1:]] == [
        m.REASON_PASS_LIMIT,
        m.REASON_PASS_LIMIT,
    ]
    wider = m.plan(
        [item("A1", "a"), item("B1", "b"), item("C1", "c")],
        projects_root=root,
        max_orders=2,
    )
    assert wider["admitted"] == ["A1", "B1"]


def test_the_jam_does_not_consume_the_pass_slot(tmp_path) -> None:
    # The whole point: a skipped order must not count against max_orders, or skipping
    # would buy nothing.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    project(root, "91000002", MOVED)
    plan = m.plan(
        [item("91000001", "買い手A"), item("91000002", "買い手B")],
        projects_root=root,
        max_orders=1,
    )
    assert plan["admitted"] == ["91000002"]


# ── starvation in the other direction ─────────────────────────────────────────────────


def test_a_permanently_skipped_order_is_probed_again(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED + ["queue_skipped"] * 6)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["admitted"] == ["91000001"]
    assert plan["decisions"][0]["probe"] is True


@pytest.mark.parametrize("skips", [1, 2, 5, 7])
def test_between_probes_it_stays_skipped(tmp_path, skips: int) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED + ["queue_skipped"] * skips)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["skipped"] == ["91000001"]
    assert plan["decisions"][0]["probe"] is False


def test_a_probe_that_changes_nothing_goes_back_to_being_skipped(tmp_path) -> None:
    # The probe appends queue_selected; the jam is still a jam, so the very next pass
    # skips it again. One wasted pass in six, bounded.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED + ["queue_skipped"] * 6 + ["queue_selected"])
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["skipped"] == ["91000001"]


def test_escalation_fires_at_the_boundary_and_not_on_every_pass(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    # 11 prior skips + this one = 12 = escalate_at.
    project(root, "91000001", JAMMED + ["queue_skipped"] * 11)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert plan["escalated"] == ["91000001"]
    assert plan["decisions"][0]["consecutive_skips_after"] == 12

    project(root, "91000001", JAMMED + ["queue_skipped"] * 12)
    quiet = m.plan([item("91000001", "買い手A")], projects_root=root)
    assert quiet["escalated"] == []


# ── the skip is recorded, not silent ──────────────────────────────────────────────────


def test_a_skip_is_durable_in_the_order_s_own_ledger(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    written = m.record_decisions(plan, projects_root=root, pass_id="pass-1")
    assert written["skips_recorded"] == 1
    events = [
        json.loads(line)["event"]
        for line in (root / "91000001" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events[-1] == m.EVENT_SKIPPED
    state = json.loads((root / "91000001" / "state.json").read_text(encoding="utf-8"))
    assert state["last_skip_pass_id"] == "pass-1"
    assert state["last_skip_reason"] == m.REASON_NO_PROGRESS


def test_one_pass_records_one_skip_however_often_it_replans(tmp_path) -> None:
    # load_top_queue_state runs again after the reply lane recollects the queue. The
    # counters are counts of PASSES, so a second row would make the order look twice
    # as stuck as it is.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    for _ in range(3):
        plan = m.plan([item("91000001", "買い手A")], projects_root=root)
        m.record_decisions(plan, projects_root=root, pass_id="pass-1")
    events = [
        json.loads(line)["event"]
        for line in (root / "91000001" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events.count(m.EVENT_SKIPPED) == 1


def test_a_skip_against_an_order_with_no_project_is_not_an_error(tmp_path) -> None:
    # Neither order has a ledger, so both start tied on last_admitted_ts (0.0, never
    # admitted) and the round-robin competition falls back to priority: A1 (index 0)
    # wins, B1 is skipped -- and B1 has no project directory for record_decisions to
    # write against.
    m = load()
    root = tmp_path / "projects"
    plan = m.plan([item("A1", "a"), item("B1", "b")], projects_root=root, max_orders=1)
    written = m.record_decisions(plan, projects_root=root, pass_id="pass-1")
    assert written["errors"] == []
    assert written["skips_recorded"] == 0


def test_an_escalation_is_written_where_a_report_can_find_it(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    ledger = tmp_path / "paid-lane-escalations.jsonl"
    project(root, "91000001", JAMMED + ["queue_skipped"] * 11)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    written = m.record_decisions(
        plan, projects_root=root, escalation_ledger=ledger, pass_id="pass-9"
    )
    assert written["escalations_recorded"] == 1
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert row["identity"] == "91000001"
    assert row["consecutive_skips"] == 12
    assert row["reason"] == m.REASON_NO_PROGRESS
    assert row["pass_id"] == "pass-9"


def test_a_skip_writes_an_ev1_trajectory_row(tmp_path, monkeypatch) -> None:
    trail = tmp_path / "trajectory.jsonl"
    monkeypatch.setenv("GIG_TRAJECTORY_FILE", str(trail))
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    plan = m.plan([item("91000001", "買い手A")], projects_root=root)
    m.record_decisions(plan, projects_root=root, pass_id="pass-1")
    rows = [json.loads(line) for line in trail.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[-1]["resource_key"] == "project:91000001"
    assert rows[-1]["result"] == "skipped"
    assert rows[-1]["ok"] is False
    assert rows[-1]["reason"].startswith(m.REASON_NO_PROGRESS)


# ── a hard external clock buys a BOUNDED number of extra passes ───────────────────
#
# Why the bound exists and why it is counted from window entry rather than off the
# stall counter: paid_admission.DEADLINE_OVERRIDE_SELECTIONS. The head-of-line
# regression it protects lives in the very first test of this file.


def _deadline(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def at_risk(identity: str, buyer: str, hours: float = 6, **over) -> dict:
    """A queue item as delivery_queue publishes it for an order at first-contact risk.

    ``first_contact_at_risk`` is delivery_queue's own verdict (delivery_queue.py:355),
    computed with the seller_message_observed retraction and against the snapshot
    clock. This module reads it rather than recomputing it.
    """
    return item(
        identity,
        buyer,
        contact_deadline=_deadline(hours),
        first_contact_at_risk=True,
        **over,
    )


# stuck_after=2, so a ledger of exactly 2 barren selections is stuck AND still inside
# the DEADLINE_OVERRIDE_SELECTIONS=2 allowance. JAMMED (8) has already spent it.
AT_RISK_STUCK = ["project_initialized"] + ["queue_selected"] * 2


def test_a_near_deadline_admits_a_stuck_order(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    plan = m.plan([at_risk("91000001", "買い手A")], projects_root=root)
    decision = plan["decisions"][0]
    assert plan["admitted"] == ["91000001"]
    assert decision["deadline_override"] is True
    assert decision["reason"] == m.REASON_DEADLINE_OVERRIDE
    assert decision["reason"] != ""


@pytest.mark.parametrize(
    "spent, still_overriding", [(0, True), (1, True), (2, False), (5, False)]
)
def test_the_allowance_is_spent_by_selections_inside_the_window(
    tmp_path, spent: int, still_overriding: bool
) -> None:
    """★ The bound. ★ Past it the deadline stops buying passes, because otherwise the
    one order that cannot move is the only order looked at for the whole width of the
    window -- the incident in this module's docstring."""
    m = load()
    root = tmp_path / "projects"
    assert m.DEADLINE_OVERRIDE_SELECTIONS == 2
    risk_ledger(root, "91000001", spent=spent)
    plan = m.plan([at_risk("91000001", "買い手A")], projects_root=root)
    assert plan["decisions"][0]["deadline_override"] is still_overriding
    assert (plan["admitted"] == ["91000001"]) is still_overriding


@pytest.mark.parametrize("stalled_before", [2, 10, 50])
def test_a_deeply_stuck_order_still_gets_its_allowance_at_window_entry(
    tmp_path, stalled_before: int
) -> None:
    """★ The defect the first bound shipped with, measured on the live order. ★

    Counting the allowance off ``selections_without_progress`` made the override
    unreachable for exactly the orders it exists for: 91000001 stood at 10 and nothing
    decrements it, since only a real event resets it and the failure mode IS that no
    real event happens. Selections predating window entry are the order's history with
    a clock that was not yet running, so they cannot spend an allowance the clock had
    not yet granted.
    """
    m = load()
    root = tmp_path / "projects"
    risk_ledger(root, "91000001", spent=0, stalled_before=stalled_before)
    plan = m.plan([at_risk("91000001", "買い手A")], projects_root=root)
    decision = plan["decisions"][0]
    assert decision["selections_without_progress"] >= stalled_before
    assert plan["admitted"] == ["91000001"]
    assert decision["deadline_override"] is True


def test_an_undated_selection_spends_the_allowance(tmp_path) -> None:
    # This is the override's only bound, and a bound malformed data can widen is not a
    # bound. Opposite fail-safe direction from selections_without_progress, deliberately.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)  # ts present but ancient
    directory = root / "91000001"
    with (directory / "events.jsonl").open("a", encoding="utf-8") as handle:
        for _ in range(2):
            handle.write(json.dumps({"request_id": "91000001", "adapter": "coconala",
                                     "event": "queue_selected"}) + "\n")
    plan = m.plan([at_risk("91000001", "買い手A")], projects_root=root)
    assert plan["skipped"] == ["91000001"]
    assert plan["decisions"][0]["deadline_override"] is False


def test_an_order_not_flagged_at_risk_gets_no_override(tmp_path) -> None:
    """delivery_queue already answered "is this still at risk"; this module obeys it.

    An item carrying a deadline but no ``first_contact_at_risk`` is one the promoter
    decided is not at risk -- contact already made, or the clock unanchored. Reading
    its verdict is what keeps the two modules from disagreeing.
    """
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    plan = m.plan(
        [item("91000001", "買い手A", contact_deadline=_deadline(6))], projects_root=root
    )
    decision = plan["decisions"][0]
    assert plan["skipped"] == ["91000001"]
    assert decision["reason"] == m.REASON_NO_PROGRESS
    assert decision["deadline_override"] is False


def test_a_far_deadline_does_not_admit_a_stuck_order(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    plan = m.plan([at_risk("91000001", "買い手A", hours=400)], projects_root=root)
    decision = plan["decisions"][0]
    assert plan["skipped"] == ["91000001"]
    assert decision["reason"] == m.REASON_NO_PROGRESS
    assert decision["deadline_override"] is False


def test_a_past_deadline_does_not_admit_a_stuck_order(tmp_path) -> None:
    # The clock has already run out; the order can never progress, so it must not
    # hold a slot forever once it is beyond saving.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    plan = m.plan([at_risk("91000001", "買い手A", hours=-6)], projects_root=root)
    decision = plan["decisions"][0]
    assert plan["skipped"] == ["91000001"]
    assert decision["reason"] == m.REASON_NO_PROGRESS
    assert decision["deadline_override"] is False


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "not-a-timestamp",
        # ★ Naive, and deliberately 6h out rather than a fixed date. ★ A hardcoded
        # "2026-08-09T23:00:00" passed only because it happened to sit outside the
        # window on the day it was written -- right answer, wrong reason, and it would
        # have stopped exercising the guard on 8/9. Built from the same instant the
        # passing cases use, this fails unless the tzinfo check actually rejects it.
        _deadline(6).split("+")[0],
    ],
    ids=["absent", "empty", "malformed", "no-offset"],
)
def test_a_missing_or_malformed_deadline_behaves_like_today(tmp_path, raw) -> None:
    m = load()
    root = tmp_path / "projects"
    risk_ledger(root, "91000001", spent=0)
    kwargs = {} if raw is None else {"contact_deadline": raw}
    plan = m.plan(
        [item("91000001", "買い手A", first_contact_at_risk=True, **kwargs)],
        projects_root=root,
    )
    decision = plan["decisions"][0]
    assert plan["skipped"] == ["91000001"]
    assert decision["reason"] == m.REASON_NO_PROGRESS
    assert decision["deadline_override"] is False


def test_a_deadline_does_not_affect_an_order_that_is_not_stuck(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", MOVED)
    near = m.plan([at_risk("91000001", "買い手A")], projects_root=root)
    project(root, "91000104", MOVED)
    far = m.plan([at_risk("91000104", "買い手A", hours=400)], projects_root=root)
    assert near["admitted"] == ["91000001"]
    assert near["decisions"][0]["deadline_override"] is False
    assert far["admitted"] == ["91000104"]


def test_deadline_window_hours_is_overridable(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    assert m.DEFAULT_DEADLINE_WINDOW_HOURS == 24
    order = [at_risk("91000001", "買い手A", hours=30)]
    # 30h is outside the shipped 24h window and inside a widened one.
    assert m.plan(order, projects_root=root)["skipped"] == ["91000001"]
    widened = m.plan(order, projects_root=root, deadline_window_hours=48)
    assert widened["admitted"] == ["91000001"]
    assert widened["decisions"][0]["deadline_override"] is True


# ── which clock the window is measured against ──────────────────────────────────


def test_the_window_is_measured_from_an_injected_now(tmp_path) -> None:
    # Without an injectable now no test can sit on the window boundary at all.
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    deadline = datetime(2026, 8, 9, 23, 0, tzinfo=timezone(timedelta(hours=9)))
    order = [item("91000001", "買い手A", contact_deadline=deadline.isoformat(),
                  first_contact_at_risk=True)]
    inside = m.plan(order, projects_root=root, now=deadline - timedelta(hours=23))
    outside = m.plan(order, projects_root=root, now=deadline - timedelta(hours=25))
    expired = m.plan(order, projects_root=root, now=deadline + timedelta(minutes=1))
    assert inside["admitted"] == ["91000001"]
    assert outside["skipped"] == ["91000001"]
    assert expired["skipped"] == ["91000001"]


def test_the_snapshot_clock_beats_the_machine_clock(tmp_path) -> None:
    """★ The honest now is when the banner was read. ★

    delivery_queue measures against the snapshot's capture instant. A machine clock
    that has run past a deadline the snapshot saw as live would otherwise disable the
    override silently and let the order die quietly.
    """
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", AT_RISK_STUCK)
    stale_deadline = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    captured = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    plan = m.plan(
        [item("91000001", "買い手A", contact_deadline=stale_deadline,
              first_contact_at_risk=True, snapshot_captured_at=captured)],
        projects_root=root,
    )
    assert plan["admitted"] == ["91000001"]
    assert plan["decisions"][0]["deadline_override"] is True


# ── the override is subordinate to both limits, and that ordering is pinned ────────
#
# Clearing ``stuck`` only removes the backoff. A deadline is a reason to stop deferring
# an order; it is never a reason to send one buyer two things at once, nor to put two
# orders through the per-pass evidence namespace that recover_prior_paid_answer globs by
# fixed path. Both tests below fail if the override branch is hoisted above either check.


def test_a_near_deadline_still_yields_to_the_pass_slot_limit(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "A1", MOVED)
    project(root, "91000001", AT_RISK_STUCK)
    plan = m.plan(
        [item("A1", "someone else"), at_risk("91000001", "買い手A")],
        projects_root=root,
        max_orders=1,
    )
    decision = plan["decisions"][1]
    assert plan["admitted"] == ["A1"]
    assert plan["skipped"] == ["91000001"]
    assert decision["reason"] == m.REASON_PASS_LIMIT
    assert decision["deadline_override"] is True


def test_a_near_deadline_still_yields_to_the_customer_partition(tmp_path) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000002", MOVED)
    project(root, "91000001", AT_RISK_STUCK)
    plan = m.plan(
        [item("91000002", "買い手A"), at_risk("91000001", "買い手A")],
        projects_root=root,
        max_orders=2,
    )
    decision = plan["decisions"][1]
    assert plan["admitted"] == ["91000002"]
    assert plan["skipped"] == ["91000001"]
    assert decision["reason"] == m.REASON_CUSTOMER_SLOT
    assert decision["deadline_override"] is True


# ── the command line the pass actually calls ──────────────────────────────────────────


def test_cli_writes_the_plan_and_reports_the_admitted_order(tmp_path, capsys) -> None:
    m = load()
    root = tmp_path / "projects"
    project(root, "91000001", JAMMED)
    project(root, "91000002", MOVED)
    queue = tmp_path / "delivery-queue.json"
    queue.write_text(
        json.dumps(
            {"items": [item("91000001", "買い手A", priority=-1),
                       item("91000002", "買い手B", priority=1)]}
        ),
        encoding="utf-8",
    )
    output = tmp_path / "paid-admission.json"
    rc = m.main(
        [
            "--queue", str(queue),
            "--projects-root", str(root),
            "--escalation-ledger", str(tmp_path / "escalations.jsonl"),
            "--pass-id", "pass-1",
            "--output", str(output),
            "--record",
        ]
    )
    assert rc == 0
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["admitted"] == ["91000002"]
    assert json.loads(output.read_text(encoding="utf-8"))["skipped"] == ["91000001"]


def test_cli_refuses_a_malformed_queue_without_writing_anything(tmp_path, capsys) -> None:
    m = load()
    queue = tmp_path / "delivery-queue.json"
    queue.write_text("{not json", encoding="utf-8")
    assert m.main(["--queue", str(queue), "--projects-root", str(tmp_path)]) == 1
    assert json.loads(capsys.readouterr().out.strip())["status"] == "failed"
