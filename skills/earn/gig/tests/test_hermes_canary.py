"""Focused, offline contract tests for the Hermes Coconala canary adapter."""

from __future__ import annotations

import json
import os
import sqlite3
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import hermes_canary  # noqa: E402


def snapshot(*, ready: bool = True, missing: list[str] | None = None) -> dict:
    return {
        "version": 1,
        "platform": "coconala",
        "ready": ready,
        "missing_sources": [] if missing is None else missing,
        "snapshot_id": "coconala:123:abcdef0123456789",
        "slot": 123,
        "idempotency": {"task_template": "gig:coconala:{lane}:{slot}"},
        "lanes": {"paid": {}, "reply": {}, "apply": {}, "storefront": {}},
    }


def write_snapshot(path: Path, value: dict | None = None) -> None:
    path.write_text(json.dumps(snapshot() if value is None else value), encoding="utf-8")


def _write_worker_truth(argv: list[str], lane: str) -> None:
    truth_path = Path(next(arg.split("=", 1)[1] for arg in argv if arg.startswith("GIG_HERMES_TRUTH_PATH=")))
    truth_path.write_text(
        json.dumps({
            "lane": lane,
            "step": hermes_canary._LANE_TO_STEP[lane],
            "status": "success",
            "coverage_complete": True,
            "collector_complete": True,
            "no_action_reason": "fixture_noop",
            "official_readback_count": 0,
        }),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _offline_storefront_observer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        hermes_canary,
        "_default_storefront_observer",
        lambda: {"content_sha256": "a" * 64, "live_listings_count": 11, "service_count": 11},
    )


def test_plan_fails_closed_for_unready_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path, snapshot(ready=False))
    with pytest.raises(hermes_canary.CanaryError):
        hermes_canary.plan_from_path(path, repo=Path("/live/repo"))


def test_plan_fails_closed_when_any_lane_descriptor_is_missing(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    value = snapshot()
    del value["lanes"]["paid"]
    write_snapshot(path, value)
    with pytest.raises(hermes_canary.CanaryError, match="lanes are incomplete"):
        hermes_canary.plan_from_path(path, repo=Path("/live/repo"))


def test_plan_builds_exact_four_specs_in_revenue_priority_order(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path)
    result = hermes_canary.plan_from_path(path, repo=Path("/live/repo"))
    assert len(result["tasks"]) == 4
    assert [task["lane"] for task in result["tasks"]] == ["paid", "reply", "apply", "storefront"]
    assert [
        (task["step"], task["assignee"], task["priority"]) for task in result["tasks"]
    ] == [
        ("PAID_WORK", "gigpaid", 40),
        ("B1", "gigreply", 30),
        ("B2", "gigapply", 20),
        ("B0", "gigstorefront", 10),
    ]
    by_lane = {task["lane"]: task for task in result["tasks"]}
    assert by_lane["paid"]["step"] == "PAID_WORK"
    assert by_lane["paid"]["assignee"] == "gigpaid"
    assert by_lane["paid"]["priority"] == 40
    assert by_lane["paid"]["idempotency_key"] == "gig:coconala:paid:123"
    assert by_lane["reply"]["step"] == "B1"
    assert by_lane["reply"]["assignee"] == "gigreply"
    assert by_lane["reply"]["priority"] == 30
    assert by_lane["reply"]["idempotency_key"] == "gig:coconala:reply:123"
    assert by_lane["apply"]["step"] == "B2"
    assert by_lane["apply"]["idempotency_key"] == "gig:coconala:apply:123"
    assert by_lane["storefront"]["step"] == "B0"
    assert by_lane["storefront"]["idempotency_key"] == "gig:coconala:storefront:123"
    assert by_lane["apply"]["priority"] > by_lane["storefront"]["priority"]
    assert by_lane["storefront"]["reserved_every_slot"] is True
    assert "python3 /live/repo/skills/earn/gig/scripts/hermes_canary.py run" in by_lane["apply"]["body"]


def test_enqueue_uses_profile_workspace_and_idempotency(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path)
    calls: list[list[str]] = []

    def fake_write_snapshot(**kwargs):
        assert kwargs["output_path"] == path
        return snapshot()

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": argv[argv.index("create") + 1]}), stderr="")

    monkeypatch.setattr(hermes_canary, "write_snapshot", fake_write_snapshot)
    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    result = hermes_canary.enqueue_from_path(
        path, repo=Path("/live/repo"), board="gig-revenue", model="pinned-model", provider="pinned-provider"
    )
    assert len(calls) == 3
    assert all(argv[:5] == ["hermes", "kanban", "--board", "gig-revenue", "create"] for argv in calls)
    assert all(argv[argv.index("--workspace") + 1] == "dir:/live/repo" for argv in calls)
    assert all(argv[argv.index("--max-runtime") + 1] == "2h" for argv in calls)
    assert all("--model" not in argv for argv in calls)
    assert all("--provider" not in argv for argv in calls)
    assert {row["idempotency_key"] for row in result["created"]} == {
        "gig:coconala:paid:123",
        "gig:coconala:reply:123",
        "gig:coconala:apply:123",
    }


def test_enqueue_cli_excludes_named_lanes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path)
    calls: list[list[str]] = []

    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": "task"}), stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    assert hermes_canary.main(
        [
            "enqueue",
            "--snapshot",
            str(path),
            "--exclude-lane",
            "apply",
            "--exclude-lane",
            "paid",
        ]
    ) == 0

    assert [argv[argv.index("--idempotency-key") + 1] for argv in calls] == [
        "gig:coconala:reply:123",
    ]
    assert [row["lane"] for row in json.loads(capsys.readouterr().out)["created"]] == [
        "reply",
    ]


