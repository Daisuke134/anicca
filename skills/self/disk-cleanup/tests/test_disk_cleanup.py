import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import disk_cleanup  # noqa: E402
from disk_cleanup import (  # noqa: E402
    GiB,
    HostDiskGovernor,
    classify_tier,
)


def test_tier_boundaries_use_bytes() -> None:
    assert classify_tier(20 * GiB) == "NORMAL"
    assert classify_tier(20 * GiB - 1) == "PREVENTIVE"
    assert classify_tier(11 * GiB) == "PREVENTIVE"
    assert classify_tier(11 * GiB - 1) == "PRESSURE"
    assert classify_tier(6 * GiB - 1) == "CRITICAL"
    assert classify_tier(3 * GiB - 1) == "ULTRA"


def test_closed_regenerable_artifact_is_reclaimed(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    candidate = tmp_path / "tmp" / "cfo-complete"
    candidate.mkdir(parents=True)
    (candidate / "payload").write_bytes(b"x" * 64)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(candidate.parent))
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=state,
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep(
        [{"path": candidate, "class": "ephemeral", "owner": "temporary-run", "discovery": "allowlisted"}]
    )

    assert result["reclaimed"] > 0
    assert not candidate.exists()
    receipt = json.loads((state / "last-receipt.json").read_text())
    assert receipt["protected_deletions"] == 0


def test_open_or_protected_artifact_is_preserved(tmp_path: Path, monkeypatch) -> None:
    state = tmp_path / "state"
    open_candidate = tmp_path / "tmp" / "cfo-open"
    open_candidate.mkdir(parents=True)
    monkeypatch.setattr(disk_cleanup.tempfile, "gettempdir", lambda: str(open_candidate.parent))
    protected = tmp_path / ".codex" / "logs.sqlite"
    protected.parent.mkdir()
    protected.write_bytes(b"x" * 64)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=state,
        lsof=lambda path: "open" if path == open_candidate else "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep(
        [
            {
                "path": open_candidate,
                "class": "ephemeral",
                "owner": "temporary-run",
                "discovery": "allowlisted",
            },
            {"path": protected, "class": "ephemeral", "owner": "unknown"},
        ]
    )

    assert result["reclaimed"] == 0
    assert open_candidate.exists()
    assert protected.exists()
    assert result["preserved"] == 2
    assert result["protected_deletions"] == 0


def test_unproved_candidate_is_preserved(tmp_path: Path) -> None:
    candidate = tmp_path / "important"
    candidate.write_bytes(b"do-not-delete")
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep([{"path": candidate, "class": "ephemeral", "owner": "operator"}])

    assert candidate.exists()
    assert result["preserved_reasons"] == {"unknown_artifact": 1}


def test_lsof_stderr_is_probe_error(monkeypatch) -> None:
    class Result:
        returncode = 1
        stdout = ""
        stderr = "permission denied"

    monkeypatch.setattr(disk_cleanup.subprocess, "run", lambda *args, **kwargs: Result())
    assert disk_cleanup._default_lsof(Path("/tmp/unknown")) == "probe-error"


def test_cli_candidate_is_rejected(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "disk_cleanup.py"
    result = subprocess.run(
        [sys.executable, str(script), "--home", str(tmp_path), "--candidate", str(tmp_path / "important")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--candidate is disabled" in result.stderr or "--candidate is disabled" in result.stdout


def test_lock_is_atomic(tmp_path: Path) -> None:
    first = HostDiskGovernor(home=tmp_path, state_dir=tmp_path / "state")
    second = HostDiskGovernor(home=tmp_path, state_dir=tmp_path / "state")
    assert first.acquire_lock()
    assert not second.acquire_lock()
    first.release_lock()


def test_launchd_is_five_minutes_and_single_owner() -> None:
    plist = Path(__file__).parents[1] / "launchd" / "ai.anicca.life-manager-disk-cleanup.plist"
    text = plist.read_text()
    assert "<integer>300</integer>" in text
    assert "disk_cleanup.py" in text


def test_legacy_hourly_trigger_delegates_to_the_same_host_guard() -> None:
    script = Path(__file__).parents[1] / "legacy-disk-janitor.sh"
    text = script.read_text()
    assert "EMERGENCY_GUARD_FULL_PASS=1" in text
    assert "disk_cleanup.py" in text


def test_run_once_records_inventory_summary(tmp_path: Path, monkeypatch) -> None:
    def fake_inventory(**_kwargs):
        return {"coverage": {"mount_count": 1, "root_count": 2, "gaps": ["size-deferred"]}}

    monkeypatch.setattr(disk_cleanup, "collect_host_inventory", fake_inventory)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=tmp_path / "state",
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (12 * GiB, 100 * GiB),
    )

    result = governor.run_once()

    assert result["inventory_mode"] == "full"
    assert (tmp_path / "state" / "host-inventory-full.at").exists()
    assert result["inventory_mounts"] == 1
    assert result["inventory_roots"] == 2
    assert result["inventory_gaps"] == 1
    receipt = json.loads((tmp_path / "state" / "last-receipt.json").read_text())
    assert receipt["inventory_roots"] == 2
