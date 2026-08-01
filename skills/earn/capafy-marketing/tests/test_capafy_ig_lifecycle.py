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
    successful_warmup_dates,
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


def warm(date, reels=6, scrolls=5, **overrides):
    value = {
        "date": date,
        "verified": {"reels_played": reels},
        "actions": {"scrolls": scrolls},
    }
    value.update(overrides)
    return value


def test_calendar_age_without_verified_actions_stays_warmup_zero():
    old = account(created="2026-07-01")
    snapshot = derive_snapshot([old], {"log": []}, {}, now())
    assert snapshot["status"] == "warmup_0_of_2"
    assert snapshot["capability"] == "warmup_only"
    assert snapshot["warmup_successes"] == 0


def test_verified_dates_are_unique_sorted_and_require_real_actions():
    data = {
        "log": [
            warm("2026-08-02"),
            warm("2026-08-01"),
            warm("2026-08-02", reels=9),
            warm("2026-08-03", reels=0),
            warm("2026-08-04", scrolls=0),
            warm("2026-08-05", ABORT="not logged in"),
            warm("2026-08-06", ban_signal="challenge"),
        ]
    }
    assert successful_warmup_dates(data) == ["2026-08-01", "2026-08-02"]


def test_two_distinct_verified_dates_grant_only_noncommercial_capability():
    data = {"log": [warm("2026-08-01"), warm("2026-08-02")]}
    snapshot = derive_snapshot([account()], data, {}, now())
    assert snapshot["warmup_successes"] == 2
    assert snapshot["status"] == "noncommercial_ready"
    assert snapshot["capability"] == "noncommercial_post"


@pytest.mark.parametrize("signal", ["ABORT", "ban", "ban_signal"])
def test_later_abort_or_ban_requests_replacement(signal):
    data = {
        "log": [warm("2026-08-01")],
        "aborts": [{"date": "2026-08-02", signal: "challenge"}],
    }
    snapshot = derive_snapshot([account()], data, {}, now())
    assert snapshot["status"] == "replacement_requested"
    assert snapshot["capability"] == "none"
    assert snapshot["replacement_requested"] is True


def test_abort_older_than_latest_success_does_not_retire_current_evidence():
    data = {
        "log": [warm("2026-08-01"), warm("2026-08-02")],
        "aborts": [{"date": "2026-07-31", "ABORT": "old"}],
    }
    assert derive_snapshot([account()], data, {}, now())["status"] == "noncommercial_ready"


def test_seven_warmups_without_reach_are_not_commercial():
    data = {"log": [warm(f"2026-08-{day:02d}") for day in range(1, 8)]}
    snapshot = derive_snapshot([account()], data, {"reach_healthy": False}, now("2026-08-08T10:00:00Z"))
    assert snapshot["capability"] == "noncommercial_post"


def test_seven_warmups_with_healthy_reach_grant_commercial_capability():
    data = {"log": [warm(f"2026-08-{day:02d}") for day in range(1, 8)]}
    snapshot = derive_snapshot(
        [account()],
        data,
        {"handle": "capafy.new", "reach_healthy": True},
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
    snapshot = derive_snapshot(accounts, {"log": []}, {}, now())
    assert snapshot["handle"] == "capafy.current"


def test_no_usable_account_requests_replacement():
    snapshot = derive_snapshot(
        [account("capafy.failed", status="session_failed")], {"log": []}, {}, now()
    )
    assert snapshot["status"] == "replacement_requested"
    assert snapshot["replacement_requested"] is True
    assert snapshot["handle"] is None


def test_verified_reel_is_preserved_only_for_same_handle():
    prior = {
        "handle": "capafy.new",
        "last_public_reel_url": "https://www.instagram.com/reel/ABC123/",
    }
    same = derive_snapshot([account()], {"log": [warm("2026-08-01"), warm("2026-08-02")]}, prior, now())
    assert same["last_public_reel_url"] == prior["last_public_reel_url"]
    assert same["status"] == "reach_observing"

    other = derive_snapshot([account("capafy.other")], {"log": []}, prior, now())
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

    result = record_public_reel(path, "capafy.new", url)

    assert result == json.loads(path.read_text(encoding="utf-8"))
    assert result["last_public_reel_url"] == url
    assert result["status"] == "first_noncommercial_post_verified"


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
        record_public_reel(path, "capafy.new", url)


def test_snapshot_timestamp_is_normalized_to_utc():
    snapshot = derive_snapshot([account()], {"log": []}, {}, datetime(2026, 8, 2, 19, 0, tzinfo=timezone.utc))
    assert snapshot["updated_at"] == "2026-08-02T19:00:00Z"


def test_cli_snapshot_and_request_replacement_write_state_atomically(tmp_path):
    accounts = tmp_path / "accounts.json"
    warmup = tmp_path / "warmup.json"
    state = tmp_path / "state.json"
    accounts.write_text(json.dumps([account()]), encoding="utf-8")
    warmup.write_text(json.dumps({"log": [warm("2026-08-01")]}), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(LIFECYCLE),
            "snapshot",
            "--accounts",
            str(accounts),
            "--warmup",
            str(warmup),
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
    assert json.loads(completed.stdout)["status"] == "warmup_1_of_2"
    assert json.loads(state.read_text(encoding="utf-8"))["warmup_successes"] == 1

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
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert recorded.returncode == 0, recorded.stderr
    assert json.loads(recorded.stdout)["last_public_reel_url"].endswith("/CLI123/")
