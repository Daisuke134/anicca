from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# 2026-08-06: application:barren_streak reached attempt_count=3 and went to 'blocked' while
# the apply lane's barren streak climbed to 104. The cheap repair for that class is
# `launchctl kickstart hf-gig-pass`, which cannot fix a code defect, so three restarts
# proved only that restarting was the wrong treatment -- and that proof was thrown away.
#
# Kubernetes keeps its restart backoff and its diagnosis separate on purpose
# (https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), and this codebase
# already has both halves: the bounded backoff, and a patch loop reached through
# DIAGNOSTIC_REPAIR_CLASSES. Only the edge between them is missing.

CONTROLLER = Path("/workspace/life-manager/src/gig/healing/controller.py")


def load():
    spec = importlib.util.spec_from_file_location("healing_controller_p2", CONTROLLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["healing_controller_p2"] = module
    spec.loader.exec_module(module)
    return module


def test_a_barren_revenue_lane_is_an_outcome_zero_defect() -> None:
    m = load()
    assert m.outcome_zero_defect({"fingerprint": "application:barren_streak"}) is True


def test_a_silent_lane_is_an_outcome_zero_defect() -> None:
    # lane:<name>:attempt_silence means the lane stopped even trying.
    m = load()
    assert m.outcome_zero_defect({"fingerprint": "lane:reply:attempt_silence"}) is True


def test_infrastructure_faults_are_not_outcome_zero() -> None:
    # These already have corrective repairs that work. Sending them to a code-patch loop
    # would burn model budget on a browser that only needed restarting.
    m = load()
    for fingerprint in (
        "browser:cdp_timeout",
        "telegram:delivery_unknown",
        "scheduler:missed_hourly_pass",
        "provider:provider_timeout:LEARN",
    ):
        assert m.outcome_zero_defect({"fingerprint": fingerprint}) is False, fingerprint


def test_a_malformed_incident_is_not_a_defect() -> None:
    # This runs on the healing path of every audit. Guessing "defect" from missing data
    # would dispatch the most expensive repair we have on no evidence at all.
    m = load()
    assert m.outcome_zero_defect({}) is False
    assert m.outcome_zero_defect({"fingerprint": None}) is False
    assert m.outcome_zero_defect({"fingerprint": 42}) is False
    assert m.outcome_zero_defect("not a dict") is False


def build_queue(tmp_path):
    """A real repair queue, seeded so the next reconcile lands on the attempt limit."""
    spec = importlib.util.spec_from_file_location(
        "repair_queue_p2",
        Path("/workspace/life-manager/.worktrees/gig-p0-promissory-stop")
        / "skills/earn/gig/scripts/repair_queue.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["repair_queue_p2"] = module
    spec.loader.exec_module(module)
    return module.RepairQueue(tmp_path / "gig-control.sqlite3")


def seed_to_attempt_limit(queue, *, fingerprint, repair_class, attempts=2):
    """Drive an incident up to attempts, the way the controller itself would."""
    # RepairQueue.enqueue takes no next_attempt_at; a new row is already due at
    # detected_at. This mirrors how test_gig_healing_controller.py seeds its queue.
    queue.enqueue(
        fingerprint=fingerprint,
        repair_class=repair_class,
        evidence={},
        detected_at=100,
    )
    for tick in range(attempts):
        incident = queue.claim(owner="seed", now=101 + tick, lease_seconds=30)
        queue.defer(
            incident["incident_id"],
            owner="seed",
            fencing_token=incident["fencing_token"],
            verification={"fresh_fingerprint_present": True},
            action={"status": "dispatched"},
            next_attempt_at=102 + tick,
        )
    return queue


def reconcile(controller, queue, *, fingerprint, dispatched, audit_path):
    # reconcile_once always appends an audit row, and _append_audit dereferences the path,
    # so this has to be a real file the way test_gig_healing_controller.py supplies one.
    return controller.reconcile_once(
        queue=queue,
        owner="healer-p2",
        uid=501,
        now=200,
        audit_path=audit_path,
        observe_incidents=lambda: [{"fingerprint": fingerprint}],
        dispatcher=lambda repair_class, uid, incident=None: dispatched.append(
            repair_class
        )
        or {"status": "dispatched", "repair_class": repair_class},
        max_attempts=3,
    )


def test_a_barren_lane_at_the_attempt_limit_reaches_the_patch_loop(tmp_path) -> None:
    m = load()
    queue = seed_to_attempt_limit(
        build_queue(tmp_path),
        fingerprint="application:barren_streak",
        repair_class="application_expand",
    )
    dispatched: list[str] = []
    result = reconcile(
        m,
        queue,
        fingerprint="application:barren_streak",
        dispatched=dispatched,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "blocked_attempt_limit"
    # The restarts proved restarting was the wrong treatment; that proof now buys a patch.
    assert result["patch_handoff_dispatched"] is True
    assert "pass_step_repair" in dispatched
    assert queue.list_incidents()[0]["state"] == "blocked"


def test_an_infrastructure_fault_at_the_limit_still_just_blocks(tmp_path) -> None:
    m = load()
    queue = seed_to_attempt_limit(
        build_queue(tmp_path),
        fingerprint="scheduler:missed_hourly_pass",
        repair_class="scheduler_restart",
    )
    dispatched: list[str] = []
    result = reconcile(
        m,
        queue,
        fingerprint="scheduler:missed_hourly_pass",
        dispatched=dispatched,
        audit_path=tmp_path / "audit.jsonl",
    )

    assert result["status"] == "blocked_attempt_limit"
    assert result.get("patch_handoff_dispatched") is not True
    assert "pass_step_repair" not in dispatched


def test_the_patch_loop_is_asked_once_per_incident(tmp_path) -> None:
    # block() is terminal, so a second reconcile finds nothing claimable. If that ever
    # changes, this test fails rather than letting one incident bill the patch loop twice.
    m = load()
    queue = seed_to_attempt_limit(
        build_queue(tmp_path),
        fingerprint="application:barren_streak",
        repair_class="application_expand",
    )
    dispatched: list[str] = []
    for _ in range(2):
        reconcile(
            m,
            queue,
            fingerprint="application:barren_streak",
            dispatched=dispatched,
            audit_path=tmp_path / "audit.jsonl",
        )

    assert dispatched.count("pass_step_repair") == 1


def test_a_failing_patch_dispatch_never_loses_the_block(tmp_path) -> None:
    # The block is the circuit-open that stops the useless restarts. If asking for a patch
    # raises, the incident must still stop being retried -- otherwise a broken patch loop
    # would reopen the restart storm it exists to end.
    m = load()
    queue = seed_to_attempt_limit(
        build_queue(tmp_path),
        fingerprint="application:barren_streak",
        repair_class="application_expand",
    )

    def exploding_dispatcher(repair_class, uid, incident=None):
        if repair_class == "pass_step_repair":
            raise RuntimeError("self-fix.sh missing")
        return {"status": "dispatched", "repair_class": repair_class}

    result = m.reconcile_once(
        queue=queue,
        owner="healer-p2",
        uid=501,
        now=200,
        audit_path=tmp_path / "audit.jsonl",
        observe_incidents=lambda: [{"fingerprint": "application:barren_streak"}],
        dispatcher=exploding_dispatcher,
        max_attempts=3,
    )

    assert result["status"] == "blocked_attempt_limit"
    assert result["patch_handoff_dispatched"] is False
    assert queue.list_incidents()[0]["state"] == "blocked"
