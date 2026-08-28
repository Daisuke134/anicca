from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = GIG_ROOT / "scripts" / "gig_disk_guard.py"
GIG_BROWSER_PATH = GIG_ROOT / "scripts" / "launch_gig_browser.sh"
MANIFEST_PATH = GIG_ROOT / "config" / "launchd-jobs.json"
SELF_BUILD_PATH = GIG_ROOT.parents[1] / "life-manager" / "self-build-daily.sh"
WRITER_DAILY_PATH = GIG_ROOT.parents[1] / "writer-agent" / "article-daily.sh"


@pytest.fixture(autouse=True)
def _isolated_host_control_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GIG_DISK_HEADROOM_KIB", "524288")
    monkeypatch.delenv("GIG_HOST_STATE_DIR", raising=False)
    monkeypatch.delenv("DISK_CONTROL_STATE_DIR", raising=False)
    monkeypatch.delenv("OPENCLAW_STATE_DIR", raising=False)
    monkeypatch.delenv("LIFE_MANAGER_HOST_STATE_DIR", raising=False)
    (tmp_path / ".openclaw" / "state").mkdir(parents=True)


def _load_guard():
    spec = importlib.util.spec_from_file_location("gig_disk_guard_test", GUARD_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_reply_detector():
    path = GIG_ROOT / "scripts" / "reply_detector.py"
    spec = importlib.util.spec_from_file_location("gig_reply_detector_disk_guard_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_one_byte_under_threshold_writes_receipt_and_never_execs(tmp_path, monkeypatch, capsys):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES - 1),
    )

    def unexpected_exec(*_args, **_kwargs):
        raise AssertionError("child must not execute with low disk headroom")

    monkeypatch.setattr(guard.os, "execvpe", unexpected_exec)

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    output = json.loads(capsys.readouterr().out)
    receipt_path = tmp_path / "state" / "disk-headroom.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert output == receipt
    assert receipt == {
        "available_bytes": guard.REQUIRED_BYTES - 1,
        "effect": 0,
        "failed": 1,
        "readback": 0,
        "reason": "disk_headroom_low",
        "required_bytes": guard.REQUIRED_BYTES,
        "status": "failed",
    }


def test_exact_threshold_execs_remaining_argv_and_environment_exactly(tmp_path, monkeypatch):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("GIG_DISK_GUARD_SENTINEL", "kept")
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES),
    )
    calls = []
    monkeypatch.setattr(guard.os, "execvpe", lambda *args: calls.append(args))

    child_argv = ["/opt/homebrew/bin/python3", "/release/lane.py", "--flag", "value"]
    assert guard.main(child_argv) == 0

    assert calls == [(child_argv[0], child_argv, os.environ)]


def test_disk_measurement_exception_fails_closed_without_exec(tmp_path, monkeypatch, capsys):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(guard.shutil, "disk_usage", lambda _path: (_ for _ in ()).throw(OSError("no stat")))
    monkeypatch.setattr(guard.os, "execvpe", lambda *_args: (_ for _ in ()).throw(
        AssertionError("child must not execute when disk headroom is unknown")
    ))

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    receipt = json.loads(capsys.readouterr().out)
    assert receipt == {
        "effect": 0,
        "failed": 1,
        "readback": 0,
        "reason": "disk_headroom_unavailable",
        "required_bytes": guard.REQUIRED_BYTES,
        "status": "failed",
    }


@pytest.mark.parametrize(
    ("flag_name", "reason", "payload"),
    (
        ("disk-writers.stop", "disk_writers_stop", "tier=4\n"),
        ("disk-pressure.block", "disk_pressure_block", "free=7.5GiB\n"),
    ),
)
def test_life_manager_producer_flags_block_child_before_exec(
    tmp_path, monkeypatch, capsys, flag_name, reason, payload,
):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path / "gig"))
    host_state = Path.home() / ".openclaw" / "state"
    (host_state / flag_name).write_text(payload, encoding="utf-8")
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES * 8),
    )
    monkeypatch.setattr(guard.os, "execvpe", lambda *_args: (_ for _ in ()).throw(
        AssertionError("stop flag must block the producer before exec")
    ))

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["reason"] == reason
    assert receipt["gate"] == "life-manager-producer-preflight"
    assert receipt["flag_path"] == str(host_state / flag_name)
    assert receipt["effect"] == 0
    assert receipt["readback"] == 0


