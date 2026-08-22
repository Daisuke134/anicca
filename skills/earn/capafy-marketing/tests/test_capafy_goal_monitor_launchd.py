from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MONITOR = ROOT / "skills/earn/capafy-marketing/capafy-goal-monitor.sh"


def run_monitor(
    tmp_path: Path,
    print_output: str,
    *,
    bootout_stuck: bool = False,
    bootstrap_fail: bool = False,
    post_mismatch: bool = False,
    launchd_test: bool = True,
) -> tuple[subprocess.CompletedProcess, list[str]]:
    repo = tmp_path / "repo"
    marketing = repo / "skills/earn/capafy-marketing"
    marketing.mkdir(parents=True)
    shutil.copy2(MONITOR, marketing / MONITOR.name)
    (marketing / "account_state.sh").write_text(
        "capafy_ig_accounts_file(){ echo /tmp/accounts.json; }\n"
        "resolve_capafy_ig_handle(){ echo fixture; }\n"
        "resolve_capafy_ig_port(){ echo 9332; }\n"
        "resolve_capafy_ig_session_owner(){ echo browser; }\n"
        "resolve_capafy_ig_started_warming(){ echo 2020-01-01; }\n"
        "capafy_ig_warming_day(){ echo 3; }\n",
        encoding="utf-8",
    )
    safe = tmp_path / "launchctl-safe"
    calls = tmp_path / "calls.log"
    state = tmp_path / "state"
    (tmp_path / "home/Library/LaunchAgents").mkdir(parents=True)
    safe.write_text(
        "#!/bin/sh\n"
        f"echo \"$*\" >> '{calls}'\n"
        "mkdir -p \"$STATE\"\n"
        "case \"$1\" in\n"
        "  print) if [ -f \"$STATE/hourly\" ] && [ \"$POST_MISMATCH\" = 1 ]; then echo 'run interval = 7200 seconds'; elif [ -f \"$STATE/hourly\" ]; then echo 'run interval = 3600 seconds'; elif [ -f \"$STATE/bootout\" ] && [ \"$BOOTOUT_STUCK\" != 1 ]; then exit 1; else printf '%s\\n' \"$PRINT_OUTPUT\"; fi ;;\n"
        "  preflight) exit 0 ;;\n"
        "  bootout) touch \"$STATE/bootout\" ;;\n"
        "  bootstrap) [ \"$BOOTSTRAP_FAIL\" = 1 ] && exit 1; mkdir -p \"$STATE\"; touch \"$STATE/hourly\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    safe.chmod(0o755)
    env = os.environ | {
        "HOME": str(tmp_path / "home"),
        "LIFE_MANAGER_REPO": str(repo),
        "CAPAFY_LAUNCHCTL_SAFE": str(safe),
        "CAPAFY_LAUNCHCTL_DOMAIN": "gui/501",
        "STATE": str(state),
        "PRINT_OUTPUT": print_output,
        "BOOTOUT_STUCK": "1" if bootout_stuck else "0",
        "BOOTSTRAP_FAIL": "1" if bootstrap_fail else "0",
        "POST_MISMATCH": "1" if post_mismatch else "0",
        "CAPAFY_IG_UNLOAD_POLL_ATTEMPTS": "2",
        "CAPAFY_IG_UNLOAD_POLL_SLEEP": "0",
    }
    if launchd_test:
        env["CAPAFY_GOAL_MONITOR_LAUNCHD_TEST"] = "1"
    result = subprocess.run(["bash", str(marketing / MONITOR.name)], env=env, text=True, capture_output=True, check=False)
    return result, calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


def test_already_hourly_has_no_launchctl_mutation(tmp_path: Path) -> None:
    result, calls = run_monitor(tmp_path, "run interval = 3600 seconds")
    assert result.returncode == 0
    assert calls == ["print gui/501/ai.anicca.capafy-ig-marketing-daily"]


def test_calendar_mismatch_boots_out_and_bootstraps_exact_service(tmp_path: Path) -> None:
    result, calls = run_monitor(tmp_path, "run interval = 86400 seconds")
    assert result.returncode == 0
    assert calls[:3] == [
        "print gui/501/ai.anicca.capafy-ig-marketing-daily",
        "preflight",
        "bootout gui/501/ai.anicca.capafy-ig-marketing-daily",
    ]
    assert calls[3].startswith("print gui/501/ai.anicca.capafy-ig-marketing-daily")
    assert calls[4].startswith("bootstrap gui/501 ")
    assert calls[5] == "print gui/501/ai.anicca.capafy-ig-marketing-daily"


def test_bootout_wait_timeout_fails_closed(tmp_path: Path) -> None:
    result, _ = run_monitor(tmp_path, "run interval = 86400 seconds", bootout_stuck=True)
    assert result.returncode != 0


def test_bootstrap_failure_fails_closed(tmp_path: Path) -> None:
    result, _ = run_monitor(tmp_path, "run interval = 86400 seconds", bootstrap_fail=True)
    assert result.returncode != 0


def test_post_readback_interval_mismatch_fails_closed(tmp_path: Path) -> None:
    result, _ = run_monitor(tmp_path, "run interval = 86400 seconds", post_mismatch=True)
    assert result.returncode != 0


def test_full_goal_monitor_propagates_bootstrap_failure_before_healthy_continuation(tmp_path: Path) -> None:
    result, _ = run_monitor(
        tmp_path,
        "run interval = 86400 seconds",
        bootstrap_fail=True,
        launchd_test=False,
    )
    assert result.returncode == 2