def test_enqueue_rejects_unknown_excluded_lane_before_snapshot_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    called = False

    def fail_if_called(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("snapshot must not be rebuilt for an invalid lane")

    monkeypatch.setattr(hermes_canary, "write_snapshot", fail_if_called)
    with pytest.raises(hermes_canary.CanaryError, match="unknown lane"):
        hermes_canary.enqueue_from_path(tmp_path / "snapshot.json", exclude_lanes=("unknown",))
    assert called is False


def test_enqueue_rebuilds_fresh_snapshot_each_invocation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path)
    first = snapshot()
    first["snapshot_id"] = "coconala:123:first"
    second = snapshot()
    second["slot"] = 124
    second["snapshot_id"] = "coconala:124:second"
    fresh = iter((first, second))
    writer_calls: list[Path] = []
    keys: list[str] = []

    def fake_write_snapshot(**kwargs):
        writer_calls.append(kwargs["output_path"])
        return next(fresh)

    def fake_run(argv, **kwargs):
        keys.append(argv[argv.index("--idempotency-key") + 1])
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": "task"}), stderr="")

    monkeypatch.setattr(hermes_canary, "write_snapshot", fake_write_snapshot)
    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    hermes_canary.enqueue_from_path(path, repo=Path("/live/repo"))
    hermes_canary.enqueue_from_path(path, repo=Path("/live/repo"))

    assert writer_calls == [path, path]
    assert keys == [
        "gig:coconala:paid:123",
        "gig:coconala:reply:123",
        "gig:coconala:apply:123",
        "gig:coconala:paid:124",
        "gig:coconala:reply:124",
        "gig:coconala:apply:124",
    ]


def test_task_body_quotes_adversarial_repo_path() -> None:
    repo = Path("/live/repo; touch /tmp/hermes-canary-pwned")
    task = next(task for task in hermes_canary.plan_snapshot(snapshot(), repo=repo)["tasks"] if task["lane"] == "apply")
    command = shlex.join([
        "/opt/homebrew/bin/python3",
        str(repo / "skills/earn/gig/scripts/hermes_canary.py"),
        "run",
        "--lane",
        "apply",
        "--task-key",
        "gig:coconala:apply:123",
    ])
    assert command in task["body"]
    assert task["body"].count(command) == 1


def test_task_body_uses_production_python_as_the_only_command() -> None:
    repo = Path("/live/repo")
    task = next(task for task in hermes_canary.plan_snapshot(snapshot(), repo=repo)["tasks"] if task["lane"] == "apply")
    command = shlex.join([
        "/opt/homebrew/bin/python3",
        str(repo / "skills/earn/gig/scripts/hermes_canary.py"),
        "run",
        "--lane",
        "apply",
        "--task-key",
        "gig:coconala:apply:123",
    ])
    assert task["body"].count(command) == 1
    assert command in task["body"].splitlines()
    assert "python3 /live/repo/skills/earn/gig/scripts/hermes_canary.py run --lane apply --task-key gig:coconala:apply:123" not in task["body"].splitlines()


def test_enqueue_preserves_integer_task_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path)

    def fake_write_snapshot(**kwargs):
        assert kwargs["output_path"] == path
        return snapshot()

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 42}), stderr="")

    monkeypatch.setattr(hermes_canary, "write_snapshot", fake_write_snapshot)
    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    result = hermes_canary.enqueue_from_path(path, repo=Path("/live/repo"))
    assert [row["task_id"] for row in result["created"]] == [42, 42, 42]


def test_duplicate_enqueue_reuses_same_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    write_snapshot(path)
    calls: list[list[str]] = []

    def fake_write_snapshot(**kwargs):
        assert kwargs["output_path"] == path
        return snapshot()

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": "existing"}), stderr="")

    monkeypatch.setattr(hermes_canary, "write_snapshot", fake_write_snapshot)
    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    hermes_canary.enqueue_from_path(path, repo=Path("/live/repo"), board="gig-revenue")
    hermes_canary.enqueue_from_path(path, repo=Path("/live/repo"), board="gig-revenue")
    keys = [argv[argv.index("--idempotency-key") + 1] for argv in calls]
    assert keys == [
        "gig:coconala:paid:123",
        "gig:coconala:reply:123",
        "gig:coconala:apply:123",
    ] * 2


