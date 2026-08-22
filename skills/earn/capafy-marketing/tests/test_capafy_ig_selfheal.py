from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
LABELS = [
    "ai.anicca.capafy-goal-monitor",
    "ai.anicca.capafy-goal-monitor-hourly",
    "ai.anicca.capafy-goal-monitor-daily-close",
    "ai.anicca.capafy-loop-daily",
    "ai.anicca.capafy-loop-healthcheck",
    "ai.anicca.capafy-outcome-monitor",
    "ai.anicca.capafy-ig-account-manager",
]


def run_selfheal(
    tmp_path: Path,
    missing_hourly: bool = False,
    fail_bootstrap: bool = False,
    launchd_test: bool = True,
):
    repo = tmp_path / "repo"
    target = repo / "skills/earn/capafy-marketing"
    target.mkdir(parents=True)
    shutil.copy2(SCRIPT, target / SCRIPT.name)
    home = tmp_path / "home"
    launchagents = home / "Library/LaunchAgents"
    launchagents.mkdir(parents=True)
    state = tmp_path / "loaded"
    state.mkdir()
    for label in LABELS:
        (launchagents / f"{label}.plist").write_text("plist")
        if not missing_hourly or label != "ai.anicca.capafy-goal-monitor-hourly":
            (state / label).touch()
    calls = tmp_path / "calls.log"
    safe = tmp_path / "launchctl-safe"
    safe.write_text(
        "#!/bin/sh\n"
        f"echo \"$*\" >> '{calls}'\n"
        "case \"$1\" in\n"
        " print) label=${2##*/}; [ -f \"$STATE/$label\" ] || exit 1 ;;\n"
        f" bootstrap) {'exit 1' if fail_bootstrap else 'label=$(basename \"$3\" .plist); mkdir -p \"$STATE\"; touch \"$STATE/$label\"'} ;;\n"
        " kickstart) ;;\n"
        " preflight) ;;\n"
        "esac\n",
    )
    safe.chmod(0o755)
    env = os.environ | {
        "HOME": str(home), "LIFE_MANAGER_REPO": str(repo),
        "CAPAFY_LAUNCHCTL_SAFE": str(safe), "CAPAFY_LAUNCHCTL_DOMAIN": "gui/501",
        "STATE": str(state),
    }
    if launchd_test:
        env["CAPAFY_IG_MARKETING_SELFHEAL_TEST"] = "1"
    result = subprocess.run(
        ["bash", str(target / SCRIPT.name)],
        env=env, text=True, capture_output=True, check=False,
    )
    return result, calls.read_text().splitlines() if calls.exists() else []


def test_all_present_prints_only(tmp_path: Path):
    result, calls = run_selfheal(tmp_path)
    assert result.returncode == 0
    assert all(call.startswith("print ") for call in calls)


def test_missing_hourly_bootstraps_and_kickstarts_only_hourly(tmp_path: Path):
    result, calls = run_selfheal(tmp_path, missing_hourly=True)
    assert result.returncode == 0
    assert any(call.startswith("preflight") for call in calls)
    assert any("bootstrap gui/501" in call for call in calls)
    assert calls[-1] == "kickstart gui/501/ai.anicca.capafy-goal-monitor-hourly"


def test_bootstrap_failure_stops_before_marketing(tmp_path: Path):
    result, calls = run_selfheal(tmp_path, missing_hourly=True, fail_bootstrap=True, launchd_test=False)
    assert result.returncode == 2
    assert not any("metrics" in call or "run_agent" in call for call in calls)


def test_production_mode_runs_selfheal_before_account_and_metrics(tmp_path: Path):
    result, calls = run_selfheal(tmp_path, launchd_test=False)
    assert calls and all(call.startswith("print ") for call in calls)
    assert result.returncode != 0
