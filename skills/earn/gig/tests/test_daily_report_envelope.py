import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_daily_envelope_is_plain_bilingual_and_uses_one_funnel_snapshot(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "daily_envelope_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "daily_envelope_outbox")
    gig = tmp_path / "gig"
    gig.mkdir()
    (gig / "applied.jsonl").write_text(
        json.dumps({
            "ts": "2026-07-30T00:01:00+00:00",
            "requestId": "1",
            "status": "applied",
        }) + "\n"
    )
    (gig / "earnings.jsonl").write_text(
        json.dumps({
            "ts": "2026/07/30 09:02",
            "requestId": "2",
            "status": "検収完了",
            "jpy": 78000,
            "evidence": "https://coconala.com/mypage/revenue",
        }) + "\n"
    )
    (gig / "shuppin.jsonl").write_text("")
    (gig / "work-events.jsonl").write_text(
        json.dumps({
            "event_key": "gig:recovery:application:fixture",
            "kind": "recovery",
            "entity_id": "application",
            "occurred_at": "2026-07-30T00:03:00+00:00",
            "state": "verified",
        }) + "\n"
    )
    usage = tmp_path / "usage.jsonl"
    usage.write_text("")
    outbox = outbox_module.TelegramOutbox(tmp_path / "telegram.sqlite3")

    envelope = report.daily_envelope(
        gig_dir=gig,
        connector_database=tmp_path / "connector.sqlite3",
        telegram_outbox=outbox,
        now=datetime(2026, 7, 30, 0, 7, tzinfo=timezone.utc),
        usage_ledger=usage,
    )
    ja = envelope["data"]["human_message_ja"]
    en = envelope["data"]["human_message_en"]

    assert envelope["data"]["report_type"] == "daily"
    assert envelope["data"]["funnel"] == {
        "applications": 1,
        "replies": 0,
        "contracts": 0,
        "deliveries": 0,
        "payments": 1,
        "net_mrr": 0,
    }
    assert "☀️ 今日のギグワーク結果｜7月30日" in ja
    assert "応募 1件 → 返信 0件 → 契約 0件 → 納品 0件 → 入金 1件" in ja
    assert "本日の入金 78,000円" in ja
    assert "1件の復旧を確認しました" in ja
    assert "ユーザーの操作は必要ありません" in ja
    assert "Daily gig work results" in en
    assert "Applications 1 → Replies 0 → Contracts 0 → Deliveries 0 → Payments 1" in en
    for jargon in (
        "verified",
        "noop",
        "lane",
        "Shuppin",
        "Oubo",
        "Nouhin",
        "route=",
        "model cost",
        "self-heal",
    ):
        assert jargon not in ja


def test_daily_runtime_uses_envelope_and_writes_the_agent_feed():
    source = (SCRIPTS / "telegram_report.py").read_text(encoding="utf-8")
    daily_branch = source[source.index('elif args.command == "daily"'):]
    daily_branch = daily_branch[:daily_branch.index('elif args.command == "weekly"')]

    assert "daily_envelope(" in daily_branch
    assert "append_agent_feed" in daily_branch
    assert "human_message_ja" in daily_branch


def test_net_mrr_counts_only_explicit_active_monthly_contract_ground_truth(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "verified_net_mrr_report")
    work_events = tmp_path / "work-events.jsonl"
    rows = [
        {
            "event_key": "gig:contract:coconala:active",
            "kind": "contract",
            "entity_id": "active",
            "occurred_at": "2026-07-30T00:01:00+00:00",
            "state": "confirmed",
            "evidence": ["marketplace_order"],
            "attributes": {
                "recurring_active": True,
                "billing_period": "monthly",
                "monthly_net_jpy": 50000,
            },
        },
        {
            "event_key": "gig:contract:coconala:application-only",
            "kind": "application",
            "entity_id": "application-only",
            "occurred_at": "2026-07-30T00:02:00+00:00",
            "state": "verified",
            "evidence": ["marketplace_readback"],
            "attributes": {
                "bucket": "retainer",
                "price_jpy": 200000,
            },
        },
        {
            "event_key": "gig:contract:coconala:single",
            "kind": "contract",
            "entity_id": "single",
            "occurred_at": "2026-07-30T00:03:00+00:00",
            "state": "confirmed",
            "evidence": ["marketplace_order"],
            "attributes": {
                "recurring_active": False,
                "billing_period": "one_time",
                "monthly_net_jpy": 100000,
            },
        },
    ]
    work_events.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n"
    )

    assert report._verified_net_mrr(work_events) == 50000
