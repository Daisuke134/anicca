import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parent / "bounty-healthcheck.sh"


def test_stale_heartbeat_is_reported_without_launchd_recovery(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    marker = tmp_path / "mutation"
    result = subprocess.run(
        ["/bin/bash", str(SCRIPT)],
        env={
            **os.environ,
            "HOME": str(home),
            "BASH_FUNC_launchctl%%": f'() {{ printf x >> "{marker}"; return 0; }}',
            "BASH_FUNC_tmux%%": "() { return 1; }",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert not marker.exists()
    assert "stale/missing" in (
        home / ".openclaw/logs/bounty-core-healthcheck.log"
    ).read_text()
