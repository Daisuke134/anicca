import copy
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_event_adapters as adapters
import capafy_event_store as store


OCCURRED_AT = "2026-08-01T20:32:53Z"


def incident_record(
    phase: str = "unresolved",
    *,
    retry_at: str | None = "2026-08-07T04:50:52Z",
    attempts: int = 0,
) -> dict:
    return {
        "schema_version": 1,
        "incident_id": "capafy-marketer-20260803T070010Z-99b1374a",
        "owner": "capafy-marketer",
        "phase": phase,
        "detected_at": "2026-08-03T07:00:10Z",
        "updated_at": "2026-08-07T04:00:00Z",
        "phase_timestamps": {
            "detected": "2026-08-03T07:00:10Z",
            "repair_started": "2026-08-03T07:01:00Z",
            "repaired": "2026-08-03T07:02:00Z",
            "verified": "2026-08-03T07:03:00Z",
            "unresolved": "2026-08-07T04:00:00Z",
        },
        "summary": "Canonical revenue source sync failed.",
        "repair_summary": "The retry did not restore the canonical writer.",
        "verification": {"event_sync_succeeded": True} if phase == "verified" else None,
        "next_retry_at": retry_at,
        "attempts": attempts,
    }


def builder_submitted() -> dict:
    return {
        "schema_version": 1,
        "kind": "builder_submitted",
        "owner": "builder",
        "title": "Portfolio Tracker — Daily Position Review",
        "agent_id": "9480246345",
        "remote_status": 1,
        "skills_confirmed": True,
        "config_confirmed": True,
        "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&page=review",
        "gross_usd": 9.99,
        "pending_usd": 8.0,
        "realized_usd": 0.0,
        "mrr_usd": 0.0,
        "cost_usd": 4.777,
        "contribution_usd": -4.777,
        "next_action": "Watch for approval and hand the public listing to Marketing",
    }


def marketing_published() -> dict:
    return {
        "schema_version": 1,
        "kind": "marketing_published",
        "owner": "marketer",
        "handle": "capafy.skills8m4q2z",
        "title": "Decision Debate",
        "agent_id": "4866150011",
        "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
        "listing_url": "https://capafy.ai/agent/4866150011",
        "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram&utm_medium=reel&utm_campaign=capafy-skill",
        "caption": "Make the tradeoff visible before the meeting.",
        "media_path": "/private/tmp/decision-debate.mp4",
        "owner_session_verified": True,
    }


def account_created() -> dict:
    return {
        "schema_version": 1,
        "kind": "account_created",
        "owner": "marketer",
        "handle": "capafy.skills8m4q2z",
        "session_owner": "browser",
        "session_established": True,
        "capability": "publish_probe",
        "public_post_url": None,
        "next_action": "publish and verify the first original product-education Reel",
    }


def test_builder_submission_emits_one_listing_event_without_snapshot_money() -> None:
    events = adapters.events_from_outcome(builder_submitted(), OCCURRED_AT, "builder-pass-1")

    assert [event["event_id"] for event in events] == [
        "capafy:listing.submitted:9480246345:status-1"
    ]
    assert events[0]["event_type"] == "listing.submitted"
    assert events[0]["entity"] == {"type": "listing", "id": "9480246345"}
    assert events[0]["occurred_at"] == OCCURRED_AT
    assert "recorded_at" not in events[0]
    assert set(events[0]["money"].values()) == {"USD", "0.00"}
    assert events[0]["public_evidence"]["urls"] == [builder_submitted()["listing_url"]]


def test_published_reel_emits_content_and_owner_proof_events() -> None:
    events = adapters.events_from_outcome(marketing_published(), OCCURRED_AT, "marketer-pass-1")

    assert [event["event_id"] for event in events] == [
        "capafy:content.published:instagram:DbgsvEbo5kd",
        "capafy:account.post_verified:capafy.skills8m4q2z:DbgsvEbo5kd",
        "capafy:account.commercial_ready:capafy.skills8m4q2z:DbgsvEbo5kd",
    ]
    assert [event["event_type"] for event in events] == [
        "content.published",
        "account.post_verified",
        "account.commercial_ready",
    ]
    assert events[0]["public_evidence"]["urls"] == [
        marketing_published()["reel_url"],
        marketing_published()["listing_url"],
        marketing_published()["campaign_url"],
    ]
    assert events[1]["entity"] == {"type": "account", "id": "capafy.skills8m4q2z"}
    assert "/private/tmp/decision-debate.mp4" not in str(events)


