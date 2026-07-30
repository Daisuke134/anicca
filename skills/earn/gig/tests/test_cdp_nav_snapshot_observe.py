from __future__ import annotations

import asyncio
import base64
import fcntl
import importlib.util
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import asynccontextmanager, redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cdp_nav_snapshot.py"
SPEC = importlib.util.spec_from_file_location("cdp_nav_snapshot", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FakeSocket:
    def __init__(
        self,
        final_url: str,
        *,
        application_form: bool = False,
        application_submission: bool = False,
        retainer_application_form: bool = False,
        retainer_application_submission: bool = False,
        retainer_completion_modal: bool = False,
        retainer_generated_message_modal: bool = False,
        proposal_text: str = "自動化ツールと手順書を納品します。",
        form_text: str = "",
    ):
        self.final_url = final_url
        self.application_form = application_form
        self.application_submission = application_submission
        self.retainer_application_form = retainer_application_form
        self.retainer_application_submission = retainer_application_submission
        self.retainer_completion_modal = retainer_completion_modal
        self.retainer_generated_message_modal = retainer_generated_message_modal
        self.proposal_text = proposal_text
        self.form_text = form_text
        self.application_submit_stage = 0
        self.pending: list[str] = []
        self.requests: list[dict] = []

    async def send(self, raw: str) -> None:
        request = json.loads(raw)
        self.requests.append(request)
        request_id = request["id"]
        method = request["method"]
        if method == "Page.navigate":
            if (
                self.retainer_completion_modal
                and self.application_submit_stage >= 3
            ):
                self.final_url = request["params"]["url"]
                self.retainer_completion_modal = False
            self.pending.extend([
                json.dumps({"id": request_id, "result": {}}),
                json.dumps({"method": "Page.loadEventFired", "params": {}}),
            ])
        elif method == "Runtime.evaluate":
            expression = request.get("params", {}).get("expression")
            if expression == "document.location.href":
                value = self.final_url
            elif "gig_public_marketplace_snapshot_v1" in str(expression):
                public_marketplace = self.final_url.startswith(
                    "https://coconala.com/requests"
                )
                value = json.dumps({
                    "url": self.final_url,
                    "title": "すべての単発の仕事を探す",
                    "public_marketplace": public_marketplace,
                    "public_text": (
                        "資料作成の仕事\n予算 30,000円\n応募する"
                        if public_marketplace
                        else None
                    ),
                    "opportunities": (
                        [{
                            "request_id": "5184001",
                            "bucket": "single",
                            "url": "https://coconala.com/requests/5184001",
                            "title": "資料作成の仕事",
                            "summary": "資料作成の仕事 予算30,000円",
                        }]
                        if public_marketplace
                        else []
                    ),
                    "has_next": public_marketplace,
                }, ensure_ascii=False)
            elif self.application_submission and "application_submit_state_v1" in str(expression):
                states = [
                    {
                        "url": self.final_url,
                        "title": "応募する | ココナラ",
                        "body": "提案内容\n提案額 3,000円\n納品予定日 2026/8/29\n確認する",
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": {"kind": "confirm", "x": 320, "y": 420},
                    },
                    {
                        "url": self.final_url,
                        "title": "応募内容を確認する | ココナラ",
                        "body": "応募内容を確認する\n応募する",
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": {"kind": "apply", "x": 320, "y": 420},
                    },
                    {
                        "url": self.final_url,
                        "title": "応募内容を確認する | ココナラ",
                        "body": "投稿前にご確認ください\n応募する",
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": {"kind": "modal_apply", "x": 320, "y": 420},
                    },
                    {
                        "url": "https://coconala.com/mypage/job_matching/applied/offers",
                        "title": "応募した仕事 | ココナラ",
                        "body": "応募しました",
                        "proposal_text": "",
                        "form_filled": False,
                        "validation_error": False,
                        "success": True,
                        "button": None,
                    },
                ]
                value = json.dumps(
                    states[min(self.application_submit_stage, len(states) - 1)],
                    ensure_ascii=False,
                )
            elif (
                self.retainer_application_submission
                and "retainer_application_submit_state_v1" in str(expression)
            ):
                if (
                    self.retainer_generated_message_modal
                    and "応募メッセージの確認" not in str(expression)
                ):
                    states = [{
                        "url": self.final_url,
                        "title": "応募する",
                        "body": self.form_text,
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": None,
                    }]
                elif self.retainer_generated_message_modal:
                    states = [
                        {
                            "url": self.final_url,
                            "title": "応募する",
                            "body": self.form_text,
                            "proposal_text": self.proposal_text,
                            "form_filled": True,
                            "validation_error": False,
                            "success": False,
                            "button": {
                                "kind": "generated_message_confirm",
                                "x": 320,
                                "y": 520,
                            },
                        },
                        {
                            "url": self.final_url,
                            "title": "応募内容を確認する",
                            "body": self.form_text,
                            "proposal_text": self.proposal_text,
                            "form_filled": True,
                            "validation_error": False,
                            "success": False,
                            "button": {"kind": "consent", "x": 180, "y": 360},
                        },
                        {
                            "url": self.final_url,
                            "title": "応募内容を確認する",
                            "body": self.form_text,
                            "proposal_text": self.proposal_text,
                            "form_filled": True,
                            "validation_error": False,
                            "success": False,
                            "button": {"kind": "apply", "x": 320, "y": 420},
                        },
                        {
                            "url": "https://coconala.com/mypage/job_matching/applied/outsource_applications",
                            "title": "応募・スカウト管理 | ココナラ",
                            "body": "",
                            "form_filled": False,
                            "validation_error": False,
                            "success": True,
                            "completion_modal": False,
                            "button": None,
                        },
                    ]
                else:
                    states = [
                    {
                        "url": self.final_url,
                        "title": "応募する",
                        "body": self.form_text,
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": {"kind": "confirm", "x": 320, "y": 420},
                    },
                    {
                        "url": self.final_url,
                        "title": "応募内容を確認する",
                        "body": self.form_text,
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": {"kind": "consent", "x": 180, "y": 360},
                    },
                    {
                        "url": self.final_url,
                        "title": "応募内容を確認する",
                        "body": self.form_text,
                        "proposal_text": self.proposal_text,
                        "form_filled": True,
                        "validation_error": False,
                        "success": False,
                        "button": {"kind": "apply", "x": 320, "y": 420},
                    },
                    {
                        "url": (
                            self.final_url
                            if self.retainer_completion_modal
                            else "https://coconala.com/mypage/job_matching/applied/outsource_applications"
                        ),
                        "title": (
                            "応募内容を確認する"
                            if self.retainer_completion_modal
                            else "応募・スカウト管理 | ココナラ"
                        ),
                        "body": (
                            "応募が完了しました！\nご応募ありがとうございます。"
                            if self.retainer_completion_modal
                            else ""
                        ),
                        "form_filled": False,
                        "validation_error": False,
                        "success": not self.retainer_completion_modal,
                        "completion_modal": (
                            self.retainer_completion_modal
                            and "body.includes('応募が完了しました！')"
                            in str(expression)
                        ),
                        "button": None,
                    },
                    ]
                value = json.dumps(
                    states[min(self.application_submit_stage, len(states) - 1)],
                    ensure_ascii=False,
                )
            elif self.application_form and "data[Offer][content]" in str(expression):
                value = json.dumps({
                    "url": self.final_url,
                    "title": "応募する | ココナラ",
                    "has_content": True,
                    "has_price": True,
                    "has_expire_date": True,
                    "has_confirm": True,
                }, ensure_ascii=False)
            elif (
                self.retainer_application_form
                and "desiredCompensation" in str(expression)
            ):
                value = json.dumps({
                    "url": self.final_url,
                    "title": "応募する",
                    "has_compensation": True,
                    "has_working_days": True,
                    "has_hours_start": True,
                    "has_hours_end": True,
                    "has_message": True,
                    "has_confirm": True,
                }, ensure_ascii=False)
            elif "document.body.innerText" in str(expression):
                value = "Rendered ground-truth body"
            else:
                value = f"{self.final_url}|||Talkroom"
            self.pending.append(json.dumps({
                "id": request_id,
                "result": {"result": {"value": value}},
            }))
        elif method == "Page.captureScreenshot":
            self.pending.append(json.dumps({
                "id": request_id,
                "result": {"data": base64.b64encode(b"png").decode("ascii")},
            }))
        elif method == "Input.dispatchMouseEvent":
            if (
                (self.application_submission or self.retainer_application_submission)
                and request.get("params", {}).get("type") == "mouseReleased"
            ):
                self.application_submit_stage += 1
            self.pending.append(json.dumps({"id": request_id, "result": {}}))
        else:
            self.pending.append(json.dumps({"id": request_id, "result": {}}))

    async def recv(self) -> str:
        return self.pending.pop(0)


class FakeConnection:
    def __init__(self, socket: FakeSocket):
        self.socket = socket

    async def __aenter__(self) -> FakeSocket:
        return self.socket

    async def __aexit__(self, *_: object) -> None:
        return None


class CdpObserveTargetTest(unittest.TestCase):
    def test_public_marketplace_route_scope_excludes_private_account_pages(
        self,
    ) -> None:
        for url in (
            "https://coconala.com/requests",
            "https://coconala.com/requests/categories/234?page=2",
            "https://coconala.com/requests/5184001",
            "https://coconala.com/job_matching/outsources",
            (
                "https://coconala.com/job_matching/outsources/"
                "01KYR8Y2F60ED5VH2KHDJEY7WS"
            ),
        ):
            self.assertTrue(module._is_public_marketplace_url(url), url)
        for url in (
            "https://coconala.com/mypage/dashboard",
            "https://coconala.com/talkrooms/101",
            "https://coconala.com/mypage/job_matching/applied/offers",
            "https://example.com/requests",
        ):
            self.assertFalse(module._is_public_marketplace_url(url), url)

    def test_submit_helper_matches_only_rendered_button_text(self) -> None:
        source = inspect.getsource(module._application_submit_state)

        self.assertIn(
            "(confirmCandidate.innerText||'').trim()==='確認する'",
            source,
        )
        self.assertIn(
            "(b.innerText||'').trim()==='応募する'",
            source,
        )
        self.assertNotIn("confirmCandidate.textContent", source)

    def test_submit_helper_skips_disabled_duplicate_application_buttons(self) -> None:
        source = inspect.getsource(module._application_submit_state)

        self.assertIn(
            "const modalApply=buttons.find(b=>visible(b)&&!b.disabled&&",
            source,
        )
        self.assertIn(
            "const apply=buttons.find(b=>visible(b)&&!b.disabled&&",
            source,
        )

    def test_submit_helper_accepts_live_form_without_legacy_offer_add_id(self) -> None:
        self.assertIn(
            'form[action^="/offers/add/"] button[type="submit"]',
            module.APPLICATION_CONFIRM_SELECTOR,
        )

    def test_retainer_submit_does_not_treat_buyer_copy_as_a_validation_error(self) -> None:
        source = inspect.getsource(module._retainer_application_submit_state)
        assert "body.includes('入力してください')" not in source
        assert "form_filled" in source

    def test_top_level_help_advertises_current_subcommands(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("open-application", result.stdout)
        self.assertIn("submit-application", result.stdout)
        self.assertIn("open-retainer-application", result.stdout)
        self.assertIn("submit-retainer-application", result.stdout)
        self.assertIn("observe", result.stdout)
        self.assertIn("probe-session", result.stdout)

    def test_hidden_target_has_no_window_and_is_closed_by_its_owner(self) -> None:
        browser = FakeSocket("about:blank")
        browser.pending = []

        async def browser_send(raw: str) -> None:
            request = json.loads(raw)
            browser.requests.append(request)
            if request["method"] == "Target.createTarget":
                browser.pending.append(json.dumps({
                    "id": request["id"],
                    "result": {"targetId": "hidden-target"},
                }))
            elif request["method"] == "Target.closeTarget":
                browser.pending.append(json.dumps({
                    "id": request["id"],
                    "result": {"success": True},
                }))

        browser.send = browser_send
        connect = mock.Mock(return_value=FakeConnection(browser))
        with (
            mock.patch.object(
                module, "_cdp_base", return_value="http://127.0.0.1:9222"
            ),
            mock.patch.object(module, "_browser_ws_url", return_value="ws://browser"),
            mock.patch.object(module.websockets, "connect", connect),
        ):
            async def exercise() -> str:
                async with module.hidden_page_target(
                    "https://coconala.com/mypage/dashboard"
                ) as ws_url:
                    return ws_url

            ws_url = asyncio.run(exercise())

        self.assertEqual(
            ws_url,
            "ws://127.0.0.1:9222/devtools/page/hidden-target",
        )
        create = next(
            row for row in browser.requests
            if row["method"] == "Target.createTarget"
        )
        self.assertEqual(create["params"], {
            "url": "https://coconala.com/mypage/dashboard",
            "hidden": True,
            "background": True,
        })
        self.assertEqual(
            [row["method"] for row in browser.requests],
            ["Target.createTarget", "Target.closeTarget"],
        )

    def test_reality_snapshot_uses_an_owned_hidden_target(self) -> None:
        expected_url = "https://coconala.com/mypage/services_lists"

        @asynccontextmanager
        async def hidden_target(url: str):
            self.assertEqual(url, expected_url)
            yield "ws://127.0.0.1:9222/devtools/page/hidden-target"

        with tempfile.TemporaryDirectory() as temp:
            page = FakeSocket(expected_url)
            connect = mock.Mock(return_value=FakeConnection(page))
            with (
                mock.patch.dict("os.environ", {"HOME": temp}),
                mock.patch.object(module, "hidden_page_target", hidden_target),
                mock.patch.object(module.websockets, "connect", connect),
            ):
                result = asyncio.run(module.navigate_and_snapshot(
                    "verify-hidden", "01", "ground-truth", expected_url, "",
                ))

            artifact = Path(result)
            self.assertEqual(artifact.suffix, ".json")
            evidence = json.loads(artifact.read_text())
            self.assertEqual(evidence["url"], expected_url)
            self.assertEqual(
                evidence["rendered_text"],
                "Rendered ground-truth body",
            )
            self.assertEqual(
                connect.call_args.args[0],
                "ws://127.0.0.1:9222/devtools/page/hidden-target",
            )

    def test_session_probe_is_hidden_and_detects_login_redirect(self) -> None:
        @asynccontextmanager
        async def hidden_target(url: str):
            yield "ws://127.0.0.1:9222/devtools/page/session-probe"

        with (
            mock.patch.object(module, "hidden_page_target", hidden_target),
            mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(
                    FakeSocket("https://coconala.com/login")
                ),
            ),
        ):
            result = asyncio.run(module.probe_session(
                "https://coconala.com/mypage/dashboard"
            ))

        self.assertTrue(result["logged_out"])
        self.assertEqual(result["final_url"], "https://coconala.com/login")

    def test_observe_reuses_exact_page_ws_and_writes_bounded_evidence(self) -> None:
        expected_url = "https://coconala.com/talkrooms/101"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "room.png"
            live_dom = root / "room.json"
            connect = mock.Mock(return_value=FakeConnection(FakeSocket(expected_url)))
            with mock.patch.object(module.websockets, "connect", connect):
                result = asyncio.run(module.observe_target(
                    "ws://127.0.0.1:9222/devtools/page/leased-target",
                    expected_url,
                    screenshot,
                    live_dom,
                ))

            self.assertEqual(result["url"], expected_url)
            self.assertEqual(screenshot.read_bytes(), b"png")
            self.assertEqual(json.loads(live_dom.read_text()), {
                "url": expected_url,
                "not_found": False,
                "observed": True,
                "title": "Talkroom",
            })
            self.assertEqual(connect.call_args.args[0], "ws://127.0.0.1:9222/devtools/page/leased-target")

    def test_observe_public_marketplace_exposes_bounded_cards_and_text(self) -> None:
        expected_url = "https://coconala.com/requests"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "requests.png"
            live_dom = root / "requests.json"
            connect = mock.Mock(
                return_value=FakeConnection(FakeSocket(expected_url))
            )
            with mock.patch.object(module.websockets, "connect", connect):
                result = asyncio.run(module.observe_target(
                    "ws://127.0.0.1:9222/devtools/page/leased-target",
                    expected_url,
                    screenshot,
                    live_dom,
                ))

            self.assertTrue(result["public_marketplace"])
            self.assertIn("資料作成", result["public_text"])
            self.assertEqual(result["opportunities"], [{
                "request_id": "5184001",
                "bucket": "single",
                "url": "https://coconala.com/requests/5184001",
                "title": "資料作成の仕事",
                "summary": "資料作成の仕事 予算30,000円",
            }])
            self.assertTrue(result["has_next"])
            self.assertEqual(json.loads(live_dom.read_text()), result)

    def test_observe_resolves_opaque_ws_from_code_owned_lease_handle(self) -> None:
        """A model cannot corrupt a WebSocket ID it never reads or copies."""
        exact_ws = (
            "ws://127.0.0.1:9223/devtools/page/"
            "A0Il1OZq-opaque-target-id"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            leases = root / "gig-leases.json"
            leases.write_text(json.dumps({
                "gig-42264-B2": {
                    "context_id": "context-1",
                    "target_id": "A0Il1OZq-opaque-target-id",
                    "ws": exact_ws,
                    "ts": 1785374663,
                },
            }), encoding="utf-8")
            observe = mock.AsyncMock(return_value={
                "url": "https://coconala.com/requests?sort=new&page=3",
                "not_found": False,
                "observed": True,
            })
            output = io.StringIO()
            with (
                mock.patch.dict(
                    os.environ,
                    {"CLOAK_CONTEXT_LEASES_FILE": str(leases)},
                ),
                mock.patch.object(module, "observe_target", observe),
                redirect_stdout(output),
            ):
                rc = module._observe_main([
                    "--lease",
                    "gig-42264-B2",
                    "--url",
                    "https://coconala.com/requests?sort=new&page=3",
                    "--screenshot",
                    str(root / "page.png"),
                    "--dom",
                    str(root / "page.json"),
                ])

            self.assertEqual(rc, 0)
            observe.assert_awaited_once_with(
                exact_ws,
                "https://coconala.com/requests?sort=new&page=3",
                root / "page.png",
                root / "page.json",
            )

    def test_open_application_form_uses_canonical_route_and_verifies_real_fields(self) -> None:
        request_id = "5170797"
        expected_url = "https://coconala.com/offers/add/5170797"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "application-form.png"
            evidence_path = root / "application-form.json"
            page = FakeSocket(expected_url, application_form=True)
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                result = asyncio.run(module.open_application_form(
                    "ws://127.0.0.1:9222/devtools/page/leased-target",
                    request_id,
                    screenshot,
                    evidence_path,
                ))

            navigate = next(
                row for row in page.requests
                if row["method"] == "Page.navigate"
            )
            self.assertEqual(navigate["params"]["url"], expected_url)
            self.assertTrue(result["form_verified"])
            self.assertEqual(result["url"], expected_url)
            self.assertEqual(screenshot.read_bytes(), b"png")
            self.assertEqual(
                json.loads(evidence_path.read_text()),
                {
                    "request_id": request_id,
                    "url": expected_url,
                    "title": "応募する | ココナラ",
                    "form_verified": True,
                    "fields": {
                        "content": True,
                        "price": True,
                        "expire_date": True,
                        "confirm": True,
                    },
                },
            )

    def test_submit_application_clicks_through_final_modal_before_writing_proof(self) -> None:
        request_id = "5174303"
        form_url = "https://coconala.com/offers/add/5174303"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "submitted.png"
            evidence_path = root / "submitted.json"
            page = FakeSocket(form_url, application_submission=True)
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                result = asyncio.run(module.submit_application(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    request_id,
                    screenshot,
                    evidence_path,
                    wait_seconds=0,
                    opportunity_brief="資料作成をチャットでお願いします。",
                ))

            released_clicks = [
                row for row in page.requests
                if row["method"] == "Input.dispatchMouseEvent"
                and row["params"]["type"] == "mouseReleased"
            ]
            self.assertEqual(len(released_clicks), 3)
            self.assertTrue(result["submit_verified"])
            self.assertTrue(result["applied_page_verified"])
            self.assertEqual(
                result["url"],
                "https://coconala.com/mypage/job_matching/applied/offers",
            )
            self.assertEqual(screenshot.read_bytes(), b"png")
            self.assertEqual(json.loads(evidence_path.read_text()), result)

    def test_submit_application_does_not_write_proof_before_applied_page(self) -> None:
        request_id = "5174303"
        form_url = "https://coconala.com/offers/add/5174303"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "submitted.png"
            evidence_path = root / "submitted.json"
            page = FakeSocket(form_url, application_form=True)
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                with self.assertRaisesRegex(RuntimeError, "submission_not_verified"):
                    asyncio.run(module.submit_application(
                        "ws://127.0.0.1:9223/devtools/page/leased-target",
                        request_id,
                        screenshot,
                        evidence_path,
                        wait_seconds=0,
                        opportunity_brief="資料作成をチャットでお願いします。",
                    ))

            self.assertFalse(screenshot.exists())
            self.assertFalse(evidence_path.exists())

    def test_submit_application_persists_intent_before_irreversible_click(self) -> None:
        request_id = "5170842"
        form_url = f"https://coconala.com/offers/add/{request_id}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "submitted.png"
            evidence_path = root / "submitted.json"
            intent_path = root / "submitted.intent.json"
            page = FakeSocket(form_url, application_submission=True)
            original_click = module._mouse_click
            click_count = 0

            async def lose_ack_after_final_click(ws, x, y, cid):
                nonlocal click_count
                click_count += 1
                result = await original_click(ws, x, y, cid)
                if click_count == 3:
                    raise RuntimeError("socket_lost_after_click")
                return result

            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ), mock.patch.object(
                module,
                "_mouse_click",
                side_effect=lose_ack_after_final_click,
            ):
                with self.assertRaisesRegex(RuntimeError, "socket_lost_after_click"):
                    asyncio.run(module.submit_application(
                        "ws://127.0.0.1:9223/devtools/page/leased-target",
                        request_id,
                        screenshot,
                        evidence_path,
                        wait_seconds=0,
                        opportunity_brief="資料作成をチャットでお願いします。",
                    ))

            self.assertFalse(screenshot.exists())
            self.assertFalse(evidence_path.exists())
            self.assertEqual(
                json.loads(intent_path.read_text()),
                {
                    "request_id": request_id,
                    "bucket": "single",
                    "url": f"https://coconala.com/requests/{request_id}",
                    "title": None,
                    "state": "prepared",
                },
            )

    def test_submit_application_blocks_unsupported_brief_before_any_click(self) -> None:
        request_id = "5173702"
        form_url = f"https://coconala.com/offers/add/{request_id}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "submitted.png"
            evidence_path = root / "submitted.json"
            policy_path = root / "submitted.eligibility.json"
            page = FakeSocket(
                form_url,
                application_submission=True,
                proposal_text=(
                    "転職活動を支援し、応募書類の改善案をお渡しします。"
                ),
            )
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "application_eligibility_rejected:"
                    "synchronous_live_presence_required",
                ):
                    asyncio.run(module.submit_application(
                        "ws://127.0.0.1:9223/devtools/page/leased-target",
                        request_id,
                        screenshot,
                        evidence_path,
                        wait_seconds=0,
                        opportunity_brief=(
                            "オンラインヒアリングにご協力いただける方を募集。"
                            "所要時間は60分〜90分で、後ほど日程調整します。"
                        ),
                    ))

            released_clicks = [
                row for row in page.requests
                if row["method"] == "Input.dispatchMouseEvent"
                and row["params"]["type"] == "mouseReleased"
            ]
            self.assertEqual(released_clicks, [])
            self.assertFalse(screenshot.exists())
            self.assertFalse(evidence_path.exists())
            verdict = json.loads(policy_path.read_text())
            self.assertFalse(verdict["allowed"])
            self.assertEqual(verdict["request_id"], request_id)
            self.assertIn(
                "synchronous_live_presence_required",
                verdict["reason_codes"],
            )

    def test_submit_application_loads_authoritative_brief_when_cli_does_not_supply_one(
        self,
    ) -> None:
        request_id = "5174303"
        form_url = f"https://coconala.com/offers/add/{request_id}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = FakeSocket(form_url, application_submission=True)
            loader = mock.AsyncMock(
                return_value="資料作成をチャットでお願いします。"
            )
            with (
                mock.patch.object(
                    module.websockets,
                    "connect",
                    return_value=FakeConnection(page),
                ),
                mock.patch.object(
                    module,
                    "_load_opportunity_brief",
                    loader,
                ),
            ):
                result = asyncio.run(module.submit_application(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    request_id,
                    root / "submitted.png",
                    root / "submitted.json",
                    wait_seconds=0,
                ))

            self.assertTrue(result["submit_verified"])
            loader.assert_awaited_once_with(
                f"https://coconala.com/requests/{request_id}"
            )

    def test_open_retainer_application_form_uses_ulid_route_and_verifies_fields(self) -> None:
        outsource_ulid = "01KYKDECET9WAY0CKRBCKH81RC"
        expected_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-form.png"
            evidence_path = root / "retainer-form.json"
            page = FakeSocket(expected_url, retainer_application_form=True)
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                result = asyncio.run(module.open_retainer_application_form(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    outsource_ulid,
                    screenshot,
                    evidence_path,
                ))

            self.assertEqual(result["request_id"], outsource_ulid)
            self.assertEqual(result["bucket"], "retainer")
            self.assertEqual(result["url"], expected_url)
            self.assertTrue(result["form_verified"])
            self.assertTrue(all(result["fields"].values()))
            self.assertEqual(screenshot.read_bytes(), b"png")

    def test_submit_retainer_application_clicks_confirm_consent_and_apply(self) -> None:
        outsource_ulid = "01KYKDECET9WAY0CKRBCKH81RC"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-submitted.png"
            evidence_path = root / "retainer-submitted.json"
            page = FakeSocket(form_url, retainer_application_submission=True)
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                result = asyncio.run(module.submit_retainer_application(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    outsource_ulid,
                    screenshot,
                    evidence_path,
                    wait_seconds=0,
                    opportunity_brief="生成AI自動化をチャットでお願いします。",
                ))

            released_clicks = [
                row for row in page.requests
                if row["method"] == "Input.dispatchMouseEvent"
                and row["params"]["type"] == "mouseReleased"
            ]
            self.assertEqual(len(released_clicks), 3)
            self.assertEqual(result["bucket"], "retainer")
            self.assertTrue(result["submit_verified"])
            self.assertTrue(result["applied_page_verified"])
            self.assertEqual(
                result["url"],
                "https://coconala.com/mypage/job_matching/applied/outsource_applications",
            )
            self.assertEqual(json.loads(evidence_path.read_text()), result)

    def test_submit_retainer_application_accepts_live_completion_modal(self) -> None:
        outsource_ulid = "01KYKDECET9WAY0CKRBCKH81RC"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-submitted.png"
            evidence_path = root / "retainer-submitted.json"
            page = FakeSocket(
                form_url,
                retainer_application_submission=True,
                retainer_completion_modal=True,
            )
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                result = asyncio.run(module.submit_retainer_application(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    outsource_ulid,
                    screenshot,
                    evidence_path,
                    wait_seconds=0,
                    opportunity_brief="生成AI自動化をチャットでお願いします。",
                ))

            self.assertEqual(
                result["url"],
                "https://coconala.com/mypage/job_matching/applied/outsource_applications",
            )
            self.assertEqual(
                result["confirmation_text"],
                "応募が完了しました！",
            )
            self.assertTrue(result["submit_verified"])
            self.assertTrue(result["applied_page_verified"])
            self.assertEqual(json.loads(evidence_path.read_text()), result)

    def test_submit_retainer_application_clears_generated_message_modal(self) -> None:
        outsource_ulid = "01KYM4VZ6VJ0SFH1HBW3FP7S6J"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-submitted.png"
            evidence_path = root / "retainer-submitted.json"
            page = FakeSocket(
                form_url,
                retainer_application_submission=True,
                retainer_generated_message_modal=True,
            )
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                result = asyncio.run(module.submit_retainer_application(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    outsource_ulid,
                    screenshot,
                    evidence_path,
                    wait_seconds=0,
                    opportunity_brief="生成AI自動化をチャットでお願いします。",
                ))

            released_clicks = [
                row for row in page.requests
                if row["method"] == "Input.dispatchMouseEvent"
                and row["params"]["type"] == "mouseReleased"
            ]
            self.assertEqual(len(released_clicks), 3)
            self.assertTrue(result["submit_verified"])
            self.assertTrue(result["applied_page_verified"])
            self.assertEqual(json.loads(evidence_path.read_text()), result)

    def test_retainer_submit_intent_preserves_title_before_final_click(self) -> None:
        outsource_ulid = "01KYKDECET9WAY0CKRBCKH81RC"
        listing_title = "Meta APIを活用したSaaS開発エンジニア募集"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-submitted.png"
            evidence_path = root / "retainer-submitted.json"
            intent_path = root / "retainer-submitted.intent.json"
            page = FakeSocket(form_url, retainer_application_submission=True)
            original_click = module._mouse_click
            click_count = 0

            async def lose_ack_after_final_click(ws, x, y, cid):
                nonlocal click_count
                click_count += 1
                result = await original_click(ws, x, y, cid)
                if click_count == 3:
                    raise RuntimeError("socket_lost_after_click")
                return result

            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ), mock.patch.object(
                module,
                "_mouse_click",
                side_effect=lose_ack_after_final_click,
            ):
                with self.assertRaisesRegex(RuntimeError, "socket_lost_after_click"):
                    asyncio.run(module.submit_retainer_application(
                        "ws://127.0.0.1:9223/devtools/page/leased-target",
                        outsource_ulid,
                        screenshot,
                        evidence_path,
                        listing_title=listing_title,
                        wait_seconds=0,
                        opportunity_brief="生成AI自動化をチャットでお願いします。",
                    ))

            self.assertEqual(
                json.loads(intent_path.read_text()),
                {
                    "request_id": outsource_ulid,
                    "bucket": "retainer",
                    "url": (
                        "https://coconala.com/job_matching/outsources/"
                        f"{outsource_ulid}"
                    ),
                    "title": listing_title,
                    "state": "prepared",
                },
            )

    def test_submit_retainer_blocks_required_client_interview_before_click(self) -> None:
        outsource_ulid = "01KYM2CBBBGRC3WVZ616VKWWZV"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "submitted.png"
            evidence_path = root / "submitted.json"
            page = FakeSocket(
                form_url,
                retainer_application_submission=True,
                form_text=(
                    "クライアント面談を行うため、8月6日の13:00に"
                    "ご対応可能でしょうか。"
                ),
            )
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "application_eligibility_rejected:"
                    "synchronous_live_presence_required",
                ):
                    asyncio.run(module.submit_retainer_application(
                        "ws://127.0.0.1:9223/devtools/page/leased-target",
                        outsource_ulid,
                        screenshot,
                        evidence_path,
                        wait_seconds=0,
                        opportunity_brief=(
                            "生成AIを使う完全在宅の業務自動化案件です。"
                        ),
                    ))

            released_clicks = [
                row for row in page.requests
                if row["method"] == "Input.dispatchMouseEvent"
                and row["params"]["type"] == "mouseReleased"
            ]
            self.assertEqual(released_clicks, [])
            verdict = json.loads(
                (root / "submitted.eligibility.json").read_text()
            )
            self.assertFalse(verdict["allowed"])
            self.assertEqual(verdict["bucket"], "retainer")

    def test_submit_retainer_loads_authoritative_brief_before_click(self) -> None:
        outsource_ulid = "01KYKDECET9WAY0CKRBCKH81RC"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = FakeSocket(
                form_url,
                retainer_application_submission=True,
            )
            loader = mock.AsyncMock(
                return_value="生成AI自動化をチャットでお願いします。"
            )
            with (
                mock.patch.object(
                    module.websockets,
                    "connect",
                    return_value=FakeConnection(page),
                ),
                mock.patch.object(
                    module,
                    "_load_opportunity_brief",
                    loader,
                ),
            ):
                result = asyncio.run(module.submit_retainer_application(
                    "ws://127.0.0.1:9223/devtools/page/leased-target",
                    outsource_ulid,
                    root / "submitted.png",
                    root / "submitted.json",
                    wait_seconds=0,
                ))

            self.assertTrue(result["submit_verified"])
            loader.assert_awaited_once_with(
                "https://coconala.com/job_matching/outsources/"
                f"{outsource_ulid}"
            )

    def test_submit_waits_for_the_same_target_lock_used_by_context_release(self) -> None:
        request_id = "5170842"
        form_url = f"https://coconala.com/offers/add/{request_id}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "submitted.png"
            evidence_path = root / "submitted.json"
            leases_path = root / "gig-leases.json"
            page = FakeSocket(form_url, application_submission=True)
            lock_path = module._target_operation_lock_path(
                "ws://127.0.0.1:9223/devtools/page/target-1",
                leases_path=leases_path,
            )
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_handle = lock_path.open("a+")
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            result = {}

            def run_submit() -> None:
                with mock.patch.object(
                    module.websockets,
                    "connect",
                    return_value=FakeConnection(page),
                ), mock.patch.dict(
                    module.os.environ,
                    {"CLOAK_CONTEXT_LEASES_FILE": str(leases_path)},
                ):
                    result.update(asyncio.run(module.submit_application(
                        "ws://127.0.0.1:9223/devtools/page/target-1",
                        request_id,
                        screenshot,
                        evidence_path,
                        wait_seconds=0,
                        opportunity_brief="資料作成をチャットでお願いします。",
                    )))

            worker = threading.Thread(target=run_submit, daemon=True)
            worker.start()
            time.sleep(0.05)

            self.assertTrue(worker.is_alive())
            self.assertEqual(page.requests, [])

            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()
            worker.join(timeout=1)

            self.assertTrue(result["submit_verified"])

    def test_observe_waits_while_the_same_target_is_being_submitted(self) -> None:
        expected_url = "https://coconala.com/requests/5170842"
        ws_url = "ws://127.0.0.1:9223/devtools/page/target-1"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "request.png"
            live_dom = root / "request.json"
            leases_path = root / "gig-leases.json"
            page = FakeSocket(expected_url)
            lock_path = module._target_operation_lock_path(
                ws_url,
                leases_path=leases_path,
            )
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_handle = lock_path.open("a+")
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            result = {}

            def run_observe() -> None:
                with mock.patch.object(
                    module.websockets,
                    "connect",
                    return_value=FakeConnection(page),
                ), mock.patch.dict(
                    module.os.environ,
                    {"CLOAK_CONTEXT_LEASES_FILE": str(leases_path)},
                ):
                    result.update(asyncio.run(module.observe_target(
                        ws_url,
                        expected_url,
                        screenshot,
                        live_dom,
                    )))

            worker = threading.Thread(target=run_observe, daemon=True)
            worker.start()
            time.sleep(0.05)

            self.assertTrue(worker.is_alive())
            self.assertEqual(page.requests, [])

            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            lock_handle.close()
            worker.join(timeout=1)

            self.assertFalse(worker.is_alive())
            self.assertTrue(result["observed"])
            self.assertEqual(result["url"], expected_url)

    def test_observe_rejects_cross_target_navigation_without_evidence(self) -> None:
        expected_url = "https://coconala.com/talkrooms/101"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "room.png"
            live_dom = root / "room.json"
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(FakeSocket("https://dev.to/settings/extensions")),
            ):
                with self.assertRaisesRegex(RuntimeError, "navigation_url_mismatch"):
                    asyncio.run(module.observe_target(
                        "ws://127.0.0.1:9222/devtools/page/leased-target",
                        expected_url,
                        screenshot,
                        live_dom,
                    ))
            self.assertFalse(screenshot.exists())
            self.assertFalse(live_dom.exists())


if __name__ == "__main__":
    unittest.main()
