import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_event_adapters as adapters
import capafy_event_projection as projection
import capafy_event_sync as sync
import capafy_experiment
from test_capafy_experiment import proposal as experiment_proposal


def stored(event: dict, recorded_at: str) -> dict:
    return event | {"recorded_at": recorded_at}


def fixture_events() -> list[dict]:
    listing = adapters.events_from_outcome(
        {
            "schema_version": 1,
            "kind": "builder_submitted",
            "owner": "builder",
            "title": "Decision Debate",
            "agent_id": "4866150011",
            "remote_status": 4,
            "skills_confirmed": True,
            "config_confirmed": True,
            "listing_url": "https://capafy.ai/agent/4866150011",
            "gross_usd": 9.99,
            "pending_usd": 8,
            "realized_usd": 0,
            "mrr_usd": 0,
            "cost_usd": 4.78,
            "contribution_usd": -4.78,
            "next_action": "market it",
        },
        "2026-08-01T10:00:00Z",
    )[0]
    account = adapters.events_from_outcome(
        {
            "schema_version": 1,
            "kind": "account_created",
            "owner": "marketer",
            "handle": "capafy.skills8m4q2z",
            "session_owner": "browser",
            "session_established": True,
            "capability": "publish_probe",
            "public_post_url": None,
            "next_action": "publish now",
        },
        "2026-08-01T10:01:00Z",
    )
    published = adapters.events_from_outcome(
        {
            "schema_version": 1,
            "kind": "marketing_published",
            "owner": "marketer",
            "handle": "capafy.skills8m4q2z",
            "title": "Decision Debate",
            "agent_id": "4866150011",
            "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
            "listing_url": "https://capafy.ai/agent/4866150011",
            "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram",
            "caption": "Make the tradeoff visible.",
            "media_path": "/private/tmp/reel.mp4",
            "owner_session_verified": True,
        },
        "2026-08-01T10:02:00Z",
    )
    measured = sync.events_from_ig_metrics(
        [
            {
                "ts": 1785578580,
                "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                "agent_id": "4866150011",
                "views": 10,
                "likes": 1,
                "comments": 0,
            },
            {
                "ts": 1785578640,
                "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                "agent_id": "4866150011",
                "views": 25,
                "likes": 2,
                "comments": 1,
            },
        ]
    )
    campaign = sync.events_from_attribution_rows(
        [
            {
                "date": "2026-08-01",
                "agents": [{"agent_id": "4866150011", "clicks": 5}],
            }
        ],
        {"4866150011": 2},
    )
    money = (
        sync.events_from_sales_rows(
            [
                {
                    "ts": 1782172800,
                    "source": "capafy-sales",
                    "date": "2026-06-23",
                    "orders": 1,
                    "gross_usd": 9.99,
                }
            ]
        )
        + sync.events_from_payout_rows(
            [
                {
                    "ts": 1784330227,
                    "source": "capafy-payout",
                    "date": "2026-07-18",
                    "balance_payout_usd": 8,
                    "total_payout_usd": 0,
                }
            ]
        )
        + sync.events_from_cost_rows(
            [{"ts": 1785539400, "provider": "openrouter", "total_usage_usd": 4.776}]
        )
    )
    events = [listing, *account, *published, *measured, *campaign, *money]
    return [
        stored(event, f"2026-08-01T12:{index:02d}:00Z")
        for index, event in enumerate(events)
    ]