def test_published_reel_uses_persisted_time_without_changing_source_identity() -> None:
    original = marketing_published()
    persisted = dict(original, published_at="2026-08-02T12:34:56Z")

    first = adapters.events_from_outcome(original, OCCURRED_AT)[0]
    retry = adapters.events_from_outcome(persisted, "2026-08-02T13:00:00Z")[0]

    assert retry["occurred_at"] == "2026-08-02T12:34:56Z"
    assert retry["source"] == first["source"]


def test_verified_account_creation_emits_created_session_and_capability_events() -> None:
    events = adapters.events_from_outcome(account_created(), OCCURRED_AT, None)

    assert [event["event_id"] for event in events] == [
        "capafy:account.created:capafy.skills8m4q2z",
        "capafy:account.session_ready:capafy.skills8m4q2z",
        "capafy:account.publish_probe_ready:capafy.skills8m4q2z",
    ]
    assert [event["event_type"] for event in events] == [
        "account.created",
        "account.session_ready",
        "account.publish_probe_ready",
    ]


def test_lifecycle_transition_emits_only_new_verified_capabilities() -> None:
    before = {
        "handle": "capafy.skills8m4q2z",
        "status": "provisioning",
        "session_established": False,
        "capability": "none",
    }
    after = {
        "handle": "capafy.skills8m4q2z",
        "status": "publish_probe_ready",
        "session_established": True,
        "capability": "publish_probe",
    }

    events = adapters.events_from_lifecycle(before, after, OCCURRED_AT)

    assert [event["event_type"] for event in events] == [
        "account.session_ready",
        "account.publish_probe_ready",
    ]


def test_dry_noop_or_unverified_outcomes_emit_no_success_event() -> None:
    dry = marketing_published() | {"kind": "marketing_dry"}
    noop = builder_submitted() | {"kind": "builder_noop", "reason": "cap full"}
    missing_owner = marketing_published() | {"owner_session_verified": False}

    assert adapters.events_from_outcome(dry, OCCURRED_AT, None) == []
    assert adapters.events_from_outcome(noop, OCCURRED_AT, None) == []
    assert adapters.events_from_outcome(missing_owner, OCCURRED_AT, None) == []


def test_non_https_success_evidence_emits_no_event() -> None:
    outcome = marketing_published()
    outcome["reel_url"] = "http://instagram.com/reel/DbgsvEbo5kd/"

    assert adapters.events_from_outcome(outcome, OCCURRED_AT, None) == []


def test_source_identity_is_deterministic_and_changes_with_source() -> None:
    first = adapters.events_from_outcome(marketing_published(), OCCURRED_AT, None)
    retry = adapters.events_from_outcome(marketing_published(), OCCURRED_AT, None)
    changed = marketing_published()
    changed["caption"] = "A changed source envelope."
    mutated = adapters.events_from_outcome(changed, OCCURRED_AT, None)

    assert first[0]["source"] == retry[0]["source"]
    assert first[0]["source"]["source_digest"].startswith("sha256:")
    assert first[0]["source"]["source_digest"] != mutated[0]["source"]["source_digest"]


