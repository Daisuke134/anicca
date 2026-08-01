import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_outcome.py"


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
        "calendar_warmup_day": 3,
        "session_established": False,
        "public_post_url": None,
    }

    result = run_cli("render", payload)

    assert result.returncode == 0, result.stderr
    rendered = result.stdout.lower()
    assert "scheduler is loaded" in rendered
    assert "live" not in rendered
    assert "published" not in rendered


def test_calendar_day_three_is_account_age_not_warmup_completion() -> None:
    payload = {
        "schema_version": 1,
        "kind": "account_state",
        "owner": "marketer",
        "handle": "capafy.skills10491",
        "scheduler_loaded": True,
        "calendar_warmup_day": 3,
        "session_established": False,
        "public_post_url": None,
    }

    result = run_cli("render", payload)

    assert result.returncode == 0, result.stderr
    assert "calendar age: day 3" in result.stdout.lower()
    assert "warmup complete" not in result.stdout.lower()


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
