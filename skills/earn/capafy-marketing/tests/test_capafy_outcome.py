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
