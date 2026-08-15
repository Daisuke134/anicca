import importlib.util
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def event(kind: str, number: int = 1) -> dict:
    attributes = {
        "application": {
            "title": "食品輸出の市場調査",
            "url": "https://coconala.com/requests/91000055",
            "bucket": "single",
            "price_jpy": 30000,
        },
        "delivery": {
            "artifact_version": "v23",
            "buyer_visible": True,
        },
        "contract": {
            "title": "Webサイト改善",
            "price_jpy": 100000,
            "delivery_date": "2026-08-12",
        },
        "payment": {
            "title": "Webサイト改善",
            "net_jpy": 78000,
            "net_of_fee": True,
        },
        "incident": {
            "failure_class": "application_readback_failed",
            "affected_lane": "application",
            "duplicate_side_effect_observed": False,
        },
        "recovery": {
            "recovered_lane": "application",
            "from": "down",
            "to": "ok",
        },
    }[kind]
    return {
        "event_key": f"gig:{kind}:fixture-{number}",
        "kind": kind,
        "entity_id": f"entity-{number}",
        "occurred_at": f"2026-07-30T00:0{number}:00+00:00",
        "state": "detected" if kind == "incident" else "confirmed",
        "action": "fixture action",
        "result": "fixture result",
        "next_action": "fixture next",
        "evidence": ["fixture"],
        "attributes": attributes,
    }


def test_business_event_envelopes_have_plain_ja_and_en_from_one_snapshot():
    envelope_module = load(SCRIPTS / "report_envelope.py", "business_envelope")

    envelopes = {
        kind: envelope_module.build_work_event_envelope(
            work_event=event(kind),
            observed_at=datetime(2026, 7, 30, 0, 10, tzinfo=timezone.utc),
        )
        for kind in (
            "application", "delivery", "contract", "payment", "incident", "recovery"
        )
    }

    assert envelopes["application"]["data"]["human_message_ja"].startswith(
        "📨 新しい仕事へ応募しました"
    )
    assert "食品輸出の市場調査" in envelopes["application"]["data"]["human_message_ja"]
    assert envelopes["delivery"]["data"]["human_message_ja"].startswith(
        "📦 納品内容を購入者へ提出しました"
    )
    assert envelopes["contract"]["data"]["human_message_ja"].startswith(
        "🎉 新しい仕事を受注しました"
    )
    assert "契約金額: 100,000円" in envelopes["contract"]["data"]["human_message_ja"]
    assert envelopes["payment"]["data"]["human_message_ja"].startswith(
        "💰 78,000円の入金を確認しました"
    )
    assert "自動で復旧しています" in envelopes["incident"]["data"]["human_message_ja"]
    assert "ユーザーの操作は必要ありません" in envelopes["incident"]["data"]["human_message_ja"]
    assert envelopes["recovery"]["data"]["human_message_ja"].startswith(
        "🟢 応募機能が復旧しました"
    )
    assert "A new contract was confirmed" in envelopes["contract"]["data"]["human_message_en"]
    assert "JPY 78,000" in envelopes["payment"]["data"]["human_message_en"]
    assert "Automatic recovery is in progress" in envelopes["incident"]["data"]["human_message_en"]
    assert "Application work has recovered" in envelopes["recovery"]["data"]["human_message_en"]
    for envelope in envelopes.values():
        assert envelope["data"]["events"] == [envelope["data"]["work_event"]]
        assert envelope["data"]["human_message_ja"]
        assert envelope["data"]["human_message_en"]
        for hidden in (
            "application_readback_failed",
            "B0",
            "B1",
            "B2",
            "verified_noop",
            "route=",
            "hash",
        ):
            assert hidden not in envelope["data"]["human_message_ja"]


def test_missing_state_bootstraps_history_then_only_new_events_are_sent(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "business_event_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "business_event_outbox")
    events_path = tmp_path / "work-events.jsonl"
    state_path = tmp_path / "work-event-report-state.json"
    feed_path = tmp_path / "report-envelopes.jsonl"
    database = tmp_path / "telegram.sqlite3"
    events_path.write_text(
        "\n".join(json.dumps(event(kind)) for kind in ("contract", "payment")) + "\n"
    )
    outbox = outbox_module.TelegramOutbox(database)
    calls: list[str] = []
    clock_values = iter(range(100, 300))

    baseline = report.publish_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or "tg-baseline",
        now=clock_values.__next__,
    )
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event("incident", 2)) + "\n")
    first = report.publish_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or "tg-new",
        now=clock_values.__next__,
    )
    second = report.publish_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or "tg-duplicate",
        now=clock_values.__next__,
    )

    assert baseline == {
        "sent": 0,
        "delivery_unknown": 0,
        "bootstrapped": 2,
        "enqueued": 0,
    }
    assert first["sent"] == 1
    assert first["enqueued"] == 1
    assert second["sent"] == 0
    assert second["enqueued"] == 0
    assert len(calls) == 1
    assert "自動で復旧しています" in calls[0]
    state = json.loads(state_path.read_text())
    assert set(state["seen_event_keys"]) == {
        "gig:contract:fixture-1",
        "gig:payment:fixture-1",
        "gig:incident:fixture-2",
    }
    feed = [json.loads(line) for line in feed_path.read_text().splitlines()]
    assert len(feed) == 1
    assert feed[0]["data"]["report_type"] == "incident"