def test_run_argv_env_receipt_and_child_rc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fresh = snapshot()
    fresh["snapshot_id"] = "coconala:123:fresh"
    receipt_dir = tmp_path / "receipts"
    calls: list[tuple[list[str], dict]] = []
    monkeypatch.delenv("CDP_LOCK_DIR", raising=False)
    monkeypatch.setenv("CLOAK_BROWSER_OWNER", "legacy-browser-owner")
    monkeypatch.setenv("GIG_LOCK_DIR", "/tmp/inherited-global-pass.lock.d")

    def fake_write_snapshot(**kwargs):
        assert kwargs["output_path"] == tmp_path / "snapshot.json"
        return fresh

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, 17, stdout="ignored", stderr="ignored")

    monkeypatch.setattr(hermes_canary, "write_snapshot", fake_write_snapshot)
    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    rc = hermes_canary.run_lane(
        lane="apply",
        task_key="gig:coconala:apply:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=receipt_dir,
    )
    assert rc == 17
    argv, kwargs = calls[0]
    assert argv[:2] == [str(tmp_path / "repo" / "skills/earn/gig/scripts/run_with_cdp_lock.sh"), "hermes-apply-123"]
    assert argv[2:5] == ["7200", "--", "/usr/bin/env"]
    assert "GIG_HERMES_FORCED_STEP=B2" in argv
    assert "GIG_HERMES_TASK_KEY=gig:coconala:apply:123" in argv
    assert "GIG_HERMES_SNAPSHOT_ID=coconala:123:fresh" in argv
    assert "GIG_WORKER_REPORTS_ENABLED=1" in argv
    assert argv[-2:] == ["/bin/bash", str(tmp_path / "repo" / "skills/earn/gig/scripts/launch_gig_worker.sh")]
    assert kwargs["shell"] is False
    assert kwargs.get("capture_output") is not True
    assert kwargs.get("stdout") is None
    assert kwargs.get("stderr") is None
    assert kwargs["env"]["CDP_LOCK_DIR"] == str(Path.home() / "gig" / ".cdp-gig-apply.lock")
    assert kwargs["env"]["CLOAK_BROWSER_OWNER"] == "gig-apply"
    apply_pass_lock = str(Path.home() / "gig" / ".gig-pass-apply.lock.d")
    assert kwargs["env"]["GIG_LOCK_DIR"] == apply_pass_lock

    explicit_lock = tmp_path / "explicit-cdp.lock"
    monkeypatch.setenv("CDP_LOCK_DIR", str(explicit_lock))
    hermes_canary.run_lane(
        lane="apply",
        task_key="gig:coconala:apply:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "override-receipts",
    )
    assert calls[1][1]["env"]["CDP_LOCK_DIR"] == str(Path.home() / "gig" / ".cdp-gig-apply.lock")
    assert calls[1][1]["env"]["CLOAK_BROWSER_OWNER"] == "gig-apply"
    assert calls[1][1]["env"]["GIG_LOCK_DIR"] == apply_pass_lock
    receipts = list(receipt_dir.glob("*.json"))
    assert len(receipts) == 1
    mode = stat.S_IMODE(receipts[0].stat().st_mode)
    assert mode == 0o600
    payload = json.loads(receipts[0].read_text(encoding="utf-8"))
    assert payload["rc"] == 17
    assert payload["snapshot_id"] == "coconala:123:fresh"
    assert "/" + "Users/" not in receipts[0].read_text(encoding="utf-8")


