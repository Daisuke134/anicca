import json
import subprocess
import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capafy_event_sync as sync


def test_sales_row_emits_order_gross_without_recognizing_contribution() -> None:
    rows = [
        {
            "ts": 1782172800,
            "source": "capafy-sales",
            "date": "2026-06-23",
            "orders": 1,
            "gross_usd": 9.99,
            "net_revenue_usd": 9.99,
            "refund_amount_usd": 0.0,
            "currency": "usd",
        }
    ]

    events = sync.events_from_sales_rows(rows)

    assert len(events) == 1
    assert events[0]["event_type"] == "order.received"
    assert events[0]["money"]["gross_delta"] == "9.99"
    assert events[0]["money"]["contribution_delta"] == "0.00"
    assert events[0]["metrics"] == {"orders": 1}


def test_duplicate_sales_source_date_is_not_counted_twice() -> None:
    row = {
        "ts": 1782172800,
        "source": "capafy-sales",
        "date": "2026-06-23",
        "orders": 1,
        "gross_usd": 9.99,
        "currency": "usd",
    }

    events = sync.events_from_sales_rows([row, dict(row)])

    assert len(events) == 1


def test_payout_snapshots_emit_pending_then_only_positive_realized_delta() -> None:
    rows = [
        {
            "ts": 1784330227,
            "source": "capafy-payout",
            "date": "2026-07-18",
            "balance_payout_usd": 8.0,
            "total_payout_usd": 0.0,
            "currency": "usd",
        },
        {
            "ts": 1784416362,
            "source": "capafy-payout",
            "date": "2026-07-19",
            "balance_payout_usd": 8.0,
            "total_payout_usd": 3.0,
            "currency": "usd",
        },
    ]

    events = sync.events_from_payout_rows(rows)

    pending = [event for event in events if event["event_type"] == "balance.reconciled"]
    realized = [event for event in events if event["event_type"] == "payout.received"]
    assert [event["money"]["pending_delta"] for event in pending] == ["8.00"]
    assert [event["money"]["realized_delta"] for event in realized] == ["3.00"]
    assert [event["money"]["contribution_delta"] for event in realized] == ["3.00"]


def test_later_lower_realized_snapshot_does_not_reverse_money_without_correction() -> None:
    rows = [
        {"ts": 100, "source": "capafy-payout", "date": "2026-07-18", "balance_payout_usd": 0, "total_payout_usd": 5},
        {"ts": 200, "source": "capafy-payout", "date": "2026-07-19", "balance_payout_usd": 0, "total_payout_usd": 2},
    ]

    realized = [
        event
        for event in sync.events_from_payout_rows(rows)
        if event["event_type"] == "payout.received"
    ]

    assert [event["money"]["realized_delta"] for event in realized] == ["5.00"]


def test_cost_uses_public_cumulative_cent_deltas_and_preserves_contribution_sign() -> None:
    rows = [
        {"ts": 1785539400, "provider": "openrouter", "total_usage_usd": 4.776955221},
        {"ts": 1785588895, "provider": "openrouter", "total_usage_usd": 4.776955221},
        {"ts": 1785675295, "provider": "openrouter", "total_usage_usd": 4.786955221},
    ]

    events = sync.events_from_cost_rows(rows)

    assert [event["money"]["cost_delta"] for event in events] == ["4.78", "0.01"]
    assert [event["money"]["contribution_delta"] for event in events] == ["-4.78", "-0.01"]


def test_attribution_excludes_known_verification_clicks_and_clamps_at_zero() -> None:
    rows = [
        {
            "date": "2026-08-01",
            "agents": [
                {"agent_id": "4866150011", "clicks": 1, "sales": None, "name": "Decision Debate"}
            ],
        },
        {
            "date": "2026-08-02",
            "agents": [
                {"agent_id": "4866150011", "clicks": 5, "sales": None, "name": "Decision Debate"}
            ],
        },
    ]

    events = sync.events_from_attribution_rows(rows, {"4866150011": 2})

    assert [event["metrics"]["clicks"] for event in events] == [0, 3]
    assert "two deployment-verification clicks excluded" in events[0]["public_evidence"]["labels"]


