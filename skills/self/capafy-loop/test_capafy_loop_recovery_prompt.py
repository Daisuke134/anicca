import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).with_name("capafy-loop-daily.sh")


def test_recovery_probe_exposes_exact_target_and_profile_contract():
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env={
            **os.environ,
            "CAPAFY_LOOP_RECOVERY_PROBE_ONLY": "1",
            "CAPAFY_LOOP_REPORTING_PROBE_ONLY": "1",
        },
        capture_output=True,
        text=True,
        check=True,
    )

    assert "capafy_target_cdp.py" in result.stdout
    assert "exact temporary-link token" in result.stdout
    assert "OPENCLAW_CONFIG_PATH" in result.stdout
    assert "OPENCLAW_STATE_DIR" in result.stdout
    assert "same isolated profile root" in result.stdout
