import asyncio
import importlib.util
import hashlib
import inspect
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_query_message_route_uses_direct_message_selector_family_for_coverage(self):
        expression = collector.INBOX_COVERAGE_EXPRESSION
        self.assertIn(
            "direct=location.pathname==='/message'&&!isB1",
            expression,
        )
        self.assertIn("sel=direct?", expression)
        self.assertIn("fromMyPage", expression)
        self.assertIn("a.c-messageItemWrap[href*='/mypage/direct_message/']", expression)

    def test_inbox_coverage_rejects_container_only_empty_dom(self):
        with self.assertRaises(collector.CollectorUnhealthy):
            collector.validate_inbox_coverage({"cards": []})

    def test_direct_inbox_snapshot_exposes_empty_orders_for_paid_fence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), hidden_no_screenshot=True,
                mode="direct-inbox-only", talkroom_id=None, project_id=None,
            )
            parser = mock.Mock(parse_args=mock.Mock(return_value=args))

            class FakeTab:
                ws = "ws"

                def __init__(self, *_args, **_kwargs):
                    pass

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return None

            async def fake_message_page(_ws, _expression, expected_url, **_kwargs):
                self.assertEqual(expected_url, collector.MESSAGES_URL)
                return {
                    "url": collector.MESSAGES_URL, "title": "メッセージ",
                    "container_present": True, "cards": [], "cards_count": 0,
                    "empty_state_present": True, "coverage_complete": True,
                    "termination_reason": "empty_state",
                }

            with (
                mock.patch.object(collector, "argument_parser", return_value=parser),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=fake_message_page),
            ):
                self.assertEqual(collector.main(), 0)

            snapshot = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["collector_mode"], "direct-inbox-only")
            self.assertEqual(snapshot["orders"], [])

    def test_source_receipt_is_bounded_and_secret_free(self):
        receipt = collector.source_receipt(
            source="direct_inbox",
            requested_url=collector.MESSAGES_URL,
            observed_at="2026-08-11T00:00:00+00:00",
            dom={
                "url": "https://coconala.com/message?token=SECRET",
                "title": "buyer@example.com",
                "container_present": True,
                "cards": [{"talkroom_url": "https://coconala.com/talkrooms/42"}],
                "coverage_complete": True,
                "termination_reason": "fixed_point",
                "iterations": 2,
                "pagination_pages": 3,
                "page_counts": [30, 30, 24],
            },
            previous_count=30,
        )
        serialized = json.dumps(receipt)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("buyer@example.com", serialized)
        self.assertEqual(receipt["cards_count"], 1)
        self.assertEqual(receipt["previous_count"], 30)
        self.assertEqual(receipt["pagination_pages"], 3)
        self.assertEqual(receipt["page_counts"], [30, 30, 24])

    def test_source_receipt_preserves_only_allowlisted_b1_query(self):
        receipt = collector.source_receipt(
            source="b1_inbox",
            requested_url=collector.B1_INBOX_URL,
            observed_at="2026-08-11T00:00:00+00:00",
            dom={
                "url": f"{collector.B1_INBOX_URL}&token=SECRET",
                "cards": [],
            },
        )
        self.assertEqual(receipt["requested_route"], collector.B1_INBOX_URL)
        self.assertEqual(receipt["final_route"], collector.B1_INBOX_URL)
        arbitrary = collector.source_receipt(
            source="direct_inbox",
            requested_url="https://coconala.com/message?token=SECRET",
            observed_at="2026-08-11T00:00:00+00:00",
            dom={"url": "https://coconala.com/message?foo=PRIVATE", "cards": []},
        )
        self.assertEqual(arbitrary["requested_route"], collector.MESSAGES_URL)
        self.assertEqual(arbitrary["final_route"], collector.MESSAGES_URL)

    def test_inbox_failure_retains_safe_diagnostics(self):
        with self.assertRaises(collector.CollectorUnhealthy) as raised:
            collector.validate_inbox_coverage({
                "url": collector.MESSAGES_URL,
                "cards": [],
                "container_present": False,
                "coverage_complete": True,
                "termination_reason": "fixed_point",
                "iterations": 20,
            })
        self.assertEqual(raised.exception.details["iterations"], 20)
        self.assertNotIn("cards", raised.exception.details)

    def test_orders_only_never_opens_unrelated_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="orders-only",
                talkroom_id=None, project_id=None,
            )
            urls = []

            def inspect(_helper, url, _expression, _screenshot, **_kwargs):
                urls.append(url)
                return {
                    "url": url, "title": "受注管理", "container_present": True,
                    "cards": [], "empty_state_present": True,
                }

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect),
            ):
                self.assertEqual(collector.main(), 0)
            snapshot = json.loads(args.output.read_text())
            self.assertEqual(urls, [collector.OPEN_ORDERS_URL])
            self.assertEqual(snapshot["collector_mode"], "orders-only")
            self.assertEqual(snapshot["observed_sources"], ["orders"])
            self.assertIs(snapshot["open_orders_list_observed"], True)

    def test_orders_only_accepts_authoritative_transaction_list_provider_container(self):
        self.assertIn(
            "document.querySelector('.d-transactionListProviderMain')",
            collector.ORDERS_ONLY_EXPRESSION,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="orders-only",
                talkroom_id=None, project_id=None,
            )
            dom = {
                "url": collector.OPEN_ORDERS_URL, "title": "受注管理",
                "container_present": True, "empty_state_present": False,
                "cards": [
                    {"talkroom_url": f"https://coconala.com/talkrooms/{room_id}", "text": "取引中"}
                    for room_id in (4201, 4202, 4203)
                ],
            }
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", return_value=dom),
            ):
                self.assertEqual(collector.main(), 0)
            snapshot = json.loads(args.output.read_text())
            self.assertEqual(len(snapshot["orders"]), 3)
            self.assertEqual(snapshot["source_receipt"]["cards_count"], 3)

    def test_orders_only_rejects_untrusted_route_or_empty_dom(self):
        self.assertIn("container_present", collector.ORDERS_ONLY_EXPRESSION)
        self.assertIn("empty_state_present", collector.ORDERS_ONLY_EXPRESSION)
        self.assertNotIn("container_present", collector.ORDERS_EXPRESSION)
        self.assertNotIn("empty_state_present", collector.ORDERS_EXPRESSION)
        cases = (
            {
                "url": "https://coconala.com/mypage/received_orders/closed",
                "title": "受注管理", "container_present": True, "cards": [],
                "empty_state_present": True,
            },
            {
                "url": "https://coconala.com/login", "title": "ログイン",
                "container_present": False, "cards": [],
            },
            {
                "url": collector.OPEN_ORDERS_URL, "title": "受注管理",
                "container_present": False, "cards": [], "empty_state_present": True,
            },
            {
                "url": collector.OPEN_ORDERS_URL, "title": "受注管理",
                "container_present": True, "cards": [], "empty_state_present": False,
            },
        )
        for dom in cases:
            with self.subTest(dom=dom):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    args = mock.Mock(
                        output=root / "snapshot.json", evidence_dir=root / "evidence",
                        cdp_helper=Path("helper"), projects_root=root / "projects",
                        hidden_no_screenshot=True, mode="orders-only",
                        talkroom_id=None, project_id=None,
                    )
                    with (
                        mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                            parse_args=mock.Mock(return_value=args))),
                        mock.patch.object(collector, "load_connector_manifest"),
                        mock.patch.object(collector, "inspect_page_with_retry", return_value=dom),
                    ):
                        self.assertNotEqual(collector.main(), 0)
                    self.assertFalse(args.output.exists())
                    failure = json.loads((args.evidence_dir / "snapshot-failure.json").read_text())
                    self.assertNotIn("open_orders_list_observed", failure)

    def test_full_and_orders_only_use_their_mode_specific_order_expressions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            orders_args = mock.Mock(
                output=root / "orders-snapshot.json", evidence_dir=root / "orders-evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="orders-only",
                talkroom_id=None, project_id=None,
            )
            orders_calls = []

            def inspect_orders(_helper, url, expression, _screenshot, **_kwargs):
                orders_calls.append((url, expression))
                return {
                    "url": url, "title": "受注管理", "container_present": True,
                    "cards": [], "empty_state_present": True,
                }

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=orders_args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect_orders),
            ):
                self.assertEqual(collector.main(), 0)
            self.assertEqual(orders_calls[0][0], collector.OPEN_ORDERS_URL)
            self.assertIs(orders_calls[0][1], collector.ORDERS_ONLY_EXPRESSION)
            self.assertIn("container_present", orders_calls[0][1])

            full_args = mock.Mock(
                output=root / "full-snapshot.json", evidence_dir=root / "full-evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="full",
            )
            full_calls = []

            def inspect_full(_helper, url, expression, _screenshot, **_kwargs):
                full_calls.append((url, expression))
                raise RuntimeError("stop_after_order_expression")

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=full_args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect_full),
            ):
                self.assertNotEqual(collector.main(), 0)
            self.assertEqual(full_calls[0][0], collector.OPEN_ORDERS_URL)
            self.assertIs(full_calls[0][1], collector.ORDERS_EXPRESSION)
            self.assertNotIn("container_present", full_calls[0][1])
            self.assertNotIn("empty_state_present", full_calls[0][1])

    def test_orders_only_rejects_when_normalization_drops_a_raw_card(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="orders-only",
                talkroom_id=None, project_id=None,
            )
            dom = {
                "url": collector.OPEN_ORDERS_URL, "title": "受注管理",
                "container_present": True, "empty_state_present": False,
                "cards": [
                    {"talkroom_url": "https://coconala.com/talkrooms/4201", "text": "取引中"},
                    {"title": "malformed card without a talkroom URL", "text": "取引中"},
                ],
            }
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", return_value=dom),
            ):
                self.assertNotEqual(collector.main(), 0)
            self.assertFalse(args.output.exists())
            failure = json.loads((args.evidence_dir / "snapshot-failure.json").read_text())
            self.assertEqual(failure["error"], "collector_unhealthy:orders_card_coverage_mismatch")
            self.assertEqual(failure["source_receipt"]["cards_count"], 1)
            self.assertNotIn("open_orders_list_observed", failure)

    def test_full_mode_failure_carries_bounded_collector_details(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="full",
            )
            details = collector.source_receipt(
                source="direct_inbox",
                requested_url=collector.MESSAGES_URL,
                observed_at="2026-08-11T00:00:00+00:00",
                dom={
                    "url": "https://coconala.com/message?token=SECRET",
                    "title": "buyer@example.com",
                    "container_present": False,
                    "cards": [{"text": "buyer message SECRET"}],
                    "coverage_complete": False,
                    "termination_reason": "fixed_point",
                    "iterations": 20,
                },
                previous_count=30,
            )

            class FakeTab:
                ws = "ws"

                def __init__(self, *_args, **_kwargs):
                    pass

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return None

            def inspect(_helper, url, _expression, _screenshot, **_kwargs):
                return {"url": url, "title": "受注管理", "container_present": True, "cards": []}

            async def inspect_message(_ws, _expression, expected_url, **_kwargs):
                if expected_url == collector.B1_INBOX_URL:
                    return {"url": expected_url, "title": "メッセージ", "not_found": False, "cards": []}
                raise collector.CollectorUnhealthy(
                    "inbox_empty_without_semantic_marker", details=details,
                )

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=inspect_message),
            ):
                self.assertNotEqual(collector.main(), 0)

            failure = json.loads((args.evidence_dir / "snapshot-failure.json").read_text())
            self.assertEqual(failure["source_receipt"], details)
            receipt = failure["source_receipt"]
            for key in (
                "source", "requested_route", "final_route", "container_found",
                "cards_count", "coverage_complete", "termination_reason",
                "iterations", "previous_count",
            ):
                self.assertIn(key, receipt)
            self.assertNotIn("raw_cards", receipt)
            self.assertNotIn("text", json.dumps(receipt))
            serialized = json.dumps(failure, ensure_ascii=False)
            self.assertNotIn("buyer@example.com", serialized)
            self.assertNotIn("SECRET", serialized)
            self.assertFalse(args.output.exists())

    def test_selected_talkroom_only_reads_and_persists_one_exact_room(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="selected-talkroom-only",
                talkroom_id="4201", project_id="5201",
                selected_order_input=json.dumps({"talkroom_id": "4201"}),
            )
            urls = []
            capture_kwargs = []

            def inspect(_helper, url, _expression, _screenshot, **_kwargs):
                urls.append(url)
                capture_kwargs.append(_kwargs)
                return {
                    "url": url, "title": "トークルーム", "history_complete": True,
                    "transaction_state": "取引中", "messages": [
                        {"side": "seller", "text": "v1", "attachments": [{"filename": "v1.zip"}]},
                        {"side": "buyer", "text": "修正してください", "attachments": []},
                    ],
                }

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect),
                mock.patch.object(collector, "install_project_posting", return_value=None),
            ):
                self.assertEqual(collector.main(), 0)
            snapshot = json.loads(args.output.read_text())
            self.assertEqual(urls, ["https://coconala.com/talkrooms/4201"])
            self.assertIs(capture_kwargs[0]["hidden"], False)
            self.assertIs(capture_kwargs[0]["capture_buyer_attachments"], True)
            self.assertEqual(snapshot["talkroom_id"], "4201")
            self.assertEqual(snapshot["talkroom"]["talkroom_id"], "4201")
            self.assertTrue((args.projects_root / "5201" / "source" / "talkroom" / "messages.jsonl").exists())

    def test_selected_mode_merges_matching_order_as_one_targeted_item(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected_input = root / "selected-order.json"
            selected_input.write_text(json.dumps({
                "request_id": "req-5201",
                "talkroom_id": "4201",
                "buyer": "Buyer",
                "selection_stage": "preliminary",
                "targeted_readback_required": True,
            }) + "\n")
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="selected-talkroom-only",
                talkroom_id="4201", project_id="req-5201",
                selected_order_input=selected_input,
            )

            def inspect(_helper, url, _expression, _screenshot, **_kwargs):
                return {
                    "url": url, "title": "トークルーム", "history_complete": True,
                    "transaction_state": "取引中", "messages": [
                        {"side": "seller", "text": "v1", "attachments": []},
                    ],
                }

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect),
                mock.patch.object(collector, "install_project_posting", return_value=None),
            ):
                self.assertEqual(collector.main(), 0)

            snapshot = json.loads(args.output.read_text())
            self.assertEqual(snapshot["observed_sources"], ["selected_talkroom"])
            self.assertEqual(len(snapshot["orders"]), 1)
            merged = snapshot["orders"][0]
            self.assertEqual(merged["request_id"], "req-5201")
            self.assertEqual(merged["talkroom_id"], "4201")
            self.assertEqual(merged["talkroom_state"], "取引中")
            self.assertEqual(merged["selection_stage"], "targeted")
            self.assertFalse(merged["targeted_readback_required"])

    def test_selected_mode_propagates_paid_feedback_identity_to_targeted_order(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            talkroom_id = "7301"
            feedback_sha256 = "b" * 64
            requirements_path = root / "projects" / "req-7301" / "requirements" / "live-buyer-reply.json"
            selected_input = root / "selected-order.json"
            selected_input.write_text(json.dumps({
                "talkroom_id": talkroom_id,
                "request_id": "req-7301",
            }) + "\n")
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="selected-talkroom-only",
                talkroom_id=talkroom_id, project_id="req-7301",
                selected_order_input=selected_input,
            )

            def inspect(_helper, url, _expression, _screenshot, **_kwargs):
                return {
                    "url": url, "title": "トークルーム", "history_complete": True,
                    "transaction_state": "取引中", "messages": [
                        {"side": "seller", "text": "v1", "attachments": [{"filename": "v1.zip"}]},
                        {"side": "buyer", "text": "修正してください", "attachments": []},
                    ],
                }

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=inspect),
                mock.patch.object(collector, "install_project_posting", return_value=None),
                mock.patch.object(collector, "persist_latest_paid_buyer_reply", return_value={
                    "requirements_path": str(requirements_path),
                    "feedback_sha256": feedback_sha256,
                    "stage": "revision",
                }),
            ):
                self.assertEqual(collector.main(), 0)

            snapshot = json.loads(args.output.read_text())
            merged = snapshot["orders"][0]
            self.assertTrue(merged["buyer_feedback_pending_artifact"])
            self.assertEqual(merged["buyer_feedback_sha256"], feedback_sha256)
            self.assertEqual(merged["buyer_feedback_requirements_path"], str(requirements_path))
            self.assertEqual(merged["buyer_feedback_stage"], "revision")
            self.assertNotIn("feedback_text", merged)

    def test_selected_mode_rejects_mismatched_input_before_browser_or_project_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected_input = root / "selected-order.json"
            selected_input.write_text(json.dumps({"talkroom_id": "4202"}) + "\n")
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="selected-talkroom-only",
                talkroom_id="4201", project_id="req-5201",
                selected_order_input=selected_input,
            )
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "inspect_page_with_retry") as inspect,
                mock.patch.object(collector, "secure_directory") as secure,
                mock.patch.object(collector, "persist_talkroom_history") as persist,
                mock.patch.object(collector, "install_project_posting") as install,
            ):
                self.assertNotEqual(collector.main(), 0)

            inspect.assert_not_called()
            secure.assert_not_called()
            persist.assert_not_called()
            install.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_selected_mode_rejects_malformed_input_before_browser_or_project_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected_input = root / "selected-order.json"
            selected_input.write_text("not-json\n")
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="selected-talkroom-only",
                talkroom_id="4201", project_id="req-5201",
                selected_order_input=selected_input,
            )
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "inspect_page_with_retry") as inspect,
                mock.patch.object(collector, "secure_directory") as secure,
                mock.patch.object(collector, "persist_talkroom_history") as persist,
                mock.patch.object(collector, "install_project_posting") as install,
            ):
                self.assertNotEqual(collector.main(), 0)

            inspect.assert_not_called()
            secure.assert_not_called()
            persist.assert_not_called()
            install.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_selected_mode_rejects_missing_or_nonnumeric_talkroom_before_browser(self):
        for talkroom_id in (None, "not-numeric"):
            args = mock.Mock(
                output=Path("/tmp/o"), evidence_dir=Path("/tmp/e"),
                cdp_helper=Path("helper"), projects_root=Path("/tmp/projects"),
                hidden_no_screenshot=True, mode="selected-talkroom-only",
                talkroom_id=talkroom_id, project_id="5201",
            )
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "inspect_page_with_retry") as inspect,
            ):
                self.assertNotEqual(collector.main(), 0)
                inspect.assert_not_called()

    def test_default_full_mode_keeps_existing_contract(self):
        parser = collector.argument_parser()
        args = parser.parse_args(["--output", "/tmp/o", "--evidence-dir", "/tmp/e"])
        self.assertEqual(args.mode, "full")
        direct = parser.parse_args([
            "--output", "/tmp/o", "--evidence-dir", "/tmp/e",
            "--mode", "direct-inbox-only",
        ])
        self.assertEqual(direct.mode, "direct-inbox-only")

    def test_direct_inbox_only_reads_inbox_and_each_room_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only",
                talkroom_id=None, project_id=None,
            )
            room_url = "https://coconala.com/mypage/direct_message/4201"
            list_dom = {
                "url": collector.MESSAGES_URL,
                "title": "メッセージ | マイページ | ココナラ",
                "container_present": True,
                "not_found_present": False,
                "error_present": False,
                "cards": [{
                    "talkroom_url": room_url,
                    "title": "事前相談",
                    "last_message_side": "",
                    "unread": True,
                }],
                "cards_count": 1,
                "empty_state_present": False,
                "coverage_complete": True,
                "termination_reason": "fixed_point",
                "iterations": 2,
            }
            room_dom = {
                "url": room_url,
                "title": "メッセージ詳細 | ココナラ",
                "container_present": True,
                "not_found_present": False,
                "error_present": False,
                "own_user_path": "/users/seller",
                "messages": [{
                    "message_id": "m-4201",
                    "author_path": "/users/buyer",
                    "sent_at": "2026-08-10T00:00:00+00:00",
                    "body": "相談内容",
                }],
            }
            opened_urls = []

            class FakeTab:
                def __init__(self, _helper, url, **_kwargs):
                    self.ws = f"ws:{url}"
                    opened_urls.append(url)

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return None

            def inspect_message(_ws, expression, expected_url, **_kwargs):
                self.assertIn(expected_url, {collector.MESSAGES_URL, room_url})
                if expected_url == collector.MESSAGES_URL:
                    self.assertIs(expression, collector.MESSAGES_EXPRESSION)
                    return list_dom
                self.assertIs(expression, collector.DIRECT_MESSAGE_EXPRESSION)
                return room_dom

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=inspect_message),
                mock.patch.object(collector, "inspect_page_with_retry") as inspect_page,
            ):
                self.assertEqual(collector.main(), 0)

            snapshot = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual(opened_urls, [collector.MESSAGES_URL, room_url])
            inspect_page.assert_not_called()
            self.assertEqual(snapshot["collector_mode"], "direct-inbox-only")
            self.assertEqual(snapshot["observed_sources"], ["direct_inbox"])
            self.assertEqual(snapshot["inquiries"][0]["talkroom_id"], "4201")
            self.assertFalse(snapshot["inquiries"][0]["reply_required"])
            self.assertEqual(snapshot["inquiries"][0]["next_action"], "semantic_failed")
            self.assertEqual(snapshot["inquiries"][0]["message_id"], "m-4201")
            self.assertEqual(snapshot["source_receipt"]["requested_route"], collector.MESSAGES_URL)
            self.assertEqual(snapshot["source_receipt"]["final_route"], collector.MESSAGES_URL)
            self.assertTrue(snapshot["source_receipt"]["coverage_complete"])
            self.assertEqual(snapshot["source_receipt"]["termination_reason"], "fixed_point")
            self.assertEqual(snapshot["source_receipt"]["cards_count"], 1)
            self.assertNotIn("相談内容", json.dumps(snapshot, ensure_ascii=False))

    def test_previous_direct_snapshot_reuses_valid_rows_and_rereads_invalid_rows_without_older_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = {
                "talkroom_id": "1",
                "talkroom_url": "https://coconala.com/mypage/direct_message/1",
                "preview_sha256": "a" * 64,
                "last_message_identity_sha256": "b" * 64,
                "last_message_side": "seller",
                "negotiation_intent": "unclear",
                "reply_required": False,
                "next_action": "observe",
                "sending_unavailable": True,
                "seller_sent_at": "2026-08-10T00:00:00+00:00",
                "message_id": "m-1",
            }

            def write_pass(name, rows, complete=True):
                evidence = root / name
                evidence.mkdir(parents=True)
                (evidence / "marketplace-snapshot.json").write_text(json.dumps({
                    "collector_mode": "direct-inbox-only", "inquiries": rows,
                    "source_receipt": {"cards_count": len(rows), "coverage_complete": complete},
                }), encoding="utf-8")
                return evidence

            old = write_pass("gig-pass-old", [{**valid, "talkroom_id": "old"}])
            latest = write_pass("reply-detector-new", [valid, {**valid, "talkroom_id": "bad", "preview_sha256": "raw"}])
            os.utime(old / "marketplace-snapshot.json", (100, 100))
            os.utime(latest / "marketplace-snapshot.json", (200, 200))
            rows = collector.previous_direct_snapshot(root, root / "reply-detector-current" / "live-dom")
            self.assertEqual(set(rows), {"1"})
            self.assertEqual(rows["1"]["message_id"], "m-1")

    def test_previous_direct_snapshot_taints_only_a_duplicate_talkroom_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = {
                "talkroom_id": "1", "talkroom_url": "https://coconala.com/mypage/direct_message/1",
                "preview_sha256": "a" * 64, "last_message_identity_sha256": "b" * 64,
                "last_message_side": "seller", "reply_required": False, "next_action": "observe",
                "negotiation_intent": "unclear",
                "seller_sent_at": "2026-08-10T00:00:00+00:00", "message_id": "m-1",
            }
            other = {
                **valid, "talkroom_id": "2", "talkroom_url": "https://coconala.com/mypage/direct_message/2",
                "preview_sha256": "c" * 64, "last_message_identity_sha256": "d" * 64,
            }
            evidence = root / "reply-detector-new"
            evidence.mkdir(parents=True)
            (evidence / "marketplace-snapshot.json").write_text(json.dumps({
                "collector_mode": "direct-inbox-only",
                "inquiries": [valid, {**valid, "preview_sha256": "raw"}, other],
                "source_receipt": {"cards_count": 3, "coverage_complete": True},
            }), encoding="utf-8")
            rows = collector.previous_direct_snapshot(root, root / "current" / "live-dom")
            self.assertEqual(set(rows), {"2"})

    def test_previous_direct_snapshot_preserves_negotiation_intent(self):
        with tempfile.TemporaryDirectory() as root_name:
            root = Path(root_name)
            evidence = root / "reply-detector-old"
            evidence.mkdir()
            row = {
                "talkroom_id": "1", "talkroom_url": "https://coconala.com/mypage/direct_message/1",
                "preview_sha256": "a" * 64, "last_message_identity_sha256": "b" * 64,
                "last_message_side": "buyer", "reply_required": True, "next_action": "reply",
                "negotiation_intent": "question", "buyer_sent_at": "2026-08-12T00:00:00+00:00",
                "message_id": "m-1", "sending_unavailable": False,
            }
            (evidence / "marketplace-snapshot.json").write_text(json.dumps({
                "collector_mode": "direct-only",
                "source_receipt": {"coverage_complete": True, "cards_count": 1},
                "inquiries": [row],
            }))

            rows = collector.previous_direct_snapshot(root, root / "current" / "live-dom")

            self.assertEqual(rows["1"]["negotiation_intent"], "question")

    def test_latest_corrupt_or_missing_inquiries_snapshot_never_falls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            row = {
                "talkroom_id": "1", "talkroom_url": "https://coconala.com/mypage/direct_message/1",
                "preview_sha256": "a" * 64, "last_message_identity_sha256": "b" * 64,
                "last_message_side": "seller", "reply_required": False, "next_action": "observe",
                "seller_sent_at": "2026-08-10T00:00:00+00:00", "message_id": "m-1",
            }
            old = root / "gig-pass-old"; old.mkdir(parents=True)
            (old / "marketplace-snapshot.json").write_text(json.dumps({
                "inquiries": [row], "source_receipt": {"cards_count": 1, "coverage_complete": True},
            }), encoding="utf-8")
            latest = root / "reply-detector-new"; latest.mkdir(parents=True)
            latest_file = latest / "marketplace-snapshot.json"
            latest_file.write_text("{broken", encoding="utf-8")
            os.utime(old / "marketplace-snapshot.json", (100, 100)); os.utime(latest_file, (200, 200))
            current = root / "reply-detector-current" / "live-dom"
            self.assertEqual(collector.previous_direct_snapshot(root, current), {})
            latest_file.write_text(json.dumps({"source_receipt": {"cards_count": 1, "coverage_complete": True}}), encoding="utf-8")
            os.utime(latest_file, (300, 300))
            self.assertEqual(collector.previous_direct_snapshot(root, current), {})
            latest_file.write_text(json.dumps({
                "inquiries": [row, row],
                "source_receipt": {"cards_count": 2, "coverage_complete": True},
            }), encoding="utf-8")
            os.utime(latest_file, (400, 400))
            self.assertEqual(collector.previous_direct_snapshot(root, current), {})
            empty = {**row, "last_message_side": "", "reply_required": False, "next_action": "observe"}
            latest_file.write_text(json.dumps({
                "inquiries": [empty],
                "source_receipt": {"cards_count": 1, "coverage_complete": True},
            }), encoding="utf-8")
            os.utime(latest_file, (500, 500))
            self.assertEqual(collector.previous_direct_snapshot(root, current), {})

    def test_direct_inbox_reuses_unchanged_readback_and_counts_full_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current_dir = root / "reply-detector-current" / "live-dom"
            previous_dir = root / "gig-pass-old" / "live-dom"
            current_dir.mkdir(parents=True)
            previous_dir.mkdir(parents=True)
            previous_rows = [
                {
                    "talkroom_id": "1", "talkroom_url": "https://coconala.com/mypage/direct_message/1",
                    "title": "old", "preview_sha256": "a" * 64,
                    "last_message_identity_sha256": "b" * 64, "unread": False,
                    "last_message_side": "seller", "reply_required": False, "next_action": "observe",
                    "negotiation_intent": "unclear",
                    "seller_sent_at": "2026-08-10T00:00:00+00:00", "message_id": "m-1",
                    "thread_read_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "talkroom_id": "2", "talkroom_url": "https://coconala.com/mypage/direct_message/2",
                    "title": "old-2", "preview_sha256": "b" * 64,
                    "last_message_identity_sha256": "c" * 64, "unread": False,
                    "last_message_side": "seller", "reply_required": False, "next_action": "observe",
                    "negotiation_intent": "unclear",
                    "seller_sent_at": "2026-08-10T00:00:00+00:00", "message_id": "m-old-2",
                    "thread_read_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "talkroom_id": "3", "talkroom_url": "https://coconala.com/mypage/direct_message/3",
                    "title": "old-3", "preview_sha256": "e" * 64,
                    "last_message_identity_sha256": "f" * 64, "unread": False,
                    "last_message_side": "seller", "reply_required": False, "next_action": "observe",
                    "negotiation_intent": "unclear",
                    "seller_sent_at": "2026-08-10T00:00:00+00:00", "message_id": "m-old-3",
                    "thread_read_at": (datetime.now(timezone.utc) - timedelta(
                        seconds=collector.DIRECT_REVALIDATION_HORIZON_SECONDS + 1,
                    )).isoformat(),
                },
            ]
            (previous_dir.parent / "marketplace-snapshot.json").write_text(json.dumps({
                "collector_mode": "direct-inbox-only", "inquiries": previous_rows,
                "source_receipt": {"cards_count": 3, "coverage_complete": True},
            }), encoding="utf-8")
            args = mock.Mock(
                output=current_dir / "snapshot.json", evidence_dir=current_dir,
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only", talkroom_id=None, project_id=None,
            )
            room_url = "https://coconala.com/mypage/direct_message/2"
            list_dom = {
                "url": collector.MESSAGES_URL, "title": "メッセージ | マイページ | ココナラ",
                "container_present": True, "not_found_present": False, "error_present": False,
                "cards": [
                    {"talkroom_url": "https://coconala.com/mypage/direct_message/1", "title": "current", "unread": False, "preview_sha256": "f" * 64, "last_message_identity_sha256": "b" * 64},
                    {"talkroom_url": room_url, "title": "changed", "unread": False, "preview_sha256": "b" * 64, "last_message_identity_sha256": "d" * 64},
                    {"talkroom_url": "https://coconala.com/mypage/direct_message/3", "title": "stale", "unread": False, "preview_sha256": "e" * 64, "last_message_identity_sha256": "f" * 64},
                ], "cards_count": 3, "empty_state_present": False,
                "coverage_complete": True, "termination_reason": "fixed_point", "iterations": 2,
            }
            room_dom = {
                "url": room_url, "title": "メッセージ詳細 | ココナラ", "container_present": True,
                "not_found_present": False, "error_present": False, "own_user_path": "/users/seller",
                "messages": [{"message_id": "m-2", "author_path": "/users/buyer", "sent_at": "2026-08-10T00:00:00+00:00", "body": "changed"}],
            }
            room1_dom = {**room_dom, "url": "https://coconala.com/mypage/direct_message/1", "messages": []}
            opened = []

            class FakeTab:
                def __init__(self, _helper, url, **_kwargs):
                    self.ws = f"ws:{url}"; opened.append(url)
                def __enter__(self): return self
                def __exit__(self, *_args): return None

            def inspect_message(_ws, expression, expected_url, **_kwargs):
                if expected_url == collector.MESSAGES_URL:
                    return list_dom
                self.assertIs(expression, collector.DIRECT_MESSAGE_EXPRESSION)
                return room1_dom if expected_url.endswith("/1") else {**room_dom, "url": expected_url}

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=inspect_message),
                mock.patch.object(collector, "inspect_page_with_retry") as inspect_page,
            ):
                self.assertEqual(collector.main(), 0)
            snapshot = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual(opened, [
                collector.MESSAGES_URL,
                room_url,
            ])
            self.assertEqual(snapshot["thread_readback_count"], 1)
            self.assertEqual(snapshot["thread_reused_count"], 2)
            self.assertEqual(snapshot["thread_readback_count"] + snapshot["thread_reused_count"], 3)
            self.assertEqual(snapshot["inquiries"][0]["title"], "current")
            self.assertEqual(snapshot["inquiries"][0]["last_message_side"], "seller")
            self.assertEqual(snapshot["inquiries"][0]["next_action"], "semantic_pending")
            self.assertFalse(snapshot["inquiries"][1]["reply_required"])
            self.assertEqual(snapshot["inquiries"][1]["next_action"], "semantic_failed")
            self.assertEqual(snapshot["source_receipt"]["thread_revalidated_count"], 0)
            self.assertEqual(snapshot["source_receipt"]["thread_reused_count"], 2)
            self.assertEqual(snapshot["source_receipt"]["thread_changed_count"], 1)
            self.assertEqual(snapshot["source_receipt"]["thread_revalidation_limit"], 0)
            self.assertNotIn("preview-", json.dumps(snapshot))
            inspect_page.assert_not_called()

    def test_direct_message_event_emits_validator_state_tuple(self):
        url = "https://coconala.com/mypage/direct_message/42"
        common = {
            "url": url, "title": "メッセージ詳細 | ココナラ", "container_present": True,
            "not_found_present": False, "error_present": False, "own_user_path": "/users/seller",
        }
        buyer = collector.direct_message_event({
            **common,
            "messages": [{"message_id": "buyer-1", "author_path": "/users/buyer",
                           "sent_at": "2026-08-11T00:00:00+00:00", "body": "buyer"}],
        }, url)
        seller = collector.direct_message_event({
            **common,
            "messages": [{"message_id": "seller-1", "author_path": "/users/seller",
                           "sent_at": "2026-08-11T00:00:00+00:00", "body": "seller"}],
        }, url)
        self.assertEqual((buyer["reply_required"], buyer["next_action"]), (False, "semantic_failed"))
        self.assertEqual((seller["reply_required"], seller["next_action"]), (False, "semantic_failed"))

    def test_seller_readback_persists_bounded_identity_without_body(self):
        url = "https://coconala.com/mypage/direct_message/42"
        event = collector.direct_message_event({
            "url": url, "title": "メッセージ詳細 | ココナラ", "container_present": True,
            "not_found_present": False, "error_present": False, "own_user_path": "/users/seller",
            "messages": [{"author_path": "/users/seller", "sent_at": "2026-08-11T00:00:00+00:00", "body": "secret seller"}],
        }, url)
        self.assertEqual(event["last_message_side"], "seller")
        self.assertEqual(event["seller_sent_at"], "2026-08-11T00:00:00+00:00")
        self.assertEqual(event["stable_ordinal"], 0)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", event["message_sha256"]))
        self.assertNotIn("secret seller", json.dumps(event))

    def test_cached_readback_requires_nonempty_side_state_tuple(self):
        self.assertEqual(collector.DIRECT_REVALIDATION_BATCH_SIZE, 1)
        base = {
            "reply_required": True, "next_action": "reply", "buyer_sent_at": "2026-08-11T00:00:00+00:00",
            "message_id": "m-1",
        }
        self.assertFalse(collector._valid_direct_readback({**base, "last_message_side": "buyer"}))
        self.assertTrue(collector._valid_direct_readback({
            **base, "last_message_side": "buyer", "negotiation_intent": "question",
        }))
        self.assertTrue(collector._valid_direct_readback({
            **base, "last_message_side": "buyer", "negotiation_intent": "unknown",
            "reply_required": False, "next_action": "semantic_pending",
            "sending_unavailable": True, "reply_unavailable_reason": "counterparty_restricted",
        }))
        self.assertTrue(collector._valid_direct_readback({
            **base, "last_message_side": "buyer", "negotiation_intent": "considering",
            "reply_required": False, "next_action": "observe",
            "semantic_receipt": {"judgement": {
                "conversation_state": "considering", "next_action": "wait", "uncertainty": [],
            }},
        }))
        self.assertFalse(collector._valid_direct_readback({**base, "last_message_side": "seller"}))
        self.assertFalse(collector._valid_direct_readback({**base, "last_message_side": ""}))
        self.assertTrue(collector._valid_direct_readback({
            **base, "last_message_side": "seller", "reply_required": False, "next_action": "observe",
            "seller_sent_at": base["buyer_sent_at"],
        }))
        self.assertFalse(collector._valid_direct_readback({
            "last_message_side": "seller", "reply_required": False, "next_action": "observe", "message_id": "m-1",
        }))

    def test_pending_estimate_thread_order_uses_existing_outbox_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = collector.ConnectorOutbox(
                root / "outbox.sqlite3",
                SCRIPT.parents[1] / "config/connectors/coconala.json",
            )
            for index, thread_id in enumerate(("9949489", "10057717")):
                database.enqueue_estimate(
                    event_key=f"coconala:estimate:v1:{thread_id}:sha256_{'a' * 64}",
                    thread_id=thread_id,
                    thread_url=f"https://coconala.com/mypage/direct_message/{thread_id}",
                    observed_at=1786500000 + index,
                )

            self.assertEqual(
                collector.estimate_pending_thread_order(
                    root / "outbox.sqlite3",
                    SCRIPT.parents[1] / "config/connectors/coconala.json",
                ),
                {"9949489": 0, "10057717": 1},
            )

    def test_legacy_semantic_cleanup_precedes_unchanged_terminal_buyer_revalidation(self):
        legacy = {
            "last_message_side": "seller", "next_action": "semantic_pending",
            "semantic_failure": "semantic_receipt_pending",
        }
        terminal_buyer = {
            "last_message_side": "buyer", "next_action": "officially_unrepliable",
        }

        self.assertLess(
            collector._direct_revalidation_priority(legacy, None, False),
            collector._direct_revalidation_priority(terminal_buyer, None, False),
        )
        self.assertEqual(collector._direct_revalidation_priority(legacy, 0, False), 0)
        self.assertEqual(collector._direct_revalidation_priority(legacy, None, True), 1)

    def test_direct_inbox_only_never_opens_paid_or_work_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only",
                talkroom_id=None, project_id=None,
            )
            empty_dom = {
                "url": collector.MESSAGES_URL,
                "title": "メッセージ | マイページ | ココナラ",
                "container_present": True,
                "cards": [],
                "empty_state_present": True,
                "coverage_complete": True,
                "termination_reason": "empty_state",
                "iterations": 2,
            }
            opened_urls = []

            class FakeTab:
                def __init__(self, _helper, url, **_kwargs):
                    self.ws = "ws"
                    opened_urls.append(url)

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return None

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", return_value=empty_dom),
                mock.patch.object(collector, "inspect_page_with_retry") as inspect_page,
            ):
                self.assertEqual(collector.main(), 0)

            self.assertEqual(opened_urls, [collector.MESSAGES_URL])
            inspect_page.assert_not_called()
            self.assertNotIn(collector.B1_INBOX_URL, opened_urls)
            self.assertNotIn(collector.OPEN_ORDERS_URL, opened_urls)
            self.assertNotIn(collector.REQUESTS_URL, opened_urls)
            self.assertNotIn(collector.RETAINER_APPLICATIONS_URL, opened_urls)

    def test_direct_inbox_only_accepts_semantic_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only",
                talkroom_id=None, project_id=None,
            )
            dom = {
                "url": collector.MESSAGES_URL,
                "title": "メッセージ | マイページ | ココナラ",
                "container_present": True,
                "cards": [],
                "cards_count": 0,
                "empty_state_present": True,
                "coverage_complete": True,
                "termination_reason": "empty_state",
                "iterations": 2,
            }
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_message_page", return_value=dom),
                mock.patch.object(collector, "DefaultTab"),
            ):
                self.assertEqual(collector.main(), 0)

            snapshot = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["inquiries"], [])
            self.assertTrue(snapshot["source_receipt"]["coverage_complete"])
            self.assertEqual(snapshot["source_receipt"]["termination_reason"], "empty_state")

    def test_direct_inbox_only_fails_closed_when_coverage_is_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only",
                talkroom_id=None, project_id=None,
            )
            dom = {
                "url": collector.MESSAGES_URL,
                "title": "メッセージ | マイページ | ココナラ",
                "container_present": True,
                "cards": [],
                "cards_count": 0,
                "empty_state_present": False,
                "coverage_complete": False,
                "termination_reason": "fixed_point",
                "iterations": 20,
            }
            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_message_page", return_value=dom),
                mock.patch.object(collector, "DefaultTab"),
            ):
                self.assertNotEqual(collector.main(), 0)

            self.assertFalse(args.output.exists())
            failure = json.loads((args.evidence_dir / "snapshot-failure.json").read_text())
            self.assertEqual(failure["error"], "collector_unhealthy:inbox_coverage_incomplete")
            self.assertEqual(failure["source_receipt"]["source"], "direct_inbox")
            self.assertFalse(failure["source_receipt"]["coverage_complete"])
            self.assertEqual(failure["source_receipt"]["iterations"], 20)

    def test_inbox_coverage_accepts_explicit_genuine_empty(self):
        result = collector.validate_inbox_coverage({
            "cards": [], "empty_state_present": True,
            "coverage_complete": True, "termination_reason": "empty_state",
        })
        self.assertEqual(result["cards_count"], 0)
        self.assertTrue(result["coverage_complete"])

    def test_inbox_coverage_accepts_deduped_complete_cards(self):
        result = collector.validate_inbox_coverage({
            "cards": [
                {"talkroom_url": "https://coconala.com/mypage/direct_message/1"},
                {"talkroom_url": "https://coconala.com/mypage/direct_message/1"},
                {"talkroom_url": "https://coconala.com/mypage/direct_message/2"},
            ], "coverage_complete": True, "termination_reason": "fixed_point",
            "iterations": 2,
        })
        self.assertEqual(result["cards_count"], 2)

    def test_paginated_inbox_contract_covers_30_30_24_unique_cards(self):
        pages = [
            [{"talkroom_url": f"https://coconala.com/mypage/direct_message/{i}"}
             for i in range(start, start + size)]
            for start, size in ((0, 30), (30, 30), (60, 24))
        ]
        cards = collector.dedupe_inbox_cards([card for page in pages for card in page])
        result = collector.validate_inbox_coverage({
            "cards": cards, "cards_count": len(cards),
            "coverage_complete": True, "termination_reason": "pagination_end",
            "pagination_next_present": False,
            "pagination_container_present": True,
            "pagination_current_present": True,
            "pagination_terminal_proven": True,
            "pagination_pages": 3,
            "page_counts": [30, 30, 24],
        })

        self.assertEqual([len(page) for page in pages], [30, 30, 24])
        self.assertEqual(result["cards_count"], 84)
        self.assertEqual(result["termination_reason"], "pagination_end")
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(result["pagination_pages"], 3)
        self.assertEqual(result["page_counts"], [30, 30, 24])
        self.assertIn(".c-pagination", collector.INBOX_COVERAGE_EXPRESSION)
        self.assertIn(".pagination-link-current", collector.INBOX_COVERAGE_EXPRESSION)
        self.assertIn("pagination-next", collector.INBOX_COVERAGE_EXPRESSION)
        self.assertIn("pagination_end", collector.INBOX_COVERAGE_EXPRESSION)

    def test_inbox_coverage_requires_explicit_last_page_proof(self):
        cards = [
            {"talkroom_url": f"https://coconala.com/mypage/direct_message/{i}"}
            for i in range(60)
        ]
        base = {
            "cards": cards,
            "cards_count": 60,
            "coverage_complete": True,
            "termination_reason": "pagination_end",
            "pagination_next_present": False,
            "pagination_container_present": True,
            "pagination_current_present": True,
            "pagination_pages": 2,
            "page_counts": [30, 30],
            "pagination_current_page": 2,
            "pagination_highest_page": 3,
        }
        for candidate in (base, {**base, "pagination_terminal_proven": True}):
            with self.assertRaises(collector.CollectorUnhealthy):
                collector.validate_inbox_coverage(candidate)
        short_page = {
            **base,
            "cards": cards[:54],
            "cards_count": 54,
            "pagination_pages": 2,
            "page_counts": [30, 24],
            "pagination_terminal_proven": True,
        }
        with self.assertRaises(collector.CollectorUnhealthy):
            collector.validate_inbox_coverage(short_page)

    def test_direct_coverage_executes_pagination_and_fails_closed_on_missing_next(self):
        if shutil.which("node") is None:
            self.skipTest("node is required for the recorded DOM contract")
        expression = json.dumps(collector.DIRECT_INBOX_COVERAGE_EXPRESSION)

        def run(states, transient_missing=False):
            script = f'''const expression={expression};
const states={json.dumps(states)};let page=0,missingLookups=0;
const location={{href:'https://coconala.com/message',pathname:'/message',origin:'https://coconala.com'}};
const state=()=>states[page];
const current=()=>{{const text=String(state().current);return {{innerText:text,textContent:text,getAttribute:()=>null}}}};
const next=()=>{{if(!state().next)return null;if({str(transient_missing).lower()}&&page===1&&missingLookups++<3)return null;return {{disabled:false,getAttribute:n=>n==='aria-disabled'?'false':null,click:()=>{{page++;location.href='https://coconala.com/message?page='+String(page+1)}}}}}};
const root={{scrollHeight:0,innerText:'Inbox',querySelector:()=>null}};
const paginator={{querySelector:s=>s.includes('pagination-link-current')?current():next(),querySelectorAll:()=>state().numbers.map(n=>({{innerText:String(n),textContent:String(n),getAttribute:()=>null}}))}};
const document={{body:root,querySelector:s=>s.startsWith('main.')?root:s==='.c-pagination'?paginator:s.includes('pagination-link-current')?current():s.includes('pagination-next')?next():null,querySelectorAll:s=>s.includes('c-messageItemWrap')?Array.from({{length:state().count}},(_,i)=>({{href:'https://coconala.com/mypage/direct_message/'+String(state().start+i),innerText:'preview-'+String(state().start+i),querySelector:()=>null,__vue__:{{_props:{{message:{{directMessagesRoomId:state().start+i,fromUserId:7,createdAt:1700000000000+state().start+i,body:'body-'+String(state().start+i),unreadCount:0}}}}}}}})):[]}};
const nodeCrypto=require('crypto');globalThis.location=location;globalThis.document=document;globalThis.window={{scrollTo:()=>{{}}}};globalThis.crypto={{subtle:{{digest:async(_algorithm,data)=>nodeCrypto.createHash('sha256').update(Buffer.from(data)).digest()}}}};globalThis.setTimeout=fn=>{{fn();return 0}};
(async()=>process.stdout.write(await eval(expression)))().catch(error=>{{console.error(error);process.exit(1)}});'''
            completed = subprocess.run(
                ["node", "-e", script], capture_output=True, text=True, check=True,
            )
            return json.loads(completed.stdout)

        complete = run([
            {"count": 30, "start": 0, "next": True, "current": 1, "numbers": [1, 2, 3]},
            {"count": 30, "start": 30, "next": True, "current": 2, "numbers": [1, 2, 3]},
            {"count": 24, "start": 60, "next": False, "current": 3, "numbers": [1, 2, 3]},
        ], transient_missing=True)
        self.assertEqual(complete["cards_count"], 84)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", card["preview_sha256"]) for card in complete["cards"]))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", card["last_message_identity_sha256"]) for card in complete["cards"]))
        self.assertNotIn('"preview":', json.dumps(complete))
        self.assertTrue(complete["coverage_complete"])

        incomplete = run([
            {"count": 30, "start": 0, "next": True, "current": 1, "numbers": [1, 2, 3]},
            {"count": 30, "start": 30, "next": False, "current": 2, "numbers": [1, 2, 3]},
        ])
        self.assertFalse(incomplete["coverage_complete"])

        short_incomplete = run([
            {"count": 30, "start": 0, "next": True, "current": 1, "numbers": [1, 2, 3]},
            {"count": 24, "start": 30, "next": False, "current": 2, "numbers": [1, 2, 3]},
        ])
        self.assertFalse(short_incomplete["coverage_complete"])

    def test_inbox_coverage_rejects_pagination_end_without_terminal_proof(self):
        cards = [
            {"talkroom_url": f"https://coconala.com/mypage/direct_message/{i}"}
            for i in range(30)
        ]
        with self.assertRaises(collector.CollectorUnhealthy):
            collector.validate_inbox_coverage({
                "cards": cards,
                "cards_count": 30,
                "coverage_complete": True,
                "termination_reason": "pagination_end",
                "pagination_next_present": False,
                "pagination_pages": 1,
                "page_counts": [30],
            })

    def test_inbox_coverage_rejects_fixed_point_while_next_page_exists(self):
        with self.assertRaises(collector.CollectorUnhealthy):
            collector.validate_inbox_coverage({
                "cards": [{"talkroom_url": "https://coconala.com/mypage/direct_message/1"}],
                "cards_count": 1,
                "coverage_complete": True,
                "termination_reason": "fixed_point",
                "pagination_next_present": True,
            })

    def test_direct_and_b1_coverage_routes_are_explicitly_separate(self):
        self.assertIs(
            collector.coverage_expression_for_route(collector.MESSAGES_URL),
            collector.INBOX_COVERAGE_EXPRESSION,
        )
        self.assertIs(
            collector.coverage_expression_for_route(f"{collector.MESSAGES_URL}?page=2"),
            collector.INBOX_COVERAGE_EXPRESSION,
        )
        self.assertIs(
            collector.coverage_expression_for_route(collector.B1_INBOX_URL),
            collector.B1_INBOX_COVERAGE_EXPRESSION,
        )
        self.assertIn("fromMyPage", collector.INBOX_COVERAGE_EXPRESSION)
        self.assertIn("a[href*='/talkrooms/']", collector.B1_MESSAGES_EXPRESSION)
        self.assertNotIn(
            "a.c-messageItemWrap[href*='/mypage/direct_message/']",
            collector.B1_MESSAGES_EXPRESSION,
        )

    def test_inbox_coverage_rejects_rotating_virtualized_ids(self):
        self.assertIn("Map", collector.INBOX_COVERAGE_EXPRESSION)
        self.assertIn("scrollHeight", collector.INBOX_COVERAGE_EXPRESSION)
        rounds = [
            [{"talkroom_url": f"https://coconala.com/mypage/direct_message/{i}"} for i in range(3)],
            [{"talkroom_url": f"https://coconala.com/mypage/direct_message/{i}"} for i in range(2, 5)],
        ]
        self.assertEqual(
            len(collector.dedupe_inbox_cards(rounds[0] + rounds[1] + rounds[0])), 5,
        )

    def test_inbox_coverage_ignores_unrelated_empty_widget(self):
        with self.assertRaises(collector.CollectorUnhealthy):
            collector.validate_inbox_coverage({
                "cards": [], "empty_state_present": False,
                "coverage_complete": True, "termination_reason": "fixed_point",
            })

    def test_inbox_coverage_receipt_rejects_count_mismatch(self):
        with self.assertRaises(collector.CollectorUnhealthy):
            collector.validate_inbox_coverage({
                "cards": [{"talkroom_url": "https://coconala.com/mypage/direct_message/1"}],
                "cards_count": 0, "coverage_complete": True,
                    "termination_reason": "fixed_point",
            })

    def test_previous_coverage_count_reads_only_success_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "gig-pass-old" / "live-dom"; good.mkdir(parents=True)
            (good / "direct-inbox-route.json").write_text(json.dumps({
                "coverage_receipt": {"cards_count": 30, "coverage_complete": True},
            }), encoding="utf-8")
            self.assertEqual(collector.previous_coverage_count(root, root / "gig-pass-current" / "live-dom"), 30)

    def test_previous_coverage_count_reads_reply_detector_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "gig-pass-old" / "live-dom"; old.mkdir(parents=True)
            old_receipt = old / "direct-inbox-route.json"
            old_receipt.write_text(json.dumps({
                "coverage_receipt": {"cards_count": 30, "coverage_complete": True},
            }), encoding="utf-8")
            unrelated = root / "reply-detector-new" / "live-dom"; unrelated.mkdir(parents=True)
            unrelated_receipt = unrelated / "direct-inbox-route.json"
            unrelated_receipt.write_text(json.dumps({
                "coverage_receipt": {"cards_count": 99, "coverage_complete": True},
            }), encoding="utf-8")
            os.utime(old_receipt, (100, 100))
            os.utime(unrelated_receipt, (200, 200))

            self.assertEqual(
                collector.previous_coverage_count(
                    root, root / "gig-pass-current" / "live-dom",
                ),
                99,
            )

    def test_previous_coverage_count_is_none_without_success_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            failed = root / "gig-pass-failed" / "live-dom"; failed.mkdir(parents=True)
            (failed / "direct-inbox-route.json").write_text(json.dumps({
                "coverage_receipt": {"cards_count": 30, "coverage_complete": False},
            }), encoding="utf-8")
            self.assertIsNone(collector.previous_coverage_count(root, failed))

    def test_previous_success_receipt_rejects_current_semantic_empty_collapse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "gig-pass-old" / "live-dom"; old.mkdir(parents=True)
            (old / "direct-inbox-route.json").write_text(json.dumps({
                "coverage_receipt": {"cards_count": 30, "coverage_complete": True},
            }), encoding="utf-8")
            current = root / "gig-pass-current" / "live-dom"; current.mkdir(parents=True)
            previous = collector.previous_coverage_count(root, current)
            with self.assertRaises(collector.CollectorUnhealthy):
                collector.validate_inbox_coverage({
                    "cards": [], "cards_count": 0, "empty_state_present": True,
                    "coverage_complete": True, "termination_reason": "empty_state",
                }, previous_count=previous)

    def test_inbox_coverage_rejects_partial_or_known_collapse(self):
        for observed in (
            {"cards": [{"talkroom_url": "x"}], "coverage_complete": False},
            {"cards": [], "coverage_complete": True, "termination_reason": "fixed_point"},
        ):
            with self.subTest(observed=observed):
                with self.assertRaises(collector.CollectorUnhealthy):
                    collector.validate_inbox_coverage(observed, previous_count=30)

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

    def test_formal_delivery_control_disabled_reaches_talkroom_and_order_readback(self):
        # Regression for the incident where all three talkrooms showed
        # present=True checked=False disabled=True: the DOM read, the minimized talkroom
        # record, and the order the builder actually consumes must all carry this field,
        # not just the raw expression string.
        self.assertIn("formal_delivery_control_disabled", collector.TALKROOM_EXPRESSION)
        self.assertIn("formal_delivery_control_disabled", collector.TALKROOM_FULL_EXPRESSION)
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "formal_delivery_control_disabled": True,
            "messages": [],
        }, "42", "2026-07-22T00:00:00+00:00")
        self.assertIs(minimized["formal_delivery_control_disabled"], True)
        order = {"talkroom_id": "42"}
        collector.enrich_order(order, minimized, None)
        self.assertIs(order["formal_delivery_control_disabled"], True)

    def test_unsent_compose_draft_reaches_talkroom_and_order_readback(self):
        # Regression for talkroom 90000001: a 383-character question sat unsent in the
        # compose textarea and the loop had no field to see it. The DOM read, the
        # minimized talkroom record, and the order the builder consumes must all carry
        # compose_draft_length/compose_draft_text, not just the raw expression string.
        self.assertIn("compose_draft_length", collector.TALKROOM_EXPRESSION)
        self.assertIn("compose_draft_text", collector.TALKROOM_EXPRESSION)
        self.assertIn("compose_draft_length", collector.TALKROOM_FULL_EXPRESSION)
        self.assertIn("compose_draft_text", collector.TALKROOM_FULL_EXPRESSION)
        draft_text = "納品前に確認したいことがあります。" * 20
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/90000001",
            "transaction_state": "取引中",
            "compose_draft_length": len(draft_text),
            "compose_draft_text": draft_text,
            "messages": [],
        }, "90000001", "2026-07-22T00:00:00+00:00")
        self.assertEqual(minimized["compose_draft_length"], len(draft_text))
        self.assertEqual(minimized["compose_draft_text"], draft_text)
        order = {"talkroom_id": "90000001"}
        collector.enrich_order(order, minimized, None)
        self.assertEqual(order["compose_draft_length"], len(draft_text))
        self.assertEqual(order["compose_draft_text"], draft_text)

    def test_unsent_compose_draft_defaults_to_zero_length_when_absent(self):
        # Observation-only field: no compose draft present must not fabricate one.
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/1",
            "transaction_state": "取引中",
            "messages": [],
        }, "1", "2026-07-22T00:00:00+00:00")
        self.assertEqual(minimized["compose_draft_length"], 0)
        self.assertEqual(minimized["compose_draft_text"], "")

    def test_seller_sent_messages_reach_talkroom_and_order_readback(self):
        # Regression for talkroom 90000001: sample-game-guide-v1.docx was
        # delivered but the readback had no field to prove it was ever sent.
        # message_id/sent_at come from TALKROOM_FULL_EXPRESSION, already reused
        # verbatim by minimize_talkroom_dom -- no new selector, no new JS.
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/90000001",
            "transaction_state": "納品送付",
            "messages": [
                {"side": "buyer", "text": "お願いします", "attachments": []},
                {
                    "side": "seller",
                    "text": "納品しました。ご確認ください。",
                    "sent_at": "2026-08-08 10:00",
                    "attachments": [{"filename": "sample-game-guide-v1.docx"}],
                },
            ],
        }, "90000001", "2026-08-08T00:00:00+00:00")
        self.assertEqual(len(minimized["seller_sent_messages"]), 1)
        sent = minimized["seller_sent_messages"][0]
        self.assertEqual(sent["attachments"], ["sample-game-guide-v1.docx"])
        self.assertIn("納品しました", sent["text"])
        # sent_at_label: the DOM value is a screen label ("たった今" etc.), not a
        # parseable timestamp -- named accordingly (A3 review follow-up, A4 pass).
        self.assertEqual(sent["sent_at_label"], "2026-08-08 10:00")
        order = {"talkroom_id": "90000001"}
        collector.enrich_order(order, minimized, None)
        self.assertEqual(order["seller_sent_messages"], minimized["seller_sent_messages"])

    def test_seller_message_readback_hash_covers_full_paid_answer(self):
        message = "安全性を優先した購入相談です。" * 80
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/90000001",
            "transaction_state": "取引中",
            "messages": [{"side": "seller", "text": message, "attachments": []}],
        }, "90000001", "2026-08-12T00:00:00+00:00")

        sent = minimized["seller_sent_messages"][0]
        self.assertEqual(len(sent["text"]), 300)
        self.assertEqual(sent["text_sha256"], hashlib.sha256(message.encode()).hexdigest())

    def test_seller_sent_messages_are_sanitized_and_bounded_to_last_ten(self):
        messages = [
            {"side": "seller", "text": f"secret@example.com update {i}", "attachments": [
                {"filename": f"file-{i}.zip"},
            ]}
            for i in range(12)
        ]
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": messages,
        }, "42", "2026-08-08T00:00:00+00:00")
        self.assertEqual(len(minimized["seller_sent_messages"]), 10)
        self.assertEqual(
            [m["attachments"][0] for m in minimized["seller_sent_messages"]],
            [f"file-{i}.zip" for i in range(2, 12)],
        )
        self.assertNotIn("secret@example.com", json.dumps(minimized, ensure_ascii=False))

    def test_seller_sent_messages_default_to_empty_when_no_seller_messages(self):
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/1",
            "transaction_state": "取引中",
            "messages": [{"side": "buyer", "text": "hi", "attachments": []}],
        }, "1", "2026-07-22T00:00:00+00:00")
        self.assertEqual(minimized["seller_sent_messages"], [])

    def test_buyer_recent_messages_reach_talkroom_and_order_readback(self):
        # Gate: talkroom 90000002 -- the buyer sent a revision request with two
        # images (IMG_0001 / IMG_0002). A4 is the buyer-side mirror of A3, built
        # inside the same per-message loop, reusing safe_text/safe_filename.
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/90000002",
            "transaction_state": "取引中",
            "messages": [
                {
                    "side": "buyer",
                    "text": "修正をお願いします。",
                    "sent_at": "たった今",
                    "attachments": [
                        {"filename": "IMG_0001.jpeg"},
                        {"filename": "IMG_0002.jpeg"},
                    ],
                },
            ],
        }, "90000002", "2026-08-08T00:00:00+00:00")
        self.assertEqual(len(minimized["buyer_recent_messages"]), 1)
        sent = minimized["buyer_recent_messages"][0]
        self.assertEqual(sent["attachments"], ["IMG_0001.jpeg", "IMG_0002.jpeg"])
        self.assertIn("修正をお願いします", sent["text"])
        self.assertEqual(sent["sent_at_label"], "たった今")
        order = {"talkroom_id": "90000002"}
        collector.enrich_order(order, minimized, None)
        self.assertEqual(order["buyer_recent_messages"], minimized["buyer_recent_messages"])

    def test_buyer_recent_messages_are_sanitized_and_bounded_to_last_ten(self):
        messages = [
            {"side": "buyer", "text": f"secret@example.com update {i}", "attachments": [
                {"filename": f"file-{i}.zip"},
            ]}
            for i in range(12)
        ]
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": messages,
        }, "42", "2026-08-08T00:00:00+00:00")
        self.assertEqual(len(minimized["buyer_recent_messages"]), 10)
        self.assertEqual(
            [m["attachments"][0] for m in minimized["buyer_recent_messages"]],
            [f"file-{i}.zip" for i in range(2, 12)],
        )
        self.assertNotIn("secret@example.com", json.dumps(minimized, ensure_ascii=False))

    def test_buyer_recent_messages_default_to_empty_when_no_buyer_messages(self):
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/1",
            "transaction_state": "取引中",
            "messages": [{"side": "seller", "text": "hi", "attachments": []}],
        }, "1", "2026-07-22T00:00:00+00:00")
        self.assertEqual(minimized["buyer_recent_messages"], [])

    def test_buyer_formal_delivery_hold_uses_only_buyer_history_and_safe_reason(self):
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": [
                {"side": "seller", "text": "正式な納品をお願いします", "attachments": []},
                {"side": "buyer", "text": "正式な納品を取り消しお願いします", "attachments": []},
            ],
        }, "42", "2026-08-10T00:00:00+00:00")
        self.assertIs(minimized["buyer_formal_delivery_hold"], True)
        self.assertEqual(
            minimized["buyer_formal_delivery_hold_reason"],
            "buyer_explicit_formal_delivery_hold",
        )
        self.assertNotIn("正式な納品を取り消しお願いします", minimized["buyer_formal_delivery_hold_reason"])
        order = {"talkroom_id": "42"}
        collector.enrich_order(order, minimized, None)
        self.assertIs(order["buyer_formal_delivery_hold"], True)
        self.assertEqual(
            order["buyer_formal_delivery_hold_reason"],
            "buyer_explicit_formal_delivery_hold",
        )

    def test_later_buyer_formal_delivery_request_releases_hold_but_seller_does_not(self):
        held = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": [
                {"side": "buyer", "text": "正式納品しないでください", "attachments": []},
                {"side": "seller", "text": "正式納品してください", "attachments": []},
            ],
        }, "42", "2026-08-10T00:00:00+00:00")
        self.assertIs(held["buyer_formal_delivery_hold"], True)

        released = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/42",
            "transaction_state": "取引中",
            "messages": [
                {"side": "buyer", "text": "正式納品しないでください", "attachments": []},
                {"side": "seller", "text": "正式納品してください", "attachments": []},
                {"side": "buyer", "text": "正式な納品をお願いします", "attachments": []},
            ],
        }, "42", "2026-08-10T00:00:00+00:00")
        self.assertIs(released["buyer_formal_delivery_hold"], False)
        self.assertIsNone(released["buyer_formal_delivery_hold_reason"])

    def test_room_contract_kind_marks_the_subscription_control_as_subscription(self):
        # Gate: talkroom 90000004 (買い手C). Measured 2026-08-07 production DOM: the
        # room shows "定期購入" / "定期購入 1回目" / "定期購入を終了する" and no step
        # bar, so transaction_state reads "unknown" the same as it always does on this
        # room. subscription_control_present (TALKROOM_FULL_EXPRESSION's own selector,
        # reused verbatim from coconala_formal_delivery_browser.py's state_expression)
        # is the only thing that tells this room apart from a stuck one-shot room.
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/90000004",
            "transaction_state": "unknown",
            "subscription_control_present": True,
            "messages": [],
        }, "90000004", "2026-08-08T00:00:00+00:00")
        self.assertEqual(minimized["room_contract_kind"], "subscription")
        order = {"talkroom_id": "90000004"}
        collector.enrich_order(order, minimized, None)
        self.assertEqual(order["room_contract_kind"], "subscription")

    def test_room_contract_kind_marks_a_real_transaction_state_as_one_shot(self):
        # Talkrooms 90000001 / 90000002: a real (non-"unknown") transaction_state only
        # ever appears with the step bar a 定期購入 room never shows.
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/90000001",
            "transaction_state": "取引中",
            "subscription_control_present": False,
            "messages": [],
        }, "90000001", "2026-08-08T00:00:00+00:00")
        self.assertEqual(minimized["room_contract_kind"], "one_shot")
        order = {"talkroom_id": "90000001"}
        collector.enrich_order(order, minimized, None)
        self.assertEqual(order["room_contract_kind"], "one_shot")

    def test_room_contract_kind_defaults_to_unknown_when_neither_signal_present(self):
        # No subscription control AND no step bar (transaction_state absent/unknown,
        # e.g. before TALKROOM_EXPRESSION's step-bar wait resolves) -- fail closed
        # rather than guess.
        minimized = collector.minimize_talkroom_dom({
            "url": "https://coconala.com/talkrooms/1",
            "messages": [],
        }, "1", "2026-07-22T00:00:00+00:00")
        self.assertEqual(minimized["room_contract_kind"], "unknown")
        order = {"talkroom_id": "1"}
        collector.enrich_order(order, minimized, None)
        self.assertEqual(order["room_contract_kind"], "unknown")

    def test_minimized_talkroom_drops_text_secrets_and_keeps_safe_buyer_attachment_metadata(self):
        raw = {
            "url": "https://coconala.com/talkrooms/90000010",
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
        minimized = collector.minimize_talkroom_dom(raw, "90000010", "2026-07-21T11:00:00+00:00")
        serialized = json.dumps(minimized, ensure_ascii=False)
        for secret in ("secret@example.com", "line.me", "TOPSECRET", "PRIVATE"):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("body", minimized)
        self.assertNotIn("messages", minimized)
        self.assertEqual([a["filename"] for a in minimized["buyer_attachments"]], ["repair.mcaddon", "error screenshot.png"])
        self.assertEqual(minimized["buyer_attachments"][0]["download_reference"], "/uploaded_files/42/download")
        self.assertTrue(minimized["buyer_feedback_pending_artifact"])
        # A4: buyer text is now surfaced (sanitized) via buyer_recent_messages --
        # the plain-text body is the point of that field; only secrets (above) drop.
        self.assertIn("エラーです", minimized["buyer_recent_messages"][0]["text"])

    def test_latest_paid_buyer_reply_is_idempotently_persisted_only_in_project_requirements(self):
        raw = {
            "url": "https://coconala.com/talkrooms/90000000",
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
                raw, "90000000", projects, "2026-07-23T01:00:00+00:00",
            )
            self.assertIsNotNone(first)
            path = Path(first["requirements_path"])
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["source"], "latest_buyer_reply_after_artifact")
            self.assertEqual(payload["project_id"], "90000000")
            self.assertEqual(payload["talkroom_id"], "90000000")
            self.assertIn("財布・カードケース・小物", payload["feedback_text"])
            self.assertNotIn("secret@example.com", path.read_text(encoding="utf-8"))
            self.assertNotIn("TOPSECRET", path.read_text(encoding="utf-8"))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

            second = collector.persist_latest_paid_buyer_reply(
                raw, "90000000", projects, "2026-07-23T02:00:00+00:00",
            )
            self.assertEqual(second["feedback_sha256"], first["feedback_sha256"])
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

            minimized = collector.minimize_talkroom_dom(
                raw, "90000000", "2026-07-23T02:00:00+00:00",
            )
            serialized = json.dumps(minimized, ensure_ascii=False)
            # A4: buyer text now also reaches buyer_recent_messages in the live
            # queue snapshot, not just the project_requirements sidecar -- but
            # secrets inside it (email, token URL) must still never survive.
            self.assertIn("財布", minimized["buyer_recent_messages"][0]["text"])
            self.assertNotIn("secret@example.com", serialized)
            self.assertNotIn("TOPSECRET", serialized)

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
        # A4: buyer_recent_messages is the one field designed to carry raw
        # (sanitized) buyer text. The narrower invariant this test guards is
        # that agreement stays a boolean flag elsewhere, not text smuggled in.
        without_readback = {k: v for k, v in minimized.items() if k != "buyer_recent_messages"}
        self.assertNotIn("確認済み", json.dumps(without_readback, ensure_ascii=False))

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

    def test_hidden_failure_diagnostic_is_bounded_sanitized_and_owner_only(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence"
            raw = {
                "url": "https://coconala.com/message?token=SECRET",
                "title": "メッセージ | ココナラ",
                "ready_state": "complete",
                "body_text": "x" * 8192,
                "body_text_overflow": True,
                "selector_counts": {"direct_message_links": 88, "message_container": 1},
                "resources": [{
                    "url": "https://coconala.com/api/message?auth=SECRET",
                    "initiator_type": "fetch", "duration_ms": 12.5,
                }],
            }

            async def fake_call(_ws, _request_id, method, _params, _sink=None):
                if method == "Runtime.evaluate":
                    return {"result": {"value": json.dumps(raw)}}
                if method == "Page.captureScreenshot":
                    return {"data": "iVBORw0KGgo="}
                self.fail(method)

            with mock.patch.object(collector, "call", side_effect=fake_call):
                asyncio.run(collector._capture_failure_diagnostic_on_ws(
                    "ws", evidence, RuntimeError("collector_unhealthy:unexpected_title"),
                ))

            diagnostic = json.loads((evidence / "failure-diagnostic.json").read_text())
            self.assertEqual(diagnostic["url"], "https://coconala.com/message")
            self.assertTrue(diagnostic["body_text_overflow"])
            self.assertEqual(len(diagnostic["body_text"]), 8192)
            self.assertEqual(diagnostic["selector_counts"]["direct_message_links"], 88)
            self.assertEqual(
                diagnostic["resources"][0]["url"], "https://coconala.com/api/message",
            )
            serialized = json.dumps(diagnostic, ensure_ascii=False)
            self.assertNotIn("SECRET", serialized)
            self.assertEqual(
                (evidence / "failure-screenshot.png").read_bytes(), b"\x89PNG\r\n\x1a\n",
            )
            self.assertEqual(os.stat(evidence).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(evidence / "failure-diagnostic.json").st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(evidence / "failure-screenshot.png").st_mode & 0o777, 0o600)

    def test_failure_diagnostic_rejects_malformed_or_non_png_screenshot(self):
        async def fake_call(_ws, _request_id, method, _params, _sink=None):
            if method == "Runtime.evaluate":
                return {"result": {"value": json.dumps({})}}
            if method == "Page.captureScreenshot":
                return {"data": "%%%"}
            self.fail(method)

        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence"
            with mock.patch.object(collector, "call", side_effect=fake_call):
                with self.assertRaisesRegex(RuntimeError, "failure screenshot invalid"):
                    asyncio.run(collector._capture_failure_diagnostic_on_ws(
                        "ws", evidence, RuntimeError("collector failed"),
                    ))
            self.assertTrue((evidence / "failure-diagnostic.json").exists())
            self.assertFalse((evidence / "failure-screenshot.png").exists())

    def test_direct_inbox_failure_captures_diagnostic_without_masking_original_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only",
                talkroom_id=None, project_id=None,
            )

            class FakeTab:
                ws = "ws"
                def __init__(self, *_args, **_kwargs): pass
                def __enter__(self): return self
                def __exit__(self, *_args): return None

            async def inspect_failure(*_args, **_kwargs):
                raise collector.CollectorUnhealthy("inbox_coverage_incomplete")

            captured = []
            async def capture(_ws, evidence_dir, error):
                captured.append((evidence_dir, str(error)))
                raise RuntimeError("diagnostic transport failed")

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=inspect_failure),
                mock.patch.object(collector, "capture_failure_diagnostic", side_effect=capture),
            ):
                self.assertNotEqual(collector.main(), 0)

            failure = json.loads((args.evidence_dir / "snapshot-failure.json").read_text())
            self.assertEqual(failure["error"], "collector_unhealthy:inbox_coverage_incomplete")
            self.assertEqual(captured, [(args.evidence_dir, "collector_unhealthy:inbox_coverage_incomplete")])

    def test_direct_inbox_post_read_validation_failure_is_captured_before_tab_closes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = mock.Mock(
                output=root / "snapshot.json", evidence_dir=root / "evidence",
                cdp_helper=Path("helper"), projects_root=root / "projects",
                hidden_no_screenshot=True, mode="direct-inbox-only",
                talkroom_id=None, project_id=None,
            )
            lifecycle = []

            class FakeTab:
                ws = "ws"
                def __init__(self, *_args, **_kwargs): pass
                def __enter__(self): lifecycle.append("open"); return self
                def __exit__(self, *_args): lifecycle.append("closed"); return None

            async def inspect_success(*_args, **_kwargs):
                return {
                    "url": collector.MESSAGES_URL, "title": "wrong title",
                    "container_present": True, "cards": [], "cards_count": 0,
                    "empty_state_present": True, "coverage_complete": True,
                    "termination_reason": "empty_state", "iterations": 2,
                }

            async def capture(_ws, _evidence_dir, error):
                lifecycle.append(f"capture:{error}")

            with (
                mock.patch.object(collector, "argument_parser", return_value=mock.Mock(
                    parse_args=mock.Mock(return_value=args))),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=inspect_success),
                mock.patch.object(collector, "capture_failure_diagnostic", side_effect=capture),
            ):
                self.assertNotEqual(collector.main(), 0)

            self.assertEqual(lifecycle[0], "open")
            self.assertTrue(lifecycle[1].startswith("capture:collector_unhealthy:unexpected_title"))
            self.assertEqual(lifecycle[2], "closed")

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
            "talkroom_url": "https://coconala.com/talkrooms/90000000",
            "buyer": "buyer",
            "title": "SNS運用",
            "text": "実績 Makuake 126,000円\n2026/08/14\n取引中",
        }]})
        self.assertIsNone(orders[0]["price_jpy"])
        self.assertEqual(orders[0]["price_source"], "missing_structured_price")

    def test_order_uses_structured_price_label_before_message_preview_amount(self):
        orders = collector.orders_from_dom({"cards": [{
            "talkroom_url": "https://coconala.com/talkrooms/90000000",
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
            "talkroom_url": "https://coconala.com/talkrooms/90000000",
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

    def test_snapshot_capture_time_is_taken_after_all_dom_reads(self):
        start = datetime(2026, 8, 11, 1, 36, 56, tzinfo=timezone.utc)
        finish = start + timedelta(minutes=5)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "marketplace-snapshot.json"
            evidence = Path(temp) / "live-dom"
            args = mock.Mock(
                output=output,
                evidence_dir=evidence,
                cdp_helper=Path("helper"),
                hidden_no_screenshot=True,
            )
            parser = mock.Mock(parse_args=mock.Mock(return_value=args))
            writes = []

            class FakeTab:
                def __init__(self, *_args, **_kwargs):
                    self.ws = "ws"

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return None

            async def fake_message_page(_ws, _expression, expected_url):
                if expected_url == collector.B1_INBOX_URL:
                    return {
                        "url": expected_url,
                        "title": "メッセージ",
                        "not_found": False,
                        "cards": [],
                    }
                return {
                    "url": expected_url,
                    "title": "メッセージ",
                    "container_present": True,
                    "cards": [],
                }

            def fake_inspect(*_args, **_kwargs):
                return {"url": _args[1], "title": "", "cards": []}

            clock = mock.Mock()
            clock.now.side_effect = [start, finish]
            with (
                mock.patch.object(collector, "argument_parser", return_value=parser),
                mock.patch.object(collector, "secure_directory"),
                mock.patch.object(collector, "load_connector_manifest"),
                mock.patch.object(collector, "inspect_page_with_retry", side_effect=fake_inspect),
                mock.patch.object(collector, "DefaultTab", FakeTab),
                mock.patch.object(collector, "inspect_message_page", side_effect=fake_message_page),
                mock.patch.object(collector, "retainer_applications_from_dom", return_value=[]),
                mock.patch.object(collector, "atomic_json", side_effect=lambda path, value: writes.append((Path(path), value))),
                mock.patch.object(collector, "datetime", clock),
            ):
                self.assertEqual(collector.main(), 0)

        snapshot = next(value for path, value in writes if path == output)
        self.assertEqual(snapshot["captured_at"], finish.isoformat())
        self.assertNotEqual(snapshot["captured_at"], start.isoformat())
        self.assertEqual(clock.now.call_count, 2)

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
