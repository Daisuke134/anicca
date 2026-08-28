import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).resolve().parent / "run.sh"


def _run(tmp_path, free_kib: int, curl_exit: int):
    home = tmp_path / "home"
    home.mkdir()
    calls = tmp_path / "lm-loop.calls"
    cli = tmp_path / "lm-loop"
    cli.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{calls}"\n')
    cli.chmod(0o755)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(f"#!/bin/sh\nexit {curl_exit}\n")
    curl.chmod(0o755)
    df_function = (
        '() { printf "Filesystem 1024-blocks Used Available Capacity Mounted on\\n'
        f'disk 1 1 {free_kib} 1% /\\n"; }}'
    )
    result = subprocess.run(
        ["/bin/bash", str(SCRIPT)],
        env={
            **os.environ,
            "HOME": str(home),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "LIFE_MANAGER_REPO": str(ROOT),
            "LIFE_MANAGER_LOOP_CLI": str(cli),
            "BASH_FUNC_df%%": df_function,
            "BASH_FUNC_sleep%%": "() { :; }",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return result, calls


def test_low_disk_requests_cleanup_through_lm_loop(tmp_path):
    result, calls = _run(tmp_path, free_kib=1, curl_exit=0)
    assert result.returncode == 75
    assert calls.read_text().strip() == "restart life-manager-disk-cleanup"


def test_unavailable_cdp_restarts_registered_owner_through_lm_loop(tmp_path):
    result, calls = _run(tmp_path, free_kib=4 * 1024 * 1024, curl_exit=1)
    assert result.returncode == 75
    assert calls.read_text().strip() == "restart life-manager-daily-driver"
