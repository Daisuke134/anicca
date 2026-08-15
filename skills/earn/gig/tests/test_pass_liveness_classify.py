from __future__ import annotations

import importlib.util
from pathlib import Path


# P1c (spec §0.1.4 #8). Tell "the cron stopped" apart from "the cron ran and failed".
#
# Measured 2026-08-05: the heartbeat was 42 hours old and the auditor had been reporting
# "no pass in 2509min — in-session cron likely stopped; healthcheck should restart" that
# entire time. In the same window the loop ran 57 passes and recorded 128 failures. The cron
# never stopped. Every pass failed, and the heartbeat is only written on success.
#
# So for 42 hours the auditor prescribed restarting something that had never stopped, which
# is a no-op, while the actual causes — b2_parent_boundary_failed 54 times,
# paid_work_validation_failed 44 — were never named in the verdict.
#
# This is the liveness/business confusion the spec warns about, appearing inside the auditor
# that exists to catch it. A stale heartbeat is not evidence of silence; it is evidence of
# no *success*, and those are different diagnoses with different remedies.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pass_liveness.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pass_liveness", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOW = 1785900000


def failures(*offsets_minutes_and_reasons):
    return [
        {"ts": NOW - minutes * 60, "reason": reason}
        for minutes, reason in offsets_minutes_and_reasons
    ]


def test_a_fresh_heartbeat_is_simply_firing() -> None:
    m = load_module()
    verdict = m.classify(heartbeat_age_min=12, failures=[], now=NOW)
    assert verdict["kind"] == "FIRING"


def test_a_stale_heartbeat_with_recent_failures_is_failing_not_stopped() -> None:
    m = load_module()
    verdict = m.classify(
        heartbeat_age_min=2509,
        failures=failures((30, "b2_parent_boundary_failed"), (90, "paid_work_validation_failed")),
        now=NOW,
    )
    assert verdict["kind"] == "FAILING"
    assert "止まって" not in verdict["text"]


def test_the_failing_verdict_names_the_top_reason() -> None:
    # "something is wrong" for 42 hours is what nobody acts on. The verdict has to say what.
    m = load_module()
    verdict = m.classify(
        heartbeat_age_min=2509,
        failures=failures(
            (10, "b2_parent_boundary_failed"),
            (20, "b2_parent_boundary_failed"),
            (30, "paid_work_validation_failed"),
        ),
        now=NOW,
    )
    assert "b2_parent_boundary_failed" in verdict["text"]
    assert verdict["top_reason"] == "b2_parent_boundary_failed"
    assert verdict["failures_in_window"] == 3


def test_a_stale_heartbeat_with_no_failures_really_is_stopped() -> None:
    # Nothing ran and nothing failed: the original verdict was right for this case, and the
    # restart it prescribes is the correct remedy.
    m = load_module()
    verdict = m.classify(heartbeat_age_min=2509, failures=[], now=NOW)
    assert verdict["kind"] == "STALE"
    assert "restart" in verdict["text"] or "再起動" in verdict["text"]


def test_old_failures_do_not_disguise_a_stopped_cron() -> None:
    # Failures from three days ago say nothing about whether it is running now.
    m = load_module()
    verdict = m.classify(
        heartbeat_age_min=5000,
        failures=failures((4320, "b2_parent_boundary_failed")),
        now=NOW,
    )
    assert verdict["kind"] == "STALE"


def test_no_heartbeat_at_all_is_its_own_case() -> None:
    m = load_module()
    verdict = m.classify(heartbeat_age_min=None, failures=[], now=NOW)
    assert verdict["kind"] == "NO_HEARTBEAT"


def test_failing_is_not_softer_than_stale() -> None:
    # A loop that runs and fails every hour is not healthier than one that stopped. It burns
    # tokens to produce nothing, so the verdict must not read as reassurance.
    m = load_module()
    verdict = m.classify(
        heartbeat_age_min=2509,
        failures=failures((30, "paid_work_validation_failed")),
        now=NOW,
    )
    assert verdict["healthy"] is False


def test_the_window_is_stated_so_the_number_can_be_checked() -> None:
    m = load_module()
    verdict = m.classify(heartbeat_age_min=2509, failures=[], now=NOW)
    assert verdict["window_minutes"] > 0
