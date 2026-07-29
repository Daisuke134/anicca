from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[3]
SCRIPT = ROOT / "scripts" / "colima-autostart.sh"


def _fake_colima(tmp_path: Path) -> Path:
    executable = tmp_path / "colima"
    executable.write_text(
        """#!/usr/bin/env bash
echo "$*" >> "$COLIMA_CALLS"
if [ "$1" = status ]; then
  exit "${COLIMA_STATUS_RC:-1}"
fi
exit 0
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def test_disk_pressure_prevents_colima_probe_and_start(tmp_path: Path) -> None:
    pressure = tmp_path / "disk-pressure.block"
    pressure.touch()
    calls = tmp_path / "calls"
    log = tmp_path / "autostart.log"
    environment = os.environ.copy()
    environment.update({
        "COLIMA_AUTOSTART_BIN": str(_fake_colima(tmp_path)),
        "COLIMA_AUTOSTART_DISK_PRESSURE_FLAG": str(pressure),
        "COLIMA_AUTOSTART_LOG": str(log),
        "COLIMA_CALLS": str(calls),
    })

    result = subprocess.run(
        ["/bin/bash", str(SCRIPT)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert not calls.exists()
    assert "disk pressure active — preserving stopped runtime" in log.read_text(
        encoding="utf-8"
    )


def test_healthy_disk_still_starts_a_stopped_colima(tmp_path: Path) -> None:
    calls = tmp_path / "calls"
    log = tmp_path / "autostart.log"
    environment = os.environ.copy()
    environment.update({
        "COLIMA_AUTOSTART_BIN": str(_fake_colima(tmp_path)),
        "COLIMA_AUTOSTART_DISK_PRESSURE_FLAG": str(tmp_path / "absent"),
        "COLIMA_AUTOSTART_LOG": str(log),
        "COLIMA_CALLS": str(calls),
        "COLIMA_STATUS_RC": "1",
    })

    result = subprocess.run(
        ["/bin/bash", str(SCRIPT)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert calls.read_text(encoding="utf-8").splitlines() == ["status", "start"]