def test_writer_override_ignores_pressure_block_but_keeps_real_floor(
    tmp_path, monkeypatch
):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path / "gig"))
    monkeypatch.setenv("GIG_IGNORE_DISK_PRESSURE_BLOCK", "1")
    host_state = Path.home() / ".openclaw" / "state"
    (host_state / "disk-pressure.block").write_text("free=9GiB\n", encoding="utf-8")
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES * 8),
    )
    calls = []
    monkeypatch.setattr(guard.os, "execvpe", lambda *args: calls.append(args))

    assert guard.main(["/bin/echo", "writer-sentinel"]) == 0
    assert calls and calls[0][1] == ["/bin/echo", "writer-sentinel"]


def test_writer_override_ignores_shared_stop_but_keeps_real_floor(
    tmp_path, monkeypatch
):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path / "gig"))
    monkeypatch.setenv("GIG_IGNORE_DISK_PRESSURE_BLOCK", "1")
    monkeypatch.setenv("GIG_IGNORE_DISK_WRITERS_STOP", "1")
    host_state = Path.home() / ".openclaw" / "state"
    (host_state / "disk-writers.stop").write_text("tier=4\n", encoding="utf-8")
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES * 8),
    )
    calls = []
    monkeypatch.setattr(guard.os, "execvpe", lambda *args: calls.append(args))

    assert guard.main(["/bin/echo", "writer-sentinel"]) == 0
    assert calls and calls[0][1] == ["/bin/echo", "writer-sentinel"]


def test_writer_override_does_not_bypass_real_disk_floor(
    tmp_path, monkeypatch, capsys
):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path / "gig"))
    monkeypatch.setenv("GIG_IGNORE_DISK_PRESSURE_BLOCK", "1")
    host_state = Path.home() / ".openclaw" / "state"
    host_state.mkdir(parents=True, exist_ok=True)
    (host_state / "disk-pressure.block").write_text("free=9GiB\n", encoding="utf-8")
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES - 1),
    )
    monkeypatch.setattr(guard.os, "execvpe", lambda *_args: (_ for _ in ()).throw(
        AssertionError("real low disk must still block Writer")
    ))

    assert guard.main(["/bin/echo", "writer-sentinel"]) == 1
    assert json.loads(capsys.readouterr().out)["reason"] == "disk_headroom_low"


def test_missing_host_control_state_fails_closed_before_exec(tmp_path, monkeypatch, capsys):
    guard = _load_guard()
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path / "gig"))
    host_state = tmp_path / "missing-control-state"
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(host_state))
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES * 8),
    )
    monkeypatch.setattr(guard.os, "execvpe", lambda *_args: (_ for _ in ()).throw(
        AssertionError("missing control state must fail closed")
    ))

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["reason"] == "disk_policy_unavailable"
    assert receipt["gate"] == "life-manager-producer-preflight"
    assert receipt["flag_path"] == str(host_state)


def test_dangling_policy_flag_fails_closed_before_exec(tmp_path, monkeypatch, capsys):
    guard = _load_guard()
    host_state = Path.home() / ".openclaw" / "state"
    (host_state / "disk-writers.stop").symlink_to(host_state / "gone")
    monkeypatch.setenv("GIG_STATE_DIR", str(tmp_path / "gig"))
    monkeypatch.setattr(
        guard.shutil,
        "disk_usage",
        lambda _path: guard.shutil._ntuple_diskusage(1, 1, guard.REQUIRED_BYTES * 8),
    )
    monkeypatch.setattr(guard.os, "execvpe", lambda *_args: (_ for _ in ()).throw(
        AssertionError("dangling policy flag must fail closed")
    ))

    assert guard.main(["/bin/echo", "child-sentinel"]) == 1

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["reason"] == "disk_policy_unavailable"
    assert receipt["flag_path"] == str(host_state / "disk-writers.stop")


