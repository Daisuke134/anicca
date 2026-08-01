import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_company_dashboard import build_dashboard
from capafy_event_projection import project_company
from capafy_event_store import read_events
from capafy_outcome import render_outcome


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_full_backfill_is_idempotent_and_one_projection_drives_both_outputs(
    tmp_path: Path,
) -> None:
    money = tmp_path / "money.jsonl"
    cost = tmp_path / "cost.jsonl"
    attribution = tmp_path / "attribution.jsonl"
    metrics = tmp_path / "metrics.jsonl"
    inventory = tmp_path / "inventory.json"
    builder = tmp_path / "builder.json"
    marketing = tmp_path / "marketing.json"
    incidents = tmp_path / "incidents"
    ledger = tmp_path / "events.jsonl"
    evidence = tmp_path / "evidence"
    incidents.mkdir()
    money.write_text(
        json.dumps(
            {
                "ts": 1782172800,
                "source": "capafy-sales",
                "date": "2026-06-23",
                "orders": 1,
                "gross_usd": 9.99,
            }
        )
        + "\n"
        + json.dumps(
            {
                "ts": 1784330227,
                "source": "capafy-payout",
                "date": "2026-07-18",
                "balance_payout_usd": 8,
                "total_payout_usd": 0,
            }
        )
        + "\n"
    )
    cost.write_text(
        json.dumps(
            {"ts": 1785539400, "provider": "openrouter", "total_usage_usd": 4.776955221}
        )
        + "\n"
    )
    attribution.write_text(
        json.dumps(
            {
                "date": "2026-08-02",
                "agents": [{"agent_id": "4866150011", "clicks": 2}],
            }
        )
        + "\n"
    )
    metrics.write_text(
        json.dumps(
            {
                "ts": 1785619889,
                "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                "agent_id": "4866150011",
                "views": 121,
                "likes": None,
                "comments": None,
            }
        )
        + "\n"
    )
    agents = [
        {
            "agentId": str(1000000000 + index),
            "name": f"Online skill {index}",
            "agentStatus": "online",
            "updatedAt": 1785000000000 + index,
        }
        for index in range(26)
    ] + [
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
            "agentId": "1037238583",
            "name": "Football Match Analyst",
            "agentStatus": "under_review",
            "updatedAt": 1785459578877,
        },
        {
            "agentId": "9470213182",
            "name": "Job Description Writer",
            "agentStatus": "draft",
            "updatedAt": 1785387235062,
        },
        {
            "agentId": "3098034209",
            "name": "Sales Objection Reply Builder",
            "agentStatus": "review_rejected",
            "updatedAt": 1785293824499,
        },
    ]
    write_json(inventory, {"agents": {"list": agents}})
    write_json(
        builder,
        {
            "recorded_at": "2026-08-01T13:07:44Z",
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
                "cost_usd": 4.776955221,
                "contribution_usd": -4.776955221,
                "next_action": "market it",
            },
        },
    )
    write_json(
        marketing,
        {
            "recorded_at": "2026-08-01T20:32:54Z",
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
                "media_path": "/private/evidence/decision-debate.mp4",
                "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
                "owner_session_verified": True,
            },
        },
    )
    write_json(
        incidents / "closed.json",
        {
            "schema_version": 1,
            "incident_id": "capafy-marketer-20260801T201313Z-6b646dbe",
            "owner": "marketer",
            "phase": "verified",
            "detected_at": "2026-08-01T20:13:13Z",
            "updated_at": "2026-08-01T20:40:03Z",
            "summary": "Reel readback failed.",
            "repair_summary": "Recovered the owner-scoped Reel URL.",
            "verification": {"owner_session_verified": True},
        },
    )
    command = [
        sys.executable,
        str(SCRIPTS / "capafy_event_sync.py"),
        "sync-all",
        "--money-ledger",
        str(money),
        "--cost-log",
        str(cost),
        "--attribution-ledger",
        str(attribution),
        "--metrics-ledger",
        str(metrics),
        "--inventory-json",
        str(inventory),
        "--builder-terminal",
        str(builder),
        "--marketing-terminal",
        str(marketing),
        "--incident-dir",
        str(incidents),
        "--ledger",
        str(ledger),
        "--evidence-dir",
        str(evidence),
    ]

    first = subprocess.run(command, text=True, capture_output=True, check=False)
    retry = subprocess.run(command, text=True, capture_output=True, check=False)

    assert first.returncode == 0, first.stderr
    assert retry.returncode == 0, retry.stderr
    assert json.loads(first.stdout)["appended"] == 42
    assert json.loads(retry.stdout)["appended"] == 0
    assert json.loads(retry.stdout)["duplicates"] == 42
    projected = project_company(read_events(ledger))
    assert projected["inventory"] == {
        "online": 27,
        "under_review": 2,
        "draft": 1,
        "rejected": 1,
    }
    assert projected["orders"] == 1
    assert projected["gross_usd"] == "9.99"
    assert projected["pending_usd"] == "8.00"
    assert projected["realized_usd"] == "0.00"
    assert projected["cost_usd"] == "4.78"
    assert projected["marketing"]["public_post_url"].endswith("/DbgsvEbo5kd/")
    assert projected["account"]["handle"] == "capafy.skills8m4q2z"
    assert projected["incident"] is None

    built = build_dashboard(projected, tmp_path / "company")
    telegram = render_outcome(projected)
    short_id = projected["projection_id"].removeprefix("sha256:")[:12]
    assert short_id in built.index_path.read_text()
    assert short_id in telegram
    public = built.index_path.read_text() + built.state_path.read_text() + telegram
    assert "/private/evidence" not in public
    assert "technical_evidence" not in public


