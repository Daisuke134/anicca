from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BRIDGE = ROOT / "skills/earn/capafy-marketing/capafy-headless-bridge.sh"


def setup_repo(tmp_path: Path, *, goal_rc: int = 0, sleep_outcome: bool = False) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    paths = {
        "outcome": repo / "skills/earn/capafy-marketing/capafy-outcome-monitor.sh",
        "loop": repo / "skills/self/capafy-loop/capafy-loop-daily.sh",
        "goal": repo / "skills/earn/capafy-marketing/capafy-goal-monitor.sh",
        "marketing": repo / "skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh",
    }
    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        delay = "sleep 1\n" if name == "outcome" and sleep_outcome else ""
        rc = goal_rc if name == "goal" else 0
        path.write_text(f"#!/bin/sh\necho {name} >> \"$CAPAFY_TEST_CALLS\"\n{delay}exit {rc}\n", encoding="utf-8")
        path.chmod(0o755)
    return repo, tmp_path / "calls.log"


def run_bridge(tmp_path: Path, **kwargs) -> tuple[subprocess.CompletedProcess, Path]:
    repo, calls = setup_repo(tmp_path, goal_rc=kwargs.pop("goal_rc", 0), sleep_outcome=kwargs.pop("sleep_outcome", False))
    state_home = tmp_path / "state-home"
    stale_bridge = kwargs.pop("stale_bridge", False)
    stale_goal = kwargs.pop("stale_goal", False)
    if stale_bridge:
        lock = state_home / "state/capafy-headless-bridge/lock"
        lock.mkdir(parents=True)
        (lock / "owner.pid").write_text("999999", encoding="utf-8")
    if stale_goal:
        lock = state_home / "state/capafy-headless-bridge/job-goal.lock"
        lock.mkdir(parents=True)
        (lock / "owner.pid").write_text("999999", encoding="utf-8")
    env = os.environ | {
        "MR_BOT_REPO": str(repo),
        "MR_BOT_STATE_HOME": str(state_home),
        "CAPAFY_HEADLESS_ONCE": "1",
        "CAPAFY_HEADLESS_NOW": "1000",
        "CAPAFY_HEADLESS_AQUA_PROBE": kwargs.pop("probe", "false"),
        "CAPAFY_HEADLESS_HOST_AQUA_PROBE": kwargs.pop("host_probe", "false"),
        "CAPAFY_TEST_CALLS": str(calls),
    } | {key: str(value) for key, value in kwargs.items()}
    return subprocess.run(["bash", str(BRIDGE), "run"], env=env, text=True, capture_output=True, check=False), calls


def test_due_and_nondue_jobs_use_durable_timestamps(tmp_path: Path) -> None:
    first, calls = run_bridge(tmp_path, probe="false")
    second = subprocess.run(
        ["bash", str(BRIDGE), "run"],
        env=os.environ | {
            "MR_BOT_REPO": str(tmp_path / "repo"),
            "MR_BOT_STATE_HOME": str(tmp_path / "state-home"),
            "CAPAFY_HEADLESS_ONCE": "1", "CAPAFY_HEADLESS_NOW": "1000",
            "CAPAFY_HEADLESS_AQUA_PROBE": "false", "CAPAFY_HEADLESS_HOST_AQUA_PROBE": "false", "CAPAFY_TEST_CALLS": str(calls),
        }, text=True, capture_output=True, check=False,
    )
    assert first.returncode == second.returncode == 0
    assert calls.read_text().splitlines() == ["outcome", "loop", "goal", "marketing", "outcome"]


