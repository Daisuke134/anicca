import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_outcome.py"
SCRIPTS = SCRIPT.parent
sys.path.insert(0, str(SCRIPTS))

import capafy_event_adapters as event_adapters
import capafy_event_store as event_store
import capafy_outcome


def run_cli(command: str, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), command],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def run_cli_args(
    *args: str, payload: dict | None = None, state_dir: Path
) -> subprocess.CompletedProcess[str]:
    env = {"CAPAFY_OUTCOME_STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def builder_submission() -> dict:
    return {
        "schema_version": 1,
        "kind": "builder_submitted",
        "owner": "builder",
        "title": "Portfolio Tracker — Daily Position Review",
        "agent_id": "9480246345",
        "remote_status": 1,
        "skills_confirmed": True,
        "config_confirmed": True,
        "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review",
        "gross_usd": 9.99,
        "pending_usd": 8.0,
        "realized_usd": 0.0,
        "mrr_usd": 0.0,
        "cost_usd": 4.777,
        "contribution_usd": -4.777,
        "next_action": "Watch for approval and hand the public listing to Marketing",
    }


def incident_record(phase: str) -> dict:
    return {
        "schema_version": 1,
        "incident_id": "capafy-marketer-20260801T201313Z-6b646dbe",
        "owner": "marketer",
        "phase": phase,
        "detected_at": "2026-08-01T20:13:13Z",
        "updated_at": "2026-08-01T20:20:00Z",
        "phase_timestamps": {
            "detected": "2026-08-01T20:13:13Z",
            "repair_started": "2026-08-01T20:14:00Z",
            "repaired": "2026-08-01T20:18:00Z",
            "verified": "2026-08-01T20:20:00Z",
            "unresolved": "2026-08-01T20:20:00Z",
        },
        "summary": "Instagram metrics writer could not append its canonical event.",
        "repair_summary": "Repaired the truncated ledger tail and retried the writer.",
        "verification": {"ledger_event_count": 1} if phase == "verified" else None,
        "next_retry_at": "2026-08-01T21:00:00Z" if phase == "unresolved" else None,
        "attempts": 1,
    }


def test_unresolved_transition_repairs_human_retry_sentinel(tmp_path: Path) -> None:
    incident = incident_record("detected")
    incident["next_retry_at"] = None
    write_path = tmp_path / "capafy-incidents" / f"{incident['incident_id']}.json"
    write_path.parent.mkdir(parents=True)
    write_path.write_text(json.dumps(incident), encoding="utf-8")

    result = run_cli_args(
        "transition-incident",
        payload={
            "incident_id": incident["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "the next repair cycle",
        },
        state_dir=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    repaired = json.loads(result.stdout)
    assert repaired["phase"] == "unresolved"
    assert repaired["next_retry_at"].endswith("Z")
    datetime.fromisoformat(repaired["next_retry_at"].replace("Z", "+00:00"))


@pytest.mark.parametrize(
    ("phase", "expected_id"),
    [
        ("detected", "capafy:incident.detected:capafy-marketer-20260801T201313Z-6b646dbe"),
        (
            "repair_started",
            "capafy:incident.repair_started:capafy-marketer-20260801T201313Z-6b646dbe:attempt-1",
        ),
        (
            "repaired",
            "capafy:incident.repaired:capafy-marketer-20260801T201313Z-6b646dbe:attempt-1",
        ),
        (
            "verified",
            "capafy:incident.verified:capafy-marketer-20260801T201313Z-6b646dbe:attempt-1",
        ),
        (
            "unresolved",
            "capafy:incident.unresolved:capafy-marketer-20260801T201313Z-6b646dbe:retry-20260801T210000Z",
        ),
    ],
)
def test_incident_phase_maps_to_legacy_or_occurrence_canonical_event(
    phase: str, expected_id: str
) -> None:
    event = event_adapters.event_from_incident(incident_record(phase))

    assert event["event_id"] == expected_id
    assert event["event_type"] == f"incident.{phase}"
    assert event["occurred_at"] == incident_record(phase)["phase_timestamps"][phase]
    assert "recorded_at" not in event


def test_verified_incident_event_requires_concrete_verification() -> None:
    record = incident_record("verified")
    record["verification"] = None

    with pytest.raises(ValueError, match="verification"):
        event_adapters.event_from_incident(record)


def test_incident_state_is_written_before_event_and_same_phase_retries_writer(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    observations = []

    record = capafy_outcome.start_incident(
        owner="marketer",
        summary="writer failed",
        fingerprint="writer-failed",
        repair_result_path=None,
        event_writer=lambda current: observations.append(
            (current["phase"], capafy_outcome.get_incident(current["incident_id"])["phase"])
        ),
    )

    def fail_after_state(current: dict) -> None:
        assert capafy_outcome.get_incident(current["incident_id"])["phase"] == "repair_started"
        raise RuntimeError("seeded event append failure")

    update = {"incident_id": record["incident_id"], "phase": "repair_started"}
    with pytest.raises(RuntimeError, match="seeded event append failure"):
        capafy_outcome.transition_incident(update, event_writer=fail_after_state)
    persisted = capafy_outcome.get_incident(record["incident_id"])
    first_phase_time = persisted["phase_timestamps"]["repair_started"]

    capafy_outcome.transition_incident(
        update,
        event_writer=lambda current: observations.append(
            (current["phase"], current["phase_timestamps"]["repair_started"])
        ),
    )

    assert observations[0] == ("detected", "detected")
    assert observations[-1] == ("repair_started", first_phase_time)


def test_new_phase_occurrence_refreshes_timestamp_but_same_phase_retry_preserves_it(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    clock = iter(
        (
            "2026-08-03T07:00:10Z",
            "2026-08-03T07:01:00Z",
            "2026-08-03T07:02:00Z",
            "2026-08-03T07:03:00Z",
            "2026-08-03T07:04:00Z",
        )
    )
    monkeypatch.setattr(capafy_outcome, "_now", lambda: next(clock))
    record = capafy_outcome.start_incident(
        owner="capafy-marketer",
        summary="sync failed",
        fingerprint="sync-failed",
        repair_result_path=None,
    )

    first = capafy_outcome.transition_incident(
        {"incident_id": record["incident_id"], "phase": "repair_started"}
    )
    first_timestamp = first["phase_timestamps"]["repair_started"]
    retry = capafy_outcome.transition_incident(
        {"incident_id": record["incident_id"], "phase": "repair_started"}
    )
    assert retry["phase_timestamps"]["repair_started"] == first_timestamp

    capafy_outcome.transition_incident(
        {
            "incident_id": record["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "2026-08-03T08:00:00Z",
        }
    )
    recurring = capafy_outcome.transition_incident(
        {"incident_id": record["incident_id"], "phase": "repair_started"}
    )
    assert recurring["attempts"] == 1
    assert recurring["phase_timestamps"]["repair_started"] == "2026-08-03T07:04:00Z"


def test_changed_unresolved_retry_schedule_is_a_new_occurrence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    clock = iter(
        (
            "2026-08-03T07:00:10Z",
            "2026-08-03T07:01:00Z",
            "2026-08-03T07:02:00Z",
            "2026-08-03T07:03:00Z",
        )
    )
    monkeypatch.setattr(capafy_outcome, "_now", lambda: next(clock))
    record = capafy_outcome.start_incident(
        owner="capafy-marketer",
        summary="sync failed",
        fingerprint="sync-failed",
        repair_result_path=None,
    )
    first = capafy_outcome.transition_incident(
        {
            "incident_id": record["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "2026-08-03T08:00:00Z",
        }
    )
    second = capafy_outcome.transition_incident(
        {
            "incident_id": record["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "2026-08-03T09:00:00Z",
        }
    )
    same = capafy_outcome.transition_incident(
        {
            "incident_id": record["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "2026-08-03T09:00:00Z",
        }
    )

    assert first["phase_timestamps"]["unresolved"] == "2026-08-03T07:01:00Z"
    assert second["phase_timestamps"]["unresolved"] == "2026-08-03T07:02:00Z"
    assert same["phase_timestamps"]["unresolved"] == "2026-08-03T07:02:00Z"


def test_same_retry_schedule_recurrence_and_semantic_change_get_new_identity(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence = tmp_path / "evidence"

    def writer(current: dict) -> None:
        event_store.append_event(
            ledger,
            event_adapters.event_from_incident(current),
            current,
            evidence,
        )

    record = capafy_outcome.start_incident(
        owner="capafy-marketer",
        summary="sync failed",
        fingerprint="sync-failed",
        repair_result_path=None,
        event_writer=writer,
    )
    incident_id = record["incident_id"]
    for phase in ("repair_started", "repaired"):
        record = capafy_outcome.transition_incident(
            {"incident_id": incident_id, "phase": phase}, event_writer=writer
        )
    retry_at = "2026-08-13T01:00:00Z"
    record = capafy_outcome.transition_incident(
        {
            "incident_id": incident_id,
            "phase": "unresolved",
            "repair_summary": "first retry",
            "next_retry_at": retry_at,
        },
        event_writer=writer,
    )
    first_unresolved = event_adapters.event_from_incident(record)["event_id"]

    for phase in ("repair_started", "repaired"):
        record = capafy_outcome.transition_incident(
            {"incident_id": incident_id, "phase": phase}, event_writer=writer
        )
    record = capafy_outcome.transition_incident(
        {
            "incident_id": incident_id,
            "phase": "unresolved",
            "repair_summary": "second retry has a new semantic result",
            "next_retry_at": retry_at,
        },
        event_writer=writer,
    )
    second_unresolved = event_adapters.event_from_incident(record)["event_id"]
    replay = capafy_outcome.transition_incident(
        {
            "incident_id": incident_id,
            "phase": "unresolved",
            "repair_summary": "second retry has a new semantic result",
            "next_retry_at": retry_at,
        },
        event_writer=writer,
    )

    assert first_unresolved != second_unresolved
    assert event_store.append_event(
        ledger,
        event_adapters.event_from_incident(replay),
        replay,
        evidence,
    ).appended is False


def test_retry_schedule_is_canonical_and_invalid_retry_reuses_persisted_value(
    tmp_path: Path, monkeypatch
) -> None:
    incident = incident_record("unresolved")
    incident["next_retry_at"] = "2026-08-13T01:00:00Z"
    path = tmp_path / "capafy-incidents" / f"{incident['incident_id']}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(incident), encoding="utf-8")
    previous = event_adapters.event_from_incident(incident)

    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    same_instant = capafy_outcome.transition_incident(
        {
            "incident_id": incident["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "2026-08-13T10:00:00+09:00",
        }
    )
    prose_retry = capafy_outcome.transition_incident(
        {
            "incident_id": incident["incident_id"],
            "phase": "unresolved",
            "next_retry_at": "the next repair cycle",
        }
    )

    assert same_instant["next_retry_at"] == "2026-08-13T01:00:00Z"
    assert prose_retry["next_retry_at"] == "2026-08-13T01:00:00Z"
    assert event_adapters.event_from_incident(same_instant) == previous
    assert event_adapters.event_from_incident(prose_retry) == previous


def test_legacy_same_phase_semantic_change_gets_occurrence_identity(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    incident = incident_record("unresolved")
    incident.pop("phase_occurrences", None)
    path = tmp_path / "capafy-incidents" / f"{incident['incident_id']}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(incident), encoding="utf-8")
    first_id = event_adapters.event_from_incident(incident)["event_id"]

    changed = capafy_outcome.transition_incident(
        {
            "incident_id": incident["incident_id"],
            "phase": "unresolved",
            "repair_summary": "semantic retry detail changed",
            "next_retry_at": incident["next_retry_at"],
        }
    )

    assert event_adapters.event_from_incident(changed)["event_id"] != first_id


def test_verified_incident_cannot_transition_back_to_unresolved(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CAPAFY_OUTCOME_STATE_DIR", str(tmp_path))
    incident = incident_record("verified")
    path = tmp_path / "capafy-incidents" / f"{incident['incident_id']}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(incident), encoding="utf-8")

    with pytest.raises(ValueError, match="backwards"):
        capafy_outcome.transition_incident(
            {"incident_id": incident["incident_id"], "phase": "unresolved"}
        )


def test_builder_success_without_listing_url_is_rejected() -> None:
    payload = builder_submission()
    payload.pop("listing_url")

    result = run_cli("validate", payload)

    assert result.returncode != 0
    assert "listing_url" in result.stderr


def test_marketing_success_without_reel_url_is_rejected() -> None:
    payload = {
        "schema_version": 1,
        "kind": "marketing_published",
        "owner": "marketer",
        "title": "Portfolio Tracker — Daily Position Review",
        "listing_url": "https://capafy.ai/agent/9480246345",
        "campaign_url": "https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram",
        "caption": "Your portfolio changed today.",
    }

    result = run_cli("validate", payload)

    assert result.returncode != 0
    assert "reel_url" in result.stderr


def test_literal_placeholder_is_rejected_before_delivery() -> None:
    payload = {
        "schema_version": 1,
        "kind": "marketing_published",
        "owner": "marketer",
        "title": "Portfolio Tracker — Daily Position Review",
        "reel_url": "{verified_reel_url}",
        "listing_url": "https://capafy.ai/agent/9480246345",
        "campaign_url": "https://capafy-skills-daily.netlify.app/go/9480246345?utm_source=instagram",
        "caption": "Your portfolio changed today.",
    }

    result = run_cli("render", payload)

    assert result.returncode != 0
    assert "placeholder" in result.stderr.lower()


def test_loaded_scheduler_never_renders_as_live_or_published() -> None:
    payload = {
        "schema_version": 1,
        "kind": "account_state",
        "owner": "marketer",
        "handle": "capafy.skills10491",
        "scheduler_loaded": True,
        "lifecycle_status": "replacement_requested",
        "capability": "none",
        "session_established": False,
        "public_post_url": None,
    }

    result = run_cli("render", payload)

    assert result.returncode == 0, result.stderr
    rendered = result.stdout.lower()
    assert "scheduler is loaded" in rendered
    assert "live" not in rendered
    assert "published" not in rendered


def test_account_state_reports_verified_lifecycle_not_calendar_age() -> None:
    payload = {
        "schema_version": 1,
        "kind": "account_state",
        "owner": "marketer",
        "handle": "capafy.skills10491",
        "scheduler_loaded": True,
        "lifecycle_status": "publish_probe_ready",
        "capability": "publish_probe",
        "session_established": True,
        "public_post_url": None,
    }

    result = run_cli("render", payload)

    assert result.returncode == 0, result.stderr
    assert "publish_probe_ready" in result.stdout
    assert "publish-probe" in result.stdout
    assert "calendar" not in result.stdout.lower()
    assert "warmup" not in result.stdout.lower()


def test_account_created_renders_verified_browser_session_without_live_claim() -> None:
    payload = {
        "schema_version": 1,
        "kind": "account_created",
        "owner": "marketer",
        "handle": "capafy.skills25042",
        "session_owner": "browser",
        "session_established": True,
        "capability": "publish_probe",
        "public_post_url": None,
        "next_action": "Start the first original Reel now",
    }

    result = run_cli("render", payload)

    assert result.returncode == 0, result.stderr
    assert "@capafy.skills25042" in result.stdout
    assert "browser session" in result.stdout.lower()
    assert "publish probe" in result.stdout.lower()
    assert "starts now" in result.stdout.lower()
    assert "warmup" not in result.stdout.lower()
    assert "waiting" not in result.stdout.lower()
    assert "no public post" in result.stdout.lower()
    assert "live" not in result.stdout.lower()


def test_account_created_requires_independently_verified_session() -> None:
    payload = {
        "schema_version": 1,
        "kind": "account_created",
        "owner": "marketer",
        "handle": "capafy.skills25042",
        "session_owner": "browser",
        "session_established": False,
        "capability": "publish_probe",
        "public_post_url": None,
        "next_action": "Start the first original Reel now",
    }
    result = run_cli("validate", payload)
    assert result.returncode != 0
    assert "session_established" in result.stderr


def test_removed_warmup_progress_kind_is_rejected() -> None:
    payload = {
        "schema_version": 1,
        "kind": "lifecycle_progress",
        "owner": "marketer",
        "handle": "capafy.skills25042",
        "before_status": "warmup_1_of_2",
        "status": "noncommercial_ready",
        "warmup_successes": 2,
        "capability": "noncommercial_post",
        "public_post_url": None,
        "next_action": "Create the first non-commercial Reel",
    }
    result = run_cli("validate", payload)
    assert result.returncode != 0
    assert "unsupported kind" in result.stderr.lower()


def test_money_dimensions_remain_separate_in_rendered_message() -> None:
    result = run_cli("render", builder_submission())

    assert result.returncode == 0, result.stderr
    assert "Lifetime gross: $9.99" in result.stdout
    assert "Pending seller balance: $8.00" in result.stdout
    assert "Realized bank payout: $0.00" in result.stdout
    assert "MRR: $0.00" in result.stdout
    assert "Model/tool cost: $4.78" in result.stdout
    assert "Contribution after recorded cost: -$4.78" in result.stdout


def test_august_first_repair_closure_contains_verified_evidence() -> None:
    payload = builder_submission() | {
        "kind": "repair_closure",
        "incident_id": "capafy-builder-20260801T081400Z-a1b2c3d4",
        "detected_summary": "The Builder could not submit because browser ownership collided.",
        "repair_summary": "Separated browser ownership and resumed the same submission.",
    }

    result = run_cli("render", payload)

    assert result.returncode == 0, result.stderr
    assert "no action needed" in result.stdout.lower()
    assert "9480246345" in result.stdout
    assert "status 1" in result.stdout
    assert "skill/config confirmed" in result.stdout.lower()
    assert payload["listing_url"] in result.stdout


def test_same_outcome_has_stable_delivery_key() -> None:
    first = run_cli("delivery-key", builder_submission())
    second = run_cli("delivery-key", builder_submission())

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout.strip() == second.stdout.strip()
    assert len(first.stdout.strip()) == 64


def test_start_incident_creates_atomic_record_and_returns_id(tmp_path: Path) -> None:
    result = run_cli_args(
        "start-incident",
        "--owner",
        "builder",
        "--summary",
        "Browser ownership collided",
        "--fingerprint",
        "browser-owner-collision",
        "--repair-result-path",
        "/tmp/.self-fix-capafy-loop.result",
        state_dir=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    created = json.loads(result.stdout)
    assert created["incident_id"].startswith("capafy-builder-")
    assert created["phase"] == "detected"
    record_path = tmp_path / "capafy-incidents" / f"{created['incident_id']}.json"
    assert json.loads(record_path.read_text()) == created
    assert list(record_path.parent.glob("*.tmp")) == []


def test_incident_cli_writes_each_phase_once_to_state_scoped_ledger(
    tmp_path: Path,
) -> None:
    started = run_cli_args(
        "start-incident",
        "--owner",
        "builder",
        "--summary",
        "Browser ownership collided",
        "--fingerprint",
        "browser-owner-collision",
        state_dir=tmp_path,
    )

    assert started.returncode == 0, started.stderr
    incident_id = json.loads(started.stdout)["incident_id"]
    update = {"incident_id": incident_id, "phase": "repair_started"}
    first = run_cli_args(
        "transition-incident", payload=update, state_dir=tmp_path
    )
    retry = run_cli_args(
        "transition-incident", payload=update, state_dir=tmp_path
    )

    assert first.returncode == 0, first.stderr
    assert retry.returncode == 0, retry.stderr
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert [event["event_id"] for event in events] == [
        f"capafy:incident.detected:{incident_id}",
        f"capafy:incident.repair_started:{incident_id}",
    ]
    evidence_dir = tmp_path / "capafy-revenue-evidence"
    assert len(list(evidence_dir.glob("*.json"))) == 2


def test_incident_cli_persists_state_before_failed_append_and_retry_heals(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    ledger.write_text("not-json\n")
    args = (
        "start-incident",
        "--owner",
        "marketer",
        "--summary",
        "Revenue ledger was corrupt",
        "--fingerprint",
        "ledger-corrupt",
    )

    failed = run_cli_args(*args, state_dir=tmp_path)

    assert failed.returncode != 0
    records = list((tmp_path / "capafy-incidents").glob("*.json"))
    assert len(records) == 1
    incident_id = json.loads(records[0].read_text())["incident_id"]

    ledger.unlink()
    healed = run_cli_args(*args, state_dir=tmp_path)

    assert healed.returncode == 0, healed.stderr
    assert json.loads(healed.stdout)["incident_id"] == incident_id
    event = json.loads(ledger.read_text())
    assert event["event_id"] == f"capafy:incident.detected:{incident_id}"


def test_same_active_fingerprint_reuses_incident_id(tmp_path: Path) -> None:
    args = (
        "start-incident",
        "--owner",
        "builder",
        "--summary",
        "Browser ownership collided",
        "--fingerprint",
        "browser-owner-collision",
        "--repair-result-path",
        "/tmp/.self-fix-capafy-loop.result",
    )

    first = run_cli_args(*args, state_dir=tmp_path)
    second = run_cli_args(*args, state_dir=tmp_path)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert json.loads(first.stdout)["incident_id"] == json.loads(second.stdout)["incident_id"]
    assert len(list((tmp_path / "capafy-incidents").glob("*.json"))) == 1


def test_incident_phase_cannot_move_backwards(tmp_path: Path) -> None:
    started = run_cli_args(
        "start-incident",
        "--owner",
        "builder",
        "--summary",
        "Browser ownership collided",
        "--fingerprint",
        "browser-owner-collision",
        state_dir=tmp_path,
    )
    incident_id = json.loads(started.stdout)["incident_id"]
    moved = run_cli_args(
        "transition-incident",
        payload={"incident_id": incident_id, "phase": "repair_started"},
        state_dir=tmp_path,
    )
    backwards = run_cli_args(
        "transition-incident",
        payload={"incident_id": incident_id, "phase": "detected"},
        state_dir=tmp_path,
    )

    assert moved.returncode == 0, moved.stderr
    assert json.loads(moved.stdout)["phase"] == "repair_started"
    assert backwards.returncode != 0
    assert "backwards" in backwards.stderr.lower()


def test_get_active_incident_returns_same_unresolved_story(tmp_path: Path) -> None:
    started = run_cli_args(
        "start-incident",
        "--owner",
        "marketer",
        "--summary",
        "Instagram returned a challenge",
        "--fingerprint",
        "instagram-challenge",
        state_dir=tmp_path,
    )
    incident_id = json.loads(started.stdout)["incident_id"]
    unresolved = run_cli_args(
        "transition-incident",
        payload={
            "incident_id": incident_id,
            "phase": "unresolved",
            "next_retry_at": "2026-08-01T18:00:00+09:00",
        },
        state_dir=tmp_path,
    )
    active = run_cli_args(
        "get-active-incident", "--owner", "marketer", state_dir=tmp_path
    )

    assert unresolved.returncode == 0, unresolved.stderr
    assert active.returncode == 0, active.stderr
    assert json.loads(active.stdout)["incident_id"] == incident_id
