import asyncio
import importlib.util
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_queue_snapshot.py"
SPEC = importlib.util.spec_from_file_location("speedy_reply_collector", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class SpeedyReplyCollectorContractTest(unittest.TestCase):
    @staticmethod
    def healthy_inbox(cards):
        return {
            "url": "https://coconala.com/message",
            "title": "メッセージ | マイページ | ココナラ",
            "container_present": True,
            "not_found_present": False,
            "error_present": False,
            "cards": cards,
        }

    def test_confirmed_manifest_drives_canonical_message_url(self):
        manifest = collector.load_connector_manifest()

        self.assertEqual(manifest["authorization_source"], "user_confirmed")
        self.assertFalse(manifest["policy_lookup_at_runtime"])
        self.assertFalse(manifest["terms_lookup_at_runtime"])
        self.assertEqual(manifest["inbox"]["url"], "https://coconala.com/message")
        self.assertEqual(collector.MESSAGES_URL, manifest["inbox"]["url"])
        self.assertEqual(collector.B1_INBOX_URL, "https://coconala.com/message?fromMyPage=true")
        self.assertNotEqual(collector.B1_INBOX_URL, collector.MESSAGES_URL)

    def test_only_verified_message_page_can_report_queue_empty(self):
        self.assertEqual(collector.inquiries_from_dom(self.healthy_inbox([])), [])
        cases = [
            ({**self.healthy_inbox([]), "title": "404 Not Found", "not_found_present": True}, "not_found"),
            ({**self.healthy_inbox([]), "url": "https://coconala.com/login", "title": "ログイン"}, "login"),
            ({**self.healthy_inbox([]), "title": "エラー", "error_present": True}, "error_page"),
            ({**self.healthy_inbox([]), "url": "https://coconala.com/mypage/dashboard"}, "unexpected_url"),
            ({**self.healthy_inbox([]), "title": "マイページ"}, "unexpected_title"),
            ({**self.healthy_inbox([]), "container_present": False}, "missing_container"),
        ]
        for dom, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(
                    collector.CollectorUnhealthy,
                    f"collector_unhealthy:{reason}",
                ):
                    collector.inquiries_from_dom(dom)

    def test_direct_message_event_extracts_bounded_platform_identity_and_time(self):
        url = "https://coconala.com/mypage/direct_message/42"
        event = collector.direct_message_event({
            "url": url,
            "title": "メッセージ詳細 | マイページ | ココナラ",
            "container_present": True,
            "not_found_present": False,
            "error_present": False,
            "own_user_path": "/users/seller",
            "messages": [{
                "message_id": "msg-7",
                "author_path": "/users/buyer",
                "sent_at": "2026-07-22T00:00:00+00:00",
                "body": "secret buyer request",
            }],
        }, url)

        self.assertEqual(event, {
            "last_message_side": "buyer",
            "reply_required": True,
            "buyer_sent_at": "2026-07-22T00:00:00+00:00",
            "message_id": "msg-7",
        })
        self.assertNotIn("secret buyer request", json.dumps(event))

    def test_direct_message_without_platform_id_uses_stable_ordinal_and_hash(self):
        url = "https://coconala.com/mypage/direct_message/42"
        sent_at = "2026-07-22T00:00:00+00:00"
        event = collector.direct_message_event({
            "url": url,
            "title": "メッセージ詳細 | マイページ | ココナラ",
            "container_present": True,
            "not_found_present": False,
            "error_present": False,
            "own_user_path": "/users/seller",
            "messages": [
                {"author_path": "/users/buyer", "sent_at": sent_at, "body": "earlier"},
                {"author_path": "/users/buyer", "sent_at": sent_at, "body": "  hello   world  "},
            ],
        }, url)

        self.assertEqual(event["buyer_sent_at"], sent_at)
        self.assertEqual(event["stable_ordinal"], 1)
        self.assertEqual(
            event["message_sha256"],
            hashlib.sha256(b"hello world").hexdigest(),
        )
        self.assertNotIn("body", event)

    def test_message_index_discovers_direct_threads_and_expression_exposes_identity_fields(self):
        rows = collector.inquiries_from_dom(self.healthy_inbox([
            {
                "talkroom_url": "https://coconala.com/mypage/direct_message/42?token=secret",
                "title": "purchase_preorder_message",
                "unread": True,
            },
        ]))

        self.assertEqual(rows, [{
            "talkroom_id": "42",
            "talkroom_url": "https://coconala.com/mypage/direct_message/42",
            "title": "purchase_preorder_message",
            "reply_required": True,
            "next_action": "reply",
        }])
        self.assertIn("/mypage/direct_message/", collector.MESSAGES_EXPRESSION)
        self.assertIn("container_present", collector.MESSAGES_EXPRESSION)
        self.assertIn("message_id", collector.DIRECT_MESSAGE_EXPRESSION)
        self.assertIn("author_path", collector.DIRECT_MESSAGE_EXPRESSION)
        self.assertIn("sent_at", collector.DIRECT_MESSAGE_EXPRESSION)

    def test_private_message_inspection_never_persists_screenshots(self):
        calls = []

        async def fake_inspect_page(ws_url, expression, screenshot, expected_url=None):
            calls.append((ws_url, expression, screenshot, expected_url))
            return {"url": expected_url}

        with mock.patch.object(collector, "inspect_page", side_effect=fake_inspect_page):
            result = asyncio.run(collector.inspect_message_page(
                "ws://readonly-message",
                "JSON.stringify({})",
                collector.MESSAGES_URL,
            ))

        self.assertEqual(result, {"url": collector.MESSAGES_URL})
        self.assertIsNone(calls[0][2])
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('args.evidence_dir / "messages.png"', source)
        self.assertNotIn('args.evidence_dir / f"direct-message-', source)
        self.assertGreaterEqual(source.count("inspect_message_page("), 3)

    def test_live_direct_message_uses_own_sidebar_identity_and_converts_jst_time(self):
        url = "https://coconala.com/mypage/direct_message/42"
        event = collector.direct_message_event({
            "url": url,
            "title": "メッセージ詳細 | マイページ | ココナラ",
            "container_present": True,
            "not_found_present": False,
            "error_present": False,
            "own_user_path": "/users/seller",
            "messages": [{
                "author_path": "/users/buyer",
                "sent_at": "2026-07-22 15:06:11",
                "body": "private request",
            }],
        }, url)

        self.assertEqual(event["buyer_sent_at"], "2026-07-22T06:06:11+00:00")
        self.assertEqual(event["last_message_side"], "buyer")
        self.assertIn(".sidebar-profile", collector.DIRECT_MESSAGE_EXPRESSION)
        self.assertIn(".threadPostTime", collector.DIRECT_MESSAGE_EXPRESSION)
