import os
import shutil
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parent / "tunnel-watcher.sh"


def test_rotated_tunnel_restarts_phone_through_lm_loop(tmp_path):
    home = tmp_path / "home"
    state = home / ".openclaw/state"
    state.mkdir(parents=True)
    (state / "anicca_phone_url.txt").write_text("https://new.example\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text('#!/bin/sh\nprintf \'{"webhookUrl":"https://old.example"}\'\n')
    curl.chmod(0o755)
    calls = tmp_path / "lm-loop.calls"
    cli = tmp_path / "lm-loop"
    cli.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{calls}"\n')
    cli.chmod(0o755)
    raw = tmp_path / "launchctl.called"
    result = subprocess.run(
        [shutil.which("timeout") or "/opt/homebrew/bin/timeout", "2", "/bin/bash", str(SCRIPT)],
        env={
            **os.environ,
            "HOME": str(home),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "MR_BOT_LOOP_CLI": str(cli),
            "TUNNEL_WATCH_ONCE": "1",
            "TUNNEL_WATCH_SLEEP_SECONDS": "0",
            "BASH_FUNC_launchctl%%": f'() {{ touch "{raw}"; }}',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert calls.read_text().strip() == "restart phone-conversation"
    assert not raw.exists()