def test_projection_folds_money_inventory_account_urls_and_latest_metrics() -> None:
    result = projection.project_company(fixture_events())

    assert result["inventory"] == {
        "online": 1,
        "under_review": 0,
        "draft": 0,
        "rejected": 0,
    }
    assert result["orders"] == 1
    assert result["gross_usd"] == "9.99"
    assert result["pending_usd"] == "8.00"
    assert result["realized_usd"] == "0.00"
    assert result["mrr_usd"] == "0.00"
    assert result["cost_usd"] == "4.78"
    assert result["contribution_usd"] == "-4.78"
    assert result["metrics"] == {
        "views": 25,
        "likes": 2,
        "comments": 1,
        "clicks": 3,
    }
    assert result["account"]["handle"] == "capafy.skills8m4q2z"
    assert result["account"]["lifecycle_status"] == "commercial_ready"
    assert result["account"]["capability"] == "commercial_post"
    assert result["account"]["session_established"] is True
    assert result["account"]["post_write_session_verified"] is True
    assert result["marketing"]["public_post_url"] == (
        "https://www.instagram.com/reel/DbgsvEbo5kd/"
    )
    assert result["listing_url"] == "https://capafy.ai/agent/4866150011"


def test_projection_id_is_deterministic_and_changes_after_one_event() -> None:
    events = fixture_events()

    first = projection.project_company(events)
    retry = projection.project_company(events)
    changed = projection.project_company(
        events
        + [
            stored(
                sync.events_from_attribution_rows(
                    [
                        {
                            "date": "2026-08-02",
                            "agents": [{"agent_id": "4866150011", "clicks": 8}],
                        }
                    ],
                    {"4866150011": 2},
                )[0],
                "2026-08-02T12:00:00Z",
            )
        ]
    )

    assert first == retry
    assert first["projection_id"].startswith("sha256:")
    assert changed["projection_id"] != first["projection_id"]
    assert changed["metrics"]["clicks"] == 6


def test_projection_exposes_active_experiment_without_counting_projection_as_revenue() -> None:
    event = capafy_experiment.activation_event(
        experiment_proposal("one_time"), "2026-08-02T13:31:00Z"
    )

    result = projection.project_company(fixture_events() + [event])

    assert result["experiment"] == {
        "experiment_id": "capafy-exp-meeting-notes-001",
        "agent_id": "3947077924",
        "owner": "marketer",
        "status": "active",
        "purchase_model": "one_time",
        "price_usd": "10.00",
        "projected_contribution_usd": "75.00",
        "observed_contribution_usd": None,
        "success_metric": "attributed paid orders and positive contribution",
        "stop_condition": "Stop after 100 verified campaign visits with zero paid orders.",
        "stop_reason": None,
        "public_url": "https://capafy.ai/agent/3947077924",
    }
    assert result["gross_usd"] == "9.99"
    assert result["contribution_usd"] == "-4.78"


def test_projection_reports_stopped_experiment_and_reason_honestly() -> None:
    value = experiment_proposal("one_time")
    activated = capafy_experiment.activation_event(value, "2026-08-02T13:31:00Z")
    stopped = capafy_experiment.stopped_event(
        value, "The live Agent cannot change to Download.", "2026-08-02T13:40:00Z"
    )

    result = projection.project_company(fixture_events() + [activated, stopped])

    assert result["experiment"]["status"] == "stopped"
    assert result["experiment"]["stop_reason"] == "The live Agent cannot change to Download."
    assert result["experiment"]["observed_contribution_usd"] is None


def test_latest_listing_status_overrides_stale_experiment_evidence_url() -> None:
    value = experiment_proposal("one_time")
    activated = capafy_experiment.activation_event(value, "2026-08-02T13:31:00Z")
    stopped = capafy_experiment.stopped_event(
        value, "The live Agent cannot change to Download.", "2026-08-02T13:40:00Z"
    )
    draft = sync.events_from_inventory_agents(
        [
            {
                "agentId": value["agent_id"],
                "agentStatus": "draft",
                "updatedAt": 1785678600000,
            }
        ]
    )[0]

    result = projection.project_company(
        fixture_events()
        + [activated, stopped, stored(draft, "2026-08-02T13:50:01Z")]
    )

    assert result["experiment"]["status"] == "stopped"
    assert result["experiment"]["public_url"] is None