def test_run_lane_strips_kanban_lifecycle_env_but_preserves_gig_and_unrelated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inherited = {
        "HERMES_KANBAN_TASK": "outer-task",
        "HERMES_KANBAN_BOARD": "gig-revenue",
        "HERMES_KANBAN_SESSION_ID": "outer-session",
        "UNRELATED_CHILD_ENV": "preserve-me",
        "GIG_HERMES_FORCED_STEP": "parent-step",
        "GIG_HERMES_TASK_KEY": "parent-key",
        "GIG_HERMES_SNAPSHOT_ID": "parent-snapshot",
        "GIG_HERMES_CUSTOM": "preserve-gig",
    }
    for name, value in inherited.items():
        monkeypatch.setenv(name, value)
    calls: list[dict] = []
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())

    def fake_run(argv, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    hermes_canary.run_lane(
        lane="reply",
        task_key="gig:coconala:reply:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "receipts",
    )
    child_env = calls[0]["env"]
    assert all(not name.startswith("HERMES_KANBAN_") for name in child_env)
    assert child_env["UNRELATED_CHILD_ENV"] == "preserve-me"
    for name, value in inherited.items():
        if name.startswith("GIG_HERMES_"):
            assert child_env[name] == value


def test_run_lanes_use_distinct_lane_locks_and_override_inherited_global(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    inherited_lock = tmp_path / "legacy-global.lock"
    lanes = ("paid", "reply", "apply", "storefront")
    expected_locks = {
        lane: Path.home() / "gig" / f".cdp-gig-{lane}.lock" for lane in lanes
    }
    calls: list[tuple[list[str], dict]] = []
    monkeypatch.setenv("CDP_LOCK_DIR", str(inherited_lock))
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    for lane in lanes:
        hermes_canary.run_lane(
            lane=lane,
            task_key=f"gig:coconala:{lane}:123",
            repo=tmp_path / "repo",
            snapshot_path=tmp_path / "snapshot.json",
            receipt_dir=tmp_path / f"{lane}-receipts",
            marker_path=tmp_path / "missing-b0-cooldown",
        )

    actual_locks = [kwargs["env"]["CDP_LOCK_DIR"] for _argv, kwargs in calls]
    actual_owners = [kwargs["env"]["CLOAK_BROWSER_OWNER"] for _argv, kwargs in calls]
    actual_pass_locks = [kwargs["env"]["GIG_LOCK_DIR"] for _argv, kwargs in calls]
    assert actual_locks == [str(expected_locks[lane]) for lane in lanes]
    assert actual_owners == [f"gig-{lane}" for lane in lanes]
    assert actual_pass_locks == [str(Path.home() / "gig" / f".gig-pass-{lane}.lock.d") for lane in lanes]
    assert len(set(actual_locks)) == len(lanes)
    assert len(set(actual_owners)) == len(lanes)
    assert all(lock != str(inherited_lock) for lock in actual_locks)
    assert all(lock != "/tmp/inherited-global-pass.lock.d" for lock in actual_pass_locks)
    assert len(set(actual_pass_locks)) == len(lanes)


@pytest.mark.parametrize(
    ("lane", "step"),
    [("paid", "PAID_WORK"), ("reply", "B1"), ("apply", "B2"), ("storefront", "B0")],
)
def test_run_forces_each_lane_step_and_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lane: str, step: str
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        _write_worker_truth(argv, lane)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    assert hermes_canary.run_lane(
        lane=lane,
        task_key=f"gig:coconala:{lane}:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "receipts",
        marker_path=tmp_path / "missing-b0-cooldown",
    ) == 0
    assert len(calls) == 1
    assert f"GIG_HERMES_FORCED_STEP={step}" in calls[0]
    assert f"GIG_HERMES_TASK_KEY=gig:coconala:{lane}:123" in calls[0]


def _run_lane_case(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    lane: str,
    marker_text: str | None,
    now: float,
    child_rc: int,
    snapshot_id: str = "coconala:123:test",
) -> tuple[int, list[list[str]], dict]:
    fresh = snapshot()
    fresh["snapshot_id"] = snapshot_id
    marker = tmp_path / ".b0-cooldown"
    if marker_text is not None:
        marker.write_text(f"{marker_text}\n", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: fresh)
    def fake_run(argv, **_):
        calls.append(list(argv))
        if child_rc == 0:
            _write_worker_truth(argv, lane)
        return subprocess.CompletedProcess(argv, child_rc, stdout="", stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    rc = hermes_canary.run_lane(
        lane=lane,
        task_key=f"gig:coconala:{lane}:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "receipts",
        marker_path=marker,
        now_epoch=lambda: now,
    )
    payload = json.loads(next((tmp_path / "receipts").glob("*.json")).read_text(encoding="utf-8"))
    return rc, calls, payload


def test_recent_b0_success_defers_storefront_before_child_and_records_reason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rc, calls, payload = _run_lane_case(
        monkeypatch, tmp_path, lane="storefront", marker_text="1000", now=2000,
        child_rc=23, snapshot_id="coconala:123:deferred",
    )
    assert rc == 0
    assert calls == []
    assert payload["outcome"] == "deferred"
    assert payload["reason"] == "storefront_write_interval"
    assert payload["rc"] == 0
    assert payload["collector_complete"] is True
    assert payload["official_readback_count"] == 0
    assert payload["no_action_reason"] == "storefront_write_interval"
    assert payload["truth_verified"] is True
    assert payload["task_key"] == "gig:coconala:storefront:123"
    assert payload["snapshot_id"] == "coconala:123:deferred"
    assert payload["started_at"] and payload["finished_at"]


def test_recent_b0_success_observes_once_without_writer_and_receipt_is_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marker = tmp_path / ".b0-cooldown"
    marker.write_text("1000\n", encoding="utf-8")
    calls: list[list[str]] = []
    observed: list[int] = []
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())

    def observer():
        observed.append(1)
        return {
            "status": "ok",
            "content_sha256": "a" * 64,
            "live_listings_count": 11,
            "service_count": 11,
            "services": [{"title": "must not enter receipt"}],
        }

    monkeypatch.setattr(
        hermes_canary.subprocess,
        "run",
        lambda argv, **_: (calls.append(list(argv)) or subprocess.CompletedProcess(argv, 23, stdout="", stderr="")),
    )
    rc = hermes_canary.run_lane(
        lane="storefront",
        task_key="gig:coconala:storefront:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "receipts",
        marker_path=marker,
        now_epoch=lambda: 2000,
        storefront_observer=observer,
    )
    payload = json.loads(next((tmp_path / "receipts").glob("*.json")).read_text(encoding="utf-8"))
    assert rc == 0
    assert observed == [1]
    assert calls == []
    assert payload["outcome"] == "deferred"
    assert payload["observation"] == {
        "status": "ok",
        "content_sha256": "a" * 64,
        "live_listings_count": 11,
        "service_count": 11,
    }
    assert "must not enter receipt" not in json.dumps(payload, ensure_ascii=False)


def test_storefront_observation_failure_defers_in_cooldown_but_fails_when_write_due(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())
    calls: list[list[str]] = []

    monkeypatch.setattr(
        hermes_canary.subprocess,
        "run",
        lambda argv, **_: (calls.append(list(argv)) or subprocess.CompletedProcess(argv, 0, stdout="", stderr="")),
    )

    def failed_observer():
        raise RuntimeError("credential and buyer text stay out of receipts")

    marker = tmp_path / ".b0-cooldown"
    marker.write_text("1000\n", encoding="utf-8")
    deferred_rc = hermes_canary.run_lane(
        lane="storefront",
        task_key="gig:coconala:storefront:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "deferred-receipts",
        marker_path=marker,
        now_epoch=lambda: 2000,
        storefront_observer=failed_observer,
    )
    deferred = json.loads(next((tmp_path / "deferred-receipts").glob("*.json")).read_text(encoding="utf-8"))
    assert deferred_rc == 0
    assert deferred["outcome"] == "deferred"
    assert deferred["observation"] == {
        "status": "failed",
        "content_sha256": None,
        "live_listings_count": None,
        "service_count": None,
    }
    assert calls == []

    due_rc = hermes_canary.run_lane(
        lane="storefront",
        task_key="gig:coconala:storefront:124",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "due-receipts",
        marker_path=marker,
        now_epoch=lambda: 11800,
        storefront_observer=failed_observer,
    )
    due = json.loads(next((tmp_path / "due-receipts").glob("*.json")).read_text(encoding="utf-8"))
    assert due_rc != 0
    assert due["outcome"] == "failed"
    assert due["reason"] == "storefront_observation_failed"
    assert due["observation"]["status"] == "failed"
    assert calls == []


def test_non_storefront_lanes_never_invoke_storefront_observer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())
    calls: list[list[str]] = []

    def fake_run(argv, **_):
        calls.append(list(argv))
        lane = next(value for value in ("paid", "reply", "apply") if f"hermes-{value}-123" in argv)
        _write_worker_truth(argv, lane)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(
        hermes_canary.subprocess,
        "run", fake_run,
    )

    def observer():
        raise AssertionError("storefront observer is lane-local")

    for lane in ("paid", "reply", "apply"):
        assert hermes_canary.run_lane(
            lane=lane,
            task_key=f"gig:coconala:{lane}:123",
            repo=tmp_path / "repo",
            snapshot_path=tmp_path / "snapshot.json",
            receipt_dir=tmp_path / f"{lane}-receipts",
            storefront_observer=observer,
        ) == 0
    assert len(calls) == 3


def test_truth_verification_failure_never_returns_zero_for_cooldown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        hermes_canary,
        "_forced_lane_truth",
        lambda *_args, **_kwargs: (False, "forced_lane_truth_invalid"),
    )

    rc, calls, payload = _run_lane_case(
        monkeypatch, tmp_path, lane="storefront", marker_text="1000", now=2000,
        child_rc=0,
    )

    assert rc != 0
    assert calls == []
    assert payload["rc"] != 0
    assert payload["truth_verified"] is False


