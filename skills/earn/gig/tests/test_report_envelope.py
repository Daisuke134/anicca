import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MODULE_PATH = SCRIPTS / "report_envelope.py"


def load_module():
    spec = importlib.util.spec_from_file_location("gig_report_envelope", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load report_envelope")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_inputs():
    pass_row = {
        "ts": 1785348055,
        "pass_id": "1785345364-30390",
        "status": "success",
        "steps_executed": ["PAID_QUEUE_DELIVERY", "B0", "B1", "B2"],
        "steps_skipped_cooldown": [],
        "steps_skipped_policy": ["LEARN:not_selected"],
    }
    applications = [{
        "ts": 1785348030,
        "pass_id": "1785345364-30390",
        "requestId": "01KXJ32G33VXT4PTVQJVQKFTA7",
        "bucket": "retainer",
        "status": "applied",
        "title": "完全在宅のセールスライター募集",
        "url": (
            "https://coconala.com/job_matching/outsources/"
            "01KXJ32G33VXT4PTVQJVQKFTA7"
        ),
        "submit_verified": True,
        "applied_page_verified": True,
    }]
    usage_rows = [{
        "loop": "gig",
        "task_label": "gig-B2",
        "provider_cost_usd": 1.25,
        "budget": {"scope_id": "1785345364-30390"},
    }]
    return pass_row, applications, usage_rows


def test_pass_envelope_has_deduplicable_identity_and_exact_work_events():
    module = load_module()
    pass_row, applications, usage_rows = fixture_inputs()

    envelope = module.build_pass_envelope(
        pass_row=pass_row,
        applications=applications,
        usage_rows=usage_rows,
        observed_at=datetime.fromtimestamp(1785348059, timezone.utc),
    )

    assert envelope["specversion"] == "1.0"
    assert envelope["id"] == "gig:report:pass:1785345364-30390:success"
    assert envelope["source"] == "life-manager/gig"
    assert envelope["type"] == "com.anicca.gig.report.pass.v1"
    assert envelope["subject"] == "gig-pass/1785345364-30390"
    assert envelope["data"]["metrics"] == {
        "model_calls": 1,
        "model_cost_usd": 1.25,
        "verified_applications": 1,
        "searched_opportunities": 0,
    }
    application = next(
        event for event in envelope["data"]["events"]
        if event["kind"] == "application"
    )
    assert application["entity_id"] == "01KXJ32G33VXT4PTVQJVQKFTA7"
    assert application["result"] == "応募を送信し、応募履歴と台帳への記録を確認しました"
    assert application["evidence"] == [
        "submission",
        "marketplace_readback",
        "canonical_ledger",
    ]


def test_human_renderer_uses_plain_japanese_and_hides_internal_jargon():
    module = load_module()
    pass_row, applications, usage_rows = fixture_inputs()
    envelope = module.build_pass_envelope(
        pass_row=pass_row,
        applications=applications,
        usage_rows=usage_rows,
        observed_at=datetime.fromtimestamp(1785348059, timezone.utc),
    )

    message = module.render_human_ja(envelope)

    assert "✅ ギグワークの作業が完了しました" in message
    assert "今回行ったこと" in message
    assert "応募: 1件" in message
    assert "完全在宅のセールスライター募集" in message
    assert "送信・応募履歴・台帳の3か所で確認済み" in message
    assert "次の予定" in message
    for jargon in (
        "gig pass", "steps=", "skipped=", "model_calls=", "verified=",
        "request=", "route=", "B0", "B1", "B2", "verified_noop",
    ):
        assert jargon not in message


def test_agent_feed_is_the_same_envelope_without_a_second_summary():
    module = load_module()
    pass_row, applications, usage_rows = fixture_inputs()
    envelope = module.build_pass_envelope(
        pass_row=pass_row,
        applications=applications,
        usage_rows=usage_rows,
        observed_at=datetime.fromtimestamp(1785348059, timezone.utc),
    )

    encoded = module.render_agent_json(envelope)

    assert json.loads(encoded) == envelope


def test_agent_feed_append_is_idempotent_by_envelope_id(tmp_path):
    module = load_module()
    pass_row, applications, usage_rows = fixture_inputs()
    envelope = module.build_pass_envelope(
        pass_row=pass_row,
        applications=applications,
        usage_rows=usage_rows,
        observed_at=datetime.fromtimestamp(1785348059, timezone.utc),
    )
    path = tmp_path / "report-envelopes.jsonl"

    first = module.append_agent_feed(path, envelope)
    second = module.append_agent_feed(path, envelope)

    assert first == {"appended": 1, "duplicate": 0}
    assert second == {"appended": 0, "duplicate": 1}
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows == [envelope]


def test_lane_evidence_becomes_separate_listing_reply_and_delivery_events(tmp_path):
    module = load_module()
    pass_id = "1785345364-30390"
    evidence = tmp_path / f"gig-pass-{pass_id}"
    (evidence / "agent-B0").mkdir(parents=True)
    (evidence / "agent-B1").mkdir(parents=True)
    (evidence / "agent-PAID_QUEUE_DELIVERY").mkdir(parents=True)
    (evidence / "agent-B0" / "attempt-01.result.json").write_text(json.dumps({
        "status": "ok",
        "current_b0": {
            "action": "verified_noop",
            "reason": "サービスの出品可能数をオーバーしています",
        },
    }, ensure_ascii=False))
    (evidence / "agent-B1" / "attempt-01.result.json").write_text(json.dumps({
        "status": "ok",
        "current_b1": {
            "inspected_talkrooms": [{
                "talkroom_id": "17943244",
                "url": "https://coconala.com/talkrooms/17943244",
                "outcome": "observed_no_action",
            }],
        },
    }, ensure_ascii=False))
    (
        evidence / "agent-PAID_QUEUE_DELIVERY" / "paid-queue-evidence.json"
    ).write_text(json.dumps({
        "sent": True,
        "talkroom_id": "17943244",
        "artifact_basename": "v23.zip",
        "artifact_version": "v23",
        "package_sha256": "c858e537",
        "live_dom_path": str(evidence / "delivery-dom.json"),
    }, ensure_ascii=False))

    events = module.collect_lane_events(
        evidence_dir=evidence,
        pass_id=pass_id,
        occurred_at=1785348055,
    )

    assert [event["kind"] for event in events] == [
        "listing",
        "reply",
        "delivery",
    ]
    assert events[0]["result"] == (
        "新しい出品は行わず、出品可能数の上限に達していることを確認しました"
    )
    assert events[1]["result"] == (
        "購入者との会話を確認し、新しく返信すべきメッセージがないことを確認しました"
    )
    assert events[2]["result"] == (
        "v23.zipが購入者画面に表示され、納品内容を確認できる状態です"
    )
    assert events[2]["evidence"] == ["buyer_visible_dom", "artifact_sha256"]


def test_b2_source_counts_become_one_application_search_event(tmp_path):
    module = load_module()
    pass_id = "1785355203-61371"
    evidence = tmp_path / f"gig-pass-{pass_id}"
    (evidence / "agent-B2").mkdir(parents=True)
    (evidence / "agent-B2" / "attempt-01.result.json").write_text(json.dumps({
        "status": "ok",
        "current_b2": {
            "inspected_requests": [{"request_id": "5179880"}],
            "search_sources": [
                {
                    "source_id": "single:new",
                    "inspected_count": 131,
                    "has_next": True,
                    "exhausted": False,
                },
                {
                    "source_id": "retainer:new",
                    "inspected_count": 55,
                    "has_next": True,
                    "exhausted": False,
                },
            ],
        },
    }))

    events = module.collect_lane_events(
        evidence_dir=evidence,
        pass_id=pass_id,
        occurred_at=1785358835,
    )

    assert len(events) == 1
    assert events[0]["kind"] == "application_search"
    assert events[0]["result"] == "単発・関連カテゴリ・継続案件を延べ186件確認しました"
    assert events[0]["attributes"]["searched"] == 186
    assert events[0]["attributes"]["sources"] == [
        {
            "source_id": "single:new",
            "inspected_count": 131,
            "has_next": True,
            "exhausted": False,
        },
        {
            "source_id": "retainer:new",
            "inspected_count": 55,
            "has_next": True,
            "exhausted": False,
        },
    ]


def test_pass_message_reports_extended_search_count_and_verified_applications(tmp_path):
    module = load_module()
    pass_row, applications, usage_rows = fixture_inputs()
    search_event = {
        "event_key": "gig:application-search:1785345364-30390",
        "kind": "application_search",
        "lane": "application",
        "entity_id": "1785345364-30390",
        "occurred_at": "2026-07-29T18:00:55+00:00",
        "state": "searched",
        "action": "応募可能な仕事を探索",
        "result": "単発・関連カテゴリ・継続案件を延べ186件確認しました",
        "next_action": "次の検索位置から探索を続けます",
        "evidence": ["b2_search_sources"],
        "attributes": {"searched": 186, "sources": []},
    }
    envelope = module.build_pass_envelope(
        pass_row=pass_row,
        applications=applications,
        usage_rows=usage_rows,
        observed_at=datetime.fromtimestamp(1785348059, timezone.utc),
        lane_events=[search_event],
    )

    assert envelope["data"]["work"]["searched"] == 186
    assert envelope["data"]["work"]["applied"] == 1
    assert envelope["data"]["metrics"]["searched_opportunities"] == 186
    message = module.render_human_ja(envelope)
    assert "応募: 延べ186件を確認し、1件に応募しました" in message


def test_human_renderer_reports_every_lane_event_in_plain_japanese(tmp_path):
    module = load_module()
    pass_row, applications, usage_rows = fixture_inputs()
    events = [
        {
            "event_key": "gig:listing:pass",
            "kind": "listing",
            "lane": "listing",
            "entity_id": "storefront",
            "occurred_at": "2026-07-29T18:00:55+00:00",
            "state": "observed_no_action",
            "action": "出品枠を確認",
            "result": "出品可能数の上限に達していることを確認しました",
            "next_action": "既存サービスの改善を続けます",
            "evidence": ["storefront_dom"],
            "attributes": {},
        },
        {
            "event_key": "gig:reply:pass:17943244",
            "kind": "reply",
            "lane": "reply",
            "entity_id": "17943244",
            "occurred_at": "2026-07-29T18:00:55+00:00",
            "state": "observed_no_action",
            "action": "購入者メッセージを確認",
            "result": "新しく返信すべきメッセージがないことを確認しました",
            "next_action": "5分ごとに新着を確認します",
            "evidence": ["talkroom_dom"],
            "attributes": {},
        },
        {
            "event_key": "gig:delivery:pass:17943244",
            "kind": "delivery",
            "lane": "delivery",
            "entity_id": "17943244",
            "occurred_at": "2026-07-29T18:00:55+00:00",
            "state": "buyer_visible",
            "action": "納品内容を確認",
            "result": "v23.zipが購入者画面に表示されていることを確認しました",
            "next_action": "購入者からの確認結果を待ちます",
            "evidence": ["buyer_visible_dom", "artifact_sha256"],
            "attributes": {"artifact_basename": "v23.zip"},
        },
    ]
    envelope = module.build_pass_envelope(
        pass_row=pass_row,
        applications=applications,
        usage_rows=usage_rows,
        observed_at=datetime.fromtimestamp(1785348059, timezone.utc),
        lane_events=events,
    )

    message = module.render_human_ja(envelope)

    assert "出品: 出品可能数の上限に達していることを確認しました" in message
    assert "返信: 新しく返信すべきメッセージがないことを確認しました" in message
    assert "納品: v23.zipが購入者画面に表示されていることを確認しました" in message
    assert message.index("出品:") < message.index("返信:") < message.index("納品:")
