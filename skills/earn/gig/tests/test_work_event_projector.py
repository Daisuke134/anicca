import importlib.util
import json
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "work_event_projector.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("work_event_projector", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load work_event_projector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_projects_contract_payment_incident_and_recovery_from_ground_truth(tmp_path):
    module = load_module()
    snapshot = tmp_path / "marketplace-snapshot.json"
    earnings = tmp_path / "earnings.jsonl"
    failures = tmp_path / "pass-failures.jsonl"
    audit = tmp_path / "audit.jsonl"
    output = tmp_path / "work-events.jsonl"
    snapshot.write_text(json.dumps({
        "captured_at": "2026-07-30T00:00:00Z",
        "orders": [{
            "talkroom_id": "17943244",
            "request_id": "5180000",
            "title": "Webサイト改善",
            "price_jpy": 100000,
            "delivery_date": "2026-08-12",
            "status": "unknown",
            "talkroom_state": "取引中",
        }],
    }, ensure_ascii=False))
    write_jsonl(earnings, [{
        "ts": "2026/07/30 09:10",
        "talkroom_id": "17943244",
        "title": "Webサイト改善",
        "jpy": 78000,
        "net_of_fee": True,
        "status": "検収完了",
        "evidence": "https://coconala.com/mypage/revenue",
        "idem_key": "coconala:revenue:17943244:2026/07/30 09:10",
    }])
    write_jsonl(failures, [{
        "ts": 1785366600,
        "pass_id": "pass-1",
        "status": "failed",
        "failed_step": "B2",
        "reason": "application_readback_failed",
    }])
    write_jsonl(audit, [{
        "ts": 1785366900,
        "lanes": [{"lane": "apply", "prev_alert_state": "down"}],
        "changed": [{"lane": "apply", "to": "ok", "problems": []}],
    }])

    result = module.project(
        snapshot_path=snapshot,
        earnings_path=earnings,
        failures_path=failures,
        audit_path=audit,
        applications_path=tmp_path / "missing-applications.jsonl",
        paid_progress_path=tmp_path / "missing-paid-progress.jsonl",
        pass_id=None,
        output_path=output,
    )
    events = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
    ]

    assert result == {"appended": 4, "duplicate": 0}
    assert {event["kind"] for event in events} == {
        "contract",
        "payment",
        "incident",
        "recovery",
    }
    assert all(
        set(("event_key", "kind", "entity_id", "occurred_at", "state",
             "action", "result", "next_action", "evidence", "attributes"))
        <= set(event)
        for event in events
    )
    payment = next(event for event in events if event["kind"] == "payment")
    assert payment["attributes"]["net_jpy"] == 78000
    assert payment["state"] == "confirmed"
    assert "buyer" not in payment["attributes"]
    recovery = next(event for event in events if event["kind"] == "recovery")
    assert recovery["attributes"]["recovered_lane"] == "application"


def test_projects_fenced_self_heal_recovery_from_fresh_verification(tmp_path):
    module = load_module()
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    audit = tmp_path / "audit.jsonl"
    output = tmp_path / "work-events.jsonl"
    write_jsonl(audit, [{
        "ts": 1785366900,
        "kind": "self_heal_recovery",
        "state": "verified",
        "incident_id": 7,
        "fingerprint": "browser:cdp_unavailable",
        "repair_class": "browser_restart",
        "fencing_token": 2,
        "verification": {
            "fresh_fingerprint_present": False,
            "observed_at": 1785366900,
        },
    }])

    result = module.project(
        snapshot_path=None,
        earnings_path=empty,
        failures_path=empty,
        audit_path=audit,
        applications_path=empty,
        paid_progress_path=empty,
        pass_id=None,
        output_path=output,
    )
    event = json.loads(output.read_text(encoding="utf-8").strip())

    assert result == {"appended": 1, "duplicate": 0}
    assert event["event_key"] == "gig:recovery:incident:7:2"
    assert event["kind"] == "recovery"
    assert event["state"] == "verified"
    assert event["attributes"]["failure_fingerprint"] == "browser:cdp_unavailable"


