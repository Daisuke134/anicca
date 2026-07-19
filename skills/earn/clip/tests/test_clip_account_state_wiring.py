import json
import os
from pathlib import Path
import subprocess
import tempfile


CLIP_DIR = Path(__file__).resolve().parents[1]
ENGINE_DIR = CLIP_DIR.parent / "marketing-engine"
CLIP_PASS = CLIP_DIR / "clip_pass.sh"
CLIP_DAILY = CLIP_DIR / "clip_daily.sh"
ACCOUNT_STATE = ENGINE_DIR / "account_state.sh"


def run_account_state(command: str, accounts: list[dict]) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "clip-accounts.json"
        state_file.write_text(json.dumps(accounts))
        env = os.environ.copy()
        env["IG_ACCOUNT_STATE_PYTHON"] = os.environ.get("PYTHON", "python3")
        result = subprocess.run(
            ["bash", "-c", f'. "{ACCOUNT_STATE}"; {command} "$1"', "bash", str(state_file)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return result.stdout.strip()


def test_active_handle_resolves_from_fixture_and_empty_state_skips():
    accounts = [
        {"handle": "retired", "status": "poisoned_manual_backup"},
        {"handle": "active_day1", "status": "warming_day1"},
    ]
    assert run_account_state("resolve_ig_handle", accounts) == "active_day1"
    assert run_account_state("resolve_ig_handle", []) == ""


def test_warming_day1_is_counted_as_usable_but_poisoned_is_not():
    accounts = [
        {"handle": "day1", "status": "warming_day1"},
        {"handle": "warm", "status": "warming"},
        {"handle": "ready", "status": "ready"},
        {"handle": "bad", "status": "ready", "poisoned_at": "2026-07-19"},
        {"handle": "bad_status", "status": "ready_poisoned"},
        {"handle": "failed", "status": "provision_failed"},
    ]
    assert run_account_state("count_ig_usable_accounts", accounts) == "3"


def test_clip_pass_bio_uses_engine_resolver_not_retired_hardcode():
    source = CLIP_PASS.read_text()
    assert '. "$MARKETING_ENGINE_DIR/account_state.sh"' in source
    assert 'resolve_ig_handle "$CLIP_ACCTS"' in source
    assert "--handle aiclipsvault" not in source
    assert 'BIO: skip — no active handle' in source


def test_both_clip_loops_use_shared_usable_counter():
    for script in (CLIP_PASS, CLIP_DAILY):
        source = script.read_text()
        assert 'count_ig_usable_accounts "$CLIP_ACCTS"' in source
