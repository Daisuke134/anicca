import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "capafy_business_health.py"
HEALTHCHECK = Path(__file__).parents[1] / "capafy-loop-healthcheck.sh"


def run_health(state: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CAPAFY_OUTCOME_STATE_DIR"] = str(state)
    env["CAPAFY_RECONCILIATION_LEDGER"] = str(state / "capafy-earn-ledger.jsonl")
    env["CAPAFY_REPORT_DELIVERY_STATE"] = str(state / "capafy-goal-monitor-delivery.json")
    env.update(overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT)], text=True, capture_output=True, env=env, check=False
    )


def iso(minutes_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def write_reconciliation_ledger(state: Path) -> Path:
    ledger = state / "capafy-earn-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{}\n")
    return ledger


def delivery(key: str, minutes_ago: int = 0) -> dict:
    return {
        "delivery_key": key,
        "projection_id": "sha256:" + "a" * 64,
        "telegram_message_id": "1",
        "delivered_at": iso(minutes_ago),
    }


def write_delivery_state(state: Path, rows: list[dict]) -> None:
    write(state / "capafy-goal-monitor-delivery.json", {"schema_version": 2, "deliveries": rows})


def write_business_baseline(state: Path) -> None:
    write_reconciliation_ledger(state)
    write_delivery_state(
        state,
        [delivery("hourly:2026-08-13T17"), delivery("daily_close:2026-08-13")],
    )


def write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


def test_scheduler_without_business_outcome_is_unhealthy(tmp_path: Path) -> None:
    write_business_baseline(tmp_path)
    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "no_recent_business_outcome"


def test_recent_verified_builder_submission_is_healthy(tmp_path: Path) -> None:
    write_business_baseline(tmp_path)
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
    write_business_baseline(tmp_path)
    write(
        tmp_path / "capafy-builder-terminal.json",
        {
            "recorded_at": iso(),
            "outcome": {"kind": "builder_noop", "reason": "publish cap full"},
        },
    )

    assert run_health(tmp_path).returncode == 0


