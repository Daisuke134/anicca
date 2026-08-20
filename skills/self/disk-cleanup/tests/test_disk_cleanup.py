import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

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


def test_closed_regenerable_artifact_is_reclaimed(tmp_path: Path) -> None:
    state = tmp_path / "state"
    candidate = tmp_path / "tmp" / "cfo-complete"
    candidate.mkdir(parents=True)
    (candidate / "payload").write_bytes(b"x" * 64)
    governor = HostDiskGovernor(
        home=tmp_path,
        state_dir=state,
        lsof=lambda _path: "confirmed-closed",
        usage=lambda: (0, 1),
    )

    result = governor.sweep([{"path": candidate, "class": "ephemeral", "owner": "cfo"}])

    assert result["reclaimed"] > 0
    assert not candidate.exists()
    receipt = json.loads((state / "last-receipt.json").read_text())
    assert receipt["protected_deletions"] == 0


def test_open_or_protected_artifact_is_preserved(tmp_path: Path) -> None:
    state = tmp_path / "state"
    open_candidate = tmp_path / "tmp" / "open"
    open_candidate.mkdir(parents=True)
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
            {"path": open_candidate, "class": "ephemeral", "owner": "browser"},
            {"path": protected, "class": "ephemeral", "owner": "unknown"},
        ]
    )

    assert result["reclaimed"] == 0
    assert open_candidate.exists()
    assert protected.exists()
    assert result["preserved"] == 2
    assert result["protected_deletions"] == 0


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
