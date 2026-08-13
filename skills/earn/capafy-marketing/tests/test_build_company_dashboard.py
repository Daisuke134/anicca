import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_company_dashboard as dashboard


def company_projection() -> dict:
    return {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": "2026-08-02T12:00:00Z",
        "date": "2026-08-02",
        "last_event_id": "capafy:incident.unresolved:incident-1",
        "projection_id": "sha256:" + "c" * 64,
        "inventory": {"online": 27, "under_review": 2, "draft": 1, "rejected": 1},
        "orders": 1,
        "gross_usd": "9.99",
        "pending_usd": "8.00",
        "realized_usd": "0.00",
        "mrr_usd": "0.00",
        "cost_usd": "4.78",
        "contribution_usd": "-4.78",
        "account": {
            "handle": "capafy.skills8m4q2z",
            "lifecycle_status": "reach_observing",
            "capability": "publish_probe",
            "session_established": True,
            "post_write_session_verified": True,
            "account_status": "clean",
        },
        "marketing": {
            "state": "reach_observing",
            "public_post_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
            "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram",
        },
        "metrics": {"views": 121, "likes": 2, "comments": 1, "clicks": 3},
        "incident": {
            "incident_id": "incident-1",
            "owner": "marketer",
            "summary": "Readback <failed> & retried.",
            "phase": "unresolved",
            "next_retry_at": "2026-08-02T12:05:00Z",
        },
        "experiment": {
            "experiment_id": "exp-7631594519-one-time-download-01",
            "agent_id": "7631594519",
            "owner": "marketer",
            "status": "active",
            "purchase_model": "one_time",
            "price_usd": "49.00",
            "projected_contribution_usd": "392.00",
            "observed_contribution_usd": None,
            "success_metric": "At least one paid download.",
            "stop_condition": "Stop after 10 verified exposures with zero paid downloads.",
            "public_url": "https://capafy.ai/agent/7631594519",
        },
        "listing_url": "https://capafy.ai/agent/4866150011",
        "dashboard_url": "https://capafy-skills-daily.netlify.app/company/",
        "sources": {
            name: {"observed_at": "2026-08-02T12:00:00Z", "freshness": "fresh"}
            for name in ("money", "inventory", "account", "marketing", "cost")
        },
    }


def test_dashboard_is_deterministic_safe_and_contains_projection_evidence(
    tmp_path: Path,
) -> None:
    projection = company_projection()

    first = dashboard.build_dashboard(projection, tmp_path)
    first_html = first.index_path.read_bytes()
    first_state = first.state_path.read_bytes()
    second = dashboard.build_dashboard(projection, tmp_path)

    assert second.index_path.read_bytes() == first_html
    assert second.state_path.read_bytes() == first_state
    assert json.loads(first_state) == projection
    html = first_html.decode()
    assert "Readback &lt;failed&gt; &amp; retried." in html
    assert "Readback <failed>" not in html
    assert projection["projection_id"].removeprefix("sha256:")[:12] in html
    assert projection["marketing"]["public_post_url"] in html
    assert projection["marketing"]["campaign_url"].replace("&", "&amp;") in html
    assert projection["listing_url"] in html
    assert "Gross revenue" in html and "$9.99" in html
    assert "Pending balance" in html and "$8.00" in html
    assert "Realized payout" in html and "$0.00" in html
    assert "MRR" in html and "Model/tool cost" in html and "Contribution" in html
    assert "reach_observing" in html
    assert "unresolved" in html
    assert "Active revenue experiment" in html
    assert "$392.00 projected" in html
    assert "not realized" in html
    assert "https://capafy.ai/agent/7631594519" in html
    assert "/Users/" not in html
    assert "technical_evidence" not in html
    assert "<script" not in html.lower()


def test_dashboard_visibly_labels_source_freshness_and_observed_at() -> None:
    projection = company_projection() | {
        "sources": {
            "money": {"observed_at": "2026-08-02T12:00:00Z", "freshness": "fresh"},
            "inventory": {"observed_at": "2026-07-31T12:00:00Z", "freshness": "stale"},
            "account": {"observed_at": None, "freshness": "unknown"},
            "marketing": {"observed_at": "2026-08-02T12:00:00Z", "freshness": "fresh"},
            "cost": {"observed_at": "2026-07-31T12:00:00Z", "freshness": "stale"},
        }
    }
    html = dashboard.render_html(projection)
    assert "Source freshness" in html
    assert "money" in html and "2026-08-02T12:00:00Z" in html
    assert "STALE" in html and "UNKNOWN" in html
    assert "not current" in html.lower() or "stale" in html.lower()


def test_dashboard_rejects_private_or_credential_bearing_projection(
    tmp_path: Path,
) -> None:
    private = company_projection() | {"debug_path": "/Users/example/private.json"}
    credential = company_projection() | {"token": "secret"}

    with pytest.raises(ValueError, match="unsupported projection fields"):
        dashboard.build_dashboard(private, tmp_path)
    with pytest.raises(ValueError, match="unsupported projection fields"):
        dashboard.build_dashboard(credential, tmp_path)


def test_dashboard_cli_changes_only_company_files(tmp_path: Path) -> None:
    site = tmp_path / "site"
    company = site / "company"
    site.mkdir()
    root = site / "index.html"
    allowed = site / "netlify/functions/allowed-agents.json"
    allowed.parent.mkdir(parents=True)
    root.write_text("root-landing-must-not-change")
    allowed.write_text('["4866150011"]\n')
    source = tmp_path / "projection.json"
    source.write_text(json.dumps(company_projection()))

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "build_company_dashboard.py"),
            "--projection",
            str(source),
            "--output-dir",
            str(company),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["projection_id"] == company_projection()["projection_id"]
    assert root.read_text() == "root-landing-must-not-change"
    assert allowed.read_text() == '["4866150011"]\n'
    assert sorted(path.name for path in company.iterdir()) == ["index.html", "state.json"]


def test_goal_monitor_builds_dashboard_after_parity_and_before_telegram() -> None:
    script = (SCRIPTS.parent / "capafy-goal-monitor.sh").read_text()

    parity_gate = script.index('if [ "$RC" -ne 0 ]')
    dashboard_build = script.index('"$PY" "$COMPANY_DASHBOARD_BUILDER"')
    telegram = script.index('bash "$TELEGRAM_SENDER"')
    assert parity_gate < dashboard_build < telegram
    assert "goal-monitor-dashboard-generation-failed" in script
