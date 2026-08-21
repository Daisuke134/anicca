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
