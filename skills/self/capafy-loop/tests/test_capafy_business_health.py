import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "capafy_business_health.py"


def run_health(state: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CAPAFY_OUTCOME_STATE_DIR"] = str(state)
    return subprocess.run(
        [sys.executable, str(SCRIPT)], text=True, capture_output=True, env=env, check=False
    )


def iso(minutes_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_scheduler_without_business_outcome_is_unhealthy(tmp_path: Path) -> None:
    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "no_recent_business_outcome"


def test_recent_verified_builder_submission_is_healthy(tmp_path: Path) -> None:
    write(
        tmp_path / "capafy-builder-terminal.json",
        {
            "recorded_at": iso(),
            "outcome": {
                "kind": "builder_submitted",
                "listing_url": "https://capafy.ai/agent/9480246345",
            },
        },
    )

    result = run_health(tmp_path)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "healthy"


def test_recent_bounded_noop_is_healthy(tmp_path: Path) -> None:
    write(
        tmp_path / "capafy-builder-terminal.json",
        {
            "recorded_at": iso(),
            "outcome": {"kind": "builder_noop", "reason": "publish cap full"},
        },
    )

    assert run_health(tmp_path).returncode == 0


def test_unresolved_incident_requires_scheduled_retry(tmp_path: Path) -> None:
    incident = {
        "incident_id": "capafy-marketer-test",
        "phase": "unresolved",
        "updated_at": iso(),
        "next_retry_at": None,
    }
    write(tmp_path / "capafy-incidents" / "capafy-marketer-test.json", incident)

    missing_retry = run_health(tmp_path)
    incident["next_retry_at"] = iso(minutes_ago=-60)
    write(tmp_path / "capafy-incidents" / "capafy-marketer-test.json", incident)
    scheduled_retry = run_health(tmp_path)

    assert missing_retry.returncode != 0
    assert scheduled_retry.returncode == 0
    assert json.loads(scheduled_retry.stdout)["status"] == "contained"


def test_unresolved_incident_with_due_retry_is_unhealthy(tmp_path: Path) -> None:
    write(
        tmp_path / "capafy-incidents" / "capafy-marketer-test.json",
        {
            "incident_id": "capafy-marketer-test",
            "phase": "unresolved",
            "updated_at": iso(minutes_ago=10),
            "next_retry_at": iso(minutes_ago=1),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "retry_due"


def test_repair_started_has_five_minute_grace_then_wakes_repair(tmp_path: Path) -> None:
    path = tmp_path / "capafy-incidents" / "capafy-builder-test.json"
    write(
        path,
        {
            "incident_id": "capafy-builder-test",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=4),
        },
    )
    grace = run_health(tmp_path)
    write(
        path,
        {
            "incident_id": "capafy-builder-test",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=6),
        },
    )
    stale = run_health(tmp_path)

    assert grace.returncode == 0
    assert json.loads(grace.stdout)["status"] == "repair_grace"
    assert stale.returncode != 0
    assert json.loads(stale.stdout)["reason"] == "repair_sla_expired"
    assert json.loads(stale.stdout)["incident_id"] == "capafy-builder-test"


def test_repaired_but_unverified_incident_obeys_five_minute_sla(tmp_path: Path) -> None:
    path = tmp_path / "capafy-incidents" / "capafy-builder-test.json"
    write(
        path,
        {
            "incident_id": "capafy-builder-test",
            "phase": "repaired",
            "updated_at": iso(minutes_ago=6),
        },
    )
    write(
        tmp_path / "capafy-builder-terminal.json",
        {"recorded_at": iso(), "outcome": {"kind": "builder_submitted"}},
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "repair_sla_expired"


def test_any_stale_incident_prevents_newer_grace_from_masking_it(tmp_path: Path) -> None:
    write(
        tmp_path / "capafy-incidents" / "old.json",
        {
            "incident_id": "old",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=20),
        },
    )
    write(
        tmp_path / "capafy-incidents" / "new.json",
        {
            "incident_id": "new",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=1),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["incident_id"] == "old"
