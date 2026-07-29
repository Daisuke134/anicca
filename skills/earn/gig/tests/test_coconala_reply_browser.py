import asyncio
import importlib.util
import inspect
import json
import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coconala_reply_browser.py"
JS_HARNESS = r"""
import { webcrypto } from "node:crypto";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
let input = "";
for await (const chunk of process.stdin) input += chunk;
const payload = JSON.parse(input);
const duplicate = payload.duplicate_body
  ? '<textarea name="data[DirectMessage][body]"></textarea>'
  : "";
const dom = new JSDOM(`<!doctype html><form id="reply" method="post"
  action="${payload.action}" target="${payload.target || ""}"
  enctype="${payload.enctype || "application/x-www-form-urlencoded"}">
  <input type="hidden" name="_method" value="POST">
  <textarea id="DirectMessageBody" name="data[DirectMessage][body]"></textarea>
  <input type="file" name="data[DirectMessage][attachments][]">
  <input type="file" name="data[DirectMessage][attachments][]">
  ${duplicate}
  <button type="button" class="js_handle-submit"
    aria-label="メッセージを送信する"></button>
</form>`, {url: payload.location, runScripts: "outside-only"});
const { window } = dom;
window.TextEncoder = TextEncoder;
const form = window.document.querySelector("form");
const textarea = window.document.querySelector("#DirectMessageBody");
textarea.value = payload.body;
if (payload.selected_attachment) {
  const fileInput = window.document.querySelector('input[type="file"]');
  Object.defineProperty(fileInput, "files", {
    value: [new window.File(["proof"], "proof.txt", {type: "text/plain"})],
  });
}
function pageFormToArray(target) {
  return Array.from(target.elements).flatMap((element) => {
    if (!element.name || element.disabled) return [];
    if (element.type === "file") {
      return element.files.length
        ? Array.from(element.files).map((file) => ({name: element.name, value: file}))
        : [{name: element.name, value: ""}];
    }
    if ((element.type === "checkbox" || element.type === "radio") && !element.checked) {
      return [];
    }
    if (["button", "submit", "reset", "image"].includes(element.type)) return [];
    return [{name: element.name, value: element.value}];
  });
}
function pageJQuery(target) {
  return {formToArray: () => pageFormToArray(target)};
}
pageJQuery.fn = {formToArray() {}};
pageJQuery.ajaxSettings = {traditional: false};
pageJQuery.param = (fields) => {
  if (payload.param_mode === "throw") throw new Error("serializer failed");
  if (payload.param_mode === "non_string") return {};
  const encoded = new window.URLSearchParams();
  for (const field of fields) encoded.append(field.name, String(field.value));
  return encoded.toString();
};
if (payload.missing_param_serializer) pageJQuery.param = undefined;
if (!payload.missing_form_serializer) window.jQuery = pageJQuery;
let submitted = null;
window.fetch = async function (url, options) {
  const encoded = new window.URLSearchParams(options.body);
  const attachments = encoded.getAll("data[DirectMessage][attachments][]");
  submitted = {
    url: new URL(url, window.location.href).href,
    method: options.method,
    body_type: typeof options.body,
    body_count: encoded.getAll("data[DirectMessage][body]").length,
    attachment_count: attachments.length,
    attachments_are_empty_strings: attachments.every(
      (value) => typeof value === "string" && value === ""
    ),
    content_type: options.headers["Content-Type"],
    accept: options.headers.Accept,
    xhr_header: options.headers["X-Requested-With"],
  };
  return {
    ok: payload.response_ok,
    status: payload.response_status,
    json: async () => payload.response_payload,
  };
};
Object.defineProperty(window, "crypto", {value: {
  subtle: {
    digest: async (...args) => {
      if (payload.mutate_action_before_digest) {
        form.action = payload.mutate_action_before_digest;
      }
      if (payload.mutate_body_before_digest) {
        textarea.value = payload.mutate_body_before_digest;
      }
      if (payload.mutate_target_before_digest) {
        form.target = payload.mutate_target_before_digest;
      }
      return webcrypto.subtle.digest(...args);
    },
  },
}});
const result = await window.eval(payload.expression);
process.stdout.write(JSON.stringify({result, submitted}));
"""


