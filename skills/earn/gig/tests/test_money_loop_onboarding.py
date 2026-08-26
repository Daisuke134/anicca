"""Isolated-home tests for the open-source Gig money-loop onboarding."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


GIG_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = GIG_ROOT.parents[2]
SCRIPT = GIG_ROOT / "scripts" / "money_loop_onboarding.py"
INSTALLER = GIG_ROOT / "install.sh"
if str(SCRIPT.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT.parent))


def _load_module():
    name = "gig_money_loop_onboarding_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


onboarding = _load_module()


def _args() -> list[str]:
    return [
        "--owner-id", "local-owner",
        "--providers", "upwork,fiverr",
        "--minimum-margin-bps", "2500",
        "--spend-cap-minor", "5000",
        "--concurrent-job-cap", "3",
        "--human-minute-value-minor", "75",
    ]


def test_isolated_install_is_private_read_only_and_never_writes_checkout(tmp_path: Path):
    home = tmp_path / "fresh-home"
    home.mkdir()
    before = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=REPO_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout
    env = {
        **os.environ,
        "HOME": str(home),
        "UPWORK_PASSWORD": "SECRET-MUST-NOT-LEAK",
        "CUSTOMER_MESSAGE": "CUSTOMER-DATA-MUST-NOT-LEAK",
        "LIFE_MANAGER_INSTALL_DAEMON": "0",
    }

    result = subprocess.run(
        ["bash", str(INSTALLER), *_args()], cwd=REPO_ROOT, env=env,
        capture_output=True, text=True,
    )

    assert result.returncode == 0, result.stderr
    after = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=REPO_ROOT,
        check=True, capture_output=True, text=True,
    ).stdout
    assert after == before
    config = home / ".config" / "anicca" / "gig"
    expected = {
        "owner-profile.json", "authorization-matrix.json", "authorizations.json",
        "capability-inventory.json", "onboarding-receipt.json",
    }
    assert {path.name for path in config.iterdir()} == expected
    assert stat.S_IMODE(config.stat().st_mode) == 0o700
    for name in expected:
        assert stat.S_IMODE((config / name).stat().st_mode) == 0o600
    for provider in ("upwork", "fiverr"):
        profile = home / ".cloak" / "profiles" / f"gig-{provider}"
        assert profile.is_dir()
        assert stat.S_IMODE(profile.stat().st_mode) == 0o700

    private_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in config.iterdir() if path.is_file()
    )
    assert "SECRET-MUST-NOT-LEAK" not in private_text
    assert "CUSTOMER-DATA-MUST-NOT-LEAK" not in private_text
    assert "/Users/anicca" not in private_text
    receipt = json.loads((config / "onboarding-receipt.json").read_text())
    assert receipt["probe_mode"] == "read_only"
    assert receipt["marketplace_mutations"] == 0


def test_selection_is_explicit_and_every_action_defaults_unknown(tmp_path: Path):
    receipt = onboarding.onboard(
        owner_id="owner-2", providers=["upwork"], minimum_margin_bps=2000,
        spend_cap_minor=0, concurrent_job_cap=1,
        human_minute_value_minor=0, home=tmp_path, repo_root=REPO_ROOT,
        observed_at="2026-08-22T10:00:00+00:00",
    )

    matrix = json.loads(
        (tmp_path / ".config/anicca/gig/authorization-matrix.json").read_text()
    )
    assert set(matrix["providers"]) == {"upwork"}
    assert matrix["providers"]["upwork"]["default_state"] == "unknown"
    assert matrix["providers"]["upwork"]["actions"]
    assert set(matrix["providers"]["upwork"]["actions"].values()) == {"unknown"}
    assert receipt["selected_providers"] == ["upwork"]
    inventory = json.loads(
        (tmp_path / ".config/anicca/gig/capability-inventory.json").read_text()
    )
    assert inventory["probe_mode"] == "read_only"
    assert inventory["skills"]


def test_onboarding_omits_legacy_connects_cap_from_owner_profile(tmp_path: Path):
    onboarding.onboard(
        owner_id="owner-no-connects-cap", providers=["upwork"],
        minimum_margin_bps=2000, spend_cap_minor=0, concurrent_job_cap=1,
        human_minute_value_minor=0, home=tmp_path, repo_root=REPO_ROOT,
        observed_at="2026-08-22T10:00:00+00:00",
    )

    profile = json.loads(
        (tmp_path / ".config/anicca/gig/owner-profile.json").read_text()
    )
    assert "connects_cap" not in profile["bounds"]


def test_existing_private_authorization_receipts_are_preserved(tmp_path: Path):
    config = tmp_path / ".config/anicca/gig"
    config.mkdir(parents=True)
    authorization = config / "authorizations.json"
    original = (
        '{"version":1,"receipts":[{"provider":"upwork","account":"owner-account",'
        '"action":"discover","transport":"official_api","state":"approved_api",'
        '"jurisdiction":"JP","terms_version":"special-approval-v1",'
        f'"evidence_hash":"{"d" * 64}","issued_at":"2026-08-01T00:00:00+00:00",'
        '"expires_at":"2027-08-01T00:00:00+00:00"}]}\n'
    )
    authorization.write_text(original, encoding="utf-8")
    authorization.chmod(0o600)

    onboarding.onboard(
        owner_id="owner-5", providers=["upwork"], minimum_margin_bps=2000,
        spend_cap_minor=0, concurrent_job_cap=1,
        human_minute_value_minor=0, home=tmp_path, repo_root=REPO_ROOT,
        observed_at="2026-08-22T10:00:00+00:00",
    )

    assert authorization.read_text(encoding="utf-8") == original


def test_malformed_existing_authorization_store_fails_before_onboarding(tmp_path: Path):
    config = tmp_path / ".config/anicca/gig"
    config.mkdir(parents=True)
    authorization = config / "authorizations.json"
    authorization.write_text('{"version":2,"receipts":[]}\n', encoding="utf-8")
    authorization.chmod(0o600)

    with pytest.raises(ValueError, match="unsupported_store_version"):
        onboarding.onboard(
            owner_id="owner-6", providers=["upwork"], minimum_margin_bps=2000,
            spend_cap_minor=0, concurrent_job_cap=1,
            human_minute_value_minor=0, home=tmp_path, repo_root=REPO_ROOT,
            observed_at="2026-08-22T10:00:00+00:00",
        )
    assert not (config / "owner-profile.json").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("minimum_margin_bps", -1),
        ("minimum_margin_bps", "twenty"),
        ("spend_cap_minor", -1),
        ("concurrent_job_cap", -2),
        ("human_minute_value_minor", "free"),
    ],
)
def test_negative_or_non_numeric_bounds_are_rejected(
    tmp_path: Path, field: str, value: object,
):
    values: dict[str, object] = {
        "minimum_margin_bps": 2000,
        "spend_cap_minor": 5000,
        "concurrent_job_cap": 3,
        "human_minute_value_minor": 75,
    }
    values[field] = value
    with pytest.raises(ValueError, match=field):
        onboarding.onboard(
            owner_id="owner-3", providers=["upwork"], home=tmp_path,
            repo_root=REPO_ROOT, observed_at="2026-08-22T10:00:00+00:00",
            **values,
        )


@pytest.mark.parametrize("providers", [[], ["unknown-market"], ["upwork", "upwork"]])
def test_missing_unknown_or_duplicate_provider_selection_is_rejected(
    tmp_path: Path, providers: list[str],
):
    with pytest.raises(ValueError, match="providers"):
        onboarding.onboard(
            owner_id="owner-4", providers=providers, minimum_margin_bps=2000,
            spend_cap_minor=0, concurrent_job_cap=1,
            human_minute_value_minor=0, home=tmp_path, repo_root=REPO_ROOT,
            observed_at="2026-08-22T10:00:00+00:00",
        )