@pytest.mark.parametrize("marker_text", ["1000", None, "malformed", "12000"])
def test_stale_missing_malformed_or_future_b0_marker_runs_storefront_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, marker_text: str | None
) -> None:
    rc, calls, payload = _run_lane_case(
        monkeypatch, tmp_path, lane="storefront", marker_text=marker_text, now=11800, child_rc=23
    )
    assert rc == 23
    assert len(calls) == 1
    assert payload["rc"] == 23
    assert payload.get("outcome") != "deferred"


def test_apply_ignores_recent_b0_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    rc, calls, _ = _run_lane_case(
        monkeypatch, tmp_path, lane="apply", marker_text="1000", now=2000, child_rc=0
    )
    assert rc == 0
    assert len(calls) == 1


def _truth_case(tmp_path: Path, *, lane: str, truth: dict) -> Path:
    path = tmp_path / "truth.json"
    path.write_text(json.dumps({"lane": lane, "step": hermes_canary._LANE_TO_STEP[lane], **truth}), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("lane", "truth", "expected"),
    [
        ("apply", {"status": "success", "coverage_complete": False, "reason": "turns_exhausted"}, 1),
        ("apply", {"status": "success", "coverage_complete": True, "collector_complete": True, "no_action_reason": "queue_empty", "official_readback_count": 0}, 0),
        ("reply", {"status": "success", "coverage_complete": False, "reason": "collector_incomplete"}, 1),
        ("paid", {"status": "blocked", "coverage_complete": True}, 1),
        ("storefront", {"status": "success", "coverage_complete": True, "collector_complete": True, "no_action_reason": "observation_complete", "official_readback_count": 0}, 0),
    ],
)
def test_forced_lane_truth_overrides_shell_rc0(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lane: str, truth: dict, expected: int
) -> None:
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())
    monkeypatch.setattr(
        hermes_canary.subprocess,
        "run",
        lambda argv, **_: subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
    )
    assert hermes_canary.run_lane(
        lane=lane,
        task_key=f"gig:coconala:{lane}:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "receipts",
        truth_path=_truth_case(tmp_path, lane=lane, truth=truth),
    ) == expected


def test_forced_lane_truth_missing_is_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())
    monkeypatch.setattr(
        hermes_canary.subprocess,
        "run",
        lambda argv, **_: subprocess.CompletedProcess(argv, 0, stdout="", stderr=""),
    )
    assert hermes_canary.run_lane(
        lane="apply", task_key="gig:coconala:apply:123", repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json", receipt_dir=tmp_path / "receipts",
        truth_path=tmp_path / "missing.json",
    ) != 0


def test_normal_forced_lane_passes_generated_truth_path_and_fails_when_worker_omits_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    receipt_dir = tmp_path / "receipts"
    assert hermes_canary.run_lane(
        lane="apply",
        task_key="gig:coconala:apply:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=receipt_dir,
    ) != 0
    truth_args = [arg for arg in calls[0] if arg.startswith("GIG_HERMES_TRUTH_PATH=")]
    assert len(truth_args) == 1
    truth_path = Path(truth_args[0].split("=", 1)[1])
    receipt = json.loads(next(receipt_dir.glob("gig_coconala_apply_123.json")).read_text(encoding="utf-8"))
    assert receipt["truth_path"] == str(truth_path)
    assert receipt["truth_verified"] is False
    assert receipt["rc"] != 0