def test_unresolved_incident_requires_scheduled_retry(tmp_path: Path) -> None:
    write_business_baseline(tmp_path)
    incident = {
        "incident_id": "capafy-marketer-test",
        "owner": "capafy-marketer",
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
    write_business_baseline(tmp_path)
    write(
        tmp_path / "capafy-incidents" / "capafy-marketer-test.json",
        {
            "incident_id": "capafy-marketer-test",
            "owner": "capafy-marketer",
            "phase": "unresolved",
            "updated_at": iso(minutes_ago=10),
            "next_retry_at": iso(minutes_ago=1),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "retry_due"


def test_repair_started_has_five_minute_grace_then_wakes_repair(tmp_path: Path) -> None:
    write_business_baseline(tmp_path)
    path = tmp_path / "capafy-incidents" / "capafy-builder-test.json"
    write(
        path,
        {
            "incident_id": "capafy-builder-test",
            "owner": "capafy-builder",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=4),
        },
    )
    grace = run_health(tmp_path)
    write(
        path,
        {
            "incident_id": "capafy-builder-test",
            "owner": "capafy-builder",
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
    write_business_baseline(tmp_path)
    path = tmp_path / "capafy-incidents" / "capafy-builder-test.json"
    write(
        path,
        {
            "incident_id": "capafy-builder-test",
            "owner": "capafy-builder",
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
    write_business_baseline(tmp_path)
    write(
        tmp_path / "capafy-incidents" / "old.json",
        {
            "incident_id": "old",
            "owner": "capafy-builder",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=20),
        },
    )
    write(
        tmp_path / "capafy-incidents" / "new.json",
        {
            "incident_id": "new",
            "owner": "capafy-builder",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=1),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["incident_id"] == "old"


def test_stale_reconciliation_routes_only_to_builder(tmp_path: Path) -> None:
    ledger = write_reconciliation_ledger(tmp_path)
    write_delivery_state(
        tmp_path,
        [delivery("hourly:2026-08-13T17"), delivery("daily_close:2026-08-13")],
    )
    stale = (datetime.now(timezone.utc) - timedelta(hours=49)).timestamp()
    os.utime(ledger, (stale, stale))

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout) == {
        "reason": "stale_reconciliation",
        "repair_action": "kickstart",
        "repair_label": "ai.anicca.capafy-loop-daily",
        "repair_owner": "builder",
        "status": "unhealthy",
    }


def test_missing_hourly_report_routes_only_to_hourly_job(tmp_path: Path) -> None:
    write_reconciliation_ledger(tmp_path)
    write_delivery_state(tmp_path, [delivery("daily_close:2026-08-13")])

    result = run_health(tmp_path)

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["reason"] == "owner_report_missing"
    assert payload["repair_owner"] == "company"
    assert payload["repair_action"] == "kickstart"
    assert payload["repair_label"] == "ai.anicca.capafy-goal-monitor-hourly"


def test_missing_daily_close_report_routes_only_to_daily_close_job(tmp_path: Path) -> None:
    write_reconciliation_ledger(tmp_path)
    write_delivery_state(tmp_path, [delivery("hourly:2026-08-13T17")])

    result = run_health(tmp_path)

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["reason"] == "owner_report_missing"
    assert payload["repair_owner"] == "company"
    assert payload["repair_action"] == "kickstart"
    assert payload["repair_label"] == "ai.anicca.capafy-goal-monitor-daily-close"


def test_overdue_marketer_incident_routes_only_to_marketer(tmp_path: Path) -> None:
    write_business_baseline(tmp_path)
    write(
        tmp_path / "capafy-incidents" / "capafy-marketer-test.json",
        {
            "incident_id": "capafy-marketer-test",
            "owner": "capafy-marketer",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=6),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["reason"] == "repair_sla_expired"
    assert payload["repair_owner"] == "marketer"
    assert payload["repair_action"] == "kickstart"
    assert payload["repair_label"] == "ai.anicca.capafy-ig-marketing-daily"


def test_unknown_incident_owner_routes_to_fixed_integrity_self_fix(tmp_path: Path) -> None:
    write_business_baseline(tmp_path)
    write(
        tmp_path / "capafy-incidents" / "unknown.json",
        {
            "incident_id": "unknown",
            "owner": "attacker-controlled",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=6),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["reason"] == "unknown_incident_owner"
    assert payload["repair_owner"] == "integrity"
    assert payload["repair_action"] == "self_fix"
    assert "repair_label" not in payload


def test_malformed_delivery_state_routes_to_company(tmp_path: Path) -> None:
    write_reconciliation_ledger(tmp_path)
    write(
        tmp_path / "capafy-goal-monitor-delivery.json",
        {"schema_version": 2, "deliveries": [{"delivery_key": "hourly:2026-08-13T17"}]},
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["reason"] == "owner_report_missing"
    assert payload["repair_label"] == "ai.anicca.capafy-goal-monitor-hourly"


def test_healthcheck_kickstarts_only_an_allowlisted_routed_owner(tmp_path: Path) -> None:
    checker = tmp_path / "checker.sh"
    launchctl = tmp_path / "launchctl.sh"
    fixer = tmp_path / "fixer.sh"
    launchctl_calls = tmp_path / "launchctl.calls"
    fixer_calls = tmp_path / "fixer.calls"
    write_executable(
        launchctl,
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$CAPAFY_LAUNCHCTL_CALLS\"\n",
    )
    write_executable(
        fixer,
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$CAPAFY_FIXER_CALLS\"\n",
    )
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path),
            "CAPAFY_BUSINESS_HEALTH_CMD": str(checker),
            "CAPAFY_LAUNCHCTL": str(launchctl),
            "CAPAFY_SELF_FIX": str(fixer),
            "CAPAFY_LAUNCHCTL_CALLS": str(launchctl_calls),
            "CAPAFY_FIXER_CALLS": str(fixer_calls),
            "CAPAFY_HEALTH_LOG": str(tmp_path / "health.log"),
            "CAPAFY_HEALTH_SKIP_SCHEDULER_CHECK": "1",
        }
    )
    routed = {
        "status": "unhealthy",
        "reason": "repair_sla_expired",
        "repair_owner": "marketer",
        "repair_label": "ai.anicca.capafy-ig-marketing-daily",
    }
    write_executable(checker, f"#!/usr/bin/env bash\nprintf '%s\\n' '{json.dumps(routed)}'\nexit 1\n")

    result = subprocess.run(["bash", str(HEALTHCHECK)], text=True, capture_output=True, env=env, check=False)

    assert result.returncode != 0
    assert launchctl_calls.read_text().splitlines() == [
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-ig-marketing-daily"
    ]
    assert not fixer_calls.exists()

    hourly = {**routed, "repair_label": "ai.anicca.capafy-goal-monitor-hourly"}
    write_executable(checker, f"#!/usr/bin/env bash\nprintf '%s\\n' '{json.dumps(hourly)}'\nexit 1\n")

    result = subprocess.run(["bash", str(HEALTHCHECK)], text=True, capture_output=True, env=env, check=False)

    assert result.returncode != 0
    assert launchctl_calls.read_text().splitlines() == [
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-ig-marketing-daily",
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-goal-monitor-hourly",
    ]
    assert not fixer_calls.exists()

    unknown = {**routed, "repair_label": "ai.anicca.attacker-controlled"}
    write_executable(checker, f"#!/usr/bin/env bash\nprintf '%s\\n' '{json.dumps(unknown)}'\nexit 1\n")

    result = subprocess.run(["bash", str(HEALTHCHECK)], text=True, capture_output=True, env=env, check=False)

    assert result.returncode != 0
    assert launchctl_calls.read_text().splitlines() == [
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-ig-marketing-daily",
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-goal-monitor-hourly",
    ]
    assert not fixer_calls.exists()

    integrity = {
        "status": "unhealthy",
        "reason": "unknown_incident_owner",
        "repair_owner": "integrity",
        "repair_action": "self_fix",
    }
    write_executable(checker, f"#!/usr/bin/env bash\nprintf '%s\\n' '{json.dumps(integrity)}'\nexit 1\n")

    result = subprocess.run(["bash", str(HEALTHCHECK)], text=True, capture_output=True, env=env, check=False)

    assert result.returncode != 0
    assert launchctl_calls.read_text().splitlines() == [
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-ig-marketing-daily",
        f"kickstart gui/{os.getuid()}/ai.anicca.capafy-goal-monitor-hourly",
    ]
    assert fixer_calls.read_text().splitlines() == ["capafy Capafy business-outcome watchdog: integrity health check failed."]


@pytest.mark.parametrize("name,value", [
    ("CAPAFY_BUSINESS_OUTCOME_MAX_HOURS", "0"),
    ("CAPAFY_REPAIR_SLA_MINUTES", "nan"),
    ("CAPAFY_RECONCILIATION_MAX_HOURS", "inf"),
    ("CAPAFY_HOURLY_REPORT_MAX_MINUTES", "-1"),
    ("CAPAFY_DAILY_CLOSE_MAX_HOURS", "not-a-number"),
])
def test_invalid_thresholds_route_to_integrity_self_fix(
    tmp_path: Path, name: str, value: str
) -> None:
    write_business_baseline(tmp_path)
    write(tmp_path / "capafy-builder-terminal.json", {"recorded_at": iso(), "outcome": {"kind": "builder_submitted"}})

    result = run_health(tmp_path, **{name: value})

    assert result.returncode != 0
    assert json.loads(result.stdout) == {
        "reason": "invalid_health_configuration",
        "repair_action": "self_fix",
        "repair_owner": "integrity",
        "status": "unhealthy",
    }


@pytest.mark.parametrize("timestamp", ["2026-08-13T17:00:00", "not-a-time"])
def test_naive_or_invalid_delivery_timestamp_is_missing(tmp_path: Path, timestamp: str) -> None:
    write_reconciliation_ledger(tmp_path)
    row = delivery("hourly:2026-08-13T17")
    row["delivered_at"] = timestamp
    write_delivery_state(tmp_path, [row, delivery("daily_close:2026-08-13")])

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["repair_label"] == "ai.anicca.capafy-goal-monitor-hourly"


def test_future_observations_cannot_be_healthy(tmp_path: Path) -> None:
    ledger = write_reconciliation_ledger(tmp_path)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    os.utime(ledger, (future, future))
    write_delivery_state(
        tmp_path,
        [delivery("hourly:2026-08-13T17", -60), delivery("daily_close:2026-08-13", -60)],
    )
    write(tmp_path / "capafy-builder-terminal.json", {"recorded_at": iso(minutes_ago=-60), "outcome": {"kind": "builder_submitted"}})

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "stale_reconciliation"


@pytest.mark.parametrize("recorded_at", ["2026-08-13T17:00:00", iso(minutes_ago=-60)])
def test_naive_or_future_terminal_timestamp_cannot_be_healthy(
    tmp_path: Path, recorded_at: str
) -> None:
    write_business_baseline(tmp_path)
    write(
        tmp_path / "capafy-builder-terminal.json",
        {"recorded_at": recorded_at, "outcome": {"kind": "builder_submitted"}},
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["reason"] == "no_recent_business_outcome"


def test_future_delivery_and_incident_timestamp_cannot_be_healthy(tmp_path: Path) -> None:
    write_reconciliation_ledger(tmp_path)
    write_delivery_state(
        tmp_path,
        [delivery("hourly:2026-08-13T17", -60), delivery("daily_close:2026-08-13")],
    )
    write(
        tmp_path / "capafy-incidents" / "future.json",
        {
            "incident_id": "future",
            "owner": "builder",
            "phase": "repair_started",
            "updated_at": iso(minutes_ago=-60),
        },
    )

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["repair_label"] == "ai.anicca.capafy-goal-monitor-hourly"

    write_business_baseline(tmp_path)
    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["repair_label"] == "ai.anicca.capafy-loop-daily"


@pytest.mark.parametrize("field,value", [
    ("delivery_key", "hourly:2026-02-30T25"),
    ("projection_id", "sha256:" + "A" * 64),
    ("telegram_message_id", "not-numeric"),
])
def test_invalid_delivery_proof_cannot_be_healthy(tmp_path: Path, field: str, value: str) -> None:
    write_reconciliation_ledger(tmp_path)
    row = delivery("hourly:2026-08-13T17")
    row[field] = value
    write_delivery_state(tmp_path, [row, delivery("daily_close:2026-08-13")])
    write(tmp_path / "capafy-builder-terminal.json", {"recorded_at": iso(), "outcome": {"kind": "builder_submitted"}})

    result = run_health(tmp_path)

    assert result.returncode != 0
    assert json.loads(result.stdout)["repair_label"] == "ai.anicca.capafy-goal-monitor-hourly"
