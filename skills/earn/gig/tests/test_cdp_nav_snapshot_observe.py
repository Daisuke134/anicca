from __future__ import annotations

import asyncio
import base64
import fcntl
import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cdp_nav_snapshot.py"
LEASED_TARGET_WS = "ws://127.0.0.1:9223/devtools/page/leased-target"

# A5-③ (2026-07-31): a brief is now also the market observation. The submit gate
# refuses a page whose 発注率 it cannot read, so these tests -- which are about the
# click sequence, the intent write and the target lock, not about the market -- pass
# a brief shaped like the real page, with a client above the threshold. The plain
# one-sentence brief they used before now describes a page that could not be read,
# and being refused is the correct answer to that.
ELIGIBLE_BRIEF = (
    "予算\n1万円\n〜\n3万円\n"
    "募集期限\n締切日 2026年8月7日 / 掲載日 2026年7月28日\n"
    "応募状況\n応募人数 26\n契約人数 0\n閲覧数 348\n"
    "募集内容\n資料作成をチャットでお願いします。\n"
    "募集者情報\nsomebody\n発注実績\n10\n発注件数\n61%\n発注率\n100%\n取引完了率\n"
    "認証状況\n"
)
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
        proposal_text: str = "自動化ツールと手順書を納品します。",
        form_text: str = "",
    ):
        self.final_url = final_url
        self.application_form = application_form
        self.application_submission = application_submission
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
            self.pending.extend([
                json.dumps({"id": request_id, "result": {}}),
                json.dumps({"method": "Page.loadEventFired", "params": {}}),
            ])
        elif method == "Runtime.evaluate":
            expression = request.get("params", {}).get("expression")
            if expression == "document.location.href":
                value = self.final_url
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
            elif self.application_form and "data[Offer][content]" in str(expression):
                value = json.dumps({
                    "url": self.final_url,
                    "title": "応募する | ココナラ",
                    "has_content": True,
                    "has_price": True,
                    "has_expire_date": True,
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
                self.application_submission
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

    def test_single_submit_does_not_treat_buyer_copy_as_a_validation_error(self) -> None:
        # Was asserted on the retainer submit state until A3 (2026-07-30) deleted
        # that helper. The property it protects -- "入力してください" appearing in a
        # buyer's own listing copy must not be read as a form validation error --
        # belongs to the single submit state too, which is the one still shipping.
        source = inspect.getsource(module._application_submit_state)
        assert "body.includes('入力してください')" not in source
        assert "form_filled" in source

    def test_top_level_help_advertises_current_subcommands(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("open-application", result.stdout)
        self.assertNotIn("submit-application", result.stdout)
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

    def test_open_application_form_uses_canonical_route_and_verifies_real_fields(self) -> None:
        request_id = "91000020"
        expected_url = "https://coconala.com/offers/add/91000020"
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
        request_id = "91000026"
        form_url = "https://coconala.com/offers/add/91000026"
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
                    opportunity_brief=ELIGIBLE_BRIEF,
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
        request_id = "91000026"
        form_url = "https://coconala.com/offers/add/91000026"
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
                        opportunity_brief=ELIGIBLE_BRIEF,
                    ))

            self.assertFalse(screenshot.exists())
            self.assertFalse(evidence_path.exists())

    def test_submit_application_persists_intent_before_irreversible_click(self) -> None:
        request_id = "91000021"
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
                        opportunity_brief=ELIGIBLE_BRIEF,
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
        request_id = "91000023"
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
        request_id = "91000026"
        form_url = f"https://coconala.com/offers/add/{request_id}"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = FakeSocket(form_url, application_submission=True)
            loader = mock.AsyncMock(
                return_value=ELIGIBLE_BRIEF
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

    # --- A3 (2026-07-30): 継続 applications are refused in code -----------------
    #
    # These replace the tests that proved a retainer application could be opened,
    # filled, confirmed and submitted. That machinery is deleted, not disabled:
    # Coconala's 継続 listings escalate to a synchronous 三者面談 before money moves
    # (observed live on 【長期・在宅】SNS投稿・更新サポートスタッフ募集, ¥1,500/時,
    # which reached 「三者面談の候補日時が届きました」), so every retainer application
    # buys a human-in-the-loop on a system built to have none. Nothing that can
    # click a retainer submit button remains in this file to be re-enabled by a
    # prompt, a quota, or a flag.

    def test_submit_retainer_application_is_refused_at_the_submit_boundary(self) -> None:
        """A retainer-shaped opportunity driven to the submit call is refused.

        The listing text used here reads as clean asynchronous chat work, so this
        proves the refusal is driven by the bucket rather than by the
        synchronous-presence patterns happening to fire on the prose.
        """
        outsource_ulid = "01KYKDECET9WAY0CKRBCKH81RC"
        form_url = (
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}/apply"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-submitted.png"
            evidence_path = root / "retainer-submitted.json"
            page = FakeSocket(form_url)
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "application_eligibility_rejected:"
                    "retainer_applications_disabled",
                ):
                    asyncio.run(module.submit_retainer_application(
                        LEASED_TARGET_WS,
                        outsource_ulid,
                        screenshot,
                        evidence_path,
                        listing_title=(
                            "【長期・在宅】SNS投稿・更新サポートスタッフ募集"
                        ),
                        wait_seconds=0,
                        opportunity_brief=(
                            "連絡はココナラのチャット形式で、隙間時間に非同期で"
                            "対応いただけます。定期投稿と月次レポートをお願いします。"
                        ),
                    ))

            # The safest click is the one whose browser was never spoken to.
            self.assertEqual(page.requests, [])
            self.assertFalse(screenshot.exists())
            self.assertFalse(evidence_path.exists())
            self.assertFalse(
                (root / "retainer-submitted.intent.json").exists()
            )

            # Refused, not silently dropped.
            verdict = json.loads(
                (root / "retainer-submitted.eligibility.json").read_text()
            )
            self.assertFalse(verdict["allowed"])
            self.assertEqual(verdict["request_id"], outsource_ulid)
            self.assertEqual(verdict["bucket"], "retainer")
            self.assertEqual(
                verdict["opportunity_url"],
                "https://coconala.com/job_matching/outsources/"
                f"{outsource_ulid}",
            )
            self.assertIn(
                "retainer_applications_disabled",
                verdict["reason_codes"],
            )

    def test_opening_the_retainer_application_form_is_refused_too(self) -> None:
        outsource_ulid = "01KYM2CBBBGRC3WVZ616VKWWZV"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screenshot = root / "retainer-form.png"
            evidence_path = root / "retainer-form.json"
            page = FakeSocket(
                "https://coconala.com/job_matching/outsources/"
                f"{outsource_ulid}/apply"
            )
            with mock.patch.object(
                module.websockets,
                "connect",
                return_value=FakeConnection(page),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "application_eligibility_rejected:"
                    "retainer_applications_disabled",
                ):
                    asyncio.run(module.open_retainer_application_form(
                        LEASED_TARGET_WS,
                        outsource_ulid,
                        screenshot,
                        evidence_path,
                    ))

            self.assertEqual(page.requests, [])
            self.assertFalse(screenshot.exists())
            self.assertFalse(evidence_path.exists())
            verdict = json.loads(
                (root / "retainer-form.eligibility.json").read_text()
            )
            self.assertFalse(verdict["allowed"])
            self.assertEqual(verdict["bucket"], "retainer")

    def test_a_malformed_retainer_identity_is_rejected_as_an_identity_first(self) -> None:
        """Fail on the identity before the policy, so a typo is never recorded as
        a refused ULID that never existed."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "outsource_ulid_invalid"):
                asyncio.run(module.submit_retainer_application(
                    LEASED_TARGET_WS,
                    "91000030",
                    root / "retainer-submitted.png",
                    root / "retainer-submitted.json",
                    wait_seconds=0,
                ))
            self.assertFalse(
                (root / "retainer-submitted.eligibility.json").exists()
            )

    def test_no_retainer_submit_machinery_survives_to_be_re_enabled(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("_submit_retainer_application_locked", source)
        self.assertNotIn("_retainer_application_submit_state", source)
        self.assertNotIn("応募が完了しました！", source)

    def test_submit_waits_for_the_same_target_lock_used_by_context_release(self) -> None:
        request_id = "91000021"
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
                        opportunity_brief=ELIGIBLE_BRIEF,
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
        expected_url = "https://coconala.com/requests/91000021"
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