def test_corrupt_writer_incident_repairs_and_closes_once_through_normal_monitor(
    tmp_path: Path,
) -> None:
    outcome_script = SCRIPTS / "capafy_outcome.py"
    monitor = SCRIPTS.parent / "capafy-outcome-monitor.sh"
    ledger = tmp_path / "capafy-revenue-events.jsonl"
    ledger.write_text("not-json\n")
    env = os.environ | {
        "CAPAFY_OUTCOME_STATE_DIR": str(tmp_path),
        "CAPAFY_EVENT_LEDGER": str(ledger),
        "CAPAFY_EVENT_EVIDENCE_DIR": str(tmp_path / "evidence"),
        "CAPAFY_OUTCOME_SCRIPT": str(outcome_script),
    }
    start = [
        sys.executable,
        str(outcome_script),
        "start-incident",
        "--owner",
        "builder",
        "--summary",
        "Canonical writer failed on a corrupt tail",
        "--fingerprint",
        "p2-corrupt-writer",
        "--repair-result-path",
        str(tmp_path / "repair.result"),
    ]

    failed = subprocess.run(start, env=env, text=True, capture_output=True, check=False)

    assert failed.returncode == 2
    record_path = next((tmp_path / "capafy-incidents").glob("*.json"))
    incident_id = json.loads(record_path.read_text())["incident_id"]
    ledger.unlink()
    healed = subprocess.run(start, env=env, text=True, capture_output=True, check=False)
    assert healed.returncode == 0, healed.stderr

    def transition(payload: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(outcome_script), "transition-incident"],
            input=json.dumps(payload),
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    assert transition(
        {"incident_id": incident_id, "phase": "repair_started"}
    ).returncode == 0
    closure = {
        "schema_version": 1,
        "kind": "repair_closure",
        "incident_id": incident_id,
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
        "detected_summary": "Canonical writer failed on a corrupt tail",
        "repair_summary": "Removed the corrupt tail and retried the same append.",
        "next_action": "Continue autonomous operation",
    }
    repaired = transition(
        {"incident_id": incident_id, "phase": "repaired", "outcome": closure}
    )
    assert repaired.returncode == 0, repaired.stderr
    result_path = tmp_path / "repair.result"
    result_path.write_text("SUCCESS 2026-08-02T12:00:00Z canonical append verified\n")
    (tmp_path / ".self-fix-capafy-loop.incident.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "incident_id": incident_id,
                "loop": "capafy-loop",
                "result_path": str(result_path),
            }
        )
    )
    messages = tmp_path / "messages.txt"
    sender = tmp_path / "send.sh"
    sender.write_text(
        f"printf '%s\\n' \"$1\" >> '{messages}'\n"
        "printf '%s\\n' 'TELEGRAM_SENT=true MSGID=888'\n"
    )
    env["CAPAFY_TELEGRAM_SENDER"] = str(sender)

    first = subprocess.run(
        ["bash", str(monitor)], env=env, text=True, capture_output=True, check=False
    )
    retry = subprocess.run(
        ["bash", str(monitor)], env=env, text=True, capture_output=True, check=False
    )

    assert first.returncode == 0, first.stderr
    assert retry.returncode == 0, retry.stderr
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert [event["event_type"] for event in events] == [
        "incident.detected",
        "incident.repair_started",
        "incident.repaired",
        "incident.verified",
    ]
    assert len({event["event_id"] for event in events}) == 4
    assert messages.read_text().count("Capafy incident resolved") == 1
    final = json.loads(record_path.read_text())
    assert final["phase"] == "verified"
    assert final["telegram_message_id"] == "888"