def test_instant_application_and_delivery_reports_send_without_history_baseline(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "instant_business_event_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "instant_business_event_outbox")
    events_path = tmp_path / "work-events.jsonl"
    state_path = tmp_path / "instant-work-event-report-state.json"
    feed_path = tmp_path / "report-envelopes.jsonl"
    database = tmp_path / "telegram.sqlite3"
    events_path.write_text(
        "\n".join(json.dumps(event(kind)) for kind in ("application", "delivery")) + "\n"
    )
    outbox = outbox_module.TelegramOutbox(database)
    calls: list[str] = []
    clock_values = iter(range(100, 300))

    first = report.publish_instant_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or f"tg-{len(calls)}",
        now=clock_values.__next__,
    )
    second = report.publish_instant_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or "tg-duplicate",
        now=clock_values.__next__,
    )

    assert first["sent"] == 2
    assert first["enqueued"] == 2
    assert second["sent"] == 0
    assert second["enqueued"] == 0
    assert calls[0].startswith("📨 新しい仕事へ応募しました")
    assert calls[1].startswith("📦 納品内容を購入者へ提出しました")
    state = json.loads(state_path.read_text())
    assert set(state["seen_event_keys"]) == {
        "gig:application:fixture-1",
        "gig:delivery:fixture-1",
    }
    feed = [json.loads(line) for line in feed_path.read_text().splitlines()]
    assert [row["data"]["report_type"] for row in feed] == [
        "application",
        "delivery",
    ]


def test_instant_skips_historical_events_but_sends_recent_once(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "historical_instant_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "historical_instant_outbox")
    events_path = tmp_path / "work-events.jsonl"
    state_path = tmp_path / "instant-work-event-report-state.json"
    feed_path = tmp_path / "report-envelopes.jsonl"
    database = tmp_path / "telegram.sqlite3"
    observed_at = datetime(2026, 7, 31, tzinfo=timezone.utc)
    old_event = event("application", 1)
    old_event["occurred_at"] = (observed_at - timedelta(hours=25)).isoformat()
    invalid_event = event("delivery", 3)
    invalid_event.pop("occurred_at")
    recent_event = event("delivery", 2)
    recent_event["occurred_at"] = (observed_at - timedelta(hours=1)).isoformat()
    events_path.write_text(
        "\n".join(json.dumps(row) for row in (old_event, invalid_event, recent_event)) + "\n"
    )
    outbox = outbox_module.TelegramOutbox(database)
    calls: list[str] = []
    now = lambda: int(observed_at.timestamp())

    first = report.publish_instant_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or f"tg-{len(calls)}",
        now=now,
    )
    second = report.publish_instant_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or "tg-duplicate",
        now=now,
    )

    assert first["sent"] == 1
    assert first["enqueued"] == 1
    assert first["historical_skipped"] == 2
    assert second["sent"] == 0
    assert second["enqueued"] == 0
    assert second["historical_skipped"] == 2
    assert len(calls) == 1
    feed = [json.loads(line) for line in feed_path.read_text().splitlines()]
    assert [row["data"]["report_type"] for row in feed] == ["delivery"]
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE event_key=?",
            ("gig:telegram:instant-work-event:v1:" + old_event["event_key"],),
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE event_key=?",
            ("gig:telegram:instant-work-event:v1:" + invalid_event["event_key"],),
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE event_key=?",
            ("gig:telegram:instant-work-event:v1:" + recent_event["event_key"],),
        ).fetchone()[0] == 1


def test_distinct_application_events_with_identical_bodies_are_both_delivered(tmp_path):
    """A new application is an event, even when its human text is unchanged."""
    report = load(SCRIPTS / "telegram_report.py", "same_body_application_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "same_body_application_outbox")
    events_path = tmp_path / "work-events.jsonl"
    state_path = tmp_path / "instant-work-event-report-state.json"
    feed_path = tmp_path / "report-envelopes.jsonl"
    database = tmp_path / "telegram.sqlite3"
    events_path.write_text(
        "\n".join(json.dumps(event("application", number)) for number in (1, 2)) + "\n"
    )
    outbox = outbox_module.TelegramOutbox(database)
    calls: list[str] = []

    result = report.publish_instant_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or f"tg-{len(calls)}",
        now=iter(range(100, 300)).__next__,
    )

    assert result["sent"] == 2
    assert result["enqueued"] == 2
    assert calls[0] == calls[1]
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE kind='application'"
        ).fetchone()[0] == 2