def test_normal_forced_lane_accepts_truth_written_by_worker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())

    def fake_run(argv, **kwargs):
        truth_path = Path(next(arg.split("=", 1)[1] for arg in argv if arg.startswith("GIG_HERMES_TRUTH_PATH=")))
        truth_path.write_text(
            json.dumps({
                "lane": "apply",
                "step": "B2",
                "status": "success",
                "coverage_complete": True,
                "collector_complete": True,
                "no_action_reason": "queue_empty",
                "official_readback_count": 0,
            }),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    assert hermes_canary.run_lane(
        lane="apply",
        task_key="gig:coconala:apply:123",
        repo=tmp_path / "repo",
        snapshot_path=tmp_path / "snapshot.json",
        receipt_dir=tmp_path / "receipts",
    ) == 0


def test_forced_lane_truth_ignores_failure_words_in_history_and_prose(
    tmp_path: Path,
) -> None:
    path = _truth_case(
        tmp_path,
        lane="apply",
        truth={
            "status": "success",
            "coverage_complete": True,
            "collector_complete": True,
            "no_action_reason": "queue_empty",
            "official_readback_count": 0,
            "history": "previous attempt failed and was blocked; prose says unclosed",
        },
    )
    assert hermes_canary._forced_lane_truth(path, lane="apply", step="B2") == (True, "verified_noop")


def test_forced_lane_truth_accepts_closed_enum_for_verified_effect(tmp_path: Path) -> None:
    path = _truth_case(
        tmp_path,
        lane="apply",
        truth={
            "status": "success",
            "coverage_complete": True,
            "collector_complete": True,
            "external_effect_expected": True,
            "lane_closure": "closed",
            "send_verified": True,
        },
    )
    assert hermes_canary._forced_lane_truth(path, lane="apply", step="B2") == (True, "verified_send")


def test_forced_lane_truth_rejects_malformed_named_enums(tmp_path: Path) -> None:
    path = _truth_case(tmp_path, lane="apply", truth={"status": {"name": "blocked"}, "coverage_complete": True})
    assert hermes_canary._forced_lane_truth(path, lane="apply", step="B2")[0] is False


@pytest.mark.parametrize(
    "truth",
    [
        {"status": "success", "coverage_complete": True, "turns_exhausted": True},
        {"status": "success", "coverage_complete": False},
        {"status": "success", "coverage_complete": True, "blocked": True},
        {
            "status": "success",
            "coverage_complete": True,
            "external_effect_expected": True,
            "lane_closure": {"closed": False},
            "send_verified": False,
        },
        {
            "status": "success",
            "coverage_complete": True,
            "no_action_reason": "queue_empty",
            "official_readback_count": 0,
            "lane_closure": {"closed": False},
        },
        {
            "status": "success",
            "coverage_complete": True,
            "no_action_reason": "queue_empty",
            "official_readback_count": 0,
            "external_effect_expected": "false",
        },
    ],
)
def test_forced_lane_truth_rejects_explicit_failure_fields(tmp_path: Path, truth: dict) -> None:
    path = _truth_case(tmp_path, lane="apply", truth=truth)
    assert hermes_canary._forced_lane_truth(path, lane="apply", step="B2")[0] is False


@pytest.mark.parametrize("value", ["malformed", "3599", "86401"])
def test_storefront_interval_configuration_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str
) -> None:
    monkeypatch.setenv("GIG_HERMES_STOREFRONT_WRITE_INTERVAL_SECONDS", value)
    monkeypatch.setattr(hermes_canary, "write_snapshot", lambda **_: snapshot())
    calls: list[object] = []
    monkeypatch.setattr(hermes_canary.subprocess, "run", lambda *args, **_: calls.append(args))
    with pytest.raises(hermes_canary.CanaryError, match="storefront write interval"):
        hermes_canary.run_lane(
            lane="storefront",
            task_key="gig:coconala:storefront:123",
            repo=tmp_path / "repo",
            snapshot_path=tmp_path / "snapshot.json",
            receipt_dir=tmp_path / "receipts",
        )
    assert calls == []


