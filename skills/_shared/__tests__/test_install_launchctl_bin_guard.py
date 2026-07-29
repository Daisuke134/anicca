"""FIND-2-001 fix verify: LAUNCHCTL_BIN override is path-restricted to a temp
root and logs to stderr when active. Reject unmanaged system/user bin folders.
(any production-looking path)."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="install-proactive-plist is Darwin-only",
)

SHARED_DIR = Path(__file__).resolve().parent.parent
INSTALL_SH = SHARED_DIR / "install-proactive-plist.sh"


def _make_executable(path: Path, body: str = "#!/bin/bash\nexit 0\n") -> None:
    path.write_text(body)
    path.chmod(0o755)


def test_override_rejected_when_outside_temp_root(tmp_path):
    """A LAUNCHCTL_BIN that resolves OUTSIDE /tmp|/private/tmp|/private/var/folders|
    $TMPDIR must be rejected with exit 9 before any side-effect."""
    # Pick a clearly-not-temp location: a subdir of $HOME.
    not_temp = Path.home() / ".cache" / "ipl-guard-test"
    not_temp.mkdir(parents=True, exist_ok=True)
    fake = not_temp / "launchctl"
    _make_executable(fake)
    try:
        env = {**os.environ, "LAUNCHCTL_BIN": str(fake)}
        r = subprocess.run(
            ["bash", str(INSTALL_SH), "probeguard"],
            capture_output=True, text=True, timeout=10, env=env,
        )
        assert r.returncode == 9
        assert "must resolve under a temp root" in r.stderr
    finally:
        fake.unlink(missing_ok=True)


def test_override_logs_to_stderr_when_in_tempdir(tmp_path):
    fake = tmp_path / "launchctl"
    # Make the fake unconditionally succeed so install.sh proceeds past it.
    _make_executable(fake, "#!/bin/bash\ncase \"$1\" in print) exit 0;; *) exit 0;; esac\n")
    slot = f"probe-log-{os.getpid()}"
    env = {**os.environ, "LAUNCHCTL_BIN": str(fake)}
    r = subprocess.run(["bash", str(INSTALL_SH), slot],
                       capture_output=True, text=True, timeout=10, env=env)
    # Should at least reach the override-active log line.
    assert "LAUNCHCTL_BIN override active (test mode)" in r.stderr
    # cleanup — disk plist may have been written by the always-succeed fake
    plist = Path.home() / "Library" / "LaunchAgents" / f"ai.anicca.{slot}-proactive.plist"
    plist.unlink(missing_ok=True)


def test_override_rejected_when_not_executable(tmp_path):
    fake = tmp_path / "launchctl"
    fake.write_text("not executable")
    # Note: NO chmod +x
    env = {**os.environ, "LAUNCHCTL_BIN": str(fake)}
    r = subprocess.run(["bash", str(INSTALL_SH), "probe"],
                       capture_output=True, text=True, timeout=10, env=env)
    assert r.returncode == 9
    assert "not executable" in r.stderr
