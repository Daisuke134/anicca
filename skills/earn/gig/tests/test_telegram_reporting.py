import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPORT_SCRIPT = SCRIPTS / "telegram_report.py"
OUTBOX_SCRIPT = SCRIPTS / "telegram_outbox.py"
RUNNER_CONFIG = Path(__file__).resolve().parents[2] / "agent-runner" / "config.json"


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
        self.assertIn("route=Terra medium → Claude Sonnet", message)

    def test_application_recovery_names_exact_verified_jobs(self):
        key, message = self.report.application_recovery_message({
            "source": "canonical_orphan_reconciliation",
            "recovery_id": "recovery-20260729-1",
            "applications": [
                {
                    "request_id": "5170842",
                    "bucket": "single",
                    "title": "AIツール活用のWebサイト制作",
                    "url": "https://coconala.com/requests/5170842",
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
            json.dumps({"action": "shuppin_published", "service_id": "4312985"}) + '\n',
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
            "requestId": "5176621",
            "bucket": "single",
            "status": "applied",
            "category": "動画編集・映像制作",
            "title": "Remotion動画生成",
            "url": "https://coconala.com/requests/5176621",
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
        self.assertIn("https://coconala.com/requests/5176621", message)
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
            "ts": 5000, "pass_id": pass_id, "requestId": "5177000",
            "bucket": "single", "status": "applied", "title": "資料作成",
            "url": "https://coconala.com/requests/5177000",
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
        self.assertEqual(rows[0][0], "gig:telegram:lane-barren:v1:apply:1753600000")
        self.assertEqual(rows[0][1], "sent")

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
            target="8547730585",
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
            "--channel", "telegram", "--target", "8547730585",
            "--message", "bounded report", "--json",
        ])
        receipts = list((self.root / "telegram-receipts").glob("*.json"))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text())
        self.assertEqual(receipt["message_id"], "321")
        self.assertEqual(receipt["event_key"], "gig:telegram:test:bounded")
        self.assertEqual(receipt["target"], "8547730585")
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