def test_run_rejects_malicious_lane_or_key_without_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("child must not run")

    monkeypatch.setattr(hermes_canary.subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        hermes_canary._parser().parse_args(
            ["run", "--lane", "storefront", "--task-key", "gig:coconala:storefront:123"]
        )
    with pytest.raises(hermes_canary.CanaryError):
        hermes_canary.run_lane(
            lane="apply; touch /tmp/pwned",
            task_key="gig:coconala:apply:123",
            repo=tmp_path / "repo",
            snapshot_path=tmp_path / "snapshot.json",
            receipt_dir=tmp_path / "receipts",
        )
    with pytest.raises(hermes_canary.CanaryError):
        hermes_canary.run_lane(
            lane="apply",
            task_key="gig:coconala:storefront:123",
            repo=tmp_path / "repo",
            snapshot_path=tmp_path / "snapshot.json",
            receipt_dir=tmp_path / "receipts",
        )
    assert called is False


@pytest.mark.parametrize("lane", ["paid", "reply", "apply", "storefront"])
def test_task_key_regex_accepts_only_canonical_lane_keys(lane: str) -> None:
    assert hermes_canary._validated_lane_key(lane, f"gig:coconala:{lane}:123") == 123
    with pytest.raises(hermes_canary.CanaryError):
        hermes_canary._validated_lane_key(lane, f"prefix-gig:coconala:{lane}:123")
    with pytest.raises(hermes_canary.CanaryError):
        hermes_canary._validated_lane_key(lane, f"gig:coconala:{lane}:123-suffix")


def test_shell_wiring_and_plist_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    shell = (root / "gig_pass.sh").read_text(encoding="utf-8")
    plist = (root / "launchd/ai.anicca.hf-gig-pass.plist").read_text(encoding="utf-8")
    assert "GIG_HERMES_FORCED_STEP" in shell
    assert "GIG_HERMES_OWNED_STEPS" in shell
    assert "GIG_HERMES_FORCED_STEP" in shell.split("GIG_WORKER_SCRIPT", 1)[0]
    assert "GIG_HERMES_OWNED_STEPS" in plist
    assert "<key>GIG_HERMES_OWNED_STEPS</key><string>B2</string>" in plist


# ---------------------------------------------------------------------------
# Read-only 24-hour canary audit contract


AUDIT_DUE_1 = 1_786_354_500  # epoch % 1800 == 300; task-key slot is 992419
AUDIT_DUE_2 = 1_786_356_300  # epoch % 1800 == 300; task-key slot is 992420
AUDIT_SLOT_1 = AUDIT_DUE_1 // 1800
AUDIT_SLOT_2 = AUDIT_DUE_2 // 1800
AUDIT_SINCE = AUDIT_DUE_1 - 1


def _audit_task(lane: str, slot: int, status: str = "done", created_at: float = AUDIT_DUE_1) -> dict:
    key = f"gig:coconala:{lane}:{slot}"
    return {
        "title": f"Canary {key}",
        "body": f"Run {key}",
        "status": status,
        "created_at": created_at,
    }


def _audit_runner(tasks: list[dict]):
    def run(argv, **kwargs):
        assert argv == [
            "hermes",
            "kanban",
            "--board",
            "gig-revenue",
            "list",
            "--archived",
            "--json",
        ]
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"tasks": tasks}), stderr="")

    return run


def _write_audit_receipt(receipt_dir: Path, lane: str, slot: int, *, outcome: str = "executed", rc: int = 0) -> None:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    key = f"gig:coconala:{lane}:{slot}"
    (receipt_dir / f"gig_coconala_{lane}_{slot}.json").write_text(
        json.dumps({"version": 1, "task_key": key, "rc": rc, "outcome": outcome}),
        encoding="utf-8",
    )