def test_repeated_projection_is_idempotent_by_event_key(tmp_path):
    module = load_module()
    snapshot = tmp_path / "marketplace-snapshot.json"
    snapshot.write_text(json.dumps({
        "captured_at": "2026-07-30T00:00:00Z",
        "orders": [{
            "talkroom_id": "42",
            "title": "資料作成",
            "price_jpy": 30000,
            "status": "paid",
        }],
    }))
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    output = tmp_path / "work-events.jsonl"

    first = module.project(
        snapshot_path=snapshot,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=empty,
        paid_progress_path=empty,
        pass_id=None,
        output_path=output,
    )
    second = module.project(
        snapshot_path=snapshot,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=empty,
        paid_progress_path=empty,
        pass_id=None,
        output_path=output,
    )

    assert first == {"appended": 1, "duplicate": 0}
    assert second == {"appended": 0, "duplicate": 1}
    assert len(output.read_text().splitlines()) == 1


def test_unverified_or_incomplete_sources_do_not_become_work_events(tmp_path):
    module = load_module()
    snapshot = tmp_path / "marketplace-snapshot.json"
    earnings = tmp_path / "earnings.jsonl"
    failures = tmp_path / "pass-failures.jsonl"
    audit = tmp_path / "audit.jsonl"
    output = tmp_path / "work-events.jsonl"
    snapshot.write_text(json.dumps({
        "captured_at": "2026-07-30T00:00:00Z",
        "orders": [
            {"talkroom_id": "1", "status": "unknown"},
            {"status": "paid", "title": "missing identity"},
        ],
    }))
    write_jsonl(earnings, [
        {"talkroom_id": "1", "status": "検収完了", "jpy": 1000},
        {"talkroom_id": "2", "status": "pending", "jpy": 2000, "evidence": "x"},
    ])
    write_jsonl(failures, [{"status": "failed", "reason": "no pass id"}])
    write_jsonl(audit, [{
        "ts": 1,
        "changed": [{"lane": "apply", "from": "ok", "to": "down"}],
    }])

    result = module.project(
        snapshot_path=snapshot,
        earnings_path=earnings,
        failures_path=failures,
        audit_path=audit,
        applications_path=tmp_path / "missing-applications.jsonl",
        paid_progress_path=tmp_path / "missing-paid-progress.jsonl",
        pass_id=None,
        output_path=output,
    )

    assert result == {"appended": 0, "duplicate": 0}
    assert not output.exists()


def test_current_pass_projects_only_verified_application_and_delivery(tmp_path):
    module = load_module()
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    applications = tmp_path / "applied.jsonl"
    paid_progress = tmp_path / "paid-progress.jsonl"
    output = tmp_path / "work-events.jsonl"
    write_jsonl(applications, [
        {
            "ts": 1785356125,
            "pass_id": "pass-current",
            "requestId": "5179880",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
            "bucket": "single",
            "title": "食品輸出の市場調査",
            "url": "https://coconala.com/requests/5179880",
            "price_jpy": 30000,
        },
        {
            "ts": 1785355000,
            "pass_id": "pass-old",
            "requestId": "5000000",
            "status": "applied",
            "submit_verified": True,
            "applied_page_verified": True,
        },
        {
            "ts": 1785356200,
            "pass_id": "pass-current",
            "requestId": "5179999",
            "status": "applied",
            "submit_verified": False,
            "applied_page_verified": True,
        },
    ])
    write_jsonl(paid_progress, [{
        "ts": 1785356300,
        "pass_id": "pass-current",
        "requestId": "17943244",
        "talkroom_id": "17943244",
        "status": "replied",
        "action": "paid_progress",
        "buyer_visible": True,
        "artifact_version": "v23",
        "url": "https://coconala.com/talkrooms/17943244",
    }])

    first = module.project(
        snapshot_path=None,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=applications,
        paid_progress_path=paid_progress,
        pass_id="pass-current",
        output_path=output,
    )
    second = module.project(
        snapshot_path=None,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=applications,
        paid_progress_path=paid_progress,
        pass_id="pass-current",
        output_path=output,
    )
    events = [json.loads(line) for line in output.read_text().splitlines()]

    assert first == {"appended": 2, "duplicate": 0}
    assert second == {"appended": 0, "duplicate": 2}
    assert [event["kind"] for event in events] == ["application", "delivery"]
    assert events[0]["attributes"]["title"] == "食品輸出の市場調査"
    assert events[1]["attributes"]["artifact_version"] == "v23"


