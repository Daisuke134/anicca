import importlib.util
import inspect
import io
import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_queue_snapshot.py"
MESSAGES_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "messages_dom.json"
NAVIGATION_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "navigation_transient.json"
SPEC = importlib.util.spec_from_file_location("coconala_queue_snapshot", SCRIPT)
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class CoconalaQueueSnapshotTest(unittest.TestCase):
    def test_read_only_cli_defaults_to_hidden_targets_and_requires_visible_opt_in(self):
        parser = collector.argument_parser()
        default = parser.parse_args([
            "--output", "/tmp/marketplace-snapshot.json",
            "--evidence-dir", "/tmp/marketplace-evidence",
        ])
        visible = parser.parse_args([
            "--output", "/tmp/marketplace-snapshot.json",
            "--evidence-dir", "/tmp/marketplace-evidence",
            "--visible-with-screenshot",
        ])

        self.assertTrue(default.hidden_no_screenshot)
        self.assertFalse(visible.hidden_no_screenshot)

    def test_collector_uses_session_owned_hidden_target(self):
        process = mock.Mock()
        process.stdout = io.StringIO(
            '{"ok":true,"target_id":"target-1","ws":"ws://target-1","hidden":true}\n'
        )
        process.stdin = mock.Mock()
        process.stdin.closed = False
        process.wait.return_value = 0
        with (
            mock.patch.object(collector.subprocess, "Popen", return_value=process) as popen,
            mock.patch.object(
                collector.select, "select",
                return_value=([process.stdout], [], []),
            ),
        ):
            with collector.DefaultTab(
                Path("/safe/helper.py"),
                "https://coconala.com/message",
                hidden=True,
                owner="gig-snapshot",
            ):
                pass
        self.assertEqual(
            popen.call_args.args[0],
            [
                "python3", "/safe/helper.py", "serve-hidden",
                "https://coconala.com/message",
                "--owner", "gig-snapshot",
            ],
        )
        process.stdin.close.assert_called_once_with()
        process.wait.assert_called_once()

    def test_production_transient_fixture_accepts_dom_ready_interactive(self):
        fixture = json.loads(NAVIGATION_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["error"], collector.TRANSIENT_NAVIGATION_ERROR)
        self.assertTrue(collector.navigation_state_ready(
            fixture["observed_states"][1], fixture["expected_url"],
        ))
        self.assertFalse(collector.navigation_state_ready(
            {"url": "about:blank", "ready": "complete"}, fixture["expected_url"],
        ))
        self.assertFalse(collector.navigation_state_ready(
            {"url": fixture["expected_url"], "ready": "loading"}, fixture["expected_url"],
        ))
        self.assertFalse(collector.navigation_state_ready(
            {"url": "https://coconala.com/mypage/messages", "ready": "interactive"}, fixture["expected_url"],
        ))

    def test_inbox_uses_real_route_and_rejects_404_or_query_loss(self):
        expected = "https://coconala.com/message?fromMyPage=true"
        self.assertEqual(collector.B1_INBOX_URL, expected)
        self.assertTrue(collector.validate_inbox_dom({
            "url": expected,
            "not_found": False,
        }))
        for observed in (
            {"url": "https://coconala.com/mypage/messages", "not_found": True},
            {"url": "https://coconala.com/message", "not_found": False},
            {"url": expected, "not_found": True},
        ):
            with self.subTest(observed=observed):
                self.assertFalse(collector.validate_inbox_dom(observed))
        self.assertIn("not_found", collector.B1_MESSAGES_EXPRESSION)
        self.assertEqual(collector.MESSAGES_URL, "https://coconala.com/message")

    def test_messages_fixture_preserves_buyer_last_side_and_expression_uses_row_parents(self):
        fixture = json.loads(MESSAGES_FIXTURE.read_text(encoding="utf-8"))
        fixture["url"] = collector.B1_INBOX_URL
        rows = collector.b1_inquiries_from_dom(fixture)
        self.assertEqual([row["talkroom_id"] for row in rows], ["4201", "4202"])
        self.assertEqual([row["reply_required"] for row in rows], [True, False])
        self.assertNotIn("closest('[class*=\\\"talkroom\\\"]')", collector.B1_MESSAGES_EXPRESSION)
        self.assertIn("last_message_side", collector.B1_MESSAGES_EXPRESSION)
        self.assertEqual(collector.last_message_side_from_dom({"messages": [
            {"side": "buyer", "text": "質問"}, {"side": "seller", "text": "回答"},
        ]}), "seller")

    def test_inquiry_dom_is_normalized_without_buyer_identity(self):
        rows = collector.b1_inquiries_from_dom({
            "url": collector.B1_INBOX_URL,
            "title": "メッセージ | マイページ | ココナラ",
            "container_present": True,
            "not_found_present": False,
            "error_present": False,
            "cards": [
            {"talkroom_url": "https://coconala.com/talkrooms/42?secret=1", "title": "相談", "last_message_side": "buyer", "unread": True, "buyer": "buyer-a"},
            {"talkroom_url": "https://coconala.com/talkrooms/43", "title": "相談", "last_message_side": "seller", "unread": False},
        ]})
        self.assertEqual(rows[0]["talkroom_id"], "42")
        self.assertTrue(rows[0]["reply_required"])
        self.assertFalse(rows[1]["reply_required"])
        self.assertNotIn("buyer-a", json.dumps(rows[0], ensure_ascii=False))
        self.assertIn("MESSAGES_URL", collector.__dict__)

    def test_unrelated_checked_checkbox_is_not_formal_delivery(self):
        self.assertFalse(collector.formal_delivery_from_dom({
            "transaction_state": "取引中",
            "formal_delivery_control_checked": False,
            "checked_checkbox_count": 4,
        }))
        self.assertTrue(collector.formal_delivery_from_dom({
            "transaction_state": "納品確認待ち",
            "formal_delivery_control_checked": True,
            "checked_checkbox_count": 4,
        }))
        self.assertTrue(collector.formal_delivery_from_dom({
            "transaction_state": "納品確認待ち",
            "formal_delivery_control_checked": False,
            "checked_checkbox_count": 0,
        }))
        self.assertNotIn('document.querySelector("input[type=checkbox]:checked")', collector.TALKROOM_EXPRESSION)
        self.assertIn("formalDelivery", collector.TALKROOM_EXPRESSION)
        self.assertIn(".d-talkroomStep_label-current", collector.TALKROOM_EXPRESSION)
        self.assertNotIn("document.body.innerText.match(/納品確認待ち", collector.TALKROOM_EXPRESSION)

    def test_minimized_talkroom_drops_text_secrets_and_keeps_safe_buyer_attachment_metadata(self):
        raw = {
            "url": "https://coconala.com/talkrooms/18011694",
            "transaction_state": "取引中",
            "formal_delivery_control_checked": False,
            "checked_checkbox_count": 1,
            "body": "mail secret@example.com LINE https://line.me/ti/p/SECRET",
            "messages": [{
                "side": "buyer",
                "text": "エラーです secret@example.com https://line.me/R/ti/p/@invite",
                "attachments": [
                    {"filename": "repair.mcaddon", "content_type": "application/octet-stream", "size_bytes": 1234,
                     "href": "https://coconala.com/uploaded_files/42/download?token=TOPSECRET&email=secret@example.com"},
                    {"filename": "error screenshot.png", "content_type": "image/png", "size_bytes": 5678,
                     "href": "https://coconala.com/uploaded_files/43/download?signature=PRIVATE"},
                ],
            }],
        }
        minimized = collector.minimize_talkroom_dom(raw, "18011694", "2026-07-21T11:00:00+00:00")
        serialized = json.dumps(minimized, ensure_ascii=False)
        for secret in ("secret@example.com", "line.me", "TOPSECRET", "PRIVATE", "エラーです"):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("body", minimized)
        self.assertNotIn("messages", minimized)
        self.assertEqual([a["filename"] for a in minimized["buyer_attachments"]], ["repair.mcaddon", "error screenshot.png"])
        self.assertEqual(minimized["buyer_attachments"][0]["download_reference"], "/uploaded_files/42/download")
        self.assertTrue(minimized["buyer_feedback_pending_artifact"])

    def test_latest_paid_buyer_reply_is_idempotently_persisted_only_in_project_requirements(self):
        raw = {
            "url": "https://coconala.com/talkrooms/17943244",
            "transaction_state": "取引中",
            "messages": [
                {"side": "seller", "text": "v3", "attachments": [{"filename": "v3.zip"}]},
                {
                    "side": "buyer",
                    "text": (
                        "ブランドストーリーから財布・カードケース・小物中心へ移してください。 "
                        "secret@example.com https://example.com/reference?token=TOPSECRET"
                    ),
                    "attachments": [],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            projects = Path(temp) / "projects"
            first = collector.persist_latest_paid_buyer_reply(
                raw, "17943244", projects, "2026-07-23T01:00:00+00:00",
            )
            self.assertIsNotNone(first)
            path = Path(first["requirements_path"])
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["source"], "latest_buyer_reply_after_artifact")
            self.assertEqual(payload["project_id"], "17943244")
            self.assertEqual(payload["talkroom_id"], "17943244")
            self.assertIn("財布・カードケース・小物", payload["feedback_text"])
            self.assertNotIn("secret@example.com", path.read_text(encoding="utf-8"))
            self.assertNotIn("TOPSECRET", path.read_text(encoding="utf-8"))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

            second = collector.persist_latest_paid_buyer_reply(
                raw, "17943244", projects, "2026-07-23T02:00:00+00:00",
            )
            self.assertEqual(second["feedback_sha256"], first["feedback_sha256"])
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

            minimized = collector.minimize_talkroom_dom(
                raw, "17943244", "2026-07-23T02:00:00+00:00",
            )
            serialized = json.dumps(minimized, ensure_ascii=False)
            self.assertNotIn("財布", serialized)
            self.assertNotIn("secret@example.com", serialized)

    def test_paid_reply_sidecar_is_not_created_before_a_buyer_reply_after_artifact(self):
        raw = {
            "url": "https://coconala.com/talkrooms/42",
            "messages": [
                {"side": "buyer", "text": "先の依頼", "attachments": []},
                {"side": "seller", "text": "v2", "attachments": [{"filename": "v2.zip"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            projects = Path(temp) / "projects"
            result = collector.persist_latest_paid_buyer_reply(
                raw, "42", projects, "2026-07-23T01:00:00+00:00",
            )
            self.assertIsNone(result)
            self.assertFalse((projects / "42").exists())

    def test_buyer_agreement_is_a_bounded_boolean_not_raw_message_text(self):
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": [{"side": "buyer", "text": "確認済み。問題ありません。", "attachments": []}],
        }, "42", "2026-07-22T00:00:00+00:00")
        self.assertTrue(minimized["buyer_agreement_observed"])
        self.assertNotIn("確認済み", json.dumps(minimized, ensure_ascii=False))

    def test_seller_attachment_waits_until_a_new_buyer_reply(self):
        base = [
            {"side": "buyer", "text": "成果物を確認したいです", "attachments": []},
            {"side": "seller", "text": "v2です", "attachments": [{"filename": "v2.zip"}]},
        ]
        waiting = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": base,
        }, "42", "2026-07-22T00:00:00+00:00")
        self.assertTrue(waiting["buyer_visible_artifact_observed"])
        self.assertFalse(waiting["buyer_feedback_pending_artifact"])
        self.assertFalse(waiting["buyer_agreement_observed"])
        self.assertFalse(waiting["buyer_reply_after_artifact_observed"])

        approved = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": base + [{"side": "buyer", "text": "確認済み。問題ありません。", "attachments": []}],
        }, "42", "2026-07-22T01:00:00+00:00")
        self.assertTrue(approved["buyer_agreement_observed"])
        self.assertTrue(approved["buyer_reply_after_artifact_observed"])

        non_keyword_revision = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": base + [{"side": "buyer", "text": "2枚目の表現だけ変えてください", "attachments": []}],
        }, "42", "2026-07-22T01:00:00+00:00")
        self.assertTrue(non_keyword_revision["buyer_reply_after_artifact_observed"])

    def test_evidence_json_and_screenshot_are_owner_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "evidence"
            root.mkdir()
            collector.secure_directory(root)
            json_path = root / "snapshot.json"
            png_path = root / "snapshot.png"
            collector.atomic_json(json_path, {"safe": True})
            collector.secure_write_bytes(png_path, b"png")
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(json_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(png_path).st_mode & 0o777, 0o600)

    def test_order_and_quote_normalization_strip_email_invite_and_query_tokens(self):
        orders = collector.orders_from_dom({"cards": [{
            "talkroom_url": "https://coconala.com/talkrooms/123?token=ORDERSECRET",
            "buyer": "secret@example.com",
            "title": "Contact https://line.me/ti/p/INVITE",
            "text": "Work\nBuyer\n1,000円\n2026/07/23\n取引中",
        }]})
        quotes = collector.quotes_from_dom({"cards": [{
            "request_url": "https://coconala.com/customize/requests/456?signature=QUOTESECRET",
            "proposal_url": "https://coconala.com/customize/offers/add/456?auth=PRIVATE",
            "buyer": "secret@example.com",
            "title": "LINE https://line.me/R/ti/p/@invite",
            "text": "1,000円 2026/07/24 要提案",
        }]})
        serialized = json.dumps({"orders": orders, "quotes": quotes}, ensure_ascii=False)
        for secret in ("secret@example.com", "line.me", "ORDERSECRET", "QUOTESECRET", "PRIVATE"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(orders[0]["marketplace_url"], "https://coconala.com/talkrooms/123")
        self.assertIsNone(orders[0]["price_jpy"])
        self.assertEqual(orders[0]["price_source"], "missing_structured_price")
        self.assertEqual(quotes[0]["proposal_url"], "https://coconala.com/customize/offers/add/456")

    def test_order_single_unstructured_preview_amount_is_unknown(self):
        orders = collector.orders_from_dom({"cards": [{
            "talkroom_url": "https://coconala.com/talkrooms/17943244",
            "buyer": "buyer",
            "title": "SNS運用",
            "text": "実績 Makuake 126,000円\n2026/08/14\n取引中",
        }]})
        self.assertIsNone(orders[0]["price_jpy"])
        self.assertEqual(orders[0]["price_source"], "missing_structured_price")

    def test_order_uses_structured_price_label_before_message_preview_amount(self):
        orders = collector.orders_from_dom({"cards": [{
            "talkroom_url": "https://coconala.com/talkrooms/17943244",
            "buyer": "buyer",
            "title": "SNS運用",
            "text": "進捗報告 Makuake 126,000円\n40,000円\n2026/08/14\n取引中",
            "price_text": "40,000円",
            "price_source": "structured_order_label",
        }]})
        self.assertEqual(orders[0]["price_jpy"], 40000)
        self.assertEqual(orders[0]["price_source"], "structured_order_label")

    def test_order_ambiguous_text_price_is_unknown_not_first_yen(self):
        orders = collector.orders_from_dom({"cards": [{
            "talkroom_url": "https://coconala.com/talkrooms/17943244",
            "buyer": "buyer",
            "title": "SNS運用",
            "text": "進捗報告 Makuake 126,000円\n契約金額 40,000円\n2026/08/14\n取引中",
        }]})
        self.assertIsNone(orders[0]["price_jpy"])
        self.assertEqual(orders[0]["price_source"], "ambiguous_card_text")

    def test_order_dom_expression_reads_price_column_not_message_preview(self):
        self.assertIn("d-providerTalkroomCassettePrice_price", collector.ORDERS_EXPRESSION)
        self.assertIn("d-providerTalkroomCassetteSpDetail_yenIcon", collector.ORDERS_EXPRESSION)
        self.assertIn("price_text", collector.ORDERS_EXPRESSION)

    def test_talkroom_capture_moves_to_server_latest_message_before_reading_dom(self):
        self.assertIn("最新のメッセージに移動", collector.TALKROOM_EXPRESSION)
        self.assertIn("jump.click()", collector.TALKROOM_EXPRESSION)
        self.assertIn("await new Promise", collector.TALKROOM_EXPRESSION)
        self.assertIn("for(let i=0;i<40&&!jump;i++)", collector.TALKROOM_EXPRESSION)
        self.assertIn("scrollIntoView", collector.TALKROOM_EXPRESSION)
        self.assertIn('"awaitPromise": True', inspect.getsource(collector.inspect_page))

    def test_navigation_retry_uses_a_fresh_closed_tab_for_recognized_transient(self):
        tabs = []

        class FakeTab:
            def __init__(self, helper, url, *, hidden=False):
                self.ws = f"ws-{len(tabs)}"
                self.closed = False
                self.hidden = hidden
                tabs.append(self)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                self.closed = True

        calls = 0

        async def fake_inspect(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError(collector.TRANSIENT_NAVIGATION_ERROR)
            return {"ok": True}

        with mock.patch.object(collector, "DefaultTab", FakeTab), mock.patch.object(collector, "inspect_page", fake_inspect):
            result = collector.inspect_page_with_retry(Path("helper"), "https://coconala.com/", "{}", Path("shot.png"))

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, 2)
        self.assertEqual(len(tabs), 2)
        self.assertTrue(all(tab.closed for tab in tabs))

    def test_navigation_retry_does_not_retry_unrecognized_errors(self):
        tabs = []

        class FakeTab:
            def __init__(self, helper, url, *, hidden=False):
                self.ws = "ws"
                self.closed = False
                self.hidden = hidden
                tabs.append(self)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                self.closed = True

        async def fake_inspect(*_args, **_kwargs):
            raise RuntimeError("evaluation failed")

        with mock.patch.object(collector, "DefaultTab", FakeTab), mock.patch.object(collector, "inspect_page", fake_inspect):
            with self.assertRaisesRegex(RuntimeError, "evaluation failed"):
                collector.inspect_page_with_retry(Path("helper"), "https://coconala.com/", "{}", Path("shot.png"))

        self.assertEqual(len(tabs), 1)
        self.assertTrue(tabs[0].closed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