def test_unresolved_retry_occurrences_coexist_with_legacy_row_and_replay_exactly(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "evidence"
    legacy_record = incident_record(retry_at=None)
    legacy_event = adapters.event_from_incident(legacy_record)
    assert legacy_event["event_id"] == (
        "capafy:incident.unresolved:capafy-marketer-20260803T070010Z-99b1374a"
    )
    assert store.append_event(ledger, legacy_event, legacy_record, evidence_dir).appended

    current_record = copy.deepcopy(legacy_record)
    current_record["next_retry_at"] = "2026-08-07T04:50:52Z"
    current_event = adapters.event_from_incident(current_record)
    assert current_event["event_id"] == (
        "capafy:incident.unresolved:capafy-marketer-20260803T070010Z-99b1374a:retry-20260807T045052Z"
    )
    first = store.append_event(ledger, current_event, current_record, evidence_dir)
    retry = store.append_event(
        ledger,
        adapters.event_from_incident(current_record),
        current_record,
        evidence_dir,
    )

    assert first.appended is True
    assert retry.appended is False
    assert len(store.read_events(ledger)) == 2

    changed = copy.deepcopy(current_record)
    changed["next_retry_at"] = "2026-08-07T05:50:52Z"
    changed_result = store.append_event(
        ledger,
        adapters.event_from_incident(changed),
        changed,
        evidence_dir,
    )
    assert changed_result.appended is True
    assert len(store.read_events(ledger)) == 3


def test_recurrent_incident_phases_use_attempt_suffix_but_attempt_zero_ids_stay_legacy() -> None:
    first_cycle = [
        adapters.event_from_incident(incident_record(phase, attempts=0))
        for phase in ("repair_started", "repaired", "verified")
    ]
    recurring_cycle = [
        adapters.event_from_incident(incident_record(phase, attempts=1))
        for phase in ("repair_started", "repaired", "verified")
    ]

    assert [event["event_id"] for event in first_cycle] == [
        "capafy:incident.repair_started:capafy-marketer-20260803T070010Z-99b1374a",
        "capafy:incident.repaired:capafy-marketer-20260803T070010Z-99b1374a",
        "capafy:incident.verified:capafy-marketer-20260803T070010Z-99b1374a",
    ]
    assert [event["event_id"] for event in recurring_cycle] == [
        "capafy:incident.repair_started:capafy-marketer-20260803T070010Z-99b1374a:attempt-1",
        "capafy:incident.repaired:capafy-marketer-20260803T070010Z-99b1374a:attempt-1",
        "capafy:incident.verified:capafy-marketer-20260803T070010Z-99b1374a:attempt-1",
    ]


def test_append_outcome_cli_uses_source_mtime_and_retries_without_duplicates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "marketing-result.json"
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "private-evidence"
    source.write_text(json.dumps(marketing_published()))
    occurred = datetime(2026, 8, 1, 20, 32, 53, tzinfo=timezone.utc).timestamp()
    os.utime(source, (occurred, occurred))
    command = [
        sys.executable,
        str(SCRIPTS / "capafy_event_adapters.py"),
        "append-outcome",
        "--source",
        str(source),
        "--ledger",
        str(ledger),
        "--evidence-dir",
        str(evidence_dir),
        "--technical-evidence-dir",
        "/private/runner-evidence/marketer-pass-1",
        "--correlation-id",
        "marketer-pass-1",
    ]

    first = subprocess.run(command, text=True, capture_output=True, check=False)
    retry = subprocess.run(command, text=True, capture_output=True, check=False)

    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout) == {
        "appended": 3,
        "duplicates": 0,
        "event_ids": [
            "capafy:content.published:instagram:DbgsvEbo5kd",
            "capafy:account.post_verified:capafy.skills8m4q2z:DbgsvEbo5kd",
            "capafy:account.commercial_ready:capafy.skills8m4q2z:DbgsvEbo5kd",
        ],
        "observed": 3,
    }
    assert retry.returncode == 0, retry.stderr
    assert json.loads(retry.stdout)["appended"] == 0
    assert json.loads(retry.stdout)["duplicates"] == 3
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(rows) == 3
    assert {row["occurred_at"] for row in rows} == {OCCURRED_AT}
    sidecar = evidence_dir / "capafy:content.published:instagram:DbgsvEbo5kd.json"
    technical = json.loads(sidecar.read_text())
    assert technical["source"] == marketing_published()
    assert technical["evidence_directory"] == "/private/runner-evidence/marketer-pass-1"


def test_append_lifecycle_cli_writes_only_new_capability_events(tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence_dir = tmp_path / "private-evidence"
    before.write_text(
        json.dumps(
            {
                "handle": "capafy.skills8m4q2z",
                "status": "provisioning",
                "session_established": False,
                "capability": "none",
            }
        )
    )
    after.write_text(
        json.dumps(
            {
                "handle": "capafy.skills8m4q2z",
                "status": "publish_probe_ready",
                "session_established": True,
                "capability": "publish_probe",
            }
        )
    )
    occurred = datetime(2026, 8, 1, 20, 32, 53, tzinfo=timezone.utc).timestamp()
    os.utime(after, (occurred, occurred))

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "capafy_event_adapters.py"),
            "append-lifecycle",
            "--before",
            str(before),
            "--after",
            str(after),
            "--ledger",
            str(ledger),
            "--evidence-dir",
            str(evidence_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "appended": 2,
        "duplicates": 0,
        "event_ids": [
            "capafy:account.session_ready:capafy.skills8m4q2z",
            "capafy:account.publish_probe_ready:capafy.skills8m4q2z",
        ],
        "observed": 2,
    }
