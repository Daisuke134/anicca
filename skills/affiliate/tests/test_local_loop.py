import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
import sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).parents[1] / "scripts" / "local_loop.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_local_loop", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LocalLoopTest(unittest.TestCase):
    def test_daily_summary_has_stable_jst_day_identity_and_money_stage(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            receipt_dir = state / "composition-receipts"
            run_dir = state / "composition-runs" / f"alpha-en-{'a' * 16}"
            receipt_dir.mkdir(parents=True)
            run_dir.mkdir(parents=True)
            MODULE.atomic_json(receipt_dir / "alpha-en.json", {
                "state": "FAILED", "failure_class": "RUNNER_REJECTED",
                "plan_id": "alpha-en", "source_set_sha256": "a" * 64,
            })
            MODULE.atomic_json(run_dir / "summary.json", {
                "status": "budget_blocked", "budget": {"day": "2026-08-16"},
            })
            (state / "provider-reports" / "partnerstack-links").mkdir(parents=True)
            MODULE.atomic_json(
                state / "provider-reports" / "partnerstack-links" / "latest.json",
                {"observed_at": "provider-time", "placements": [{
                    "current_click_count": 0,
                }]},
            )
            wake = {
                "provider_state": "AUTHENTICATED",
                "impact_state": "APPLICATION_PENDING",
                "systeme_state": "CAPTCHA_CHALLENGE",
            }
            morning = datetime(2026, 8, 16, 8, tzinfo=ZoneInfo("Asia/Tokyo"))
            evening = datetime(2026, 8, 16, 21, tzinfo=ZoneInfo("Asia/Tokyo"))
            next_day = datetime(2026, 8, 17, 8, tzinfo=ZoneInfo("Asia/Tokyo"))
            first = MODULE.daily_summary_event(state, wake, morning)
            second = MODULE.daily_summary_event(state, wake, evening)
            third = MODULE.daily_summary_event(state, wake, next_day)
            unknown = MODULE.daily_summary_event(
                state,
                {"provider_state": "SIGN_IN_REQUIRED", "impact_state": "UNKNOWN", "systeme_state": "FAILED"},
                next_day,
            )
            self.assertEqual(first["event_uuid"], second["event_uuid"])
            self.assertNotEqual(first["event_uuid"], third["event_uuid"])
            self.assertIn("専用リンクで最初の外部クリック", first["body"])
            self.assertIn("英語campaign 1件の制作stage", first["body"])
            self.assertIn("次のJST予算で同じ仕事を自動再開", first["body"])
            self.assertNotIn("SIGN_IN_REQUIRED", unknown["body"])
            self.assertIn("確認が必要な状態", unknown["body"])

    def test_all_unsent_commissions_and_clicks_precede_daily_summary(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            for number in (1, 2):
                MODULE.append(state / "commission-ledger.jsonl", {
                    "transition_id": f"commission-{number}",
                    "provider_transaction_id": f"tx-{number}",
                    "status": "approved", "gross_commission_minor": 1000,
                    "net_commission_minor": 1000, "currency": "USD",
                    "placement": {"public_url": "https://example.test/article"},
                })
                MODULE.append(state / "click-ledger.jsonl", {
                    "transition_id": f"click-{number}", "delta_click_count": 1,
                    "public_url": "https://example.test/article",
                })
            wake = {"status": "READY_FOR_PUBLICATION"}
            observed = []
            for number in range(4):
                event = MODULE.next_telegram_event(state, wake)
                observed.append(event["kind"])
                MODULE.append(state / "telegram-sent.jsonl", {
                    "event_uuid": event["event_uuid"], "message_id": str(number),
                })
            self.assertEqual(observed, [
                "COMMISSION_APPROVED", "COMMISSION_APPROVED", "CLICK_DELTA", "CLICK_DELTA",
            ])

    def test_reconciled_impact_login_emits_one_natural_self_healed_event(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            wake = {
                "impact_state": "APPLICATION_PENDING",
                "impact_login_reconciled_job_id": "job-1",
                "status": "READY_FOR_PUBLICATION",
            }
            event = MODULE.owner_event(state, wake)
            self.assertEqual(event["kind"], "SELF_HEALED")
            self.assertIn("同じlogin jobを完了", event["body"])
            self.assertNotIn("EFFECT_STARTED", event["body"])

    def test_completed_generic_campaign_advances_to_tts_campaign(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            receipt = state / "x-posts" / "elevenagents-en-1.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({
                "state": "LIVE", "public_url": "https://x.com/selawmqt/status/1",
            }))
            expected = {"state": "X_LIVE", "public_url": "https://x.com/selawmqt/status/1"}
            for generic_state in ("ALREADY_LIVE", "PUBLICATION_CONFLICT"):
                with self.subTest(generic_state=generic_state):
                    with (
                        patch.object(MODULE, "advance_generic_publication", return_value={
                            "state": generic_state, "public_url": None,
                        }),
                        patch.object(
                            MODULE, "advance_legacy_dedicated_publication",
                            return_value={"state": "ALREADY_LIVE", "public_url": None},
                        ),
                        patch.object(
                            MODULE, "advance_tts_api_publication",
                            return_value=dict(expected),
                        ) as advance,
                    ):
                        result = MODULE.advance_known_publication(
                            state, Path(root) / "landing", 9326, Path(root) / "private.md",
                        )
                    self.assertEqual(result, {
                        **expected, "generic_state": generic_state,
                        "legacy_state": "ALREADY_LIVE",
                    })
                    advance.assert_called_once()

    def test_legacy_migration_stops_after_creating_one_provider_link(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "state"
            receipt = state / "x-posts" / "elevenlabs-en-1.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({
                "state": "LIVE", "public_url": "https://x.com/selawmqt/status/1",
            }))
            acquire = Mock(return_value={
                "state": "VERIFIED", "deduplicated": False,
                "private_link_field": "Placement example affiliate link",
            })
            result = MODULE.advance_legacy_dedicated_publication(
                state, Path(root) / "landing", 9326, Path(root) / "private.md",
                link_acquirer=acquire,
            )
            self.assertEqual(result["state"], "WAITING_FOR_PLACEMENT_LINK")
            acquire.assert_called_once()

    def test_wake_recovers_provider_and_advances_publication_without_cross_lane_blocking(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            private = root / "affiliate-credentials.md"
            private.write_text(
                "## ElevenLabs\n"
                "- Default affiliate link: `https://try.elevenlabs.io/example`\n",
                encoding="utf-8",
            )
            private.chmod(0o600)
            args = Namespace(
                private_markdown=private, state=root / "state", cdp_port=9324,
                x_cdp_port=9326, landing_root=root / "landing",
            )
            signed_out = {
                "state": "SIGN_IN_REQUIRED", "changed": False,
                "transition_id": "transition-1",
            }
            authenticated = {
                "state": "AUTHENTICATED", "changed": True,
                "transition_id": "transition-2",
            }
            output = io.StringIO()
            with (
                patch.object(MODULE, "browser_ready", side_effect=lambda port: port == 9324),
                patch.object(MODULE, "provider_poll", return_value=signed_out),
                patch.object(MODULE, "recover_provider", return_value=authenticated) as recover,
                patch.object(MODULE, "elevenlabs_link_action", return_value={
                    "state": "VERIFIED", "placement": MODULE.TTS_PLACEMENT,
                    "deduplicated": True, "provider_link_key": "link-1",
                }),
                patch.object(MODULE, "apply_getresponse", return_value={
                    "state": "ELIGIBILITY_BLOCKED", "program": "getresponse",
                    "deduplicated": True,
                }),
                patch.object(MODULE, "verify_systeme_email", return_value={
                    "state": "CAPTCHA_CHALLENGE", "deduplicated": True,
                }),
                patch.object(MODULE, "advance_known_publication", return_value={
                    "state": "X_LIVE", "public_url": "https://x.com/selawmqt/status/1",
                }) as advance,
                patch.object(MODULE, "observe_devto_acquisition", return_value={
                    "state": "OBSERVED", "article_count": 1,
                    "total_page_views": 0, "delta_page_views": 0,
                }),
                patch.object(MODULE, "run_revenue_cycle", return_value={
                    "state": "NO_TRANSACTIONS", "source_rows": 0,
                    "appended_transitions": 0,
                }),
                patch.object(MODULE, "flush_telegram", return_value={
                    "state": "NO_PENDING", "sent": 0, "message_id": None,
                }),
                contextlib.redirect_stdout(output),
            ):
                MODULE.wake(args)
            event = json.loads(output.getvalue())
            recover.assert_called_once()
            advance.assert_called_once()
            self.assertEqual(event["provider_state"], "AUTHENTICATED")
            self.assertEqual(event["publication_state"], "X_LIVE")
            self.assertEqual(event["revenue_state"], "NO_TRANSACTIONS")

    def test_wake_requires_authenticated_provider_and_receipts_transition(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            private = root / "affiliate-credentials.md"
            private.write_text(
                "## ElevenLabs\n"
                "- Default affiliate link: `https://try.elevenlabs.io/example`\n",
                encoding="utf-8",
            )
            private.chmod(0o600)
            args = Namespace(private_markdown=private, state=root / "state", cdp_port=9324)
            provider = {
                "state": "AUTHENTICATED", "changed": True,
                "transition_id": "transition-1",
            }
            output = io.StringIO()
            with (
                patch.object(MODULE, "browser_ready", return_value=True),
                patch.object(MODULE, "provider_poll", return_value=provider),
                patch.object(MODULE, "elevenlabs_link_action", return_value={
                    "state": "VERIFIED", "placement": MODULE.TTS_PLACEMENT,
                    "deduplicated": True, "provider_link_key": "link-1",
                }),
                patch.object(MODULE, "apply_getresponse", return_value={
                    "state": "ELIGIBILITY_BLOCKED", "program": "getresponse",
                    "deduplicated": True,
                }),
                patch.object(MODULE, "verify_systeme_email", return_value={
                    "state": "CAPTCHA_CHALLENGE", "deduplicated": True,
                }),
                patch.object(MODULE, "observe_devto_acquisition", return_value={
                    "state": "OBSERVED", "article_count": 1,
                    "total_page_views": 0, "delta_page_views": 0,
                }),
                patch.object(MODULE, "run_revenue_cycle", return_value={
                    "state": "NO_TRANSACTIONS", "source_rows": 0,
                    "appended_transitions": 0,
                }),
                patch.object(MODULE, "flush_telegram", return_value={
                    "state": "NO_PENDING", "sent": 0, "message_id": None,
                }),
                contextlib.redirect_stdout(output),
            ):
                MODULE.wake(args)
            event = json.loads(output.getvalue())
            self.assertEqual(event["status"], "READY_FOR_PUBLICATION")
            self.assertEqual(event["provider_state"], "AUTHENTICATED")
            self.assertEqual(event["provider_transition_id"], "transition-1")
            self.assertEqual(event["revenue_state"], "NO_TRANSACTIONS")

    def test_telegram_outbox_precedes_send_and_deduplicates_message_id(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            event = {"event_uuid": "event-1", "kind": "REVENUE_RECONCILED", "body": "report", "created_at": 1}
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                self.assertTrue((state / "telegram-outbox.jsonl").is_file())
                return subprocess.CompletedProcess(command, 0, '{"result":{"messageId":"7640"}}', "")

            with patch.object(MODULE.shutil, "which", return_value="/opt/homebrew/bin/openclaw"):
                first = MODULE.flush_telegram(state, event, runner=runner)
                second = MODULE.flush_telegram(state, event, runner=runner)
            self.assertEqual(first, {"state": "SENT", "sent": 1, "message_id": "7640"})
            self.assertEqual(second["state"], "NO_PENDING")
            self.assertEqual(len(calls), 1)
            self.assertEqual(json.loads((state / "telegram-sent.jsonl").read_text())["message_id"], "7640")

    def test_revenue_cycle_cooldown_is_independent_of_wake(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            MODULE.atomic_json(state / "revenue-cycle.json", {"completed_at": 1000})
            self.assertFalse(MODULE.revenue_cycle_due(state, now=4599))
            self.assertTrue(MODULE.revenue_cycle_due(state, now=4600))

    def test_placement_receipt_is_exactly_once_and_hides_tracking_link(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            private = root / "affiliate-credentials.md"
            private.write_text(
                "# Affiliate Credentials (local only)\n\n"
                "## ElevenLabs\n"
                "- Default affiliate link: `https://try.elevenlabs.io/example`\n",
                encoding="utf-8",
            )
            private.chmod(0o600)
            args = Namespace(
                private_markdown=private, state=root / "state",
                placement="article-1", locale="en", print_url=False,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                MODULE.placement(args)
                MODULE.placement(args)
            rows = (args.state / "placements.jsonl").read_text().splitlines()
            emitted = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual([row["deduplicated"] for row in emitted], [False, True])
            self.assertNotIn("try.elevenlabs.io", output.getvalue())


if __name__ == "__main__":
    unittest.main()
