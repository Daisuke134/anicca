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
    assert envelope["data"]["outcome_progress"]["coverage_pct"] == 0.0
    assert envelope["data"]["outcome_progress"]["competitive_win_rate_pct"] is None
    assert envelope["data"]["outcome_progress"]["price_bands"]["不明"]["applications"] == 1
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
    assert "gig:telegram:weekly:v3:" in weekly_branch


def test_weekly_envelope_reports_rolling_outcomes_price_bands_and_high_budget(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "weekly_outcome_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "weekly_outcome_outbox")
    gig = tmp_path / "gig"
    gig.mkdir()
    now = datetime(2026, 8, 10, 0, 0, tzinfo=timezone.utc)
    applied = [
        {"requestId": "win", "status": "applied", "ts": "2026-08-01T00:00:00+00:00", "bid_jpy": "4,999", "budget_lo_jpy": "50,000"},
        # A duplicate application must stay one cohort member.
        {"requestId": "win", "status": "applied", "ts": "2026-08-01T00:01:00+00:00", "bid_jpy": 4999, "budget_lo_jpy": 50000},
        {"requestId": "other", "status": "applied", "ts": "2026-08-02T00:00:00+00:00", "price_jpy": 5000, "budget_hi_jpy": "50,000"},
        {"requestId": "open", "status": "applied", "ts": "2026-08-03T00:00:00+00:00", "price_proposed": "10,000", "budget_lo_jpy": None, "budget_hi_jpy": None},
        {"requestId": "closed", "status": "applied", "ts": "2026-08-04T00:00:00+00:00", "price_jpy": "49,999", "budget_hi_jpy": 49999},
        {"requestId": "expired", "status": "applied", "ts": "2026-08-05T00:00:00+00:00", "bid_jpy": 50000, "budget_hi_jpy": "50,000"},
        {"requestId": "win100", "status": "applied", "ts": "2026-08-06T00:00:00+00:00", "price_jpy": 100000, "budget_lo_jpy": 50000},
        {"requestId": "other299", "status": "applied", "ts": "2026-08-07T00:00:00+00:00", "price_proposed": "299,999", "budget_hi_jpy": 100000},
        {"requestId": "high", "status": "applied", "ts": "2026-08-08T00:00:00+00:00", "price_jpy": 300000},
        {"requestId": "unknown", "status": "applied", "ts": "2026-08-09T00:00:00+00:00"},
        {"requestId": "old", "status": "applied", "ts": "2026-06-01T00:00:00+00:00", "bid_jpy": 1000},
        {"requestId": "not-applied", "status": "replied", "ts": "2026-08-09T00:00:00+00:00", "bid_jpy": 1000},
    ]
    (gig / "applied.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in applied), encoding="utf-8"
    )
    outcomes = [
        {"request_id": "win", "status": "we_won", "checked_ts": 1},
        {"request_id": "other", "status": "someone_contracted", "checked_ts": 1},
        {"request_id": "open", "status": "someone_contracted", "checked_ts": 1},
        # Latest outcome wins: this request is now an open/no-pick observation.
        {"request_id": "open", "status": "open", "checked_ts": 2},
        {"request_id": "closed", "status": "closed_unfilled", "checked_ts": 1},
        {"request_id": "expired", "status": "expired", "checked_ts": 1},
        {"request_id": "win100", "status": "we_won", "checked_ts": 1},
        {"request_id": "other299", "status": "someone_contracted", "checked_ts": 1},
        {"request_id": "high", "status": "someone_contracted", "checked_ts": 1},
        {"request_id": "old", "status": "we_won", "checked_ts": 1},
    ]
    (gig / "applied-outcomes.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in outcomes), encoding="utf-8"
    )
    for name in ("earnings.jsonl", "shuppin.jsonl", "work-events.jsonl"):
        (gig / name).write_text("", encoding="utf-8")
    usage = tmp_path / "usage.jsonl"
    usage.write_text("", encoding="utf-8")
    outbox = outbox_module.TelegramOutbox(tmp_path / "telegram.sqlite3")

    envelope = report.weekly_envelope(
        gig_dir=gig, telegram_outbox=outbox, now=now, usage_ledger=usage
    )

    outcome = envelope["data"]["outcome_progress"]
    assert outcome["applications"] == 9
    assert outcome["tracked"] == 8
    assert outcome["coverage_pct"] == 88.89
    assert outcome["we_won"] == 2
    assert outcome["someone_contracted"] == 3
    assert outcome["closed_unfilled"] == 1
    assert outcome["expired"] == 1
    assert outcome["open"] == 1
    assert outcome["application_win_rate_pct"] == 22.22
    assert outcome["application_win_rate_target_pct"] == 5.0
    assert outcome["application_win_rate_gap_pct_points"] == 17.22
    assert outcome["competitive_win_rate_pct"] == 40.0
    bands = outcome["price_bands"]
    assert bands["<¥5k"] == {"applications": 1, "tracked": 1, "we_won": 1, "someone_contracted": 0}
    assert bands["¥5k–<10k"]["someone_contracted"] == 1
    assert bands["¥10k–<50k"]["applications"] == 2
    assert bands["¥50k–<100k"] == {"applications": 1, "tracked": 1, "we_won": 0, "someone_contracted": 0}
    assert bands["¥100k–<300k"]["applications"] == 2
    assert bands["¥300k+"]["applications"] == 1
    assert bands["不明"]["applications"] == 1
    high_budget = outcome["client_budget_50k_plus"]
    assert high_budget == {
        "applications": 5, "tracked": 5, "we_won": 2, "someone_contracted": 2,
    }
    ja = envelope["data"]["human_message_ja"]
    en = envelope["data"]["human_message_en"]
    assert "目標5%" in ja
    assert "追跡8件（88.89%）" in ja
    assert "自受注2件 / 他者契約3件 / 未契約終了1件 / 消滅1件 / 追跡中(open)1件" in ja
    assert "<¥5k" in ja and "¥300k+" in ja and "不明" in ja
    assert "client提示¥50k+" in ja
    assert "目標5%" not in en