def _write_audit_telegram_db(path: Path, request_id: str, *, created_at: int = 500) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE telegram_reports (
             event_key TEXT, kind TEXT, state TEXT, created_at INTEGER, message_id TEXT
           )"""
    )
    connection.execute(
        "INSERT INTO telegram_reports VALUES(?,?,?,?,?)",
        (f"gig:application:{request_id}", "application", "sent", created_at, "42"),
    )
    connection.commit()
    connection.close()


def _green_audit_fixture(tmp_path: Path):
    receipt_dir = tmp_path / "receipts"
    lanes = ("paid", "reply", "apply", "storefront")
    tasks = [
        _audit_task(lane, slot, created_at=due)
        for slot, due in ((AUDIT_SLOT_1, AUDIT_DUE_1), (AUDIT_SLOT_2, AUDIT_DUE_2))
        for lane in lanes
    ]
    for lane in lanes:
        for slot in (AUDIT_SLOT_1, AUDIT_SLOT_2):
            _write_audit_receipt(receipt_dir, lane, slot)
    return tasks, receipt_dir


def test_audit_green_full_window_and_cadence_metrics(tmp_path: Path) -> None:
    tasks, receipt_dir = _green_audit_fixture(tmp_path)
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_2,
        receipt_dir=receipt_dir,
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["version"] == 1
    assert result["window_complete"] is True
    assert result["verdict"] == "GREEN"
    assert result["lanes"]["apply"]["expected_due"] == 2
    assert result["lanes"]["apply"]["enqueued"] == 2
    assert result["lanes"]["apply"]["done"] == 2
    assert result["lanes"]["apply"]["executed"] == 2
    assert result["invariants"]["all_lanes_nonstarved"] is True
    assert all(result["lanes"][lane]["executed"] == 2 for lane in ("paid", "reply", "apply", "storefront"))


def test_audit_window_complete_requires_every_lane_execution(tmp_path: Path) -> None:
    tasks, receipt_dir = _green_audit_fixture(tmp_path)
    for receipt in receipt_dir.glob("gig_coconala_paid_*.json"):
        receipt.unlink()
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_2,
        receipt_dir=receipt_dir,
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["invariants"]["all_lanes_nonstarved"] is False
    assert result["verdict"] == "RED"


def test_audit_pending_keeps_recent_running_task_non_red(tmp_path: Path) -> None:
    tasks = [
        _audit_task("apply", AUDIT_SLOT_1, "running", created_at=AUDIT_DUE_1),
        _audit_task("storefront", AUDIT_SLOT_1, "running", created_at=AUDIT_DUE_1),
    ]
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_1 + 300,
        receipt_dir=tmp_path / "receipts",
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["verdict"] == "PENDING"
    assert result["invariants"]["no_stale_active"] is True


def test_audit_missing_slot_after_enqueue_grace_is_red(tmp_path: Path) -> None:
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_1 + 700,
        receipt_dir=tmp_path / "receipts",
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner([]),
    )
    assert result["verdict"] == "RED"
    assert result["lanes"]["apply"]["missing_slots"] == 1
    assert result["invariants"]["no_missing_due"] is False


def test_audit_duplicate_verified_applications_are_red(tmp_path: Path) -> None:
    tasks, receipt_dir = _green_audit_fixture(tmp_path)
    (tmp_path / "applied.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "requestId": "9001",
                    "status": "applied",
                    "submit_verified": True,
                    "applied_page_verified": True,
                    "ts": AUDIT_DUE_1 + 100 + index,
                }
            )
            for index in range(2)
        )
        + "\n",
        encoding="utf-8",
    )
    _write_audit_telegram_db(tmp_path / "telegram.sqlite3", "9001", created_at=AUDIT_DUE_1 + 100)
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_2,
        receipt_dir=receipt_dir,
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["applications"]["duplicate_request_ids"] == ["9001"]
    assert result["verdict"] == "RED"


def test_audit_missing_telegram_report_is_red(tmp_path: Path) -> None:
    tasks, receipt_dir = _green_audit_fixture(tmp_path)
    (tmp_path / "applied.jsonl").write_text(
        json.dumps(
            {
                "requestId": 9002,
                "status": "applied",
                "submit_verified": True,
                "applied_page_verified": True,
                "ts": AUDIT_DUE_1 + 100,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_2,
        receipt_dir=receipt_dir,
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["telegram"]["unreported_application_ids"] == ["9002"]
    assert result["verdict"] == "RED"


def test_audit_deferred_storefront_does_not_count_as_execution(tmp_path: Path) -> None:
    tasks, receipt_dir = _green_audit_fixture(tmp_path)
    _write_audit_receipt(receipt_dir, "storefront", AUDIT_SLOT_1, outcome="deferred")
    (tmp_path / "shuppin.jsonl").write_text(
        json.dumps({"service_id": 1, "action": "shuppin_edited", "ts": AUDIT_DUE_1 + 100}) + "\n",
        encoding="utf-8",
    )
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_2,
        now=AUDIT_DUE_2,
        receipt_dir=receipt_dir,
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["lanes"]["storefront"]["deferred"] == 1
    assert result["lanes"]["storefront"]["executed"] == 1
    assert result["storefront"]["effect_count"] == 1
    assert result["invariants"]["no_excess_storefront_effects"] is True


def test_audit_done_task_without_receipt_is_red(tmp_path: Path) -> None:
    tasks = [
        _audit_task("apply", AUDIT_SLOT_1, "done"),
        _audit_task("storefront", AUDIT_SLOT_1, "done"),
    ]
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_1 + 700,
        now=AUDIT_DUE_1 + 700,
        receipt_dir=tmp_path / "receipts",
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["lanes"]["apply"]["nonzero_or_invalid_receipts"] == 1
    assert result["verdict"] == "RED"


def test_audit_blocked_task_is_immediately_red(tmp_path: Path) -> None:
    tasks = [
        _audit_task("apply", AUDIT_SLOT_1, "blocked"),
        _audit_task("storefront", AUDIT_SLOT_1, "done"),
    ]
    receipt_dir = tmp_path / "receipts"
    _write_audit_receipt(receipt_dir, "storefront", AUDIT_SLOT_1)
    result = hermes_canary.audit_canary(
        since=AUDIT_SINCE,
        until=AUDIT_DUE_1 + 700,
        now=AUDIT_DUE_1 + 700,
        receipt_dir=receipt_dir,
        applied_ledger=tmp_path / "applied.jsonl",
        shuppin_ledger=tmp_path / "shuppin.jsonl",
        telegram_db=tmp_path / "telegram.sqlite3",
        runner=_audit_runner(tasks),
    )
    assert result["lanes"]["apply"]["blocked"] == 1
    assert result["invariants"]["no_blocked_tasks"] is False
    assert result["verdict"] == "RED"


def test_audit_cli_redacts_paths_and_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        hermes_canary.subprocess,
        "run",
        lambda argv, **_: subprocess.CompletedProcess(argv, 0, stdout='{"tasks":[]}', stderr=""),
    )
    rc = hermes_canary.main(
        [
            "audit",
            "--since",
            "0",
            "--until",
            "1",
            "--now",
            "0.5",
            "--receipt-dir",
            str(tmp_path / "secret-marker"),
            "--applied-ledger",
            str(tmp_path / "numeric-marker.jsonl"),
            "--shuppin-ledger",
            str(tmp_path / "identity-marker.jsonl"),
            "--telegram-db",
            str(tmp_path / "telegram.sqlite3"),
        ]
    )
    output = capsys.readouterr()
    assert rc == 0
    assert "/" + "Users/" not in output.out + output.err
    assert "secret-marker" not in output.out + output.err
    assert "numeric-marker" not in output.out + output.err