def test_seen_application_event_without_outbox_row_is_repaired_on_normal_rerun(tmp_path):
    """A seen cursor must not permanently hide a lost durable outbox row."""
    report = load(SCRIPTS / "telegram_report.py", "seen_only_application_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "seen_only_application_outbox")
    events_path = tmp_path / "work-events.jsonl"
    state_path = tmp_path / "instant-work-event-report-state.json"
    feed_path = tmp_path / "report-envelopes.jsonl"
    database = tmp_path / "telegram.sqlite3"
    work_event = event("application", 2)
    events_path.write_text(json.dumps(work_event) + "\n")
    state_path.write_text(json.dumps({
        "version": 1,
        "seen_event_keys": [work_event["event_key"]],
    }) + "\n")
    outbox = outbox_module.TelegramOutbox(database)
    calls: list[str] = []

    result = report.publish_instant_work_event_reports(
        events_path=events_path,
        state_path=state_path,
        agent_feed_path=feed_path,
        outbox=outbox,
        transport=lambda message: calls.append(message) or "tg-repaired",
        now=iter(range(100, 300)).__next__,
    )

    assert result["sent"] == 1
    assert result["enqueued"] == 1
    assert len(calls) == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM telegram_reports WHERE event_key=?",
            ("gig:telegram:instant-work-event:v1:" + work_event["event_key"],),
        ).fetchone()[0] == 1


def test_launcher_publishes_new_work_events_after_the_pass_report():
    launcher = (SCRIPTS / "launch_gig_worker.sh").read_text(encoding="utf-8")
    pass_report = launcher.index('telegram_report.py" pass')
    instant = launcher.index('telegram_report.py" instant-work-events')
    work_events = launcher.index('telegram_report.py" work-events')
    barren = launcher.index('telegram_report.py" lane-barren')

    assert pass_report < instant < work_events < barren


def test_live_pass_publishes_application_and_delivery_events_immediately():
    source = (
        SCRIPTS.parent / "gig_pass.sh"
    ).read_text(encoding="utf-8")
    assert "publish_instant_work_events" in source
    assert 'work_event_projector.py" --gig-dir "$HOME/gig" --pass-id "$PASS_ID"' in source
    assert 'telegram_report.py" instant-work-events' in source
    b2_gate = source.index('b2_result_gate.py" validate')
    b2_publish = source.index('publish_instant_work_events "application"', b2_gate)
    b2_continue = source.index("return 3", b2_gate)
    assert b2_gate < b2_publish < b2_continue
    paid_record = source.index('paid_progress_ledger.py" record')
    delivery_publish = source.index('publish_instant_work_events "delivery"', paid_record)
    assert paid_record < delivery_publish


def test_two_unrelated_incidents_do_not_render_the_same_text():
    """Identical bodies are how a real alert gets swallowed.

    Measured 2026-08-04 on ~/gig/telegram-outbox.sqlite3: "🟠 納品機能を自動で
    復旧しています" had been sent 104 times and the 応募 variant 98 times,
    because the body was fixed text plus the lane name. The outbox now
    suppresses a body it has already sent for 24 hours, so two unrelated
    failures that render the same bytes become one delivery and the second
    outage is never reported.
    """
    envelope_module = load(SCRIPTS / "report_envelope.py", "incident_envelope")

    first = event("incident", 1)
    second = event("incident", 2)
    second["attributes"] = dict(second["attributes"], failure_class="delivery_upload_failed")

    def body(work_event):
        return envelope_module.build_work_event_envelope(
            work_event=work_event,
            observed_at=datetime(2026, 7, 30, 0, 10, tzinfo=timezone.utc),
        )["data"]["human_message_ja"]

    assert body(first) != body(second)


def test_an_incident_body_says_when_it_was_detected():
    """The Japanese body may not carry the raw failure class, so it carries time.

    test_business_event_envelopes_have_plain_ja_and_en_from_one_snapshot pins
    "application_readback_failed" as forbidden in human_message_ja. The class
    still belongs somewhere a human can diagnose from, so it goes in the English
    body, and the Japanese body gets the detection minute — which is what the
    suppression window actually needs to tell two incidents apart.
    """
    envelope_module = load(SCRIPTS / "report_envelope.py", "incident_envelope_detail")

    data = envelope_module.build_work_event_envelope(
        work_event=event("incident", 1),
        observed_at=datetime(2026, 7, 30, 0, 10, tzinfo=timezone.utc),
    )["data"]

    assert "7月30日 09:01" in data["human_message_ja"]
    assert "application_readback_failed" in data["human_message_en"]
