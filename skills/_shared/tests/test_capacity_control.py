from __future__ import annotations

import gzip
import importlib.util
import json
import os
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "capacity_control.py"
SPEC = importlib.util.spec_from_file_location("capacity_control", MODULE_PATH)
assert SPEC and SPEC.loader
capacity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capacity)

PRODUCERS = ("gig", "marketing", "clip", "video", "browser", "worktree")


def write_config(tmp_path: Path, *, max_runs: int = 4, reserve_bytes: int = 1_000) -> Path:
    producers = {}
    for name in PRODUCERS:
        owner_path = tmp_path / "owners" / name
        owner_path.mkdir(parents=True)
        log = tmp_path / "logs" / f"{name}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        producers[name] = {
            "owner": f"{name}-owner",
            "max_active": 1,
            "max_runs_per_window": max_runs,
            "window_seconds": 3600,
            "log_paths": [str(log)],
            "log_max_bytes": 20,
            "log_keep": 2,
            "owner_paths": [str(owner_path)],
            "checkpoint_keep": 2,
        }
    path = tmp_path / "capacity.json"
    path.write_text(
        json.dumps(
            {
                "policy_version": "capacity-v1",
                "reserve_bytes": reserve_bytes,
                "producers": producers,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_low_reserve_refuses_new_run_without_touching_active_or_checkpoint(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    state = tmp_path / "state"
    leases = state / "leases" / "gig"
    checkpoints = state / "checkpoints" / "gig"
    leases.mkdir(parents=True)
    checkpoints.mkdir(parents=True)
    active = leases / "active.json"
    checkpoint = checkpoints / "active.json"
    active.write_text('{"run_id":"active","pid":1}', encoding="utf-8")
    checkpoint.write_text('{"status":"active","important":"keep"}', encoding="utf-8")
    active_before = active.read_bytes()
    checkpoint_before = checkpoint.read_bytes()

    result = capacity.begin_run(
        config_path=config,
        state_root=state,
        producer="gig",
        run_id="blocked",
        pid=os.getpid(),
        free_bytes=999,
        now=10_000,
    )

    assert result["status"] == "backpressure"
    assert active.read_bytes() == active_before
    assert checkpoint.read_bytes() == checkpoint_before
    assert not (leases / "blocked.json").exists()
    assert not (checkpoints / "blocked.json").exists()


@pytest.mark.parametrize("producer", PRODUCERS)
def test_each_producer_enforces_window_quota(tmp_path: Path, producer: str) -> None:
    config = write_config(tmp_path, max_runs=1)
    state = tmp_path / "state"
    first = capacity.begin_run(
        config_path=config,
        state_root=state,
        producer=producer,
        run_id="first",
        pid=os.getpid(),
        free_bytes=10_000,
        now=10_000,
    )
    assert first["status"] == "started"
    assert capacity.end_run(
        config_path=config,
        state_root=state,
        producer=producer,
        run_id="first",
        exit_code=0,
        now=10_001,
    )["status"] == "ended"

    second = capacity.begin_run(
        config_path=config,
        state_root=state,
        producer=producer,
        run_id="second",
        pid=os.getpid(),
        free_bytes=10_000,
        now=10_002,
    )

    assert second["status"] == "quota_exceeded"
    assert not (state / "leases" / producer / "second.json").exists()


def test_log_rotation_and_completed_checkpoint_compression_preserve_active(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    state = tmp_path / "state"
    log = tmp_path / "logs" / "clip.log"
    log.write_bytes(b"x" * 21)
    checkpoints = state / "checkpoints" / "clip"
    leases = state / "leases" / "clip"
    checkpoints.mkdir(parents=True)
    leases.mkdir(parents=True)
    for index in range(4):
        (checkpoints / f"done-{index}.json").write_text(
            json.dumps({"run_id": f"done-{index}", "status": "ended", "started_at": index}),
            encoding="utf-8",
        )
    active_checkpoint = checkpoints / "active.json"
    active_checkpoint.write_text('{"run_id":"active","status":"active"}', encoding="utf-8")
    (leases / "active.json").write_text(
        json.dumps({"run_id": "active", "pid": os.getpid(), "checkpoint": str(active_checkpoint)}),
        encoding="utf-8",
    )

    result = capacity.begin_run(
        config_path=config,
        state_root=state,
        producer="clip",
        run_id="new",
        pid=os.getpid(),
        free_bytes=10_000,
        now=10_000,
    )

    assert result["status"] == "quota_exceeded" or result["status"] == "active_quota_exceeded"
    # Maintenance runs before quota evaluation only when reserve is healthy.
    assert log.exists() and log.stat().st_size == 0
    assert (tmp_path / "logs" / "clip.log.1").read_bytes() == b"x" * 21
    assert active_checkpoint.exists()
    compressed = sorted(checkpoints.glob("done-*.json.gz"))
    assert len(compressed) == 2
    assert json.loads(gzip.open(compressed[0], "rt", encoding="utf-8").read())["status"] == "ended"


def test_recovery_resumes_and_owner_growth_is_observed(tmp_path: Path) -> None:
    config = write_config(tmp_path)
    state = tmp_path / "state"
    owner_path = tmp_path / "owners" / "video" / "artifact"
    owner_path.write_bytes(b"a" * 10)
    blocked = capacity.begin_run(
        config_path=config,
        state_root=state,
        producer="video",
        run_id="blocked",
        pid=os.getpid(),
        free_bytes=100,
        now=10_000,
    )
    assert blocked["status"] == "backpressure"
    owner_path.write_bytes(b"a" * 25)

    resumed = capacity.begin_run(
        config_path=config,
        state_root=state,
        producer="video",
        run_id="resumed",
        pid=os.getpid(),
        free_bytes=10_000,
        now=10_100,
    )

    assert resumed["status"] == "started"
    trend = [json.loads(line) for line in (state / "capacity-trend.jsonl").read_text().splitlines()]
    assert trend[-1]["owner"] == "video-owner"
    assert trend[-1]["owner_bytes"] == 25
    assert trend[-1]["growth_bytes"] == 15


def test_two_consecutive_zero_reclaims_alert_and_nonzero_resets(tmp_path: Path) -> None:
    state = tmp_path / "state"
    alert = tmp_path / "disk-pressure.alert"

    first = capacity.record_reclaim(state_root=state, reclaimed_bytes=0, alert_path=alert, now=10)
    second = capacity.record_reclaim(state_root=state, reclaimed_bytes=0, alert_path=alert, now=11)

    assert first == {"status": "warning", "consecutive_zero_reclaims": 1}
    assert second == {"status": "failure", "consecutive_zero_reclaims": 2}
    assert "consecutive_zero_reclaims=2" in alert.read_text()
    reset = capacity.record_reclaim(state_root=state, reclaimed_bytes=50, alert_path=alert, now=12)
    assert reset == {"status": "recovered", "consecutive_zero_reclaims": 0}
    assert not alert.exists()


def test_all_six_production_entrypoints_are_capacity_wrapped() -> None:
    home = Path.home()
    wiring = {
        home / "anicca/skills/earn/gig/gig_pass.sh": "gig",
        home / "anicca/skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh": "marketing",
        home / "anicca/skills/earn/clip/clip_daily.sh": "clip",
        home / "anicca/skills/earn/video/run.sh": "video",
        home / "anicca/skills/browser/ensure_browser.sh": "browser",
        home / "profitable-claude/skills/life-manager-dev/dev-pass.sh": "worktree",
    }
    for script, producer in wiring.items():
        text = script.read_text(encoding="utf-8")
        assert "capacity_control.py" in text, script
        assert f"--producer {producer}" in text, script

