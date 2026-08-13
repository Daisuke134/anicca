import json
import os
import subprocess
import sys
from datetime import datetime, timezone
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


def test_projection_counts_paid_orders_without_attributing_zero_dollar_orders() -> None:
    sales_rows = [
        {"ts": 1785888000, "source": "capafy-sales", "date": "2026-08-05", "orders": 1, "gross_usd": 0.0},
        {"ts": 1786147200, "source": "capafy-sales", "date": "2026-08-08", "orders": 1, "gross_usd": 9.99},
        {"ts": 1786320000, "source": "capafy-sales", "date": "2026-08-10", "orders": 1, "gross_usd": 0.0},
        {"ts": 1786492800, "source": "capafy-sales", "date": "2026-08-12", "orders": 1, "gross_usd": 0.0},
    ]
    events = fixture_events() + [
        stored(event, f"2026-08-{index + 5:02d}T12:00:00Z")
        for index, row in enumerate(sales_rows)
        for event in sync.events_from_sales_rows([row])
    ]

    result = projection.project_company(events)

    assert result["orders"] == 5
    assert result["paid_orders"] == 2
    assert result["gross_usd"] == "19.98"


def test_projection_marks_multi_order_batch_paid_count_unknown() -> None:
    event = sync.events_from_sales_rows(
        [{"ts": 1786579200, "source": "capafy-sales", "date": "2026-08-13", "orders": 2, "gross_usd": 19.98}]
    )[0]

    result = projection.project_company(fixture_events() + [stored(event, "2026-08-13T12:00:00Z")])

    assert result["orders"] == 3
    assert result["gross_usd"] == "29.97"
    assert result["paid_orders"] is None


def test_projection_uses_explicit_paid_orders_for_multi_order_batch() -> None:
    event = sync.events_from_sales_rows(
        [{"ts": 1786579200, "source": "capafy-sales", "date": "2026-08-13", "orders": 2, "gross_usd": 19.98}]
    )[0] | {"metrics": {"orders": 2, "paid_orders": 1}}

    result = projection.project_company(fixture_events() + [stored(event, "2026-08-13T12:00:00Z")])

    assert result["paid_orders"] == 2


def test_projection_marks_explicit_paid_orders_above_orders_unknown() -> None:
    event = sync.events_from_sales_rows(
        [{"ts": 1786579200, "source": "capafy-sales", "date": "2026-08-13", "orders": 2, "gross_usd": 19.98}]
    )[0] | {"metrics": {"orders": 2, "paid_orders": 3}}

    result = projection.project_company(fixture_events() + [stored(event, "2026-08-13T12:00:00Z")])

    assert result["paid_orders"] is None


@pytest.mark.parametrize("paid_orders", [True, -1, 1.0, "1", None])
def test_projection_fails_closed_for_invalid_explicit_paid_orders(paid_orders: object) -> None:
    event = sync.events_from_sales_rows(
        [{"ts": 1786579200, "source": "capafy-sales", "date": "2026-08-13", "orders": 1, "gross_usd": 9.99}]
    )[0] | {"metrics": {"orders": 1, "paid_orders": paid_orders}}

    assert projection.project_company(fixture_events() + [stored(event, "2026-08-13T12:00:00Z")])["paid_orders"] is None


def test_projection_fails_closed_for_negative_gross_order_batch() -> None:
    event = sync.events_from_sales_rows(
        [{"ts": 1786579200, "source": "capafy-sales", "date": "2026-08-13", "orders": 1, "gross_usd": -1.0}]
    )[0]

    assert projection.project_company(fixture_events() + [stored(event, "2026-08-13T12:00:00Z")])["paid_orders"] is None


def test_projection_sources_report_mixed_fresh_stale_unknown_and_stable_id() -> None:
    reference = "2026-08-02T12:00:00Z"
    events = []
    for event in fixture_events():
        event_type = event["event_type"]
        if event_type.startswith("account."):
            continue
        if event_type.startswith("listing.") or event_type == "cost.measured":
            recorded_at = "2026-08-01T11:00:00Z"
        else:
            recorded_at = "2026-08-02T11:30:00Z"
        events.append(event | {"recorded_at": recorded_at})

    result = projection.project_company(events, reference_time=reference)
    assert result["sources"]["money"] == {"observed_at": "2026-08-02T11:30:00Z", "freshness": "fresh"}
    assert result["sources"]["inventory"] == {"observed_at": "2026-08-01T11:00:00Z", "freshness": "stale"}
    assert result["sources"]["account"] == {"observed_at": None, "freshness": "unknown"}
    assert result["sources"]["marketing"] == {"observed_at": "2026-08-02T11:30:00Z", "freshness": "fresh"}
    assert result["sources"]["cost"] == {"observed_at": "2026-08-01T11:00:00Z", "freshness": "stale"}
    assert projection.project_company(events, reference_time="2026-08-02T12:30:00Z")["projection_id"] == result["projection_id"]


