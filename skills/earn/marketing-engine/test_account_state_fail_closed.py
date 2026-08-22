from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ACCOUNT_STATE = ROOT / "skills/earn/marketing-engine/account_state.sh"
IG_ENTRYPOINT = ROOT / "skills/earn/capafy-marketing/capafy-ig-marketing-daily.sh"
IG_ACCOUNT_STATE = ROOT / "skills/earn/capafy-marketing/account_state.sh"


def resolve_field(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f'source "{ACCOUNT_STATE}"; resolve_ig_account_field "$1" handle', "bash", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_shared_resolver_keeps_valid_empty_list_empty_but_rejects_malformed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("[]\n", encoding="utf-8")
    valid = resolve_field(empty)
    assert valid.returncode == 0
    assert valid.stdout == ""

    malformed = tmp_path / "malformed.json"
    malformed.write_text('{"accounts":\n', encoding="utf-8")
    invalid = resolve_field(malformed)
    assert invalid.returncode != 0


def test_existing_account_with_day_zero_stops_before_dry_or_live_work(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    marketing = repo / "skills/earn/capafy-marketing"
    engine = repo / "skills/earn/marketing-engine"
    browser_scripts = repo / "skills/browser/scripts"
    marketing.mkdir(parents=True)
    engine.mkdir(parents=True)
    browser_scripts.mkdir(parents=True)
    shutil.copy2(IG_ENTRYPOINT, marketing / IG_ENTRYPOINT.name)
    shutil.copy2(IG_ACCOUNT_STATE, marketing / "account_state.sh")
    shutil.copy2(ACCOUNT_STATE, engine / "account_state.sh")
    (engine / "provision_prompt.sh").write_text("render_ig_provision_prompt(){ :; }\n", encoding="utf-8")
    (engine / "load_manifest.sh").write_text("me_load_manifest(){ :; }\n", encoding="utf-8")
    accounts = tmp_path / "accounts.json"
    accounts.write_text(json.dumps([{
        "status": "ready",
        "handle": "existing",
        "port": "9332",
        "started_warming": "2999-01-01",
    }]), encoding="utf-8")
    (marketing / "scripts").mkdir()
    for name in ("ig_metrics.py", "pull_attribution.py"):
        (marketing / "scripts" / name).write_text("", encoding="utf-8")
    (marketing / "scripts" / "build_landing.py").write_text("raise SystemExit(1)\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(marketing / IG_ENTRYPOINT.name)],
        env=os.environ | {
            "HOME": str(tmp_path / "home"),
            "LIFE_MANAGER_REPO": str(repo),
            "CAPAFY_IG_ACCOUNTS_FILE": str(accounts),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
