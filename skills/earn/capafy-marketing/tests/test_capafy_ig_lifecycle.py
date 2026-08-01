import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
LIFECYCLE = SCRIPTS / "capafy_ig_lifecycle.py"
sys.path.insert(0, str(SCRIPTS))

from capafy_ig_lifecycle import (  # noqa: E402
    derive_snapshot,
    record_public_reel,
    retire_account,
)


def now(value="2026-08-02T10:00:00Z"):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def account(handle="capafy.new", created="2026-08-01", **overrides):
    value = {
        "handle": handle,
        "status": "warming",
        "session_owner": "browser",
        "created": created,
    }
    value.update(overrides)
    return value


def test_verified_browser_session_is_immediately_publish_probe_ready():
    old = account(created="2026-07-01")
    snapshot = derive_snapshot([old], {}, now())
    assert snapshot["status"] == "publish_probe_ready"
    assert snapshot["capability"] == "publish_probe"
    assert "warmup_successes" not in snapshot


def test_legacy_warmup_evidence_never_changes_immediate_capability():
    prior = {"warmup_successes": 7, "warmup_success_dates": ["2026-08-01"]}
    snapshot = derive_snapshot([account()], prior, now())
    assert snapshot["status"] == "publish_probe_ready"
    assert snapshot["capability"] == "publish_probe"


def test_reel_without_reach_waits_for_real_measurement():
    snapshot = derive_snapshot(
        [account()],
        {
            "handle": "capafy.new",
            "last_public_reel_url": "https://www.instagram.com/reel/ABC123/",
            "reach_healthy": False,
        },
        now(),
    )
    assert snapshot["status"] == "reach_observing"
    assert snapshot["capability"] == "none"


def test_verified_reel_and_healthy_reach_grant_commercial_capability():
    snapshot = derive_snapshot(
        [account()],
        {
            "handle": "capafy.new",
            "last_public_reel_url": "https://www.instagram.com/reel/ABC123/",
            "post_write_session_verified": True,
            "reach_healthy": True,
        },
        now("2026-08-08T10:00:00Z"),
    )
    assert snapshot["status"] == "commercial_ready"
    assert snapshot["capability"] == "commercial_post"


def test_newest_usable_browser_owned_account_wins():
    accounts = [
        account("capafy.old", "2026-07-01"),
        account("capafy.private", "2026-08-03", session_owner="private_api"),
        account("capafy.failed", "2026-08-04", status="session_failed"),
        account("capafy.current", "2026-08-02"),
    ]
    snapshot = derive_snapshot(accounts, {}, now())
    assert snapshot["handle"] == "capafy.current"


def test_no_usable_account_requests_replacement():
    snapshot = derive_snapshot(
        [account("capafy.failed", status="session_failed")], {}, now()
    )
    assert snapshot["status"] == "replacement_requested"
    assert snapshot["replacement_requested"] is True
    assert snapshot["handle"] is None


def test_verified_reel_is_preserved_only_for_same_handle():
    prior = {
        "handle": "capafy.new",
        "last_public_reel_url": "https://www.instagram.com/reel/ABC123/",
    }
    same = derive_snapshot([account()], prior, now())
    assert same["last_public_reel_url"] == prior["last_public_reel_url"]
    assert same["status"] == "reach_observing"

    other = derive_snapshot([account("capafy.other")], prior, now())
    assert other["last_public_reel_url"] is None


def test_retire_is_atomic_and_preserves_every_other_registry_row(tmp_path):
    path = tmp_path / "accounts.json"
    rows = [account("capafy.failed"), account("capafy.keep"), {"handle": "historical", "status": "poisoned"}]
    path.write_text(json.dumps(rows), encoding="utf-8")

    result = retire_account(path, "capafy.failed", "challenge", "capafy-marketer-1")

    written = json.loads(path.read_text(encoding="utf-8"))
    assert result["retired_handle"] == "capafy.failed"
    assert result["incident_id"] == "capafy-marketer-1"
    assert written[0]["status"] == "session_failed"
    assert written[0]["retirement_reason"] == "challenge"
    assert written[1:] == rows[1:]
    assert len(written) == 3
    assert not list(tmp_path.glob("*.tmp"))