def load_module():
    spec = importlib.util.spec_from_file_location("coconala_reply_browser", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load coconala_reply_browser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoconalaReplyBrowserTest(unittest.TestCase):
    def setUp(self):
        self.browser = load_module()
        self.url = "https://coconala.com/mypage/direct_message/42"

    def raw(self):
        return {
            "url": self.url,
            "title": "メッセージ詳細 | マイページ | ココナラ",
            "container_present": True,
            "not_found_present": False,
            "error_present": False,
            "own_user_path": "/users/seller",
            "messages": [
                {
                    "author_path": "/users/buyer",
                    "sent_at": "2026-07-22 15:06:11",
                    "body": "private buyer question",
                },
                {
                    "author_path": "/users/seller",
                    "sent_at": "2026-07-22 15:07:12",
                    "body": "specific helpful reply",
                },
            ],
        }

    def execute_submit_expression(self, **overrides):
        body = overrides.pop("expected_body", "bounded reply")
        payload = {
            "location": self.url,
            "action": self.url,
            "target": "",
            "enctype": "application/x-www-form-urlencoded",
            "body": body,
            "duplicate_body": False,
            "mutate_action_before_digest": "",
            "mutate_body_before_digest": "",
            "mutate_target_before_digest": "",
            "missing_form_serializer": False,
            "missing_param_serializer": False,
            "param_mode": "",
            "selected_attachment": False,
            "response_ok": True,
            "response_status": 200,
            "response_payload": {"status": "ok"},
            "expression": self.browser.submit_expression(
                self.url, self.browser.outgoing_sha256(body)
            ),
        }
        payload.update(overrides)
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", JS_HARNESS],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
            cwd=SCRIPT.parents[3],
        )
        return json.loads(completed.stdout)

    def test_raw_thread_becomes_transient_context_and_bounded_hash_observation(self):
        context, bounded = self.browser.thread_state(self.raw(), self.url)

        self.assertEqual(context["conversation"], [
            {"side": "buyer", "body": "private buyer question"},
            {"side": "seller", "body": "specific helpful reply"},
        ])
        self.assertEqual(bounded["talkroom_id"], "42")
        self.assertEqual(bounded["url"], self.url)
        self.assertEqual(bounded["seller_count"], 1)
        self.assertEqual(bounded["seller_sent_at"], "2026-07-22T06:07:12+00:00")
        self.assertEqual(bounded["latest_buyer_sent_at"], "2026-07-22T06:06:11+00:00")
        self.assertEqual(bounded["last_sender"], "seller")
        self.assertEqual(bounded["seller_messages"], [{
            "body_sha256": bounded["seller_message_hashes"][0],
            "sent_at": "2026-07-22T06:07:12+00:00",
        }])
        serialized = json.dumps(bounded, ensure_ascii=False)
        self.assertNotIn("private buyer question", serialized)
        self.assertNotIn("specific helpful reply", serialized)
        self.assertEqual(len(bounded["seller_message_hashes"][0]), 64)
        self.assertEqual(len(bounded["fingerprint"]), 64)

    def test_missing_own_identity_is_unhealthy_not_assumed(self):
        raw = self.raw()
        raw["own_user_path"] = None

        with self.assertRaisesRegex(Exception, "missing_sender_identity"):
            self.browser.thread_state(raw, self.url)

    def test_live_fill_and_click_selectors_are_exact_and_fail_closed(self):
        fill = self.browser.fill_expression("bounded reply")
        submit = self.browser.submit_expression(
            self.url, self.browser.outgoing_sha256("bounded reply")
        )

        self.assertIn("#DirectMessageBody", fill)
        self.assertIn("data[DirectMessage][body]", fill)
        self.assertIn("dispatchEvent", fill)
        self.assertIn(".js_handle-submit", submit)
        self.assertIn("disabled", submit)
        self.assertIn("メッセージを送信する", submit)
        self.assertIn('"/mypage/direct_message/42"', submit)
        self.assertIn("fetch(expectedSubmitUrl", submit)
        self.assertIn("formToArray(false)", submit)
        self.assertNotIn("new FormData(current.form)", submit)
        self.assertIn("serializer.param(fields", submit)
        self.assertIn("application/x-www-form-urlencoded", submit)
        self.assertNotIn("const formData=new FormData()", submit)
        self.assertIn("unexpected_attachment", submit)
        self.assertIn("X-Requested-With", submit)
        self.assertIn(
            '"https://coconala.com/mypage/direct_message_ajax/42"',
            submit,
        )
        self.assertIn("crypto.subtle.digest", submit)
        self.assertIn("location.origin", submit)
        self.assertIn("action.search", submit)
        self.assertIn("form.target", submit)
        self.assertNotIn("button.click()", submit)
        self.assertNotIn("ajaxSubmit", submit)
        self.assertIn("textarea_length", self.browser.POST_CLICK_DIAGNOSTIC_EXPRESSION)
        self.assertIn("visible_error_count", self.browser.POST_CLICK_DIAGNOSTIC_EXPRESSION)
        self.assertNotIn("innerText", self.browser.POST_CLICK_DIAGNOSTIC_EXPRESSION)
        self.assertNotIn("textContent", self.browser.POST_CLICK_DIAGNOSTIC_EXPRESSION)

    def test_submit_expression_executes_only_for_exact_form_and_intent_hash(self):
        executed = self.execute_submit_expression()

        self.assertEqual(executed["result"], {"ok": True})
        self.assertEqual(executed["submitted"], {
            "url": "https://coconala.com/mypage/direct_message_ajax/42",
            "method": "POST",
            "body_type": "string",
            "body_count": 1,
            "attachment_count": 2,
            "attachments_are_empty_strings": True,
            "content_type": "application/x-www-form-urlencoded; charset=UTF-8",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "xhr_header": "XMLHttpRequest",
        })
        normalized = self.execute_submit_expression(
            expected_body="  cafe\u0301\tline\r\nnext  "
        )
        self.assertEqual(normalized["result"], {"ok": True})
        for codepoint in (
            "\u001c", "\u001d", "\u001e", "\u001f", "\u0085",
            "\u00a0", "\u1680", "\u2028", "\u202f", "\u3000", "\ufeff",
        ):
            with self.subTest(codepoint=f"U+{ord(codepoint):04X}"):
                normalized = self.execute_submit_expression(
                    expected_body=f"before{codepoint}after"
                )
                self.assertEqual(normalized["result"], {"ok": True})
                self.assertIsNotNone(normalized["submitted"])

    def test_submit_expression_fails_closed_without_coconala_form_serializer(self):
        executed = self.execute_submit_expression(missing_form_serializer=True)

        self.assertEqual(executed["result"], {
            "ok": False,
            "error": "missing_form_serializer",
        })
        self.assertIsNone(executed["submitted"])

    def test_submit_expression_fails_closed_without_coconala_param_serializer(self):
        executed = self.execute_submit_expression(missing_param_serializer=True)

        self.assertEqual(executed["result"], {
            "ok": False,
            "error": "missing_param_serializer",
        })
        self.assertIsNone(executed["submitted"])

    def test_submit_expression_fails_closed_for_invalid_param_serialization(self):
        for mode, error in (
            ("throw", "param_serialization_failed"),
            ("non_string", "unexpected_encoded_form"),
        ):
            with self.subTest(mode=mode):
                executed = self.execute_submit_expression(param_mode=mode)
                self.assertEqual(executed["result"], {"ok": False, "error": error})
                self.assertIsNone(executed["submitted"])

    def test_submit_expression_rejects_unexpected_form_encoding(self):
        executed = self.execute_submit_expression(enctype="multipart/form-data")

        self.assertEqual(executed["result"], {
            "ok": False,
            "error": "unexpected_form_encoding",
        })
        self.assertIsNone(executed["submitted"])

    def test_submit_expression_classifies_validation_without_echoing_server_text(self):
        cases = (
            ("外部URLやメールアドレスは送信できません", "external_contact"),
            ("本文を入力してください", "message_validation"),
            ("現在メッセージを送信することができません", "sending_unavailable"),
            ("予期しない検証エラー", "other_validation"),
        )
        for server_text, category in cases:
            with self.subTest(category=category):
                executed = self.execute_submit_expression(response_payload={
                    "status": "error",
                    "validationErrorMsg": server_text,
                })
                self.assertEqual(executed["result"], {
                    "ok": False,
                    "error": "submit_rejected",
                    "http_status": 200,
                    "validation_category": category,
                })
                self.assertNotIn(server_text, json.dumps(executed, ensure_ascii=False))

    def test_submit_expression_fails_closed_when_attachment_is_selected(self):
        executed = self.execute_submit_expression(selected_attachment=True)

        self.assertEqual(executed["result"], {
            "ok": False,
            "error": "unexpected_attachment",
        })
        self.assertIsNone(executed["submitted"])

    def test_executor_newline_canonicalization_survives_textarea_dom(self):
        executor_path = SCRIPT.with_name("reply_executor.py")
        spec = importlib.util.spec_from_file_location("reply_executor_for_dom_test", executor_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load reply executor")
        executor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(executor)

        for original in (
            "A\rB",
            "A\rB\rC",
            "A\nB",
            "A\r\nB",
            "\rA\r",
            "\nA\n",
        ):
            with self.subTest(original=repr(original)):
                canonical = executor.dom_compatible_outgoing_body(original)
                executed = self.execute_submit_expression(expected_body=canonical)
                self.assertEqual(executed["result"], {"ok": True})
                self.assertIsNotNone(executed["submitted"])

    def test_submit_expression_rejects_origin_query_target_and_duplicate_body(self):
        cases = (
            {
                "location": "https://evil.example/mypage/direct_message/42",
                "action": "https://evil.example/mypage/direct_message/42",
            },
            {"action": "https://evil.example/mypage/direct_message/42"},
            {"action": f"{self.url}?mode=other"},
            {"target": "_blank"},
            {"duplicate_body": True},
            {"body": "different reply"},
        )
        for case in cases:
            with self.subTest(case=case):
                executed = self.execute_submit_expression(**case)
                self.assertFalse(executed["result"]["ok"])
                self.assertIsNone(executed["submitted"])

    def test_submit_expression_rechecks_action_and_body_after_async_hash(self):
        for case in (
            {"mutate_action_before_digest": "https://evil.example/mypage/direct_message/42"},
            {"mutate_action_before_digest": f"{self.url}?mode=other"},
            {"mutate_body_before_digest": "changed during digest"},
            {"mutate_target_before_digest": "_blank"},
        ):
            with self.subTest(case=case):
                executed = self.execute_submit_expression(**case)
                self.assertFalse(executed["result"]["ok"])
                self.assertIsNone(executed["submitted"])

    def test_fill_waits_for_coconala_throttled_form_analysis(self):
        browser = self.browser.CoconalaCdpReplyBrowser(Path("/tmp/cdp-helper"), self.url)
        browser.tab = type("Tab", (), {"ws": "ws://example.test/page"})()
        calls = []
        original_evaluate = self.browser._evaluate
        original_sleep = self.browser.time.sleep

        async def fake_evaluate(ws, expression):
            calls.append(("evaluate", ws, expression))
            return {"ok": True}

        self.browser._evaluate = fake_evaluate
        self.browser.time.sleep = lambda seconds: calls.append(("sleep", seconds))
        try:
            browser.fill("bounded reply")
        finally:
            self.browser._evaluate = original_evaluate
            self.browser.time.sleep = original_sleep

        self.assertEqual(calls[-1], ("sleep", self.browser.FORM_ANALYSIS_SETTLE_SECONDS))
        self.assertGreaterEqual(self.browser.FORM_ANALYSIS_SETTLE_SECONDS, 0.75)

    def test_native_submit_wait_covers_coconala_ajax_timeout(self):
        timeout_default = inspect.signature(
            self.browser._drain_network_events
        ).parameters["timeout_seconds"].default

        self.assertGreaterEqual(
            self.browser.NATIVE_SUBMIT_TIMEOUT_SECONDS,
            300.0,
        )
        self.assertEqual(
            timeout_default,
            self.browser.NATIVE_SUBMIT_TIMEOUT_SECONDS,
        )

    def test_click_uses_native_fetch_to_exact_ajax_endpoint_then_refreshes_thread(self):
        calls = []
        observed = [
            {
                "method": "POST",
                "path": "/mypage/direct_message_ajax/42",
                "status": 200,
                "outcome": "finished",
            }
        ]

        class FakeConnection:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *args):
                return None

        async def fake_call(
            ws, command_id, method, params, network, *, timeout_seconds=30.0
        ):
            calls.append((command_id, method, params, timeout_seconds))
            if method == "Runtime.evaluate":
                return {"result": {"value": {"ok": True}}}
            return {}

        async def fake_drain(ws, network):
            return observed

        original_connect = self.browser.websockets.connect
        original_call = self.browser._call_with_network_events
        original_drain = self.browser._drain_network_events
        self.browser.websockets.connect = lambda *args, **kwargs: FakeConnection()
        self.browser._call_with_network_events = fake_call
        self.browser._drain_network_events = fake_drain
        try:
            result = asyncio.run(
                self.browser._click(
                    "ws://example.test/page",
                    self.url,
                    self.browser.outgoing_sha256("bounded reply"),
                )
            )
        finally:
            self.browser.websockets.connect = original_connect
            self.browser._call_with_network_events = original_call
            self.browser._drain_network_events = original_drain

        self.assertEqual([method for _, method, _, _ in calls], [
            "Network.enable",
            "Page.bringToFront",
            "Runtime.evaluate",
            "Page.navigate",
        ])
        expression = calls[2][2]["expression"]
        self.assertIn("fetch(expectedSubmitUrl", expression)
        self.assertIn(
            '"https://coconala.com/mypage/direct_message_ajax/42"',
            expression,
        )
        self.assertNotIn("ajaxSubmit", expression)
        self.assertEqual(
            calls[2][3],
            self.browser.NATIVE_SUBMIT_TIMEOUT_SECONDS,
        )
        self.assertEqual(calls[3][2], {"url": self.url})
        self.assertEqual(result, observed)

    def test_click_preserves_bounded_server_validation_category(self):
        class FakeConnection:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *args):
                return None

        async def fake_call(
            ws, command_id, method, params, network, *, timeout_seconds=30.0
        ):
            if method == "Runtime.evaluate":
                return {"result": {"value": {
                    "ok": False,
                    "error": "submit_rejected",
                    "validation_category": "external_contact",
                }}}
            return {}

        original_connect = self.browser.websockets.connect
        original_call = self.browser._call_with_network_events
        self.browser.websockets.connect = lambda *args, **kwargs: FakeConnection()
        self.browser._call_with_network_events = fake_call
        try:
            with self.assertRaises(self.browser.BrowserSendFailure) as raised:
                asyncio.run(self.browser._click(
                    "ws://example.test/page",
                    self.url,
                    self.browser.outgoing_sha256("bounded reply"),
                ))
        finally:
            self.browser.websockets.connect = original_connect
            self.browser._call_with_network_events = original_call

        self.assertEqual(raised.exception.code, "submit_rejected_external_contact")
        self.assertEqual(raised.exception.network, [])

    def test_network_call_uses_one_total_deadline_across_unrelated_events(self):
        class FakeSocket:
            def __init__(self):
                self.sent = []

            async def send(self, value):
                self.sent.append(value)

            async def recv(self):
                return json.dumps({"method": "Runtime.consoleAPICalled", "params": {}})

        socket = FakeSocket()
        summary = self.browser.NetworkSummary("coconala.com")
        ticks = iter((0.0, 1.0, 2.0, 6.0))
        original_wait_for = self.browser.asyncio.wait_for

        async def immediate(awaitable, timeout):
            self.assertLessEqual(timeout, 5.0)
            return await awaitable

        self.browser.asyncio.wait_for = immediate
        try:
            with self.assertRaises(TimeoutError):
                asyncio.run(self.browser._call_with_network_events(
                    socket, 9, "Runtime.evaluate", {}, summary,
                    timeout_seconds=5.0,
                    monotonic=lambda: next(ticks),
                ))
        finally:
            self.browser.asyncio.wait_for = original_wait_for

    def test_network_call_allows_silent_response_after_thirty_seconds_within_deadline(self):
        class FakeSocket:
            async def send(self, value):
                return None

            async def recv(self):
                return json.dumps({"id": 9, "result": {"value": "ok"}})

        observed_timeouts = []
        original_wait_for = self.browser.asyncio.wait_for

        async def delayed(awaitable, timeout):
            observed_timeouts.append(timeout)
            return await awaitable

        ticks = iter((0.0, 31.0))
        self.browser.asyncio.wait_for = delayed
        try:
            result = asyncio.run(self.browser._call_with_network_events(
                FakeSocket(), 9, "Runtime.evaluate", {},
                self.browser.NetworkSummary("coconala.com"),
                timeout_seconds=305.0,
                monotonic=lambda: next(ticks),
            ))
        finally:
            self.browser.asyncio.wait_for = original_wait_for

        self.assertEqual(result, {"value": "ok"})
        self.assertEqual(observed_timeouts, [274.0])

    def test_network_summary_keeps_only_same_host_mutations_without_payloads(self):
        summary = self.browser.NetworkSummary("coconala.com")
        summary.observe({
            "method": "Network.requestWillBeSent",
            "params": {
                "requestId": "1",
                "request": {
                    "method": "POST",
                    "url": "https://coconala.com/mypage/direct_message/42?secret=discard",
                    "postData": "private reply",
                    "headers": {"Cookie": "secret"},
                },
            },
        })
        summary.observe({
            "method": "Network.responseReceived",
            "params": {"requestId": "1", "response": {"status": 422}},
        })
        self.assertFalse(summary.settled())
        summary.observe({
            "method": "Network.loadingFinished",
            "params": {"requestId": "1"},
        })
        self.assertTrue(summary.settled())
        summary.observe({
            "method": "Network.requestWillBeSent",
            "params": {
                "requestId": "2",
                "request": {"method": "GET", "url": "https://coconala.com/private"},
            },
        })
        summary.observe({
            "method": "Network.requestWillBeSent",
            "params": {
                "requestId": "3",
                "request": {"method": "POST", "url": "https://tracker.example/private"},
            },
        })

        serialized = json.dumps(summary.rows(), ensure_ascii=False)
        self.assertEqual(summary.rows(), [{
            "method": "POST",
            "path": "/mypage/direct_message/42",
            "status": 422,
            "outcome": "finished",
        }])
        self.assertNotIn("private reply", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("Cookie", serialized)

    def test_network_summary_waits_for_exact_native_fetch_submit_not_analytics(self):
        summary = self.browser.NetworkSummary(
            "coconala.com",
            expected_path="/mypage/direct_message_ajax/42",
        )
        summary.observe({
            "method": "Network.requestWillBeSent",
            "params": {
                "requestId": "analytics",
                "request": {
                    "method": "POST",
                    "url": "https://coconala.com/tr/",
                },
            },
        })
        summary.observe({
            "method": "Network.loadingFinished",
            "params": {"requestId": "analytics"},
        })

        self.assertEqual(summary.rows(), [])
        self.assertFalse(summary.settled())

        summary.observe({
            "method": "Network.requestWillBeSent",
            "params": {
                "requestId": "wrong-method",
                "request": {
                    "method": "PUT",
                    "url": "https://coconala.com/mypage/direct_message_ajax/42",
                },
            },
        })
        summary.observe({
            "method": "Network.loadingFinished",
            "params": {"requestId": "wrong-method"},
        })

        self.assertEqual(summary.rows(), [])
        self.assertFalse(summary.settled())

        summary.observe({
            "method": "Network.requestWillBeSent",
            "params": {
                "requestId": "native-submit",
                "request": {
                    "method": "POST",
                    "url": "https://coconala.com/mypage/direct_message_ajax/42",
                },
            },
        })
        self.assertFalse(summary.settled())
        summary.observe({
            "method": "Network.responseReceived",
            "params": {
                "requestId": "native-submit",
                "response": {"status": 200},
            },
        })
        summary.observe({
            "method": "Network.loadingFinished",
            "params": {"requestId": "native-submit"},
        })

        self.assertEqual(summary.rows(), [{
            "method": "POST",
            "path": "/mypage/direct_message_ajax/42",
            "status": 200,
            "outcome": "finished",
        }])
        self.assertTrue(summary.settled())

    def test_read_after_does_not_accept_old_hash_plus_unrelated_new_seller_message(self):
        browser = self.browser.CoconalaCdpReplyBrowser(
            Path("/tmp/cdp-helper"),
            self.url,
            verify_attempts=1,
            verify_timeout_seconds=1.0,
        )
        outgoing = "reused bounded reply"
        outgoing_hash = self.browser.outgoing_sha256(outgoing)
        browser.before = {
            "seller_count": 1,
            "seller_message_hashes": [outgoing_hash],
        }
        browser.outgoing_hash = outgoing_hash
        browser.tab = type("Tab", (), {"ws": "ws://example.test/page"})()
        after = {
            "talkroom_id": "42",
            "url": self.url,
            "fingerprint": "after",
            "seller_count": 2,
            "seller_message_hashes": [outgoing_hash, "b" * 64],
            "seller_sent_at": "2026-07-22T06:08:12+00:00",
            "last_sender": "seller",
        }
        browser._read = lambda: ({}, after)
        original_evaluate = self.browser._evaluate

        async def fake_evaluate(ws, expression):
            return {
                "ok": True,
                "textarea_length": 12,
                "button_disabled": False,
                "visible_error_count": 0,
                "url_path": "/mypage/direct_message/42",
            }

        self.browser._evaluate = fake_evaluate
        try:
            result = browser.read_after()
        finally:
            self.browser._evaluate = original_evaluate

        self.assertIn("send_diagnostic", result)

    def test_read_after_retries_transient_navigation_before_verifying(self):
        browser = self.browser.CoconalaCdpReplyBrowser(
            Path("/tmp/cdp-helper"), self.url, verify_attempts=2,
        )
        outgoing = "bounded reply"
        browser.before = {"seller_count": 0}
        browser.outgoing_hash = self.browser.outgoing_sha256(outgoing)
        browser.send_network = [{
            "method": "POST",
            "path": "/mypage/direct_message/42",
            "status": 200,
            "outcome": "finished",
        }]
        after = {
            "talkroom_id": "42",
            "url": self.url,
            "fingerprint": "after",
            "seller_count": 1,
            "seller_message_hashes": [browser.outgoing_hash],
            "seller_sent_at": "2026-07-22T06:07:12+00:00",
            "last_sender": "seller",
        }
        reads = iter([RuntimeError("navigation in progress"), ({}, after)])
        browser._read = lambda: (
            (_ for _ in ()).throw(value) if isinstance(value := next(reads), Exception)
            else value
        )
        original_sleep = self.browser.time.sleep
        self.browser.time.sleep = lambda _: None
        try:
            result = browser.read_after()
        finally:
            self.browser.time.sleep = original_sleep

        self.assertEqual(result["seller_message_hashes"], [browser.outgoing_hash])
        self.assertEqual(result["send_network"], browser.send_network)

    def test_read_after_has_one_total_deadline_not_nested_retry_multiplication(self):
        browser = self.browser.CoconalaCdpReplyBrowser(
            Path("/tmp/cdp-helper"),
            self.url,
            verify_attempts=40,
            verify_timeout_seconds=1.0,
        )
        browser.before = {"seller_count": 0}
        browser.outgoing_hash = "a" * 64
        calls = []
        browser._read = lambda: (
            calls.append("read"),
            (_ for _ in ()).throw(RuntimeError("navigation in progress")),
        )[1]
        ticks = iter([0.0, 0.0, 2.0])
        original_monotonic = self.browser.time.monotonic
        original_sleep = self.browser.time.sleep
        self.browser.time.monotonic = lambda: next(ticks, 2.0)
        self.browser.time.sleep = lambda _: None
        try:
            result = browser.read_after()
        finally:
            self.browser.time.monotonic = original_monotonic
            self.browser.time.sleep = original_sleep

        self.assertEqual(result["status"], "read_failed")
        self.assertEqual(calls, ["read"])

    def test_reply_browser_uses_background_tab_with_a_real_viewport(self):
        calls = []

        class FakeTab:
            def __init__(self, helper, url, *, hidden=False, background=False):
                calls.append((helper, url, hidden, background))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        original = self.browser.collector.DefaultTab
        self.browser.collector.DefaultTab = FakeTab
        try:
            helper = Path("/tmp/cdp-helper")
            with self.browser.CoconalaCdpReplyBrowser(helper, self.url):
                pass
        finally:
            self.browser.collector.DefaultTab = original

        self.assertEqual(calls, [(helper, self.url, False, True)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
