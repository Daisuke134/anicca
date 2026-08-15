"""A19: the daily report must never print success while the business is dead.

The RED reproduction fixture below is the REAL 2026-08-01 06:00 JST outage state,
copied from the read-only observation windows (§0.8): ~/gig/earnings.jsonl (all
rows), ~/gig/pass-report.jsonl / pass-failures.jsonl (rows inside the 24h window,
trimmed to the fields the verdict reads), ~/gig/applied.jsonl (last verified
apply before the cutoff), and configured runtime state/logs/gig-auditor.out.log (real STALE
rows). Nothing is invented: on that morning the daily Telegram still said
"success" — this suite makes that lie structurally impossible.
"""

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
JST = timezone(timedelta(hours=9))

# 2026-08-01 06:00 JST -- the measured moment of §0.1.3.
OUTAGE_NOW = datetime(2026, 7, 31, 21, 0, tzinfo=timezone.utc)

# ~/gig/earnings.jsonl, complete ledger as of the outage (2 rows, ¥63,960).
REAL_EARNINGS_ROWS = [
    {
        "ts": "2026/07/25 06:11",
        "loop": "gig",
        "adapter": "coconala",
        "requestId": "90000008",
        "talkroom_id": "90000008",
        "buyer": "buyer_handle_a",
        "title": "【Python/OpenCV】囲碁盤のカメラ画像から黒石・白石・空点を判定するPoC開発",
        "jpy": 50700.0,
        "net_of_fee": True,
        "status": "検収完了",
        "payout_requested": True,
        "evidence": "https://coconala.com/mypage/revenue",
        "idem_key": "coconala:revenue:90000008:2026/07/25 06:11",
    },
    {
        "ts": "2026/07/26 14:24",
        "loop": "gig",
        "adapter": "coconala",
        "requestId": "90000010",
        "talkroom_id": "90000010",
        "buyer": "buyer_handle_c",
        "title": "マインクラフト統合版の銃アドオンのバグ修正",
        "jpy": 13260.0,
        "net_of_fee": True,
        "status": "検収完了",
        "payout_requested": True,
        "evidence": "https://coconala.com/mypage/revenue",
        "idem_key": "coconala:revenue:90000010:2026/07/26 14:24",
    },
]

# ~/gig/pass-report.jsonl rows inside [07-31 06:00, 08-01 06:00) JST.
REAL_PASS_SUCCESS_ROWS = [
    {"ts": 1785448260, "driver": "gig_pass.sh", "status": "success",
     "pass_id": "1785445204-64277"},
    {"ts": 1785480563, "driver": "gig_pass.sh", "status": "success",
     "pass_id": "1785477600-62284"},
]

