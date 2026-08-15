import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPORT_SCRIPT = SCRIPTS / "telegram_report.py"
OUTBOX_SCRIPT = SCRIPTS / "telegram_outbox.py"
GIG_PASS_SCRIPT = Path(__file__).resolve().parents[1] / "gig_pass.sh"
RUNNER_CONFIG = Path(__file__).resolve().parents[4] / "runtime" / "agent-runner" / "config.json"
JST = timezone(timedelta(hours=9))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TelegramReportingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.connector_db = self.root / "connector.sqlite3"
        self.telegram_db = self.root / "telegram.sqlite3"
        self.gig_dir = self.root / "gig"
        self.gig_dir.mkdir()
        self.report = load(REPORT_SCRIPT, "telegram_report")
        self.outbox_module = load(OUTBOX_SCRIPT, "telegram_report_outbox")
        self.route = self.report.composition_route(RUNNER_CONFIG)

    def tearDown(self):
        self.temp.cleanup()

    def create_connector_rows(self):
        with sqlite3.connect(self.connector_db) as connection:
            connection.execute("""CREATE TABLE connector_actions(
                action_id INTEGER,thread_id TEXT,state TEXT,revision INTEGER,
                created_at INTEGER,updated_at INTEGER,seller_sent_at INTEGER
            )""")
            connection.executemany(
                "INSERT INTO connector_actions VALUES(?,?,?,?,?,?,?)",
                [
                    (1, "42", "replied", 1, 100, 200, 190),
                    (2, "43", "pending", 1, 210, 210, None),
                    (3, "44", "reconcile_pending", 1, 220, 220, None),
                ],
            )

    def test_instant_verified_reply_is_idempotent_and_contains_no_private_content(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        event = {
            "action_id": 7,
            "revision": 2,
            "talkroom_id": "9942584",
            "origin_at": "2026-07-22T06:06:11+00:00",
            "seller_sent_at": "2026-07-22T06:07:11+00:00",
            "status": "replied",
            "private_body": "must never appear",
            "outgoing_hash": "a" * 64,
        }
        calls = []
        clock = iter((200, 201, 202, 203, 204, 205)).__next__
        agent_feed = self.gig_dir / "report-envelopes.jsonl"

        first = self.report.publish_reply_events(
            events=[event], outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-1",
            now=clock, agent_feed_path=agent_feed,
        )
        second = self.report.publish_reply_events(
            events=[event], outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-duplicate",
            now=clock, agent_feed_path=agent_feed,
        )

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(len(calls), 1)
        message = calls[0]
        self.assertIn("💬 お客様への返信が完了しました", message)
        self.assertIn("新しい質問1件へ1分で回答しました", message)
        self.assertIn("現在の未返信は0件です", message)
        self.assertIn("次は契約または追加メッセージを自動で確認します", message)
        for jargon in ("thread=", "hash", "route=", "verified"):
            self.assertNotIn(jargon, message)
        self.assertNotIn("must never appear", message)
        self.assertNotIn("a" * 64, message)
        envelopes = [json.loads(line) for line in agent_feed.read_text().splitlines()]
        self.assertEqual(len(envelopes), 1)
        self.assertEqual(envelopes[0]["data"]["report_type"], "reply")
        self.assertIn(
            "The buyer reply was completed",
            envelopes[0]["data"]["human_message_en"],
        )

    def test_reply_wake_message_is_natural_and_truthful_for_each_health_state(self):
        base = {
            "run_id": "wake-1",
            "status": "completed",
            "observed": 85,
            "actionable": 3,
            "oldest_actionable": "2026-05-30T00:00:00+00:00",
            "effect": 0,
            "official_readback": 0,
            "pending": 0,
            "blocked": 0,
            "dlq": 0,
            "historical_dlq": 0,
            "newly_dlq": 0,
            "failed": 0,
            "skipped": 0,
            "deferred": 0,
            "officially_unrepliable_count": 0,
            "stop_contact_count": 0,
            "classification_failed_count": 0,
            "semantic_judgement_failed_count": 0,
            "semantic_migration_pending_count": 0,
            "thread_changed_buyer_count": 0,
            "thread_readback_count": 0,
            "thread_revalidated_count": 0,
        }
        for state, emoji in (
            (base, "✅"),
            ({**base, "blocked": 3, "historical_dlq": 8}, "🟡"),
            ({**base, "newly_dlq": 1}, "🟡"),
            ({**base, "deferred": 1}, "🟡"),
            ({**base, "status": "failed", "failed": 1}, "🔴"),
        ):
            with self.subTest(state=state["status"]):
                key, message = self.report.reply_wake_message(state, self.route)
                self.assertTrue(message.startswith("[ココナラ][交渉ループ]"))
                self.assertIn(emoji, message)
                self.assertIn("85件", message)
                self.assertIn("0件", message)
                self.assertIn("以前から隔離している会話は", message)
                self.assertIn("今回新たに隔離した会話は", message)
                self.assertIn(
                    f"通常返信で次回へ持ち越した会話は{state['deferred']}件です。", message,
                )
                self.assertIn("約3分後", message)
                self.assertNotIn("現在の未返信は0件", message)
                self.assertNotIn("wake-1", message)
                self.assertNotIn("key=", message)
                self.assertNotIn("a" * 64, message)
                self.assertNotIn("private body", message)
                self.assertTrue(key.startswith("gig:telegram:reply-wake:"))

    def test_reply_wake_reports_terminal_classification_in_natural_japanese(self):
        state = {
            "run_id": "wake-terminal", "status": "completed", "observed": 17,
            "actionable": 0, "effect": 0, "official_readback": 0,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0, "deferred": 0,
            "estimate_required": 0, "estimate_effect": 0, "estimate_readback": 0,
            "estimate_pending": 0, "estimate_failed": 0, "officially_unrepliable_count": 10,
            "stop_contact_count": 2, "classification_failed_count": 1,
            "semantic_judgement_failed_count": 0,
            "semantic_migration_pending_count": 1,
            "thread_changed_buyer_count": 2,
            "thread_readback_count": 3,
            "thread_revalidated_count": 1,
        }

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn(
            "公式上メッセージを送れない会話は10件、相手が連絡終了を希望した会話は2件です。これらには送信していません。",
            message,
        )
        self.assertIn("現在の会話状態を判定できなかった会話は0件、旧判定記録を整理中の会話は1件です。", message)
        self.assertIn(
            "新着・変更されたbuyer-lastは2件、今回strict判定した会話は3件、旧記録を再確認した会話は1件です。",
            message,
        )
        self.assertNotIn("officially_unrepliable", message)
        self.assertNotIn("classification_failed", message)
        self.assertNotIn("今回新たに隔離した会話は0件、失敗は0件", message)
        self.assertIn("🟡", message)

    def test_operator_brake_is_reported_as_paused_not_failed_or_running(self):
        state = {"run_id": "wake-braked", "status": "operator_brake"}

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn("⏸️ 交渉ループはオペレーターの安全停止中です。", message)
        self.assertIn("今回は受信箱を確認しておらず", message)
        self.assertIn("交渉処理の失敗ではありません", message)
        self.assertNotIn("稼働しています", message)
        self.assertNotIn("実処理で失敗", message)
        self.assertNotIn("未確認の会話", message)

    def test_missing_terminal_classification_is_degraded_and_unconfirmed(self):
        state = {
            "run_id": "wake-terminal-missing", "status": "completed", "observed": 1,
            "actionable": 0, "effect": 0, "official_readback": 0,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0,
            "estimate_required": 0, "estimate_effect": 0, "estimate_readback": 0,
            "estimate_pending": 0, "estimate_failed": 0,
        }

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn("🟡", message)
        self.assertIn("公式上メッセージを送れない会話は未確認", message)
        self.assertIn("相手が連絡終了を希望した会話は未確認", message)
        self.assertIn("現在の会話状態を判定できなかった会話は未確認", message)
        self.assertIn("旧判定記録を整理中の会話は未確認", message)

    def test_missing_deferred_truth_is_degraded_and_visible(self):
        state = {
            "run_id": "wake-deferred-missing", "status": "completed", "observed": 1,
            "actionable": 0, "effect": 0, "official_readback": 0,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0,
            "officially_unrepliable_count": 0, "stop_contact_count": 0,
            "classification_failed_count": 0,
            "semantic_judgement_failed_count": 0,
            "semantic_migration_pending_count": 0,
        }

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn("🟡", message)
        self.assertIn("通常返信で次回へ持ち越した会話は未確認です。", message)

    def test_reply_wake_separates_normal_reply_and_estimate_truth(self):
        state = {
            "run_id": "wake-estimate", "status": "completed", "observed": 2,
            "actionable": 1, "effect": 1, "official_readback": 1,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0,
            "estimate_required": 1, "estimate_effect": 1,
            "estimate_readback": 1, "estimate_pending": 0, "estimate_failed": 0,
        }
        _, message = self.report.reply_wake_message(state, self.route)
        self.assertIn("通常返信", message)
        self.assertIn("見積りの追跡対象", message)
        self.assertIn("通常返信の新規送信は0件", message)
        self.assertIn("見積りの新規提出は1件", message)
        self.assertIn("公式提出確認は1件", message)
        self.assertNotIn("新しく送った返信は1件", message)

    def test_reply_wake_separates_estimate_retry_confirmation_and_normal_deferred(self):
        base = {
            "run_id": "wake-retry-truth", "status": "completed", "observed": 1,
            "actionable": 0, "effect": 0, "official_readback": 0,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0, "deferred": 0,
            "estimate_required": 0, "estimate_effect": 0,
            "estimate_readback": 0, "estimate_pending": 0, "estimate_failed": 0,
            "officially_unrepliable_count": 0, "stop_contact_count": 0,
            "classification_failed_count": 0, "semantic_judgement_failed_count": 0,
            "semantic_migration_pending_count": 0, "thread_changed_buyer_count": 0,
            "thread_readback_count": 0, "thread_revalidated_count": 0,
        }
        cases = (
            ({**base, "status": "failed", "failed": 1, "estimate_failed": 1},
             "送信前に失敗し次回再試行する見積りは1件"),
            ({**base, "status": "reconcile_pending", "pending": 1, "estimate_pending": 1},
             "送信後の公式確認待ちは1件です。確認待ちには再送しません"),
            ({**base, "deferred": 1}, "通常返信で次回へ持ち越した会話は1件"),
            (base, "送信前に失敗し次回再試行する見積りは0件"),
        )
        for state, expected in cases:
            with self.subTest(expected=expected):
                _, message = self.report.reply_wake_message(state, self.route)
                self.assertIn(expected, message)

    def test_negotiate_wake_reports_delivered_estimates_as_tracked_not_required(self):
        state = {
            "run_id": "wake-estimate-delivered", "status": "completed",
            "observed": 95, "actionable": 3, "effect": 0,
            "official_readback": 3, "pending": 0, "blocked": 0,
            "historical_dlq": 0, "newly_dlq": 0, "failed": 0,
            "skipped": 0, "deferred": 0, "estimate_required": 3,
            "estimate_effect": 0, "estimate_readback": 3,
            "estimate_pending": 0, "estimate_failed": 0,
            "officially_unrepliable_count": 10, "stop_contact_count": 1,
            "classification_failed_count": 30,
            "semantic_judgement_failed_count": 0,
            "semantic_migration_pending_count": 30,
        }

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn("🟡 交渉ループは稼働しています", message)
        self.assertIn("通常返信の処理対象は0件、見積りの追跡対象は3件", message)
        self.assertIn("見積りの新規提出は0件、公式提出確認は3件", message)
        self.assertIn("実処理失敗は0件", message)
        self.assertIn("旧判定記録を整理中の会話は30件", message)
        self.assertNotIn("見積り提案が必要な会話は3件", message)
        self.assertNotIn("🔴", message)

    def test_missing_reply_wake_truth_is_degraded_and_unconfirmed(self):
        state = {
            "run_id": "wake-missing", "status": "completed", "observed": 1,
            "actionable": 1, "effect": None, "official_readback": 0,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0,
        }

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn("🟡", message)
        self.assertIn("未確認", message)

    def test_malformed_official_readback_is_degraded_and_unconfirmed(self):
        state = {
            "run_id": "wake-malformed", "status": "completed", "observed": 1,
            "actionable": 1, "effect": 0, "official_readback": None,
            "pending": 0, "blocked": 0, "historical_dlq": 0,
            "newly_dlq": 0, "failed": 0, "skipped": 0,
        }

        _, message = self.report.reply_wake_message(state, self.route)

        self.assertIn("🟡", message)
        self.assertIn("未確認", message)

    def test_reply_wake_publisher_dedupes_one_run_and_sends_each_new_run(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        state = {
            "run_id": "wake-1", "status": "completed", "observed": 0,
            "actionable": 0, "effect": 0, "official_readback": 0,
            "pending": 0, "blocked": 0, "dlq": 0,
            "historical_dlq": 0, "newly_dlq": 0, "failed": 0, "skipped": 0,
        }
        calls = []
        transport = lambda message: calls.append(message) or f"tg-{len(calls)}"

        first = self.report.publish_reply_wake(
            state=state, outbox=outbox, route=self.route,
            transport=transport, now_epoch=100,
        )
        second = self.report.publish_reply_wake(
            state=state, outbox=outbox, route=self.route,
            transport=transport, now_epoch=101,
        )
        third = self.report.publish_reply_wake(
            state={**state, "run_id": "wake-2"}, outbox=outbox,
            route=self.route, transport=transport, now_epoch=102,
        )

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(third["sent"], 1)
        self.assertEqual(len(calls), 2)

    def test_reply_wake_dispatches_only_its_row_and_leaves_old_pending(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        outbox.enqueue(
            event_key="old-pending", kind="fixture", message="old pending", created_at=1,
        )
        state = {
            "run_id": "wake-isolated", "status": "completed", "observed": 0,
            "actionable": 0, "effect": 0, "official_readback": 0,
            "pending": 0, "blocked": 0, "dlq": 0,
            "historical_dlq": 0, "newly_dlq": 0, "failed": 0, "skipped": 0,
        }
        calls = []

        result = self.report.publish_reply_wake(
            state=state, outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-wake",
            now_epoch=100,
        )

        self.assertEqual(result["sent"], 1)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith("[ココナラ][交渉ループ]"))
        with sqlite3.connect(self.telegram_db) as connection:
            rows = connection.execute(
                "SELECT event_key,state FROM telegram_reports ORDER BY report_id"
            ).fetchall()
        self.assertEqual(rows[0], ("old-pending", "pending"))
        self.assertEqual(rows[1][0], "gig:telegram:reply-wake:v1:wake-isolated")
        self.assertEqual(rows[1][1], "sent")

    def test_hourly_pulse_reports_real_action_and_telegram_states(self):
        self.create_connector_rows()
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        outbox.enqueue(event_key="unknown-1", kind="fixture", message="fixture", created_at=100)
        action = outbox.claim(owner="fixture", now=101, lease_seconds=10)
        outbox.mark_send_started(
            action["report_id"], owner="fixture",
            fencing_token=action["fencing_token"], now=102,
        )
        outbox.recover_expired(now=112)

        message = self.report.hourly_message(
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime.fromtimestamp(300, timezone.utc),
        )

        self.assertIn("⏱ gig毎時SLA", message)
        self.assertIn("verified=1 / pending=1 / reconcile=1", message)
        self.assertIn("Telegram未確定=1", message)
        self.assertIn("route=Terra medium", message)

    def test_application_recovery_names_exact_verified_jobs(self):
        key, message = self.report.application_recovery_message({
            "source": "canonical_orphan_reconciliation",
            "recovery_id": "recovery-20260729-1",
            "applications": [
                {
                    "request_id": "91000021",
                    "bucket": "single",
                    "title": "AIツール活用のWebサイト制作",
                    "url": "https://coconala.com/requests/91000021",
                },
                {
                    "request_id": "01KYKDECET9WAY0CKRBCKH81RC",
                    "bucket": "retainer",
                    "title": "Meta APIを活用したSaaS開発",
                    "url": (
                        "https://coconala.com/job_matching/outsources/"
                        "01KYKDECET9WAY0CKRBCKH81RC"
                    ),
                },
            ],
        }, route=self.route)

        self.assertEqual(
            key,
            "gig:telegram:application-recovery:v1:recovery-20260729-1",
        )
        self.assertIn("[単発] AIツール活用のWebサイト制作", message)
        self.assertIn("[継続] Meta APIを活用したSaaS開発", message)
        self.assertIn("応募履歴✅ 台帳✅ 過去報告補正✅", message)

    def test_daily_message_keeps_honest_revenue_and_adds_sla(self):
        self.create_connector_rows()
        (self.gig_dir / "applied.jsonl").write_text(
            '\n'.join((
                json.dumps({"status": "applied"}),
                json.dumps({"status": "replied"}),
            )) + '\n', encoding="utf-8",
        )
        # A publish row must name the listing it published: the count is now
        # deduplicated by service_id, and an unidentifiable publish is quarantined
        # rather than added to the total (see tests/test_listing_accounting.py).
        (self.gig_dir / "shuppin.jsonl").write_text(
            json.dumps({"action": "shuppin_published", "service_id": "94000016"}) + '\n',
            encoding="utf-8",
        )
        (self.gig_dir / "earnings.jsonl").write_text("", encoding="utf-8")
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        message = self.report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime(2026, 7, 22, 0, 7, tzinfo=timezone.utc),
        )

        self.assertIn("🧰 gig日報 (Coconala/mtdc) 2026-07-22", message)
        # Totals carry the JST-natural-day delta; these fixture rows are undated and so
        # fall outside it, which is why every delta reads ±0 against a non-zero total.
        self.assertIn("応募累計:1(±0) / 返信・納品:1(±0) / 出品公開:1(±0)", message)
        self.assertIn("売上(検収済):0件 ¥0", message)
        self.assertIn("即応: verified=1 / pending=1 / reconcile=1", message)
        self.assertIn("日次funnel: 応募 0 → 返信 0 → 契約 0 → 納品 0 → 入金 0", message)
        self.assertIn(
            "日次運用: model cost $0.00 / incident 0 / self-heal recovery evidence 0",
            message,
        )
        self.assertIn("実¥まだ0", message)

    def test_daily_message_counts_paid_progress_from_its_own_ledger(self):
        # X22: buyer-visible progress replies on already-won paid contracts used to be
        # appended to applied.jsonl, which broke the paid-work gate's byte-freeze on the
        # lower-priority ledgers and made application_ledger/category_bandit count a paid
        # contract update as a 募集 application reply. The write moved to its own ledger;
        # 返信・納品 must still count it, because an action that happened and stops being
        # counted is indistinguishable from an action that never happened.
        self.create_connector_rows()
        (self.gig_dir / "applied.jsonl").write_text(
            json.dumps({"status": "replied"}) + '\n', encoding="utf-8",
        )
        (self.gig_dir / "paid-progress.jsonl").write_text(
            json.dumps({"status": "replied", "action": "paid_progress",
                        "requestId": "4201", "buyer_visible": True}) + '\n',
            encoding="utf-8",
        )
        (self.gig_dir / "earnings.jsonl").write_text("", encoding="utf-8")
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        message = self.report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime(2026, 7, 22, 0, 7, tzinfo=timezone.utc),
        )

        self.assertIn("返信・納品:2(±0)", message)

    def test_daily_message_joins_four_lane_attribution_by_pass_and_task_label(self):
        self.create_connector_rows()
        lane_db = self.gig_dir / "lane-actions.sqlite3"
        with sqlite3.connect(lane_db) as connection:
            connection.execute("""CREATE TABLE lane_actions(
                action_id INTEGER PRIMARY KEY,
                lane TEXT,event_key TEXT,action_kind TEXT,state TEXT,
                side_effect_count INTEGER,blind_retry_count INTEGER,
                observed_at INTEGER
            )""")
            observed_at = int(datetime(2026, 7, 23, 6, 0, tzinfo=timezone.utc).timestamp())
            connection.executemany(
                "INSERT INTO lane_actions VALUES(?,?,?,?,?,?,?,?)",
                [
                    (1, "listing", "listing:pass-daily-pass", "verified_noop",
                     "verified_noop", 0, 0, observed_at),
                    (2, "application", "application:pass-daily-pass", "verified_noop",
                     "verified_noop", 0, 0, observed_at),
                    (3, "reply", "reply:pass-daily-pass", "verified_noop",
                     "verified_noop", 0, 0, observed_at),
                    (4, "delivery", "delivery:pass-daily-pass", "revision",
                     "verified", 1, 0, observed_at),
                    (5, "listing", "listing:debug-old-fixture", "verified_noop",
                     "verified_noop", 0, 0, observed_at),
                ],
            )
        evidence_root = self.gig_dir / "evidence"
        pass_dir = evidence_root / "gig-pass-daily-pass"
        pass_dir.mkdir(parents=True)
        (pass_dir / "poll-control.json").write_text(
            json.dumps({
                "version": 1,
                "pass_id": "daily-pass",
                "outcome": "material_event_handled",
                "model_calls": 1,
                "model_call_labels": ["PAID_WORK"],
            }) + "\n",
            encoding="utf-8",
        )
        usage_ledger = self.gig_dir / "agent-usage.jsonl"
        usage_ledger.write_text(
            "\n".join((
                json.dumps({
                    "loop": "gig",
                    "task_label": "gig-PAID_WORK",
                    "budget": {"scope_id": "daily-pass"},
                    "provider_cost_usd": 0.25,
                }),
                json.dumps({
                    "loop": "gig",
                    "task_label": "gig-PAID_WORK",
                    "budget": {"scope_id": "different-pass"},
                    "provider_cost_usd": 99,
                }),
            )) + "\n",
            encoding="utf-8",
        )
        (self.gig_dir / "applied.jsonl").write_text("", encoding="utf-8")
        (self.gig_dir / "shuppin.jsonl").write_text("", encoding="utf-8")
        (self.gig_dir / "earnings.jsonl").write_text(
            "\n".join((
                json.dumps({
                    "pass_id": "daily-pass",
                    "task_label": "gig-PAID_WORK",
                    "status": "paid",
                    "jpy": 40000,
                    "evidence": "ground-truth://settlement/1",
                }),
                json.dumps({
                    "pass_id": "different-pass",
                    "task_label": "gig-PAID_WORK",
                    "status": "paid",
                    "jpy": 90000,
                    "evidence": "ground-truth://settlement/2",
                }),
            )) + "\n",
            encoding="utf-8",
        )
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        message = self.report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime(2026, 7, 24, 0, 7, tzinfo=timezone.utc),
            lane_database=lane_db,
            evidence_root=evidence_root,
            usage_ledger=usage_ledger,
        )

        self.assertIn("状態: HEALTHY | lane evidence=4/4", message)
        shuppin_line = next(
            line for line in message.splitlines() if "Shuppin:" in line
        )
        self.assertIn("実行=0", shuppin_line)
        self.assertIn("checked=1", shuppin_line)
        self.assertIn("model_calls=0", shuppin_line)
        self.assertIn("cost=$0.00", shuppin_line)
        self.assertIn("revenue=¥0", shuppin_line)
        # no side effects recorded, so the lane must be flagged as silent
        self.assertTrue(shuppin_line.startswith("🔴"), shuppin_line)
        oubo_line = next(
            line for line in message.splitlines() if "Oubo:" in line
        )
        self.assertIn("実行=0", oubo_line)
        self.assertIn("checked=1", oubo_line)
        self.assertIn("model_calls=0", oubo_line)
        self.assertIn("cost=$0.00", oubo_line)
        self.assertIn("revenue=¥0", oubo_line)
        # no side effects recorded, so the lane must be flagged as silent
        self.assertTrue(oubo_line.startswith("🔴"), oubo_line)
        reply_line = next(
            line for line in message.splitlines() if "Reply:" in line
        )
        self.assertIn("実行=0", reply_line)
        self.assertIn("checked=1", reply_line)
        self.assertIn("model_calls=0", reply_line)
        self.assertIn("cost=$0.00", reply_line)
        self.assertIn("revenue=¥0", reply_line)
        # no side effects recorded, so the lane must be flagged as silent
        self.assertTrue(reply_line.startswith("🔴"), reply_line)
        nouhin_line = next(
            line for line in message.splitlines() if "Nouhin:" in line
        )
        self.assertIn("実行=1", nouhin_line)
        self.assertIn("checked=1", nouhin_line)
        self.assertIn("model_calls=1", nouhin_line)
        self.assertIn("cost=$0.25", nouhin_line)
        self.assertIn("revenue=¥40000", nouhin_line)
        self.assertNotIn("$99.00", message)

    def test_daily_message_fails_when_one_lane_has_missing_evidence(self):
        self.create_connector_rows()
        lane_db = self.gig_dir / "lane-actions.sqlite3"
        with sqlite3.connect(lane_db) as connection:
            connection.execute("""CREATE TABLE lane_actions(
                action_id INTEGER PRIMARY KEY,
                lane TEXT,event_key TEXT,action_kind TEXT,state TEXT,
                side_effect_count INTEGER,blind_retry_count INTEGER,
                observed_at INTEGER
            )""")
            observed_at = int(datetime(2026, 7, 23, 6, 0, tzinfo=timezone.utc).timestamp())
            for action_id, lane in enumerate(("listing", "application", "reply"), start=1):
                connection.execute(
                    "INSERT INTO lane_actions VALUES(?,?,?,?,?,?,?,?)",
                    (action_id, lane, f"{lane}:pass-incomplete-pass", "verified_noop",
                     "verified_noop", 0, 0, observed_at),
                )
        evidence_root = self.gig_dir / "evidence"
        pass_dir = evidence_root / "gig-pass-incomplete-pass"
        pass_dir.mkdir(parents=True)
        (pass_dir / "poll-control.json").write_text(
            json.dumps({
                "version": 1,
                "pass_id": "incomplete-pass",
                "outcome": "no_change",
                "model_calls": 0,
                "model_call_labels": [],
            }) + "\n",
            encoding="utf-8",
        )
        usage_ledger = self.gig_dir / "agent-usage.jsonl"
        usage_ledger.write_text("", encoding="utf-8")
        for name in ("applied.jsonl", "shuppin.jsonl", "earnings.jsonl"):
            (self.gig_dir / name).write_text("", encoding="utf-8")
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        message = self.report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime(2026, 7, 24, 0, 7, tzinfo=timezone.utc),
            lane_database=lane_db,
            evidence_root=evidence_root,
            usage_ledger=usage_ledger,
        )

        self.assertIn("状態: FAIL | missing evidence=delivery", message)

    def test_daily_message_reports_silence_for_lanes_that_never_ran(self):
        """Replay of the outage the old report hid.

        For 4.5 days poll mode invoked no lane at all, yet every morning's message read
        "checked=47 eligible=0 actions=0 verified=47" -- a number large enough to look
        like health. X1 made the ledger say not_run; this asserts the report stops
        laundering that into a verification and names the silence instead.
        """
        self.create_connector_rows()
        lane_db = self.gig_dir / "lane-actions.sqlite3"
        observed_at = int(datetime(2026, 7, 23, 6, 0, tzinfo=timezone.utc).timestamp())
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
                    (idx, lane, f"{lane}:pass-silent-pass", "not_run",
                     "verified_noop", 0, 0, observed_at)
                    for idx, lane in enumerate(
                        ("listing", "application", "reply", "delivery"), start=1
                    )
                ],
            )
        evidence_root = self.gig_dir / "evidence"
        pass_dir = evidence_root / "gig-pass-silent-pass"
        pass_dir.mkdir(parents=True)
        (pass_dir / "poll-control.json").write_text(
            json.dumps({
                "version": 1,
                "pass_id": "silent-pass",
                "outcome": "no_change",
                "model_calls": 0,
                "model_call_labels": [],
            }) + "\n",
            encoding="utf-8",
        )
        usage_ledger = self.gig_dir / "agent-usage.jsonl"
        usage_ledger.write_text("", encoding="utf-8")
        for name in ("applied.jsonl", "shuppin.jsonl", "earnings.jsonl"):
            (self.gig_dir / name).write_text("", encoding="utf-8")
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        message = self.report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime(2026, 7, 24, 0, 7, tzinfo=timezone.utc),
            lane_database=lane_db,
            evidence_root=evidence_root,
            usage_ledger=usage_ledger,
        )

        self.assertIn("⚠️ 停止中のlane: Shuppin, Oubo, Reply, Nouhin", message)
        for report_name in ("Shuppin", "Oubo", "Reply", "Nouhin"):
            line = next(l for l in message.splitlines() if f"{report_name}:" in l)
            self.assertTrue(line.startswith("🔴"), line)
            self.assertIn("未実行pass=1", line)
            self.assertIn("実行=0", line)
            self.assertIn("最終実行=記録なし", line)
            # The whole point: a pass that never invoked the lane is not a verification.
            self.assertIn("verified=0", line)

    def test_daily_message_marks_a_lane_healthy_once_it_acts(self):
        """A lane that produced a side effect inside its budget must not be flagged."""
        self.create_connector_rows()
        lane_db = self.gig_dir / "lane-actions.sqlite3"
        # Two hours before the report, well inside Oubo's 8h silence budget.
        acted_at = int(datetime(2026, 7, 23, 22, 0, tzinfo=timezone.utc).timestamp())
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
                    (1, "application", "application:pass-acting-pass", "revision",
                     "verified", 2, 0, acted_at),
                    (2, "listing", "listing:pass-acting-pass", "not_run",
                     "verified_noop", 0, 0, acted_at),
                    (3, "reply", "reply:pass-acting-pass", "not_run",
                     "verified_noop", 0, 0, acted_at),
                    (4, "delivery", "delivery:pass-acting-pass", "not_run",
                     "verified_noop", 0, 0, acted_at),
                ],
            )
        evidence_root = self.gig_dir / "evidence"
        pass_dir = evidence_root / "gig-pass-acting-pass"
        pass_dir.mkdir(parents=True)
        (pass_dir / "poll-control.json").write_text(
            json.dumps({
                "version": 1,
                "pass_id": "acting-pass",
                "outcome": "material_event_handled",
                "model_calls": 1,
                "model_call_labels": ["B2"],
            }) + "\n",
            encoding="utf-8",
        )
        usage_ledger = self.gig_dir / "agent-usage.jsonl"
        usage_ledger.write_text("", encoding="utf-8")
        for name in ("applied.jsonl", "shuppin.jsonl", "earnings.jsonl"):
            (self.gig_dir / name).write_text("", encoding="utf-8")
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        message = self.report.daily_message(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            route=self.route,
            now=datetime(2026, 7, 24, 0, 7, tzinfo=timezone.utc),
            lane_database=lane_db,
            evidence_root=evidence_root,
            usage_ledger=usage_ledger,
        )

        oubo = next(l for l in message.splitlines() if "Oubo:" in l)
        self.assertTrue(oubo.startswith("✅"), oubo)
        self.assertIn("実行=2", oubo)
        self.assertIn("最終実行=2.1h", oubo)
        self.assertNotIn("Oubo", message.split("停止中のlane:")[1].split("\n")[0])

    def test_pass_message_reports_latest_finished_pass(self):
        usage_ledger = self.root / "agent-usage.jsonl"
        (self.gig_dir / "pass-report.jsonl").write_text(json.dumps({
            "ts": 1000, "pass_id": "111-1", "status": "success",
            "steps_executed": ["INQUIRY_REPLY"], "steps_skipped_cooldown": [],
            "steps_skipped_policy": ["SHUPPIN"],
        }) + "\n", encoding="utf-8")
        (self.gig_dir / "pass-failures.jsonl").write_text(json.dumps({
            "ts": 2000, "pass_id": "222-2", "status": "failed",
            "failed_step": "PAID_WORK", "reason": "paid_work_validation_failed",
        }) + "\n", encoding="utf-8")
        usage_ledger.write_text(json.dumps({
            "loop": "gig", "task_label": "gig-PAID_WORK",
            "provider_cost_usd": 0.0034918,
            "budget": {"scope_id": "222-2"},
        }) + "\n", encoding="utf-8")

        pair = self.report.pass_message(
            gig_dir=self.gig_dir, usage_ledger=usage_ledger, route=self.route,
        )

        self.assertIsNotNone(pair)
        key, message = pair
        self.assertEqual(key, "gig:telegram:pass:v3:222-2:failed")
        self.assertIn("ギグワークで修復が必要な問題を見つけました", message)
        self.assertIn("検出内容: paid_work_validation_failed", message)
        self.assertIn("AI処理費: $0.0035", message)
        self.assertNotIn("gig pass", message)
        self.assertNotIn("step=", message)
        self.assertNotIn("model_calls=", message)

    def test_pass_message_success_and_empty_ledgers(self):
        usage_ledger = self.root / "agent-usage.jsonl"
        self.assertIsNone(self.report.pass_message(
            gig_dir=self.gig_dir, usage_ledger=usage_ledger, route=self.route,
        ))
        (self.gig_dir / "pass-report.jsonl").write_text(json.dumps({
            "ts": 3000, "pass_id": "333-3", "status": "success",
            "steps_executed": ["INQUIRY_REPLY", "PAID_WORK"],
            "steps_skipped_cooldown": ["OUBO"], "steps_skipped_policy": [],
        }) + "\n", encoding="utf-8")

        pair = self.report.pass_message(
            gig_dir=self.gig_dir, usage_ledger=usage_ledger, route=self.route,
        )

        key, message = pair
        self.assertEqual(key, "gig:telegram:pass:v3:333-3:success")
        self.assertIn("ギグワークの作業が完了しました", message)
        self.assertIn("問い合わせへの返信、納品物の作成を確認・実行しました", message)
        self.assertIn("次の予定", message)
        self.assertNotIn("steps=", message)
        self.assertNotIn("skipped=", message)

    def test_pass_message_names_each_verified_application_and_three_point_evidence(self):
        usage_ledger = self.root / "agent-usage.jsonl"
        pass_id = "444-4"
        (self.gig_dir / "pass-report.jsonl").write_text(json.dumps({
            "ts": 4000, "pass_id": pass_id, "status": "success",
            "steps_executed": ["B2"], "steps_skipped_cooldown": [],
            "steps_skipped_policy": [],
        }) + "\n", encoding="utf-8")
        (self.gig_dir / "applied.jsonl").write_text(json.dumps({
            "ts": 4000,
            "pass_id": pass_id,
            "requestId": "91000030",
            "bucket": "single",
            "status": "applied",
            "category": "動画編集・映像制作",
            "title": "Remotion動画生成",
            "url": "https://coconala.com/requests/91000030",
            "submit_verified": True,
            "applied_page_verified": True,
            "applied_page_evidence": "/evidence/code-applied-readback.json",
            "recorded_by": "application_report",
        }, ensure_ascii=False) + "\n", encoding="utf-8")

        pair = self.report.pass_message(
            gig_dir=self.gig_dir, usage_ledger=usage_ledger, route=self.route,
        )

        self.assertIsNotNone(pair)
        _, message = pair
        self.assertIn("応募: 1件", message)
        self.assertIn("[単発]", message)
        self.assertIn("Remotion動画生成", message)
        self.assertIn("https://coconala.com/requests/91000030", message)
        self.assertIn("送信・応募履歴・台帳の3か所で確認済み", message)
        self.assertNotIn("verified=", message)
        self.assertNotIn("request=", message)
        self.assertNotIn("route=", message)

    def test_pass_human_message_and_agent_feed_share_one_envelope(self):
        usage_ledger = self.root / "agent-usage.jsonl"
        pass_id = "555-5"
        (self.gig_dir / "pass-report.jsonl").write_text(json.dumps({
            "ts": 5000, "pass_id": pass_id, "status": "success",
            "steps_executed": ["B2"], "steps_skipped_cooldown": [],
            "steps_skipped_policy": [],
        }) + "\n", encoding="utf-8")
        (self.gig_dir / "applied.jsonl").write_text(json.dumps({
            "ts": 5000, "pass_id": pass_id, "requestId": "91000032",
            "bucket": "single", "status": "applied", "title": "資料作成",
            "url": "https://coconala.com/requests/91000032",
            "submit_verified": True, "applied_page_verified": True,
        }, ensure_ascii=False) + "\n", encoding="utf-8")

        envelope = self.report.pass_envelope(
            gig_dir=self.gig_dir, usage_ledger=usage_ledger,
        )
        key, message = self.report.pass_message(
            gig_dir=self.gig_dir, usage_ledger=usage_ledger, route=self.route,
        )

        self.assertEqual(key, "gig:telegram:pass:v3:555-5:success")
        self.assertEqual(
            message,
            self.report.report_envelope.render_human_ja(envelope),
        )
        self.assertEqual(
            json.loads(self.report.report_envelope.render_agent_json(envelope)),
            envelope,
        )

    def test_lane_barren_alert_sends_once_and_dedupes_within_the_same_streak(self):
        # X7: three consecutive attempts with a frozen productivity clock alert
        # exactly once. The outbox event key embeds the streak anchor, so calling
        # the hook on every pass (its only call site) cannot re-send mid-streak.
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        alerts = [{
            "lane": "apply", "label": "応募", "streak": 3,
            "streak_started_at": 1753600000.25,
        }]
        calls = []
        first = self.report.publish_barren_alerts(
            alerts=alerts, outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-barren-1",
            now_epoch=1753600300,
        )
        second = self.report.publish_barren_alerts(
            alerts=alerts, outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-barren-dup",
            now_epoch=1753600400,
        )
        # The streak keeps growing while nobody fixes the lane: same anchor, new
        # count. Still the same streak, so still no second message.
        grown = self.report.publish_barren_alerts(
            alerts=[dict(alerts[0], streak=5)], outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-barren-grown",
            now_epoch=1753600500,
        )

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(grown["sent"], 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("apply", calls[0])
        with sqlite3.connect(self.telegram_db) as connection:
            rows = connection.execute(
                "SELECT event_key,state FROM telegram_reports WHERE event_key LIKE ?",
                ("gig:telegram:lane-barren:v1:apply:%",),
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "gig:telegram:lane-barren:v1:apply:1753600000:3")
        self.assertEqual(rows[0][1], "sent")

    def test_lane_barren_escalates_at_milestones_instead_of_going_silent_forever(self):
        # 2026-08-05: the apply lane reached a barren streak of 104 -- three days
        # without a single recorded application -- and Dais was told exactly once,
        # on the first pass of the streak. Anchoring the key to the streak's start
        # stops mid-streak spam, but it also means a silence that keeps getting
        # worse never speaks again. The escalation ladder keeps both properties:
        # quiet while nothing changes, one more message each time the failure
        # multiplies.
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        calls = []

        def send(streak):
            return self.report.publish_barren_alerts(
                alerts=[{
                    "lane": "apply", "label": "応募", "streak": streak,
                    "streak_started_at": 1753600000.0,
                }],
                outbox=outbox, route=self.route,
                transport=lambda message: calls.append(message) or f"tg-{len(calls)}",
                now_epoch=1753600000 + streak,
            )

        self.assertEqual(send(3)["sent"], 1)    # silence begins
        self.assertEqual(send(7)["sent"], 0)    # same order of magnitude, stay quiet
        self.assertEqual(send(11)["sent"], 0)
        self.assertEqual(send(12)["sent"], 1)   # four times worse: speak again
        self.assertEqual(send(30)["sent"], 0)
        self.assertEqual(send(48)["sent"], 1)
        self.assertEqual(send(104)["sent"], 0)  # still inside the 48 rung
        self.assertEqual(len(calls), 3)
        # Every message has to name the lane and how long it has been silent, or
        # the reader cannot tell an escalation from the first alert.
        self.assertIn("12", calls[1])
        self.assertIn("48", calls[2])

    def test_lane_barren_new_streak_alerts_again_with_a_new_key(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        calls = []
        for anchor in (1753600000, 1753700000):
            result = self.report.publish_barren_alerts(
                alerts=[{
                    "lane": "reply", "label": "返信", "streak": 3,
                    "streak_started_at": float(anchor),
                }],
                outbox=outbox, route=self.route,
                transport=lambda message: calls.append(message) or f"tg-{len(calls)}",
                now_epoch=anchor + 300,
            )
            self.assertEqual(result["sent"], 1)
        self.assertEqual(len(calls), 2)

    def test_a_repair_the_healer_gave_up_on_reaches_dais(self):
        # 2026-08-05: incident 42, application:barren_streak, reached the healer's
        # bounded attempt limit on 2026-08-03 01:45 and moved to 'blocked'. Blocked
        # is terminal -- the unique index keeps any newer incident with the same
        # fingerprint from opening -- so the loop stopped both repairing and
        # detecting, for three days, in silence. The healer giving up is exactly
        # the moment a human has to hear about it.
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        calls = []
        blocked = [{
            "incident_id": 42,
            "fingerprint": "application:barren_streak",
            "repair_class": "application_expand",
            "attempt_count": 3,
            "blocked_at": 1785000000,
        }]
        first = self.report.publish_blocked_repair_alerts(
            blocked=blocked, outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-blocked-1",
            now_epoch=1785000100,
        )
        # Still blocked on the next audit: the human already knows.
        second = self.report.publish_blocked_repair_alerts(
            blocked=blocked, outbox=outbox, route=self.route,
            transport=lambda message: calls.append(message) or "tg-blocked-dup",
            now_epoch=1785003700,
        )
        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertIn("application:barren_streak", calls[0])
        self.assertIn("application_expand", calls[0])

    def test_no_blocked_repairs_is_a_quiet_noop(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        result = self.report.publish_blocked_repair_alerts(
            blocked=[], outbox=outbox, route=self.route,
            transport=lambda message: self.fail("nothing to say"),
            now_epoch=1785000100,
        )
        self.assertEqual(result, {"sent": 0, "delivery_unknown": 0})

    def test_hermes_audit_pending_is_quiet_and_terminal_report_is_exactly_once(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        pending = {
            "audit_id": "1786365299-1786451699",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "active",
            "verdict": "PENDING",
        }
        self.assertEqual(
            self.report.publish_hermes_audit(
                state=pending,
                outbox=outbox,
                transport=lambda message: self.fail("PENDING must be quiet"),
                now_epoch=1786365300,
            ),
            {"sent": 0, "delivery_unknown": 0},
        )

        terminal = {
            **pending,
            "phase": "terminal",
            "verdict": "GREEN",
            "raw_verdict": "GREEN",
            "result": {
                "version": 1,
                "since": 1786365299,
                "until": 1786451699,
                "window_complete": True,
                "verdict": "GREEN",
                "lanes": {
                    lane: {"expected_due": 2, "enqueued": 2, "done": 2, "executed": 2, "deferred": 0}
                    for lane in ("paid", "reply", "apply", "storefront")
                },
                "invariants": {"no_missing_due": True},
            },
        }
        calls = []
        first = self.report.publish_hermes_audit(
            state=terminal,
            outbox=outbox,
            transport=lambda message: calls.append(message) or "tg-hermes-1",
            now_epoch=1786451700,
        )
        second = self.report.publish_hermes_audit(
            state=terminal,
            outbox=outbox,
            transport=lambda message: calls.append(message) or "tg-hermes-2",
            now_epoch=1786451800,
        )

        self.assertEqual(first, {"sent": 1, "delivery_unknown": 0})
        self.assertEqual(second, {"sent": 0, "delivery_unknown": 0})
        self.assertEqual(len(calls), 1)
        self.assertIn("1786365299-1786451699", calls[0])
        self.assertIn("GREEN", calls[0])
        for lane in ("paid", "reply", "apply", "storefront"):
            self.assertIn(lane, calls[0])
        self.assertTrue(
            outbox.has_event("gig:telegram:hermes-audit:v1:1786365299-1786451699")
        )

    def test_hermes_audit_report_rejects_payload_flip_and_red_message_is_safe(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        secret = "client secret/path/credentials"
        state = {
            "audit_id": "1786365299-1786451699",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "terminal",
            "verdict": "RED",
            "raw_verdict": "RED",
            "result": {
                "version": 1,
                "since": 1786365299,
                "until": 1786451699,
                "window_complete": True,
                "verdict": "RED",
                "lanes": {
                    lane: {"expected_due": 2, "enqueued": 1, "done": 0, "executed": 0, "deferred": 1}
                    for lane in ("paid", "reply", "apply", "storefront")
                },
                "invariants": {"no_missing_due": False},
                "secret": secret, "path": secret, "client_text": secret,
            },
        }
        calls = []
        self.report.publish_hermes_audit(
            state=state,
            outbox=outbox,
            transport=lambda message: calls.append(message) or "tg-red-1",
            now_epoch=1786451700,
        )
        self.assertIn("no_missing_due", calls[0])
        self.assertNotIn(secret, calls[0])
        changed = dict(state, result={**state["result"], "invariants": {"no_missing_due": True}})
        with self.assertRaises(self.outbox_module.TelegramOutboxError):
            self.report.publish_hermes_audit(
                state=changed,
                outbox=outbox,
                transport=lambda message: self.fail("payload flip must fail before send"),
                now_epoch=1786451800,
            )

    def test_hermes_terminal_invalid_result_fails_without_enqueue(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        invalid = {
            "audit_id": "1786365299-1786451699",
            "since": 1786365299,
            "until": 1786451699,
            "phase": "terminal",
            "verdict": "RED",
            "result": {"version": 1, "window_complete": False, "verdict": "RED"},
        }
        with self.assertRaises(ValueError):
            self.report.publish_hermes_audit(
                state=invalid, outbox=outbox,
                transport=lambda message: self.fail("invalid result must not send"),
                now_epoch=1786451700,
            )
        self.assertFalse(outbox.has_event("gig:telegram:hermes-audit:v1:1786365299-1786451699"))

    def test_hermes_distinct_audits_with_identical_body_are_not_body_suppressed(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        original = self.report.hermes_audit_message
        self.report.hermes_audit_message = lambda state: (
            f"gig:telegram:hermes-audit:v1:{state['audit_id']}", "same terminal body"
        )
        calls = []
        try:
            first = self.report.publish_hermes_audit(
                state={"audit_id": "10-20"}, outbox=outbox,
                transport=lambda message: calls.append(message) or "tg-1",
                now_epoch=100,
            )
            second = self.report.publish_hermes_audit(
                state={"audit_id": "30-40"}, outbox=outbox,
                transport=lambda message: calls.append(message) or "tg-2",
                now_epoch=200,
            )
        finally:
            self.report.hermes_audit_message = original
        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 1)
        self.assertEqual(calls, ["same terminal body", "same terminal body"])
        with sqlite3.connect(self.telegram_db) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM telegram_reports WHERE kind='hermes_audit'"
            ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_lane_barren_no_alerts_is_a_quiet_noop(self):
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)
        result = self.report.publish_barren_alerts(
            alerts=[], outbox=outbox, route=self.route,
            transport=lambda message: (_ for _ in ()).throw(AssertionError("no send")),
            now_epoch=1753600300,
        )
        self.assertEqual(result, {"sent": 0, "delivery_unknown": 0})

    def test_weekly_message_reports_previous_completed_jst_week(self):
        start = int(datetime(2026, 7, 19, 15, 0, tzinfo=timezone.utc).timestamp())
        inside = start + 3600
        outside = start - 1
        (self.gig_dir / "applied.jsonl").write_text("\n".join((
            json.dumps({"requestId": "501", "status": "applied", "ts": inside,
                        "private_body": "never print me"}),
            json.dumps({"requestId": "501", "status": "replied", "ts": inside + 60}),
            json.dumps({"requestId": "502", "status": "applied", "ts": inside + 120}),
            json.dumps({"requestId": "old", "status": "applied", "ts": outside}),
            json.dumps({"requestId": "501", "status": "delivered", "ts": inside + 180}),
        )) + "\n", encoding="utf-8")
        (self.gig_dir / "earnings.jsonl").write_text(json.dumps({
            "requestId": "501", "status": "paid", "jpy": 12000,
            "evidence": "receipt", "ts": inside + 240,
        }) + "\n", encoding="utf-8")
        (self.gig_dir / "shuppin.jsonl").write_text(json.dumps({
            "action": "shuppin_published", "service_id": "9001", "ts": inside + 300,
        }) + "\n", encoding="utf-8")
        (self.gig_dir / "pass-failures.jsonl").write_text(json.dumps({
            "ts": inside + 360, "reason": "browser_cdp_unavailable",
        }) + "\n", encoding="utf-8")
        (self.gig_dir / "audit.jsonl").write_text("\n".join((
            json.dumps({"ts": inside + 420, "changed": [
                {"lane": "apply", "from": "down", "to": "ok"},
            ]}),
            json.dumps({"ts": inside + 480, "verdict": "FIRING (healthy heartbeat)"}),
        )) + "\n", encoding="utf-8")
        (self.gig_dir / "strategy.json").write_text(json.dumps({"experiments": [
            {"id": "kept-one", "ts": inside + 500, "status": "kept"},
            {"id": "reverted-one", "ts": inside + 510, "status": "reverted"},
            {"id": "old", "ts": outside, "status": "kept"},
        ]}), encoding="utf-8")
        usage = self.root / "usage.jsonl"
        usage.write_text(json.dumps({
            "timestamp": datetime.fromtimestamp(inside, timezone.utc).isoformat(),
            "loop": "gig", "provider_cost_usd": 1.25,
        }) + "\n", encoding="utf-8")
        transactions = self.gig_dir / "evidence" / "pass-1"
        transactions.mkdir(parents=True)
        (transactions / "paid-work-transaction.json").write_text(json.dumps({
            "status": "committed",
            "finished_at": datetime.fromtimestamp(inside + 600, timezone.utc).isoformat(),
        }), encoding="utf-8")
        (transactions / "paid-queue-evidence.json").write_text(json.dumps({
            "sent": True,
            "send_performed": True,
            "formal_delivery_checkbox": True,
            "captured_at": datetime.fromtimestamp(inside + 660, timezone.utc).isoformat(),
            "talkroom_id": "501",
        }), encoding="utf-8")

        message = self.report.weekly_message(
            gig_dir=self.gig_dir, usage_ledger=usage,
            now=datetime(2026, 7, 28, 0, 12, tzinfo=timezone.utc),
        )

        self.assertIn("📈 gig週報 2026-07-20..2026-07-26", message)
        self.assertIn("応募 2 → 返信 1 → 契約 1 → 納品 1 → 入金 1", message)
        self.assertIn("売上 ¥12000 / 出品 1 / model cost $1.25", message)
        self.assertIn("前週比 応募 +1 / 売上 +¥12000", message)
        self.assertIn("incident 1 / self-heal recovery evidence 1", message)
        self.assertIn("experiment kept 1 / reverted 1", message)
        self.assertNotIn("never print me", message)

    def test_weekly_event_key_is_one_per_completed_week(self):
        first = datetime(2026, 7, 27, 0, 12, tzinfo=timezone.utc)
        later = datetime(2026, 7, 30, 0, 12, tzinfo=timezone.utc)
        self.assertEqual(
            self.report.weekly_event_key(first),
            self.report.weekly_event_key(later),
        )

    def test_openclaw_transport_requires_json_ack_message_id(self):
        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            return type("Completed", (), {
                "returncode": 0,
                "stdout": json.dumps({"payload": {"ok": True}, "messageId": "321"}),
                "stderr": "",
            })()

        transport = self.report.OpenClawTelegramTransport(
            target="42",
            executable=Path("/opt/homebrew/bin/openclaw"),
            run=run,
            receipt_dir=self.root / "telegram-receipts",
            now_ms=lambda: 123000,
        )
        message_id = transport.send_report(
            "bounded report",
            event_key="gig:telegram:test:bounded",
        )

        self.assertEqual(message_id, "321")
        self.assertEqual(calls[0][0], [
            "/opt/homebrew/bin/openclaw", "message", "send",
            "--channel", "telegram", "--target", "42",
            "--message", "bounded report", "--json",
        ])
        receipts = list((self.root / "telegram-receipts").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text())
        self.assertEqual(receipt["message_id"], "321")
        self.assertEqual(receipt["event_key"], "gig:telegram:test:bounded")
        self.assertEqual(receipt["target"], "42")
        self.assertEqual(receipt["provider_acked_at_epoch_ms"], 123000)
        self.assertEqual(
            receipt["message_sha256"],
            self.report.hashlib.sha256(b"bounded report").hexdigest(),
        )

    def test_runtime_reconciles_provider_receipts_before_dispatch(self):
        source = REPORT_SCRIPT.read_text(encoding="utf-8")
        recover = source.index("outbox.recover_expired")
        reconcile = source.index("outbox.reconcile_receipts", recover)
        transport = source.index("OpenClawTelegramTransport", reconcile)

        self.assertLess(recover, reconcile)
        self.assertLess(reconcile, transport)

    def test_volume_controller_official_rows_deficit_and_shortfall_are_durable(self):
        now, stamp = datetime(2026, 8, 10, 12, 15, tzinfo=JST), int(datetime(2026, 8, 10, 12, 15, tzinfo=JST).timestamp())
        rows = [{"requestId": "100", "status": "applied", "submit_verified": True, "applied_page_verified": True, "ts": stamp - 3600},
                {"requestId": "100", "status": "applied", "submit_verified": True, "applied_page_verified": True, "ts": stamp - 3500},
                {"requestId": "101", "status": "applied", "submit_verified": False, "applied_page_verified": True, "ts": stamp - 3300}]
        (self.gig_dir / "applied.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (self.gig_dir / "pass-report.jsonl").write_text(json.dumps({"pass_id": "p1", "ts": stamp - 1800}) + "\n", encoding="utf-8")
        (self.gig_dir / "pass-failures.jsonl").write_text(json.dumps({"pass_id": "p2", "ts": stamp - 900}) + "\n", encoding="utf-8")
        (self.gig_dir / "b2-shortfall.jsonl").write_text(json.dumps({"recorded_at": stamp - 60, "outcome": "shortfall", "eligible_work_available": 0, "source_status": "exhausted", "largest_loss_stage": "source_exhaustion"}) + "\n", encoding="utf-8")
        output = self.gig_dir / "application-volume-controller.json"
        result = self.report.write_application_volume_controller(gig_dir=self.gig_dir, output_path=output, now=now)
        self.assertEqual((result["verified_applications"], result["remaining_applications"], result["target_this_wake"], result["turn_cap"]), (1, 99, 5, 6))
        self.assertEqual((result["source_status"], result["largest_loss_stage"]), ("exhausted", "source_exhaustion"))
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)

    def test_daily_envelope_and_shell_render_the_controller_state(self):
        now = datetime(2026, 8, 10, 12, 15, tzinfo=JST)
        now_epoch = int(now.timestamp())
        self.create_connector_rows()
        (self.gig_dir / "applied.jsonl").write_text(
            json.dumps({
                "requestId": "300", "status": "applied", "submit_verified": True,
                "applied_page_verified": True, "ts": now_epoch - 300,
            }) + "\n", encoding="utf-8"
        )
        for name in (
            "pass-report.jsonl", "pass-failures.jsonl", "earnings.jsonl",
            "shuppin.jsonl", "paid-progress.jsonl", "work-events.jsonl",
        ):
            (self.gig_dir / name).write_text("", encoding="utf-8")
        (self.gig_dir / "audit.jsonl").write_text(
            json.dumps({"ts": now_epoch, "progressing": True, "heartbeat_age_min": 1})
            + "\n", encoding="utf-8"
        )
        controller_path = self.gig_dir / "application-volume-controller.json"
        self.report.write_application_volume_controller(
            gig_dir=self.gig_dir, output_path=controller_path, now=now
        )
        outbox = self.outbox_module.TelegramOutbox(self.telegram_db)

        envelope = self.report.daily_envelope(
            gig_dir=self.gig_dir,
            connector_database=self.connector_db,
            telegram_outbox=outbox,
            now=now,
            usage_ledger=self.gig_dir / "usage.jsonl",
            auditor_log=self.gig_dir / "audit.jsonl",
        )

        metrics = envelope["data"]["metrics"]["volume_controller"]
        message = envelope["data"]["human_message_ja"]
        self.assertEqual(metrics["verified_applications"], 1)
        self.assertIn("verified=1/100 deficit=99", message)
        self.assertIn("wake average=0", message)
        self.assertIn("turn cap=6", message)
        self.assertEqual(metrics["largest_loss_stage"], "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