def test_ig_metric_snapshots_remain_snapshots_instead_of_additive_deltas() -> None:
    rows = [
        {
            "ts": 1785394813,
            "reel_url": "https://www.instagram.com/reel/Da7VQY8MIOK/",
            "agent_id": "7686597754",
            "views": 2,
            "likes": 1,
            "comments": 0,
        },
        {
            "ts": 1785481207,
            "reel_url": "https://www.instagram.com/reel/Da7VQY8MIOK/",
            "agent_id": "7686597754",
            "views": 3,
            "likes": 1,
            "comments": 1,
        },
    ]

    events = sync.events_from_ig_metrics(rows)

    assert [event["metrics"] for event in events] == [
        {"views": 2, "likes": 1, "comments": 0},
        {"views": 3, "likes": 1, "comments": 1},
    ]


def test_ig_metric_snapshot_does_not_turn_unavailable_engagement_into_zero() -> None:
    rows = [
        {
            "ts": 1785619491,
            "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
            "agent_id": "4866150011",
            "views": 95,
            "likes": None,
            "comments": None,
        }
    ]

    events = sync.events_from_ig_metrics(rows)

    assert events[0]["metrics"] == {"views": 95}


def test_inventory_snapshot_emits_one_stable_observation_per_listing() -> None:
    agents = [
        {
            "agentId": "4866150011",
            "name": "Decision Debate",
            "agentStatus": "online",
            "updatedAt": 1785120576575,
        },
        {
            "agentId": "9480246345",
            "name": "Portfolio Tracker",
            "agentStatus": "under_review",
            "updatedAt": 1785460544396,
        },
        {
            "agentId": "3098034209",
            "name": "Sales Objection Reply Builder",
            "agentStatus": "review_rejected",
            "updatedAt": 1785293824499,
        },
    ]

    events = sync.events_from_inventory_agents(agents)

    assert [event["status"]["after"] for event in events] == [
        "online",
        "under_review",
        "rejected",
    ]
    assert all(event["event_type"] == "listing.observed" for event in events)
    assert events[0]["public_evidence"]["urls"] == [
        "https://capafy.ai/agent/4866150011"
    ]
    assert events[1]["public_evidence"]["urls"] == []
    assert sync.events_from_inventory_agents(agents) == events


def test_verified_runtime_artifacts_backfill_outcomes_and_honest_incident_phases() -> None:
    builder = {
        "recorded_at": "2026-08-01T13:07:44+00:00",
        "outcome": {
            "schema_version": 1,
            "kind": "builder_submitted",
            "owner": "builder",
            "title": "Portfolio Tracker",
            "agent_id": "9480246345",
            "remote_status": 1,
            "skills_confirmed": True,
            "config_confirmed": True,
            "listing_url": "https://capafy.ai/agent/9480246345",
            "gross_usd": 9.99,
            "pending_usd": 8,
            "realized_usd": 0,
            "mrr_usd": 0,
            "cost_usd": 4.78,
            "contribution_usd": -4.78,
            "next_action": "market it",
        },
    }
    marketing = {
        "recorded_at": "2026-08-01T20:32:54+00:00",
        "outcome": {
            "schema_version": 1,
            "kind": "marketing_published",
            "owner": "marketer",
            "handle": "capafy.skills8m4q2z",
            "title": "Decision Debate",
            "agent_id": "4866150011",
            "listing_url": "https://capafy.ai/agent/4866150011",
            "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram",
            "caption": "Make the tradeoff visible.",
            "media_path": "/private/tmp/reel.mp4",
            "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
            "owner_session_verified": True,
        },
    }
    incident = {
        "schema_version": 1,
        "incident_id": "capafy-marketer-20260801T201313Z-6b646dbe",
        "owner": "marketer",
        "phase": "verified",
        "detected_at": "2026-08-01T20:13:13Z",
        "updated_at": "2026-08-01T20:40:03Z",
        "summary": "Reel readback failed.",
        "repair_summary": "Recovered the owner-scoped Reel URL.",
        "verification": {"owner_session_verified": True},
    }

    events = sync.events_from_verified_runtime(builder, marketing, [incident])

    assert [event["event_type"] for event in events] == [
        "listing.submitted",
        "content.published",
        "account.post_verified",
        "incident.detected",
        "incident.verified",
    ]
    assert events[-2]["public_evidence"]["urls"] == []
    assert events[-1]["status"]["after"] == "verified"


