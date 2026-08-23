import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)


def run_money_entrypoint(tmp_path: Path, runner_rc: int) -> subprocess.CompletedProcess:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    script = repo / "skills/self/capafy-loop/capafy-loop-daily.sh"
    script.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "skills/self/capafy-loop/capafy-loop-daily.sh", script)
    write_executable(
        repo / "skills/earn/marketing-engine/run_agent.sh",
        f"#!/usr/bin/env bash\ncat >/dev/null\nexit {runner_rc}\n",
    )
    return subprocess.run(
        ["bash", str(script)],
        env=os.environ | {"HOME": str(home), "LIFE_MANAGER_REPO": str(repo)},
        text=True,
        capture_output=True,
        check=False,
    )


def run_ig_entrypoint(
    tmp_path: Path,
    runner_rc: int,
    *,
    recent_rotation: bool = False,
    invalid_rotation: bool = False,
    warm_day: str = "3",
) -> subprocess.CompletedProcess:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    marketing = repo / "skills/earn/capafy-marketing"
    script = marketing / "capafy-ig-marketing-daily.sh"
    marketing.mkdir(parents=True)
    shutil.copy2(ROOT / "skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh", script)
    accounts = tmp_path / "accounts.json"
    accounts.write_text("[]\n")
    write_executable(
        marketing / "account_state.sh",
        f'''#!/usr/bin/env bash
capafy_ig_accounts_file() {{ printf '%s\\n' '{accounts}'; }}
resolve_capafy_ig_handle() {{ printf '%s\\n' 'capafy.fixture'; }}
resolve_capafy_ig_port() {{ printf '%s\\n' '9332'; }}
resolve_capafy_ig_started_warming() {{ printf '%s\\n' '2020-01-01'; }}
capafy_ig_provision_reason() {{ printf '%s' ''; }}
capafy_ig_warming_day() {{ printf '%s\\n' '{warm_day}'; }}
''',
    )
    write_executable(
        repo / "skills/earn/marketing-engine/provision_prompt.sh",
        "#!/usr/bin/env bash\nrender_ig_provision_prompt() { printf '%s\\n' fixture; }\n",
    )
    write_executable(
        repo / "skills/earn/marketing-engine/load_manifest.sh",
        "#!/usr/bin/env bash\nme_load_manifest() { return 0; }\n",
    )
    write_executable(
        repo / "skills/earn/marketing-engine/run_agent.sh",
        f"#!/usr/bin/env bash\ncat >/dev/null\nexit {runner_rc}\n",
    )
    scripts = marketing / "scripts"
    for name in ("ig_metrics.py", "pull_attribution.py"):
        write_executable(scripts / name, "#!/usr/bin/env python3\n")
    write_executable(scripts / "build_landing.py", "#!/usr/bin/env python3\nraise SystemExit(1)\n")
    if recent_rotation:
        rotation = home / ".local/state/life-manager/state/capafy-marketing-rotation.jsonl"
        rotation.parent.mkdir(parents=True, exist_ok=True)
        rotation.write_text(f'{{"platform":"ig","ts":{int(time.time())}}}\n')
    elif invalid_rotation:
        rotation = home / ".local/state/life-manager/state/capafy-marketing-rotation.jsonl"
        rotation.parent.mkdir(parents=True, exist_ok=True)
        rotation.write_text('{"platform":\n')
    return subprocess.run(
        ["bash", str(script)],
        env=os.environ
        | {
            "HOME": str(home),
            "LIFE_MANAGER_REPO": str(repo),
            "TELEGRAM_ALERT_CHAT_ID": "fixture-chat",
        },
        text=True,
        capture_output=True,
        check=False,
    )


def test_money_child_failure_propagates_without_heartbeat(tmp_path: Path):
    result = run_money_entrypoint(tmp_path, 17)
    marker = tmp_path / "home/.local/state/life-manager/state/.capafy-loop-last-pass"
    assert result.returncode == 17
    assert not marker.exists()


def test_money_success_writes_heartbeat(tmp_path: Path):
    result = run_money_entrypoint(tmp_path, 0)
    marker = tmp_path / "home/.local/state/life-manager/state/.capafy-loop-last-pass"
    assert result.returncode == 0
    assert marker.is_file()


def test_ig_child_failure_propagates_without_heartbeat(tmp_path: Path):
    result = run_ig_entrypoint(tmp_path, 23)
    marker = tmp_path / "home/.local/state/life-manager/state/.capafy-ig-marketing-last-pass"
    assert result.returncode == 23
    assert not marker.exists()


def test_ig_success_and_cadence_noop_are_terminal(tmp_path: Path):
    success = run_ig_entrypoint(tmp_path / "success", 0)
    success_marker = tmp_path / "success/home/.local/state/life-manager/state/.capafy-ig-marketing-last-pass"
    noop = run_ig_entrypoint(tmp_path / "noop", 99, recent_rotation=True)
    noop_marker = tmp_path / "noop/home/.local/state/life-manager/state/.capafy-ig-marketing-last-pass"
    assert success.returncode == 0
    assert success_marker.is_file()
    assert noop.returncode == 0
    assert noop_marker.is_file()


def test_ig_refuses_to_run_when_warmup_or_cadence_state_is_unreadable(tmp_path: Path):
    warmup = run_ig_entrypoint(tmp_path / "warmup", 0, warm_day="")
    cadence = run_ig_entrypoint(tmp_path / "cadence", 0, invalid_rotation=True)
    assert warmup.returncode == 2
    assert cadence.returncode == 2


def test_ig_private_telegram_aliases_precede_provision_prompt() -> None:
    script = (ROOT / "skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh").read_text()
    alert_alias = script.index('export TELEGRAM_ALERT_CHAT_ID="$LM_TELEGRAM_ALERT_CHAT_ID"')
    bot_alias = script.index('export TELEGRAM_BOT_TOKEN="$LM_TELEGRAM_BOT_TOKEN"')
    provision_prompt = script.index("PROVISION_PROMPT=\"$(")
    assert alert_alias < provision_prompt
    assert bot_alias < provision_prompt