def test_projection_marks_future_source_observation_stale() -> None:
    future = [
        event
        | ({"recorded_at": "2026-08-02T13:00:00Z"} if event["event_type"] in {"order.received", "balance.reconciled", "payout.received"} else {})
        for event in fixture_events()
    ]
    result = projection.project_company(future, reference_time="2026-08-02T12:00:00Z")
    assert result["sources"]["money"]["freshness"] == "stale"


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


def test_incident_projection_uses_business_chronology_not_append_order() -> None:
    historical_later = {
        "schema_version": 1,
        "incident_id": "capafy-company-20260808T003008Z-e465c6a6",
        "owner": "company",
        "phase": "detected",
        "phase_timestamps": {"detected": "2026-08-08T00:30:08Z"},
        "summary": "The company projection needs reconciliation.",
    }
    current_earlier = {
        "schema_version": 1,
        "incident_id": "capafy-marketer-20260803T070010Z-99b1374a",
        "owner": "marketer",
        "phase": "unresolved",
        "phase_timestamps": {"unresolved": "2026-08-03T07:00:10Z"},
        "summary": "The marketer retry remains unresolved.",
        "next_retry_at": "2026-08-07T04:50:52Z",
    }
    appended_later = stored(
        adapters.event_from_incident(historical_later), "2026-08-13T10:00:00Z"
    )
    appended_earlier = stored(
        adapters.event_from_incident(current_earlier), "2026-08-13T10:00:01Z"
    )

    result = projection.project_company([appended_later, appended_earlier])

    assert result["incident"] == {
        "incident_id": historical_later["incident_id"],
        "owner": "company",
        "summary": historical_later["summary"],
        "phase": "detected",
        "next_retry_at": None,
    }


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
            "paid_orders",
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


def test_parity_gate_compares_paid_orders_and_fails_closed_when_missing() -> None:
    assert projection.parity_errors({"paid_orders": 2}, {"paid_orders": 1}) == [
        "paid_orders mismatch: projection=2 source=1"
    ]
    assert projection.parity_errors({}, {"paid_orders": 0}) == [
        "paid_orders missing: projection=<missing> source=0"
    ]


def test_parity_gate_compares_incident_retry_at_by_canonical_utc_second() -> None:
    incident = {
        "incident_id": "capafy-marketer-20260807T045052Z-deadbeef",
        "owner": "marketer",
        "summary": "Instagram readback failed.",
        "phase": "unresolved",
        "next_retry_at": "2026-08-07T04:50:52Z",
    }
    independent = {
        "paid_orders": 0,
        "incident": incident
        | {"next_retry_at": "2026-08-07T13:50:52.266822+09:00"}
    }

    assert projection.parity_errors({"paid_orders": 0, "incident": incident}, independent) == []


@pytest.mark.parametrize(
    ("projected_retry_at", "independent_retry_at"),
    [
        ("2026-08-07T04:50:52Z", "2026-08-07T04:50:53Z"),
        (None, "2026-08-07T04:50:52Z"),
        ("2026-08-07T04:50:52", "2026-08-07T04:50:52"),
        ("not-a-timestamp", "not-a-timestamp"),
    ],
)
def test_parity_gate_fails_closed_for_invalid_incident_retry_at(
    projected_retry_at: str | None, independent_retry_at: str | None
) -> None:
    projected = {
        "paid_orders": 0,
        "incident": {
            "incident_id": "capafy-marketer-20260807T045052Z-deadbeef",
            "owner": "marketer",
            "summary": "Instagram readback failed.",
            "phase": "unresolved",
            "next_retry_at": projected_retry_at,
        }
    }
    independent = {
        "paid_orders": 0,
        "incident": projected["incident"]
        | {"next_retry_at": independent_retry_at}
    }

    assert projection.parity_errors(projected, independent) == [
        f"incident mismatch: projection={projected['incident']!r} "
        f"source={independent['incident']!r}"
    ]


@pytest.mark.parametrize(
    "malformed_retry_at",
    [
        "20260807T045052+00:00",
        "2026-W32-5T04:50:52+00:00",
        "2026-08-07 04:50:52+00:00",
        "not-a-timestamp",
        42,
    ],
)
def test_parity_gate_rejects_non_rfc3339_incident_retry_at(
    malformed_retry_at: object,
) -> None:
    incident = {
        "incident_id": "capafy-marketer-20260807T045052Z-deadbeef",
        "owner": "marketer",
        "summary": "Instagram readback failed.",
        "phase": "unresolved",
        "next_retry_at": malformed_retry_at,
    }

    assert projection.parity_errors(
        {"paid_orders": 0, "incident": incident}, {"paid_orders": 0, "incident": dict(incident)}
    ) == [
        f"incident mismatch: projection={incident!r} source={incident!r}"
    ]


