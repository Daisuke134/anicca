from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import disk_cleanup  # noqa: E402


def test_default_bootstrap_health_does_not_skip_alternate_home_on_macos(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(disk_cleanup.sys, "platform", "darwin")

    def fake_run(argv: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if argv[0].endswith("/dscl"):
            output = f"UniqueID: {os.getuid()}\nNFSHomeDirectory: {tmp_path}\n"
        else:
            output = "service = ai.anicca.life-manager-disk-cleanup\n"
        return subprocess.CompletedProcess(argv, 0, output, "")

    monkeypatch.setattr(disk_cleanup.subprocess, "run", fake_run)

    result = disk_cleanup._default_bootstrap_health(tmp_path, tmp_path / "state")

    assert result["status"] == "ok"
    assert calls[0][:3] == ["/usr/bin/dscl", ".", "-read"]
    assert calls[1] == [
        "/bin/launchctl",
        "print",
        f"gui/{os.getuid()}/ai.anicca.life-manager-disk-cleanup",
    ]


def test_cleanup_label_load_readback_is_required(tmp_path: Path, monkeypatch) -> None:
    launchctl_statuses = iter((113, 0))
    launchctl_calls: list[list[str]] = []
    monkeypatch.setattr(disk_cleanup.sys, "platform", "darwin")
    monkeypatch.setattr(
        disk_cleanup.os,
        "kill",
        lambda *_args: (_ for _ in ()).throw(AssertionError("cleanup must not kill app-server")),
    )

    def fake_run(argv: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        if argv[0] == "/usr/bin/dscl":
            stdout = f"UniqueID: {os.getuid()}\nNFSHomeDirectory: {tmp_path}\n"
            return subprocess.CompletedProcess(argv, 0, stdout, "")
        launchctl_calls.append(argv)
        status = next(launchctl_statuses)
        return subprocess.CompletedProcess(argv, status, "service = canonical\n" if status == 0 else "", "")

    monkeypatch.setattr(disk_cleanup.subprocess, "run", fake_run)

    missing = disk_cleanup._default_bootstrap_health(tmp_path, tmp_path / "state")
    restored = disk_cleanup._default_bootstrap_health(tmp_path, tmp_path / "state")

    target = [
        "/bin/launchctl",
        "print",
        f"gui/{os.getuid()}/ai.anicca.life-manager-disk-cleanup",
    ]
    assert missing["status"] == "failure"
    assert missing["error_code"] == "launchctl-113"
    assert restored["status"] == "ok"
    assert launchctl_calls == [target, target]