def test_verified_publication_advances_account_to_immediate_commercial_capability() -> None:
    result = projection.project_company(fixture_events())
    assert result["account"]["lifecycle_status"] == "commercial_ready"
    assert result["account"]["capability"] == "commercial_post"
    assert result["account"]["post_write_session_verified"] is True


def test_duplicate_event_identifier_fails_closed() -> None:
    event = fixture_events()[0]

    with pytest.raises(ValueError, match="duplicate event_id"):
        projection.project_company([event, dict(event)])


def test_verified_incident_is_not_active_but_unresolved_incident_is() -> None:
    base = fixture_events()
    record = {
        "schema_version": 1,
        "incident_id": "capafy-marketer-20260802T120000Z-deadbeef",
        "owner": "marketer",
        "phase": "unresolved",
        "phase_timestamps": {"unresolved": "2026-08-02T12:00:00Z"},
        "summary": "Instagram readback failed.",
        "repair_summary": "Reattached the owner browser once.",
        "next_retry_at": "2026-08-02T12:05:00Z",
    }
    unresolved = stored(
        adapters.event_from_incident(record), "2026-08-02T12:00:01Z"
    )
    active = projection.project_company(base + [unresolved])

    assert active["incident"] == {
        "incident_id": record["incident_id"],
        "owner": "marketer",
        "summary": "Instagram readback failed.",
        "phase": "unresolved",
        "next_retry_at": "2026-08-02T12:05:00Z",
    }

    record["phase"] = "verified"
    record["phase_timestamps"]["verified"] = "2026-08-02T12:06:00Z"
    record["verification"] = {"owner_readback": True}
    verified = stored(adapters.event_from_incident(record), "2026-08-02T12:06:01Z")

    assert projection.project_company(base + [unresolved, verified])["incident"] is None


def test_project_cli_reads_validated_jsonl(tmp_path: Path) -> None:
    ledger = tmp_path / "events.jsonl"
    ledger.write_text(
        "\n".join(json.dumps(event) for event in fixture_events()) + "\n"
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "capafy_event_projection.py"), "project", "--ledger", str(ledger)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["orders"] == 1


def test_parity_gate_accepts_equivalent_sources_and_rejects_contradiction() -> None:
    projected = projection.project_company(fixture_events())
    independent = {
        field: projected[field]
        for field in (
            "inventory",
            "orders",
            "gross_usd",
            "pending_usd",
            "realized_usd",
            "mrr_usd",
            "cost_usd",
            "contribution_usd",
            "account",
            "marketing",
            "incident",
        )
    }
    independent["cost_usd"] = 4.776
    independent["contribution_usd"] = -4.776

    assert projection.parity_errors(projected, independent) == []

    independent["gross_usd"] = 999
    assert projection.parity_errors(projected, independent) == [
        "gross_usd mismatch: projection='9.99' source='999.00'"
    ]