def test_receipt_fsyncs_parent_directory_after_atomic_replace(tmp_path, monkeypatch):
    guard = _load_guard()
    fsynced = []
    closed = []
    original_close = guard.os.close

    monkeypatch.setattr(guard.os, "fsync", lambda fd: fsynced.append(fd))
    monkeypatch.setattr(
        guard.os, "close",
        lambda fd: (closed.append(fd), original_close(fd))[1],
    )

    guard._fsync_directory(tmp_path)

    assert len(fsynced) == 1
    assert len(closed) == 1


def test_low_headroom_skips_probe_worker_reconcile_and_sqlite(tmp_path, monkeypatch):
    detector = _load_reply_detector()
    args = SimpleNamespace(
        database=tmp_path / "supervisor.sqlite3",
        manifest=GIG_ROOT / "config" / "connectors" / "coconala.json",
        poll_seconds=0.01,
        workers=2,
        reconcile_seconds=0.01,
    )
    stop = detector.asyncio.Event()
    calls = {"probe": 0, "worker": 0, "reconcile": 0}

    monkeypatch.setattr(detector, "disk_headroom_ok", lambda: False)

    class UnexpectedSQLite:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("low headroom must not initialize SQLite")

    monkeypatch.setattr(detector, "ConnectorOutbox", UnexpectedSQLite)

    async def probe():
        calls["probe"] += 1
        return {"inquiries": []}

    async def worker(_work):
        calls["worker"] += 1

    async def reconcile():
        calls["reconcile"] += 1

    async def run():
        task = detector.asyncio.create_task(
            detector.supervise_replies(
                args, probe=probe, worker=worker, reconcile=reconcile, stop=stop,
            )
        )
        await detector.asyncio.sleep(0.04)
        stop.set()
        await task

    detector.asyncio.run(run())

    assert calls == {"probe": 0, "worker": 0, "reconcile": 0}


def test_manifest_wraps_only_four_business_lanes():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    jobs = {job["lane"]: job for job in manifest["jobs"]}
    business = {"apply", "negotiate", "storefront", "paid"}

    for lane in business:
        program = jobs[lane]["program"]
        assert program[0] == "{{PYTHON}}"
        assert program[1] == "{{RELEASE}}/skills/earn/gig/scripts/gig_disk_guard.py"
        assert program[2] == "{{PYTHON}}"

    for lane in {"browser", "release"}:
        program = jobs[lane]["program"]
        assert "gig_disk_guard.py" not in program


def test_manifest_keeps_browser_start_direct_and_pins_real_floor():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    browser = next(job for job in manifest["jobs"] if job["lane"] == "browser")

    assert browser["program"] == [
        "/bin/bash",
        "{{RELEASE}}/skills/earn/gig/scripts/launch_gig_browser.sh",
    ]
    assert browser["env"]["GIG_DISK_HEADROOM_KIB"] == "524288"
    assert "GIG_IGNORE_DISK_PRESSURE_BLOCK" not in browser["env"]
    assert "GIG_IGNORE_DISK_WRITERS_STOP" not in browser["env"]
    # KeepAlive retry behavior remains A-22 scope; this slice only fences starts.
    assert browser["KeepAlive"] is True
    assert browser["ThrottleInterval"] == 30


def test_browser_script_preflights_before_profile_and_chromium_with_fixed_policy():
    script = GIG_BROWSER_PATH.read_text(encoding="utf-8")

    guard = script.index("/usr/bin/python3")
    profile = script.index('mkdir -p "$GIG_BROWSER_PROFILE"')
    chromium = script.index("chromium_bin=")
    assert guard < profile < chromium
    assert "GIG_DISK_HEADROOM_KIB=524288" in script
    assert 'GIG_HOST_STATE_DIR="$HOME/.openclaw/state"' in script
    assert 'GIG_STATE_DIR="$HOME/gig"' in script
    assert "unset GIG_IGNORE_DISK_PRESSURE_BLOCK GIG_IGNORE_DISK_WRITERS_STOP" in script
    assert "unset DISK_CONTROL_STATE_DIR OPENCLAW_STATE_DIR LIFE_MANAGER_HOST_STATE_DIR" in script
    assert "export GIG_DISK_HEADROOM_KIB GIG_HOST_STATE_DIR GIG_STATE_DIR" in script
    assert '"$DISK_GUARD" /usr/bin/true' in script


