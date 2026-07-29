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


def test_weekly_envelope_is_plain_bilingual_and_compares_one_snapshot(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "weekly_envelope_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "weekly_envelope_outbox")
    gig = tmp_path / "gig"
    gig.mkdir()
    (gig / "applied.jsonl").write_text(
        json.dumps({
            "ts": "2026-07-21T00:01:00+00:00",
            "requestId": "1",
            "status": "applied",
        }) + "\n"
    )
    (gig / "earnings.jsonl").write_text(
        json.dumps({
            "ts": "2026/07/25 09:02",
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
            "occurred_at": "2026-07-22T00:03:00+00:00",
            "state": "verified",
        }) + "\n"
    )
    usage = tmp_path / "usage.jsonl"
    usage.write_text("")
    outbox = outbox_module.TelegramOutbox(tmp_path / "telegram.sqlite3")

    envelope = report.weekly_envelope(
        gig_dir=gig,
        telegram_outbox=outbox,
        now=datetime(2026, 7, 27, 0, 12, tzinfo=timezone.utc),
        usage_ledger=usage,
    )
    ja = envelope["data"]["human_message_ja"]
    en = envelope["data"]["human_message_en"]

    assert envelope["data"]["report_type"] == "weekly"
    assert envelope["data"]["funnel"]["applications"] == 1
    assert envelope["data"]["funnel"]["payments"] == 1
    assert "📊 1週間のギグワーク成績｜7月20日〜7月26日" in ja
    assert "応募 1件 → 返信 0件 → 契約 0件 → 納品 0件 → 入金 1件" in ja
    assert "売上 78,000円" in ja
    assert "前週比" in ja
    assert "次週の自動方針" in ja
    assert "ユーザーの操作は必要ありません" in ja
    assert "Weekly gig work results" in en
    assert "Revenue: JPY 78,000" in en
    for jargon in (
        "model cost",
        "incident",
        "self-heal",
        "route=",
        "verified",
        "noop",
        "lane",
    ):
        assert jargon not in ja


def test_weekly_runtime_uses_envelope_and_writes_the_agent_feed():
    source = (SCRIPTS / "telegram_report.py").read_text(encoding="utf-8")
    weekly_branch = source[source.index('elif args.command == "weekly"'):]
    weekly_branch = weekly_branch[:weekly_branch.index("else:")]

    assert "weekly_envelope(" in weekly_branch
    assert "append_agent_feed" in weekly_branch
    assert "human_message_ja" in weekly_branch