def test_two_ticks_release_job_locks_and_keep_hourly_jobs_nondue(tmp_path: Path) -> None:
    repo, calls = setup_repo(tmp_path)
    state_home = tmp_path / "state-home"
    result = subprocess.run(
        ["bash", str(BRIDGE), "run"],
        env=os.environ | {
            "MR_BOT_REPO": str(repo), "MR_BOT_STATE_HOME": str(state_home),
            "CAPAFY_HEADLESS_MAX_TICKS": "2", "CAPAFY_HEADLESS_NOW": "1000",
            "CAPAFY_HEADLESS_AQUA_PROBE": "false", "CAPAFY_HEADLESS_HOST_AQUA_PROBE": "false",
            "CAPAFY_HEADLESS_INTERVAL": "1", "CAPAFY_TEST_CALLS": str(calls),
        }, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    assert calls.read_text().splitlines() == ["outcome", "loop", "goal", "marketing", "outcome"]


def test_child_failure_retries_without_false_success_timestamp(tmp_path: Path) -> None:
    result, calls = run_bridge(tmp_path, goal_rc=7, probe="false")
    assert result.returncode == 0
    assert (calls.read_text().splitlines()) == ["outcome", "loop", "goal", "marketing"]
    assert not (tmp_path / "state-home/state/capafy-headless-bridge/timestamps/goal").exists()


def test_aqua_restored_exits_after_tick(tmp_path: Path) -> None:
    result, calls = run_bridge(tmp_path, probe="true")
    assert result.returncode == 0
    assert not calls.exists() or calls.read_text().splitlines() == []


def test_new_host_aqua_detection_skips_children_and_records_seen(tmp_path: Path) -> None:
    result, calls = run_bridge(tmp_path, probe="false", host_probe="true")
    assert result.returncode == 0
    assert not calls.exists()
    assert (tmp_path / "state-home/state/capafy-headless-bridge/aqua-seen-at").read_text().strip() == "1000"


def test_persistent_host_aqua_exits_without_children(tmp_path: Path) -> None:
    state = tmp_path / "state-home/state/capafy-headless-bridge"
    state.mkdir(parents=True)
    (state / "aqua-seen-at").write_text("800")
    result, calls = run_bridge(tmp_path, probe="false", host_probe="true", CAPAFY_HEADLESS_AQUA_GRACE="180")
    assert result.returncode == 0
    assert not calls.exists()


def test_transient_host_aqua_disappearance_resumes_children(tmp_path: Path) -> None:
    state = tmp_path / "state-home/state/capafy-headless-bridge"
    state.mkdir(parents=True)
    (state / "aqua-seen-at").write_text("800")
    result, calls = run_bridge(tmp_path, probe="false", host_probe="false")
    assert result.returncode == 0
    assert calls.read_text().splitlines() == ["outcome", "loop", "goal", "marketing"]


def test_host_probe_requires_current_uid_and_exact_ucomm_names(tmp_path: Path) -> None:
    uid = os.getuid()
    ps_output = f"{uid} /usr/libexec/Dock\n{uid} Dock\n{uid} SystemUIServer\n{uid + 1} Dock"
    result, calls = run_bridge(tmp_path, probe="false", host_probe="", CAPAFY_HEADLESS_PS_OUTPUT=ps_output)
    assert result.returncode == 0
    assert not calls.exists()


def test_single_instance_lock_and_no_capacity_gate_text(tmp_path: Path) -> None:
    repo, calls = setup_repo(tmp_path, sleep_outcome=True)
    state_home = tmp_path / "state-home"
    env = os.environ | {
        "MR_BOT_REPO": str(repo), "MR_BOT_STATE_HOME": str(state_home),
        "CAPAFY_HEADLESS_ONCE": "1", "CAPAFY_HEADLESS_AQUA_PROBE": "false",
        "CAPAFY_HEADLESS_HOST_AQUA_PROBE": "false",
        "CAPAFY_TEST_CALLS": str(calls),
    }
    state = state_home / "state/capafy-headless-bridge"
    state.mkdir(parents=True)
    (state / "lock").mkdir()
    (state / "lock/owner.pid").write_text(str(os.getpid()), encoding="utf-8")
    result = subprocess.run(["bash", str(BRIDGE), "run"], env=env, text=True, capture_output=True, check=False)
    assert result.returncode == 0
    text = BRIDGE.read_text(encoding="utf-8").lower()
    assert "disk" not in text and "headroom" not in text and "gib" not in text


def test_stale_bridge_and_job_locks_are_recovered(tmp_path: Path) -> None:
    result, calls = run_bridge(tmp_path, stale_bridge=True, stale_goal=True, probe="false")
    assert result.returncode == 0
    assert calls.read_text().splitlines() == ["outcome", "loop", "goal", "marketing"]


def test_recent_ownerless_lock_is_busy_but_aged_ownerless_is_reclaimed(tmp_path: Path) -> None:
    repo, calls = setup_repo(tmp_path)
    state_home = tmp_path / "state-home"
    lock = state_home / "state/capafy-headless-bridge/lock"
    lock.mkdir(parents=True)
    env = os.environ | {
        "MR_BOT_REPO": str(repo), "MR_BOT_STATE_HOME": str(state_home),
        "CAPAFY_HEADLESS_ONCE": "1", "CAPAFY_HEADLESS_NOW": "1000",
        "CAPAFY_HEADLESS_AQUA_PROBE": "false", "CAPAFY_HEADLESS_HOST_AQUA_PROBE": "false",
        "CAPAFY_TEST_CALLS": str(calls),
        "CAPAFY_HEADLESS_LOCK_GRACE": "5",
    }
    recent = subprocess.run(["bash", str(BRIDGE), "run"], env=env, text=True, capture_output=True, check=False)
    assert recent.returncode == 0 and not calls.exists()
    import time
    old = int(time.time()) - 10
    os.utime(lock, (old, old))
    aged = subprocess.run(["bash", str(BRIDGE), "run"], env=env, text=True, capture_output=True, check=False)
    assert aged.returncode == 0 and calls.exists()