def test_self_build_uses_shared_guard_before_dependency_and_node_effects():
    script = SELF_BUILD_PATH.read_text(encoding="utf-8")

    assert "GIG_DISK_HEADROOM_KIB=524288" in script
    assert "GIG_HOST_STATE_DIR=" in script
    assert 'readonly LM_SELFBUILD_CANONICAL_HOST_STATE="$LIFE_MANAGER_STATE_HOME/state"' in script
    assert "GIG_STATE_DIR=" in script
    assert script.count('/usr/bin/python3 "$DISK_GUARD" /usr/bin/true') == 2
    assert "unset GIG_IGNORE_DISK_PRESSURE_BLOCK GIG_IGNORE_DISK_WRITERS_STOP" in script
    assert "unset DISK_CONTROL_STATE_DIR OPENCLAW_STATE_DIR LIFE_MANAGER_HOST_STATE_DIR" in script
    assert script.count("/usr/bin/true") == 2
    first_guard = script.index("/usr/bin/true")
    npm_effect = script.index("npm ci")
    second_guard = script.rindex("/usr/bin/true")
    node_effect = script.index('RESULT="$("$NODE_BIN"')
    assert first_guard < npm_effect < second_guard < node_effect


def test_writer_article_daily_already_has_media_preflight_and_bounded_stop_paths():
    script = WRITER_DAILY_PATH.read_text(encoding="utf-8")

    assert "media_create_once.py" in script
    assert "arm --run-dir \"$RUN_DIR\"" in script
    assert "writer_capacity_preflight" in script
    assert (
        'BOUNDED_EXEC_STOP_PATHS="$HOME/.openclaw/state/disk-writers.stop:'
        '$HOME/.openclaw/state/disk-pressure.block"'
    ) in script


