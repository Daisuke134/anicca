import os
import subprocess
from pathlib import Path


REPLIER = Path(__file__).resolve().parent / "replier.ts"


def test_replier_default_adapter_is_release_relative(tmp_path):
    database = tmp_path / "agentmail.db"
    database.touch()
    result = subprocess.run(
        ["node", str(REPLIER)],
        env={
            **os.environ,
            "HOME": str(tmp_path),
            "DEEPSEEK_API_KEY": "test-only",
            "AGENTMAIL_DB_PATH": str(database),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "spec-12 adapter not found" not in result.stderr