def test_retire_rejects_unknown_handle_without_changing_registry(tmp_path):
    path = tmp_path / "accounts.json"
    original = json.dumps([account("capafy.keep")])
    path.write_text(original, encoding="utf-8")
    with pytest.raises(ValueError, match="not found"):
        retire_account(path, "capafy.missing", "challenge", "incident-1")
    assert path.read_text(encoding="utf-8") == original


def test_record_public_reel_validates_url_and_reads_back_written_state(tmp_path):
    path = tmp_path / "lifecycle.json"
    path.write_text(json.dumps({"schema_version": 1, "handle": "capafy.new"}), encoding="utf-8")
    url = "https://www.instagram.com/reel/ABC123/"

    result = record_public_reel(path, "capafy.new", url, owner_session_verified=True)

    assert result == json.loads(path.read_text(encoding="utf-8"))
    assert result["last_public_reel_url"] == url
    assert result["status"] == "first_publish_probe_verified"
    assert result["post_write_session_verified"] is True


def test_record_public_reel_requires_post_write_owner_session(tmp_path):
    path = tmp_path / "lifecycle.json"
    path.write_text(json.dumps({"schema_version": 1, "handle": "capafy.new"}), encoding="utf-8")
    with pytest.raises(ValueError, match="owner session"):
        record_public_reel(
            path,
            "capafy.new",
            "https://www.instagram.com/reel/ABC123/",
            owner_session_verified=False,
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://instagram.com/p/ABC123/",
        "https://evil.example/reel/ABC123/",
        "javascript:alert(1)",
    ],
)
def test_record_public_reel_rejects_non_reel_urls(tmp_path, url):
    path = tmp_path / "lifecycle.json"
    path.write_text(json.dumps({"schema_version": 1, "handle": "capafy.new"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Instagram Reel"):
        record_public_reel(path, "capafy.new", url, owner_session_verified=True)


def test_snapshot_timestamp_is_normalized_to_utc():
    snapshot = derive_snapshot([account()], {}, datetime(2026, 8, 2, 19, 0, tzinfo=timezone.utc))
    assert snapshot["updated_at"] == "2026-08-02T19:00:00Z"


def test_cli_snapshot_and_request_replacement_write_state_atomically(tmp_path):
    accounts = tmp_path / "accounts.json"
    state = tmp_path / "state.json"
    accounts.write_text(json.dumps([account()]), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(LIFECYCLE),
            "snapshot",
            "--accounts",
            str(accounts),
            "--state",
            str(state),
            "--now",
            "2026-08-02T10:00:00Z",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "publish_probe_ready"
    assert json.loads(state.read_text(encoding="utf-8"))["capability"] == "publish_probe"

    completed = subprocess.run(
        [
            sys.executable,
            str(LIFECYCLE),
            "request-replacement",
            "--state",
            str(state),
            "--reason",
            "challenge",
            "--incident-id",
            "incident-cli-1",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    written = json.loads(state.read_text(encoding="utf-8"))
    assert written["status"] == "replacement_requested"
    assert written["incident_id"] == "incident-cli-1"
    assert written["replacement_reason"] == "challenge"


def test_cli_retire_and_record_reel_cover_mutating_commands(tmp_path):
    accounts = tmp_path / "accounts.json"
    state = tmp_path / "state.json"
    accounts.write_text(json.dumps([account()]), encoding="utf-8")
    state.write_text(json.dumps({"schema_version": 1, "handle": "capafy.new"}), encoding="utf-8")

    retired = subprocess.run(
        [
            sys.executable,
            str(LIFECYCLE),
            "retire",
            "--accounts",
            str(accounts),
            "--handle",
            "capafy.new",
            "--reason",
            "challenge",
            "--incident-id",
            "incident-cli-2",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert retired.returncode == 0, retired.stderr
    assert json.loads(retired.stdout)["retired_handle"] == "capafy.new"
    assert json.loads(accounts.read_text(encoding="utf-8"))[0]["status"] == "session_failed"

    recorded = subprocess.run(
        [
            sys.executable,
            str(LIFECYCLE),
            "record-reel",
            "--state",
            str(state),
            "--handle",
            "capafy.new",
            "--reel-url",
            "https://www.instagram.com/reel/CLI123/",
            "--owner-session-verified",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert recorded.returncode == 0, recorded.stderr
    assert json.loads(recorded.stdout)["last_public_reel_url"].endswith("/CLI123/")