@pytest.mark.parametrize(
    ("flag_name", "reason"),
    (
        ("disk-writers.stop", "disk_writers_stop"),
        ("disk-pressure.block", "disk_pressure_block"),
    ),
)
def test_self_build_stop_flag_blocks_npm_and_node_effects(tmp_path, flag_name, reason):
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    marker = tmp_path / "effect.marker"
    env_file = tmp_path / "self-build.env"
    explicit_log = tmp_path / "explicit-self-build.log"
    (home / ".openclaw" / "state").mkdir(parents=True)
    (home / ".openclaw" / "state" / flag_name).write_text(
        "tier=4\n", encoding="utf-8",
    )
    hostile_state = tmp_path / "hostile-state"
    hostile_state.mkdir()
    hostile_life = tmp_path / "hostile-life"
    hostile_life.mkdir()
    env_file.write_text(
        "GIG_DISK_HEADROOM_KIB=0\n"
        "GIG_IGNORE_DISK_PRESSURE_BLOCK=1\n"
        "GIG_IGNORE_DISK_WRITERS_STOP=1\n"
        "GIG_HOST_STATE_DIR=" + str(hostile_state) + "\n"
        "DISK_CONTROL_STATE_DIR=" + str(hostile_state) + "\n"
        "OPENCLAW_STATE_DIR=" + str(hostile_state) + "\n"
        "LIFE_MANAGER_HOST_STATE_DIR=" + str(hostile_state) + "\n"
        "GIG_STATE_DIR=" + str(hostile_state) + "\n"
        "LIFE_MANAGER_STATE_HOME=" + str(hostile_life) + "\n"
        "REPO_ROOT=" + str(tmp_path / "hostile-repo") + "\n"
        "DISK_GUARD=" + str(tmp_path / "hostile-guard.py") + "\n"
        "DAILY_CLI=" + str(tmp_path / "hostile-cli.js") + "\n",
        encoding="utf-8",
    )
    (repo / "skills" / "earn" / "gig" / "scripts").mkdir(parents=True)
    (repo / "apps" / "life-manager" / "scripts").mkdir(parents=True)
    guard_source = GUARD_PATH.read_text(encoding="utf-8")
    guard_source = guard_source.replace(
        "from __future__ import annotations\n",
        "from __future__ import annotations\n"
        "from pathlib import Path as _GuardCounterPath\n"
        "import os as _GuardCounterOS\n"
        "_guard_counter_path = _GuardCounterPath(_GuardCounterOS.environ[\"GUARD_CALL_COUNT\"])\n"
        "_guard_counter = int(_guard_counter_path.read_text(encoding=\"utf-8\") or \"0\") if _guard_counter_path.exists() else 0\n"
        "_guard_counter_path.write_text(str(_guard_counter + 1), encoding=\"utf-8\")\n",
        1,
    )
    (repo / "skills" / "earn" / "gig" / "scripts" / "gig_disk_guard.py").write_text(
        guard_source, encoding="utf-8",
    )
    (repo / "apps" / "life-manager" / "scripts" / "self-build-daily.js").write_text(
        "process.exit(0);\n", encoding="utf-8",
    )
    bin_dir.mkdir()
    node = bin_dir / "node"
    node.write_text(
        f"#!/bin/sh\nprintf node >> {marker}\nexit 0\n", encoding="utf-8",
    )
    npm = bin_dir / "npm"
    npm.write_text(
        f"#!/bin/sh\nprintf npm >> {marker}\nexit 0\n", encoding="utf-8",
    )
    node.chmod(0o755)
    npm.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "LM_SELFBUILD_REPO": str(repo),
        "LM_SELFBUILD_TELEGRAM_TARGET": "test-target",
        "NODE_BIN": str(node),
        "GIG_DISK_HEADROOM_KIB": "0",
        "GIG_IGNORE_DISK_PRESSURE_BLOCK": "1",
        "GIG_IGNORE_DISK_WRITERS_STOP": "1",
        "LIFE_MANAGER_ENV_FILE": str(env_file),
        "LM_SELFBUILD_LOG": str(explicit_log),
        "GIG_HOST_STATE_DIR": str(hostile_state),
        "DISK_CONTROL_STATE_DIR": str(hostile_state),
        "OPENCLAW_STATE_DIR": str(hostile_state),
        "LIFE_MANAGER_HOST_STATE_DIR": str(hostile_state),
        "GIG_STATE_DIR": str(hostile_state),
        "GUARD_CALL_COUNT": str(tmp_path / "guard-calls"),
    })
    result = subprocess.run(
        ["/bin/bash", str(SELF_BUILD_PATH)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert not marker.exists()
    assert explicit_log.is_file()
    assert (tmp_path / "guard-calls").read_text(encoding="utf-8") == "1"
    receipt = json.loads(
        (home / ".local" / "state" / "life-manager" / "state" / "disk-headroom.json")
        .read_text(encoding="utf-8")
    )
    assert receipt["required_bytes"] == 536870912
    assert receipt["effect"] == 0
    assert receipt["reason"] == reason
    assert not (hostile_state / "state" / "disk-headroom.json").exists()


@pytest.mark.parametrize(
    ("flag_name", "reason"),
    (
        ("disk-writers.stop", "disk_writers_stop"),
        ("disk-pressure.block", "disk_pressure_block"),
    ),
)
def test_browser_stop_flag_blocks_before_profile_or_chromium(tmp_path, flag_name, reason):
    home = tmp_path / "home"
    profile = tmp_path / "browser-profile"
    chromium_marker = tmp_path / "chromium-started"
    hostile_state = tmp_path / "hostile-state"
    (home / ".openclaw" / "state").mkdir(parents=True)
    hostile_state.mkdir()
    (home / ".openclaw" / "state" / flag_name).write_text("tier=4\n", encoding="utf-8")
    chromium = (
        home / ".cloakbrowser" / "chromium-999.0.0" / "Chromium.app" / "Contents"
        / "MacOS" / "Chromium"
    )
    chromium.parent.mkdir(parents=True)
    chromium.write_text(
        f"#!/bin/sh\nprintf started >> {chromium_marker}\n", encoding="utf-8",
    )
    chromium.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "GIG_BROWSER_PROFILE": str(profile),
        "GIG_DISK_HEADROOM_KIB": "0",
        "GIG_HOST_STATE_DIR": str(hostile_state),
        "DISK_CONTROL_STATE_DIR": str(hostile_state),
        "OPENCLAW_STATE_DIR": str(hostile_state),
        "LIFE_MANAGER_HOST_STATE_DIR": str(hostile_state),
        "GIG_STATE_DIR": str(hostile_state),
        "GIG_IGNORE_DISK_PRESSURE_BLOCK": "1",
        "GIG_IGNORE_DISK_WRITERS_STOP": "1",
        "GIG_BROWSER_TLS_COMPAT": "off",
    })
    result = subprocess.run(
        ["/bin/bash", str(GIG_BROWSER_PATH)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert not profile.exists()
    assert not chromium_marker.exists()
    receipt = json.loads(
        (home / "gig" / "state" / "disk-headroom.json").read_text(encoding="utf-8")
    )
    assert receipt["required_bytes"] == 536870912
    assert receipt["effect"] == 0
    assert receipt["reason"] == reason


def test_apply_ignores_preventive_flags_but_keeps_a_real_disk_floor():
    release_path = Path("/release")
    release_script = GIG_ROOT / "scripts" / "gig_release.py"
    spec = importlib.util.spec_from_file_location("gig_release_apply_guard_test", release_script)
    assert spec and spec.loader
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    manifest, table = release.settings(release_path)
    apply = next(job for job in manifest["jobs"] if job["lane"] == "apply")

    environment = release.plist_for(apply, table)["EnvironmentVariables"]
    assert environment["GIG_IGNORE_DISK_PRESSURE_BLOCK"] == "1"
    assert environment["GIG_IGNORE_DISK_WRITERS_STOP"] == "1"
    assert environment["GIG_DISK_HEADROOM_KIB"] == "524288"


def test_negotiate_ignores_preventive_flags_but_keeps_a_real_disk_floor():
    release_path = Path("/release")
    release_script = GIG_ROOT / "scripts" / "gig_release.py"
    spec = importlib.util.spec_from_file_location("gig_release_negotiate_guard_test", release_script)
    assert spec and spec.loader
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    manifest, table = release.settings(release_path)
    negotiate = next(job for job in manifest["jobs"] if job["lane"] == "negotiate")

    environment = release.plist_for(negotiate, table)["EnvironmentVariables"]
    assert environment["GIG_IGNORE_DISK_PRESSURE_BLOCK"] == "1"
    assert environment["GIG_IGNORE_DISK_WRITERS_STOP"] == "1"
    assert environment["GIG_DISK_HEADROOM_KIB"] == "524288"


def test_writer_lanes_render_from_immutable_release_and_life_manager_state():
    import importlib.util

    release_path = Path("/release")
    release_script = GIG_ROOT / "scripts" / "gig_release.py"
    spec = importlib.util.spec_from_file_location("gig_release_writer_test", release_script)
    assert spec and spec.loader
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    manifest, table = release.settings(release_path)
    writer = [job for job in manifest["jobs"] if job.get("env_profile") == "writer"]

    assert len(writer) == 14
    for job in writer:
        rendered = release.plist_for(job, table)
        assert rendered["EnvironmentVariables"]["ARTICLE_ROOT"] == (
            "/release/skills/writer-agent"
        )
        assert rendered["EnvironmentVariables"]["ARTICLE_STATE_DIR"] == (
            str(Path.home() / ".local/state/life-manager/writer")
        )
        assert rendered["EnvironmentVariables"]["GIG_DISK_HEADROOM_KIB"] == "524288"
        assert rendered["ProgramArguments"][1].endswith(
            "/skills/earn/gig/scripts/gig_disk_guard.py"
        )
        assert all("profitable-claude" not in value for value in rendered["ProgramArguments"])
        if "StartCalendarInterval" in job:
            assert rendered["StartCalendarInterval"] == job["StartCalendarInterval"]
        else:
            assert "StartCalendarInterval" not in rendered

    for job in manifest["jobs"]:
        rendered = release.plist_for(job, table)
        if "StartCalendarInterval" in job:
            assert rendered["StartCalendarInterval"] == job["StartCalendarInterval"]
        else:
            assert "StartCalendarInterval" not in rendered


def test_all_coconala_chromium_launches_disable_code_sign_clone():
    scripts = [
        GIG_ROOT / "scripts" / "launch_gig_browser.sh",
        GIG_ROOT / "scripts" / "cdp_daily_driver_guard.sh",
    ]
    for script in scripts:
        assert "--disable-features=MacAppCodeSignClone" in script.read_text()