# ~/gig/pass-failures.jsonl rows inside the same window (16 distinct passes),
# trimmed to the fields the verdict reads.
REAL_PASS_FAILURE_ROWS = [
    {"ts": 1785475852, "pass_id": "1785474018-76905", "status": "failed",
     "failed_step": "B2", "reason": "b2_result_evidence_failed"},
    {"ts": 1785481229, "pass_id": "1785481200-50338", "status": "failed",
     "failed_step": "PAID_QUEUE_DELIVERY", "reason": "paid_queue_delivery_failed"},
    {"ts": 1785484954, "pass_id": "1785484817-4391", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
    {"ts": 1785488429, "pass_id": "1785488400-12708", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
    {"ts": 1785492036, "pass_id": "1785492000-71909", "status": "failed",
     "failed_step": "QUEUE", "reason": "live_queue_snapshot_failed"},
    {"ts": 1785495637, "pass_id": "1785495600-48425", "status": "failed",
     "failed_step": "QUEUE", "reason": "live_queue_snapshot_failed"},
    {"ts": 1785499236, "pass_id": "1785499200-24890", "status": "failed",
     "failed_step": "QUEUE", "reason": "live_queue_snapshot_failed"},
    {"ts": 1785502857, "pass_id": "1785502800-97856", "status": "failed",
     "failed_step": "QUEUE", "reason": "live_queue_snapshot_failed"},
    {"ts": 1785506435, "pass_id": "1785506400-91634", "status": "failed",
     "failed_step": "QUEUE", "reason": "live_queue_snapshot_failed"},
    {"ts": 1785507517, "pass_id": "1785507489-41375", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
    {"ts": 1785510080, "pass_id": "1785510000-19238", "status": "failed",
     "failed_step": "INQUIRY_REPLY", "reason": "reply_lane_failed"},
    {"ts": 1785513692, "pass_id": "1785513636-48735", "status": "failed",
     "failed_step": "INQUIRY_REPLY", "reason": "reply_lane_failed"},
    {"ts": 1785517236, "pass_id": "1785517205-56890", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
    {"ts": 1785520835, "pass_id": "1785520800-63683", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
    {"ts": 1785524428, "pass_id": "1785524400-74511", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
    {"ts": 1785528027, "pass_id": "1785528000-83826", "status": "failed",
     "failed_step": "PAID_WORK", "reason": "paid_work_transaction_begin_failed"},
]

# ~/gig/applied.jsonl: last verified apply before the cutoff
# (2026-07-31 04:52 JST -- more than 24h of application silence at 06:00).
REAL_LAST_APPLIED_ROW = {
    "ts": 1785441145,
    "pass_id": "1785438015-90901",
    "requestId": "91000075",
    "bucket": "single",
    "status": "applied",
    "title": "【WordPress・ドメイン移管】21サイトのサーバーおよびドメイン移管をお願いします",
    "price_jpy": None,
    "url": "https://coconala.com/requests/91000075",
    "submit_verified": True,
    "evidence": "gig-90901-B2-91000075-submitted.intent.json",
}

# configured runtime state/logs/gig-auditor.out.log: real STALE rows inside the window.
REAL_AUDITOR_ROWS = [
    {"ts": 1785465905,
     "verdict": "STALE (no pass in 294min — in-session cron likely stopped; healthcheck should restart)",
     "core_alive": True, "heartbeat_age_min": 294, "applied_total": 191,
     "actions_total": 315, "actions_delta_since_last_audit": 0,
     "earn_rows": 2, "jpy_earned": 63960.0, "progressing": False},
    {"ts": 1785469503,
     "verdict": "STALE (no pass in 354min — in-session cron likely stopped; healthcheck should restart)",
     "core_alive": True, "heartbeat_age_min": 354, "applied_total": 191,
     "actions_total": 315, "actions_delta_since_last_audit": 0,
     "earn_rows": 2, "jpy_earned": 63960.0, "progressing": False},
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def build_outage_gig_dir(tmp_path: Path) -> tuple[Path, Path]:
    gig = tmp_path / "gig"
    gig.mkdir()
    write_jsonl(gig / "earnings.jsonl", REAL_EARNINGS_ROWS)
    write_jsonl(gig / "applied.jsonl", [REAL_LAST_APPLIED_ROW])
    write_jsonl(gig / "pass-report.jsonl", REAL_PASS_SUCCESS_ROWS)
    write_jsonl(gig / "pass-failures.jsonl", REAL_PASS_FAILURE_ROWS)
    (gig / "shuppin.jsonl").write_text("", encoding="utf-8")
    (gig / "work-events.jsonl").write_text("", encoding="utf-8")
    auditor_log = tmp_path / "gig-auditor.out.log"
    write_jsonl(auditor_log, REAL_AUDITOR_ROWS)
    return gig, auditor_log


def test_outage_2026_08_01_daily_report_is_red_with_four_layer_breakdown(tmp_path):
    report = load(SCRIPTS / "telegram_report.py", "false_ok_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "false_ok_outbox")
    gig, auditor_log = build_outage_gig_dir(tmp_path)
    usage = tmp_path / "usage.jsonl"
    usage.write_text("", encoding="utf-8")
    outbox = outbox_module.TelegramOutbox(tmp_path / "telegram.sqlite3")

    envelope = report.daily_envelope(
        gig_dir=gig,
        connector_database=tmp_path / "connector.sqlite3",
        telegram_outbox=outbox,
        now=OUTAGE_NOW,
        usage_ledger=usage,
        auditor_log=auditor_log,
    )
    health = envelope["data"]["metrics"]["health"]
    ja = envelope["data"]["human_message_ja"]

    # Whole-day verdict: the real outage state may never render as success.
    assert health["verdict"] == "RED"
    assert envelope["data"]["status"] == "critical"
    assert ja.startswith("🔴")
    assert "☀️" not in ja
    assert "4つの仕事をすべて確認できています" not in ja

    # Each of the four layers is judged separately with a one-line reason.
    layers = health["layers"]
    assert set(layers) == {"liveness", "coverage", "productivity", "economics"}
    for layer in layers.values():
        assert layer["verdict"] in {"GREEN", "WARN", "RED"}
        assert layer["reason_ja"].strip()
    assert layers["liveness"]["verdict"] == "RED"       # auditor: STALE, not progressing
    assert layers["coverage"]["verdict"] == "RED"       # no lane closure evidence at all
    assert layers["productivity"]["verdict"] == "RED"   # 24h applications == 0
    assert layers["economics"]["verdict"] == "RED"      # settled revenue flat for 6 days

    # The breakdown itself is printed for Dais, one line per layer.
    for label in ("稼働", "確認", "実作業", "売上"):
        assert any(label in line and ("🔴" in line or "🟠" in line or "✅" in line)
                   for line in ja.splitlines()), label

    # ③ pass success rate and the last successful pass time are in the body.
    assert health["pass_24h"] == {"succeeded": 2, "failed": 16, "total": 18}
    assert "成功2/全18回" in ja
    assert "07-31 15:49" in ja

    # Economics: day-over-day delta is explicit, and the flat streak is named.
    assert health["settled_today_jpy"] == 0
    assert health["settled_delta_jpy"] == 0
    assert health["zero_settlement_streak_days"] == 6
    assert "前日比" in ja
    assert "6日連続" in ja

    # §4.2 invariants: a tappable link, and both today + month amounts.
    assert "https://coconala.com/mypage/job_matching/applied/offers" in ja
    assert "本日の入金 0円" in ja
    assert "今月の検収済売上" in ja


def test_daily_period_envelope_without_health_verdict_refuses_to_render(tmp_path):
    envelope_module = load(SCRIPTS / "report_envelope.py", "false_ok_envelope")
    snapshot = {
        "revenue_today_jpy": 0,
        "revenue_month_jpy": 0,
        "work": {"applied": 0, "replied": 0, "delivered": 0, "listings_created": 0},
        "funnel": {"applications": 0, "replies": 0, "contracts": 0,
                   "deliveries": 0, "payments": 0, "net_mrr": 0},
    }
    with pytest.raises(ValueError):
        envelope_module.build_period_envelope(
            report_type="daily",
            period_id="20260801",
            snapshot=snapshot,
            occurred_at=OUTAGE_NOW,
        )


def test_overall_verdict_never_green_when_any_layer_is_red():
    verdict = load(SCRIPTS / "daily_verdict.py", "false_ok_verdict")
    layers = {
        "liveness": {"verdict": "GREEN", "reason_ja": "ok"},
        "coverage": {"verdict": "GREEN", "reason_ja": "ok"},
        "productivity": {"verdict": "GREEN", "reason_ja": "ok"},
        "economics": {"verdict": "RED", "reason_ja": "flat"},
    }
    assert verdict.overall_verdict(layers) == "RED"
    layers["economics"] = {"verdict": "WARN", "reason_ja": "flat today"}
    assert verdict.overall_verdict(layers) == "WARN"
    layers["economics"] = {"verdict": "GREEN", "reason_ja": "grew"}
    assert verdict.overall_verdict(layers) == "GREEN"


def test_healthy_day_still_renders_green(tmp_path):
    """The inverse guard: the RED fix must not turn every day into an alarm."""
    import sqlite3

    report = load(SCRIPTS / "telegram_report.py", "false_ok_green_report")
    outbox_module = load(SCRIPTS / "telegram_outbox.py", "false_ok_green_outbox")
    now = datetime(2026, 7, 30, 0, 7, tzinfo=timezone.utc)  # 09:07 JST
    now_epoch = int(now.timestamp())
    gig = tmp_path / "gig"
    gig.mkdir()
    write_jsonl(gig / "applied.jsonl", [{
        "ts": now_epoch - 3600, "requestId": "9001", "status": "applied",
        "pass_id": "green-pass", "url": "https://coconala.com/requests/9001",
    }])
    write_jsonl(gig / "earnings.jsonl", [{
        "ts": "2026/07/30 09:02", "requestId": "9002", "status": "検収完了",
        "jpy": 78000, "evidence": "https://coconala.com/mypage/revenue",
    }])
    (gig / "shuppin.jsonl").write_text("", encoding="utf-8")
    (gig / "work-events.jsonl").write_text("", encoding="utf-8")
    write_jsonl(gig / "pass-report.jsonl", [
        {"ts": now_epoch - 1800, "driver": "gig_pass.sh",
         "status": "success", "pass_id": "green-pass"},
    ])
    auditor_log = tmp_path / "auditor.jsonl"
    write_jsonl(auditor_log, [{
        "ts": now_epoch - 900, "verdict": "OK", "core_alive": True,
        "heartbeat_age_min": 15, "progressing": True,
    }])
    lane_db = gig / "lane-actions.sqlite3"
    with sqlite3.connect(lane_db) as connection:
        connection.execute("""CREATE TABLE lane_actions(
            action_id INTEGER PRIMARY KEY,
            lane TEXT,event_key TEXT,action_kind TEXT,state TEXT,
            side_effect_count INTEGER,blind_retry_count INTEGER,
            observed_at INTEGER
        )""")
        connection.executemany(
            "INSERT INTO lane_actions VALUES(?,?,?,?,?,?,?,?)",
            [
                (1, "listing", "listing:pass-green-pass", "verified_noop",
                 "verified_noop", 0, 0, now_epoch - 1800),
                (2, "application", "application:pass-green-pass", "submit",
                 "verified", 1, 0, now_epoch - 1800),
                (3, "reply", "reply:pass-green-pass", "verified_noop",
                 "verified_noop", 0, 0, now_epoch - 1800),
                (4, "delivery", "delivery:pass-green-pass", "verified_noop",
                 "verified_noop", 0, 0, now_epoch - 1800),
            ],
        )
    evidence_root = gig / "evidence"
    pass_dir = evidence_root / "gig-pass-green-pass"
    pass_dir.mkdir(parents=True)
    (pass_dir / "poll-control.json").write_text(json.dumps({
        "version": 1, "pass_id": "green-pass", "model_calls": 1,
        "model_call_labels": ["B2"],
    }) + "\n", encoding="utf-8")
    usage = tmp_path / "usage.jsonl"
    write_jsonl(usage, [{
        "loop": "gig", "task_label": "gig-B2",
        "budget": {"scope_id": "green-pass"}, "provider_cost_usd": 0.10,
        "timestamp": now_epoch - 1700,
    }])
    outbox = outbox_module.TelegramOutbox(tmp_path / "telegram.sqlite3")

    envelope = report.daily_envelope(
        gig_dir=gig,
        connector_database=tmp_path / "connector.sqlite3",
        telegram_outbox=outbox,
        now=now,
        usage_ledger=usage,
        auditor_log=auditor_log,
    )
    health = envelope["data"]["metrics"]["health"]

    assert health["layers"]["liveness"]["verdict"] == "GREEN"
    assert health["layers"]["coverage"]["verdict"] == "GREEN"
    assert health["layers"]["productivity"]["verdict"] == "GREEN"
    assert health["layers"]["economics"]["verdict"] == "GREEN"
    assert health["verdict"] == "GREEN"
    assert envelope["data"]["status"] == "healthy"
    assert envelope["data"]["human_message_ja"].startswith("☀️")
