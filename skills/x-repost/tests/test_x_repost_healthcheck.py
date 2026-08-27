import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[3]
SCRIPT = ROOT / "skills/x-repost/x-repost-healthcheck.sh"


def test_missing_plist_is_reported_without_recreating_launchagent(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    generator = tmp_path / "plistgen"
    generator.write_text(
        "#!/bin/sh\n"
        "while [ $# -gt 0 ]; do\n"
        "  if [ \"$1\" = --out-dir ]; then shift; out=$1; fi\n"
        "  shift\n"
        "done\n"
        "mkdir -p \"$out\"\n"
        "touch \"$out/ai.anicca.x-repost-pass.plist\"\n"
    )
    generator.chmod(0o755)
    result = subprocess.run(
        ["/bin/bash", str(SCRIPT)],
        env={**os.environ, "HOME": str(home), "PY": str(generator)},
        capture_output=True, text=True, check=False,
    )

    assert result.returncode != 0
    assert not (home / "Library/LaunchAgents/ai.anicca.x-repost-pass.plist").exists()