def test_goal_monitor_reports_projection_ignores_legacy_builder_and_blocks_mismatch(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    state = home / ".openclaw/state"
    ledger = state / "capafy-revenue-events.jsonl"
    evidence = state / "capafy-revenue-evidence"
    tmp = tmp_path / "tmp"
    for directory in (
        state,
        home / ".openclaw/logs",
        home / "anicca/skills/self/capafy-loop/state",
        home / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher",
        tmp,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    ledger.write_text("\n".join(json.dumps(event) for event in fixture_events()) + "\n")
    (home / "anicca/skills/self/capafy-loop/state/STATE.md").write_text(
        "capafy_lifetime_orders: 1\n"
        "capafy_lifetime_gross_usd: 9.99\n"
        "capafy_seller_balance_pending_usd: 8.00\n"
        "capafy_realized_payout_usd: 0.00\n"
        "capafy_mrr_usd: 0.00\n"
    )
    (home / ".openclaw/logs/capafy-loop-daily.log").write_text(
        json.dumps(
            {"provider": "openrouter", "total_usage_usd": 4.776}
        )
        + "\n"
    )
    (state / "capafy-ig-lifecycle.json").write_text(
        json.dumps(
            {
                "handle": "capafy.skills8m4q2z",
                "status": "commercial_ready",
                "capability": "commercial_post",
                "session_established": True,
                "post_write_session_verified": True,
                "replacement_requested": False,
            }
        )
    )
    (state / "capafy-marketing-terminal.json").write_text(
        json.dumps(
            {
                "outcome": {
                    "kind": "marketing_published",
                    "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                    "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram",
                }
            }
        )
    )
    (state / "capafy-builder-terminal.json").write_text(
        json.dumps(
            {
                "outcome": {
                    "gross_usd": 999999,
                    "listing_url": "https://capafy.ai/agent/wrong-legacy-value",
                }
            }
        )
    )
    publisher = home / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher"
    (publisher / "packager.py").write_text(
        'import json\nprint(json.dumps({"agents":{"list":[{"agentStatus":"online"}]}}))\n'
    )
    helper = tmp_path / "account_state.sh"
    helper.write_text(
        "capafy_ig_accounts_file() { printf '%s\\n' \"$HOME/accounts.jsonl\"; }\n"
        "resolve_capafy_ig_handle() { printf '%s\\n' capafy.skills8m4q2z; }\n"
        "resolve_capafy_ig_port() { printf '%s\\n' 65063; }\n"
    )
    fake_sync = tmp_path / "sync.py"
    fake_sync.write_text("raise SystemExit(0)\n")
    sent = tmp_path / "telegram.txt"
    sender = tmp_path / "send.sh"
    sender.write_text(
        f"printf '%s\\n' \"$1\" >> '{sent}'\n"
        "printf '%s\\n' 'TELEGRAM_SENT=true MSGID=777'\n"
    )
    env = os.environ | {
        "HOME": str(home),
        "CAPAFY_ACCOUNT_STATE_HELPER": str(helper),
        "CAPAFY_IG_LIFECYCLE_STATE": str(state / "capafy-ig-lifecycle.json"),
        "CAPAFY_EVENT_LEDGER": str(ledger),
        "CAPAFY_EVENT_EVIDENCE_DIR": str(evidence),
        "CAPAFY_EVENT_SYNC": str(fake_sync),
        "CAPAFY_EVENT_PROJECTION": str(SCRIPTS / "capafy_event_projection.py"),
        "CAPAFY_COMPANY_DASHBOARD_BUILDER": str(
            SCRIPTS / "build_company_dashboard.py"
        ),
        "CAPAFY_COMPANY_DASHBOARD_DIR": str(tmp_path / "site/company"),
        "CAPAFY_GOAL_MONITOR_TMP_DIR": str(tmp),
        "CAPAFY_TELEGRAM_SENDER": str(sender),
    }
    goal_monitor = SCRIPTS.parent / "capafy-goal-monitor.sh"

    clean = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )

    assert clean.returncode == 0, clean.stderr
    report = json.loads(clean.stdout)
    expected = projection.project_company(fixture_events())
    assert report["company_state"] == expected
    assert json.loads((tmp_path / "site/company/state.json").read_text()) == expected
    assert "wrong-legacy-value" not in sent.read_text()
    assert expected["projection_id"].removeprefix("sha256:")[:12] in sent.read_text()

    duplicate = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )
    assert duplicate.returncode == 0, duplicate.stderr
    assert sent.read_text().count("Capafy — Consolidated company state") == 1

    state_md = home / "anicca/skills/self/capafy-loop/state/STATE.md"
    state_md.write_text(state_md.read_text().replace("9.99", "999.00"))
    mismatch = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )

    assert mismatch.returncode == 3
    assert "gross_usd mismatch" in mismatch.stderr
    assert sent.read_text().count("Capafy — Consolidated company state") == 1
    incidents = list((state / "capafy-incidents").glob("*.json"))
    assert len(incidents) == 1
