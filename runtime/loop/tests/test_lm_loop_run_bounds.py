import os
import sys
import time

from runtime.loop.lm_loop_run import _run_entrypoint, _runtime_limit


def test_scheduled_wakes_have_a_finite_one_hour_safety_limit():
    assert _runtime_limit({"cadence": {"start_interval_seconds": 300}}) == 3600
    assert _runtime_limit({"cadence": {"calendar_interval": {"Minute": 5}}}) == 3600
    assert _runtime_limit({"cadence": {"run_at_load": True}}) == 3600


def test_continuous_owner_has_no_scheduled_wake_deadline():
    assert _runtime_limit({"cadence": {"keep_alive": True}}) is None


def test_entrypoint_timeout_terminates_its_process_group():
    started = time.monotonic()
    result = _run_entrypoint(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        timeout_seconds=0.05,
        termination_grace_seconds=0.05,
    )

    assert result == 124
    assert time.monotonic() - started < 2