@pytest.mark.parametrize(
    "missing_key", ["incident_id", "owner", "summary", "phase", "next_retry_at"]
)
def test_parity_gate_fails_closed_when_incident_required_key_is_missing(
    missing_key: str,
) -> None:
    incident = {
        "incident_id": "capafy-marketer-20260807T045052Z-deadbeef",
        "owner": "marketer",
        "summary": "Instagram readback failed.",
        "phase": "unresolved",
        "next_retry_at": "2026-08-07T04:50:52Z",
    }
    incident.pop(missing_key)

    assert projection.parity_errors(
        {"paid_orders": 0, "incident": incident}, {"paid_orders": 0, "incident": dict(incident)}
    ) == [
        f"incident mismatch: projection={incident!r} source={incident!r}"
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
    sales_rows = [
        {"ts": 1785888000, "source": "capafy-sales", "date": "2026-08-05", "orders": 1, "gross_usd": 0.0},
        {"ts": 1786147200, "source": "capafy-sales", "date": "2026-08-08", "orders": 1, "gross_usd": 9.99},
        {"ts": 1786320000, "source": "capafy-sales", "date": "2026-08-10", "orders": 1, "gross_usd": 0.0},
        {"ts": 1786492800, "source": "capafy-sales", "date": "2026-08-12", "orders": 1, "gross_usd": 0.0},
    ]
    canonical_events = fixture_events() + [
        stored(event, f"{row['date']}T12:00:00Z")
        for row in sales_rows
        for event in sync.events_from_sales_rows([row])
    ]
    ledger.write_text("\n".join(json.dumps(event) for event in canonical_events) + "\n")
    earn_ledger = home / "anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl"
    earn_ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"ts": 1782172800, "source": "capafy-sales", "date": "2026-06-23", "orders": 9, "gross_usd": 1.11},
                {"ts": 1782172800, "source": "capafy-sales", "date": "2026-06-23", "orders": 1, "gross_usd": 9.99},
                *sales_rows,
                {"ts": 1784330227, "source": "capafy-payout", "date": "2026-07-18", "balance_payout_usd": 77.0, "total_payout_usd": 66.0},
                {"ts": 1784330227, "source": "capafy-payout", "date": "2026-07-18", "balance_payout_usd": 8.0, "total_payout_usd": 0.0},
            )
        )
        + "\n"
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
    assert report["goal_b"]["orders"] == 5
    assert report["goal_b"]["paid_orders"] == 2
    assert report["goal_b"]["gross_usd"] == 19.98
    assert report["company_state"]["pending_usd"] == "8.00"
    assert report["company_state"]["realized_usd"] == "0.00"
    expected = projection.project_company(canonical_events, reference_time=datetime.now(timezone.utc))
    assert report["company_state"] == expected
    assert json.loads((tmp_path / "site/company/state.json").read_text()) == expected
    assert "wrong-legacy-value" not in sent.read_text()
    assert expected["projection_id"].removeprefix("sha256:")[:12] in sent.read_text()

    duplicate = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )
    assert duplicate.returncode == 0, duplicate.stderr
    assert sent.read_text().count("Capafy — Consolidated company state") == 1

    earn_ledger.write_text(earn_ledger.read_text().replace("9.99", "999.00"))
    mismatch = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )

    assert mismatch.returncode == 3
    assert "gross_usd mismatch" in mismatch.stderr
    assert sent.read_text().count("Capafy — Consolidated company state") == 1
    incidents = list((state / "capafy-incidents").glob("*.json"))
    assert len(incidents) == 1

    earn_ledger.write_text(earn_ledger.read_text().replace("999.00", "9.99"))
    recovered = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )

    assert recovered.returncode == 0, recovered.stderr
    recovered_report = json.loads(recovered.stdout)
    assert recovered_report["company_state"]["incident"] is None
    incident = json.loads(incidents[0].read_text())
    assert incident["phase"] == "verified"
    assert incident["verification"]["projection_parity_verified"] is True
    message = sent.read_text()
    assert message.count("Capafy — Consolidated company state") == 2
    assert "Capafy incident resolved — no action needed" in message
    assert json.loads((tmp_path / "site/company/state.json").read_text()) == recovered_report["company_state"]

    recovered_retry = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )
    assert recovered_retry.returncode == 0, recovered_retry.stderr
    assert sent.read_text().count("Capafy — Consolidated company state") == 2
    incident_events = [
        json.loads(line)
        for line in ledger.read_text().splitlines()
        if line.strip() and json.loads(line)["entity"]["id"] == incident["incident_id"]
    ]
    assert [event["event_type"] for event in incident_events] == [
        "incident.detected",
        "incident.repair_started",
        "incident.repaired",
        "incident.verified",
    ]

    ambiguous_row = {
        "ts": 1786579200,
        "source": "capafy-sales",
        "date": "2026-08-13",
        "orders": 2,
        "paid_orders": 3,
        "gross_usd": 19.98,
    }
    ambiguous_event = sync.events_from_sales_rows([ambiguous_row])[0]
    ledger.write_text(
        ledger.read_text()
        + json.dumps(stored(ambiguous_event, "2026-08-13T12:00:00Z"))
        + "\n"
    )
    with earn_ledger.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(ambiguous_row) + "\n")

    ambiguous = subprocess.run(
        ["bash", str(goal_monitor)], env=env, text=True, capture_output=True, check=False
    )

    assert ambiguous.returncode == 0, ambiguous.stderr
    ambiguous_report = json.loads(ambiguous.stdout)
    assert ambiguous_report["goal_b"]["paid_orders"] is None
    assert ambiguous_report["company_state"]["paid_orders"] is None
