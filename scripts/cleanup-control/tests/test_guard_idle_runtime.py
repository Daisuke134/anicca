from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[3]
GUARD = ROOT / "scripts" / "emergency-disk-guard.sh"


def test_guard_stops_idle_colima_before_pressure_sweep(tmp_path: Path) -> None:
    home = tmp_path / "home"
    state = home / ".openclaw" / "state"
    state.mkdir(parents=True)
    calls = tmp_path / "colima-calls.txt"

    fake_colima = tmp_path / "colima"
    fake_colima.write_text(
        """#!/bin/bash
set -u
if [ "$1" = status ]; then
  exit 0
fi
if [ "$1" = stop ]; then
  printf 'stop\\n' >> "$CALLS"
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    fake_colima.chmod(0o755)

    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        """#!/bin/bash
set -u
if [ "$1" = ps ] && [ "$2" = -aq ]; then
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        {
            "CALLS": str(calls),
            "EMERGENCY_GUARD_TEST_HOME": str(home),
            "EMERGENCY_GUARD_TEST_FREE_GB": "4",
            "EMERGENCY_GUARD_COLIMA_BIN": str(fake_colima),
            "EMERGENCY_GUARD_DOCKER_BIN": str(fake_docker),
            "CLEANUP_CONTROL_PATH": str(tmp_path / "missing-cleanup-control.py"),
        }
    )

    result = subprocess.run(
        ["/bin/bash", str(GUARD)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    assert calls.read_text(encoding="utf-8").splitlines() == ["stop"]


def test_guard_prunes_only_unreferenced_docker_images_and_trims_vm(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    state = home / ".openclaw" / "state"
    state.mkdir(parents=True)
    calls = tmp_path / "runtime-calls.txt"

    fake_colima = tmp_path / "colima"
    fake_colima.write_text(
        """#!/bin/bash
set -u
if [ "$1" = status ]; then
  exit 0
fi
printf 'colima %s\\n' "$*" >> "$CALLS"
exit 0
""",
        encoding="utf-8",
    )
    fake_colima.chmod(0o755)

    fake_docker = tmp_path / "docker"
    fake_docker.write_text(
        """#!/bin/bash
set -u
if [ "$1" = ps ] && [ "$2" = -aq ]; then
  printf 'running-container\\n'
  exit 0
fi
printf 'docker %s\\n' "$*" >> "$CALLS"
exit 0
""",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        {
            "CALLS": str(calls),
            "EMERGENCY_GUARD_TEST_HOME": str(home),
            "EMERGENCY_GUARD_TEST_FREE_GB": "4",
            "EMERGENCY_GUARD_COLIMA_BIN": str(fake_colima),
            "EMERGENCY_GUARD_DOCKER_BIN": str(fake_docker),
            "CLEANUP_CONTROL_PATH": str(tmp_path / "missing-cleanup-control.py"),
        }
    )

    result = subprocess.run(
        ["/bin/bash", str(GUARD)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    recorded = calls.read_text(encoding="utf-8").splitlines()
    assert recorded == [
        "docker image prune -f",
        "colima ssh -- sudo fstrim -a",
    ]
    assert all("volume" not in call and "system prune" not in call for call in recorded)