def test_sync_all_cli_backfills_once_and_keeps_exact_cost_private(tmp_path: Path) -> None:
    money = tmp_path / "capafy-earn-ledger.jsonl"
    cost = tmp_path / "capafy-loop.log"
    attribution = tmp_path / "capafy-attribution.jsonl"
    metrics = tmp_path / "capafy-marketing-ig-metrics.jsonl"
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    evidence = tmp_path / "capafy-revenue-evidence"
    money.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": 1782172800,
                        "source": "capafy-sales",
                        "date": "2026-06-23",
                        "orders": 1,
                        "gross_usd": 9.99,
                        "currency": "usd",
                    }
                ),
                json.dumps(
                    {
                        "ts": 1784330227,
                        "source": "capafy-payout",
                        "date": "2026-07-18",
                        "balance_payout_usd": 8.0,
                        "total_payout_usd": 0.0,
                        "currency": "usd",
                    }
                ),
            ]
        )
        + "\n"
    )
    cost.write_text(
        "not-json log output\n"
        + json.dumps(
            {
                "ts": 1785539400,
                "provider": "openrouter",
                "total_usage_usd": 4.776955221,
            }
        )
        + "\n"
    )
    attribution.write_text(
        json.dumps(
            {
                "date": "2026-08-02",
                "agents": [
                    {"agent_id": "4866150011", "clicks": 2, "name": "Decision Debate"}
                ],
            }
        )
        + "\n"
    )
    metrics.write_text(
        json.dumps(
            {
                "ts": 1785567607,
                "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                "agent_id": "4866150011",
                "views": 3,
                "likes": 1,
                "comments": 0,
            }
        )
        + "\n"
    )
    command = [
        sys.executable,
        str(SCRIPTS / "capafy_event_sync.py"),
        "sync-all",
        "--skip-runtime",
        "--money-ledger",
        str(money),
        "--cost-log",
        str(cost),
        "--attribution-ledger",
        str(attribution),
        "--metrics-ledger",
        str(metrics),
        "--verification-clicks-json",
        '{"4866150011":2}',
        "--ledger",
        str(ledger),
        "--evidence-dir",
        str(evidence),
    ]

    first = subprocess.run(command, text=True, capture_output=True, check=False)
    retry = subprocess.run(command, text=True, capture_output=True, check=False)

    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout) == {
        "appended": 5,
        "conflicts": 0,
        "duplicates": 0,
        "observed": 5,
        "sources": {
            "attribution": {"appended": 1, "duplicates": 0, "observed": 1},
            "cost": {"appended": 1, "duplicates": 0, "observed": 1},
            "metrics": {"appended": 1, "duplicates": 0, "observed": 1},
            "money": {"appended": 2, "duplicates": 0, "observed": 2},
        },
    }
    assert json.loads(retry.stdout)["appended"] == 0
    assert json.loads(retry.stdout)["duplicates"] == 5
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(rows) == 5
    cost_event = next(row for row in rows if row["event_type"] == "cost.measured")
    assert cost_event["money"]["cost_delta"] == "4.78"
    cost_sidecar = evidence / f"{cost_event['event_id']}.json"
    assert json.loads(cost_sidecar.read_text())["source"]["total_usage_usd"] == 4.776955221
