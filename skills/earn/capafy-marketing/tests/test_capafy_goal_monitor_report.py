import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_outcome.py"


def test_august_first_company_state_is_natural_and_truthful() -> None:
    payload = {
        "schema_version": 1,
        "kind": "company_state",
        "date": "2026-08-01",
        "inventory": {"online": 27, "under_review": 1, "draft": 2, "rejected": 1},
        "orders": 1,
        "gross_usd": 9.99,
        "pending_usd": 8.0,
        "realized_usd": 0.0,
        "mrr_usd": 0.0,
        "cost_usd": 4.777,
        "contribution_usd": -4.777,
        "account": {
            "handle": "capafy.skills10491",
            "lifecycle_status": "publish_probe_ready",
            "capability": "publish_probe",
            "session_established": True,
            "post_write_session_verified": False,
            "account_status": "clean",
        },
        "marketing": {"scheduler_loaded": True, "public_post_url": None},
        "incident": {
            "summary": "The Instagram agent runner timed out at 180 seconds",
            "phase": "repair_started",
            "next_retry_at": "2026-08-01T16:00:00+09:00",
        },
        "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review",
        "dashboard_url": "https://capafy-skills-daily.netlify.app",
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "render"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = result.stdout
    assert "27 online, 1 under review, 2 drafts" in report
    assert "1 lifetime order / $9.99 gross" in report
    assert "Pending seller balance: $8.00" in report
    assert "Realized bank payout: $0.00" in report
    assert "MRR: $0.00" in report
    assert "Model/tool cost: $4.78" in report
    assert "Contribution after recorded cost: -$4.78" in report
    assert "publish_probe_ready" in report
    assert "posting session is established" in report
    assert "Account status: clean" in report
    assert "calendar" not in report.lower()
    assert "warmup" not in report.lower()
    assert "Marketing is scheduled" in report
    assert "no public post is verified" in report
    assert "repair_started" in report
    assert payload["listing_url"] in report
    assert payload["dashboard_url"] in report
    assert "goal(a)" not in report
    assert "already_live" not in report
    assert "goal(d) health" not in report


def test_singular_inventory_nouns_are_grammatical() -> None:
    payload = {
        "schema_version": 1,
        "kind": "company_state",
        "date": "2026-08-01",
        "inventory": {"online": 1, "under_review": 1, "draft": 1, "rejected": 1},
        "orders": 0,
        "gross_usd": 0,
        "pending_usd": 0,
        "realized_usd": 0,
        "mrr_usd": 0,
        "cost_usd": 0,
        "contribution_usd": 0,
        "account": {"handle": "no-active-account", "lifecycle_status": "replacement_requested", "capability": "none", "session_established": False, "post_write_session_verified": False, "account_status": "replacement requested"},
        "marketing": {"scheduler_loaded": True, "public_post_url": None},
        "incident": None,
        "listing_url": None,
        "dashboard_url": "https://capafy-skills-daily.netlify.app",
    }
    result = subprocess.run([sys.executable, str(SCRIPT), "render"], input=json.dumps(payload), text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert "1 online, 1 under review, 1 draft, 1 rejected" in result.stdout
    assert "1 drafts" not in result.stdout