def test_paid_text_answer_projects_as_reply_not_delivery(tmp_path):
    module = load_module()
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    paid_progress = tmp_path / "paid-progress.jsonl"
    output = tmp_path / "work-events.jsonl"
    write_jsonl(paid_progress, [{
        "ts": 1785356300,
        "pass_id": "answer-pass",
        "requestId": "contract-42",
        "talkroom_id": "42",
        "status": "replied",
        "action": "paid_progress",
        "buyer_visible": True,
        "interaction_mode": "answer",
        "url": "https://coconala.com/talkrooms/42",
    }])

    result = module.project(
        snapshot_path=None,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=empty,
        paid_progress_path=paid_progress,
        pass_id="answer-pass",
        output_path=output,
    )
    event = json.loads(output.read_text())

    assert result == {"appended": 1, "duplicate": 0}
    assert event["kind"] == "reply"
    assert event["state"] == "replied"
    assert event["action"] == "購入者の質問へ回答"
    assert "納品" not in event["result"]


def test_contract_projection_preserves_explicit_recurring_revenue_facts(tmp_path):
    module = load_module()
    snapshot = tmp_path / "marketplace-snapshot.json"
    snapshot.write_text(json.dumps({
        "captured_at": "2026-07-30T00:00:00+00:00",
        "orders": [{
            "status": "paid",
            "talkroom_id": "monthly-1",
            "title": "月次運用",
            "price_jpy": 64000,
            "recurring_active": True,
            "billing_period": "monthly",
            "monthly_net_jpy": 50000,
        }],
    }))
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    output = tmp_path / "work-events.jsonl"

    module.project(
        snapshot_path=snapshot,
        earnings_path=empty,
        failures_path=empty,
        audit_path=empty,
        applications_path=empty,
        paid_progress_path=empty,
        pass_id=None,
        output_path=output,
    )
    contract = json.loads(output.read_text())

    assert contract["attributes"]["recurring_active"] is True
    assert contract["attributes"]["billing_period"] == "monthly"
    assert contract["attributes"]["monthly_net_jpy"] == 50000


def test_finished_pass_projects_events_before_the_telegram_report():
    launcher = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "launch_gig_worker.sh"
    ).read_text(encoding="utf-8")

    projector = launcher.index("work_event_projector.py")
    report = launcher.index('telegram_report.py" pass')
    assert projector < report
    assert '--gig-dir "$HOME/gig"' in launcher
    assert "GIG_WORK_EVENT_PROJECTOR_LOG" in launcher
    assert '>> "$WORK_EVENT_PROJECTOR_LOG"' in launcher


def test_latest_snapshot_skips_a_newer_failure_without_a_snapshot(tmp_path):
    module = load_module()
    older = tmp_path / "evidence" / "gig-pass-old"
    newer = tmp_path / "evidence" / "gig-pass-new"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    expected = older / "marketplace-snapshot.json"
    expected.write_text("{}")
    write_jsonl(tmp_path / "pass-report.jsonl", [{
        "ts": 100,
        "pass_id": "old",
        "evidence_dir": str(older),
    }])
    write_jsonl(tmp_path / "pass-failures.jsonl", [{
        "ts": 200,
        "pass_id": "new",
        "evidence_dir": str(newer),
    }])

    assert module._latest_snapshot(tmp_path) == expected
