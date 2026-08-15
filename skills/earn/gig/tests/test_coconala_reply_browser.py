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
            "own_user_path": "/users/9999999",
            "messages": [
                {
                    "author_path": "/users/6231861",
                    "sent_at": "2026-07-22 15:06:11",
                    "body": "private buyer question",
                },
                {
                    "author_path": "/users/9999999",
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

        conversation = context["conversation"]
        self.assertEqual(
            [{"side": row["side"], "body": row["body"]} for row in conversation],
            [
                {"side": "buyer", "body": "private buyer question"},
                {"side": "seller", "body": "specific helpful reply"},
            ],
        )
        self.assertEqual([row["role"] for row in conversation], ["buyer", "seller"])
        self.assertEqual(
            [row["sent_at"] for row in conversation],
            ["2026-07-22 15:06:11", "2026-07-22 15:07:12"],
        )
        self.assertTrue(all(row["message_id"].startswith("sha256_") for row in conversation))
        self.assertEqual(bounded["talkroom_id"], "42")
        self.assertEqual(bounded["url"], self.url)
        self.assertEqual(bounded["seller_count"], 1)
        self.assertEqual(bounded["seller_sent_at"], "2026-07-22T06:07:12+00:00")
        self.assertEqual(bounded["latest_buyer_sent_at"], "2026-07-22T06:06:11+00:00")
        self.assertEqual(bounded["last_sender"], "seller")
        self.assertEqual(context["counterparty_user_id"], "6231861")
        self.assertEqual(bounded["seller_messages"], [{
            "body_sha256": bounded["seller_message_hashes"][0],
            "sent_at": "2026-07-22T06:07:12+00:00",
        }])
        serialized = json.dumps(bounded, ensure_ascii=False)
        self.assertNotIn("private buyer question", serialized)
        self.assertNotIn("specific helpful reply", serialized)
        self.assertEqual(len(bounded["seller_message_hashes"][0]), 64)
        self.assertEqual(len(bounded["fingerprint"]), 64)
        self.assertNotIn("6231861", json.dumps(bounded))

    def _reply_browser_for_application(self, *, after=None):
        browser = self.browser.CoconalaCdpReplyBrowser(Path("/tmp/cdp-helper"), self.url)
        browser.required_official_context = "application"
        browser.tab = type("Tab", (), {"ws": "ws://example.test/page"})()
        raw = self.raw()
        raw["messages"].append({"author_path": "/users/6231861", "sent_at": "2026-07-22 15:08:11", "body": "応募時の見積りから変更はありますか？"})
        initial = self.browser.thread_state(raw, self.url)
        fresh = after or initial
        reads = iter((initial, fresh))
        browser._read = lambda: next(reads)
        browser._navigate_to = lambda url: None
        return browser, initial

    def _application_page(self, *cards, url=None, next_href=None, title="応募・スカウト管理 | ココナラ", later_page_present=None):
        return {
            "url": url or self.browser.APPLIED_APPLICATIONS_URL,
            "title": title,
            "cards": list(cards),
            "next_href": next_href,
            "pagination_later_page_present": next_href is not None if later_page_present is None else later_page_present,
        }

    @staticmethod
    def _card(*, offer_id="6311743", title="同じ案件", buyer="6231861"):
        card = {
            "offer_url": f"https://coconala.com/mypage/offers/{offer_id}",
            "title": title,
            "title_byte_length": len(title.encode("utf-8")),
            "title_overflow": False,
            "card_text": "提案額50,000円 納品予定日2026/08/14",
        }
        if buyer is not None:
            card["buyer_user_path"] = f"/users/{buyer}"
        return card

    @staticmethod
    def _offer(*, offer_id="6311743", requester="6231861", request_id="5205196", foreign=None, expire_date="2026-08-14", proposal_body="応募時の提案本文"):
        paths = [f"/users/{requester}"]
        if foreign is not None:
            paths.append(f"/users/{foreign}")
        return {"url": f"https://coconala.com/mypage/offers/{offer_id}", "user_paths": paths, "user_paths_count": len(paths), "user_paths_overflow": False, "request_id": request_id, "offer_price": "50000", "expire_date": expire_date, "proposal_body": proposal_body, "proposal_body_byte_length": len(proposal_body.strip().encode("utf-8")), "proposal_body_overflow": False}

    def test_unique_exact_user_application_is_verified_and_thread_round_trip_is_fresh(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
        browser._read_offer_page = lambda url: self._offer()
        context, bounded = browser.read_before()
        self.assertEqual(context["verified_application"]["price_jpy"], 50000)
        self.assertEqual(context["verified_application"]["deliver_date"], "2026-08-14")
        self.assertEqual(context["verified_application"]["requester_user_id"], "6231861")
        self.assertEqual(context["verified_application"]["offer_url"], "https://coconala.com/mypage/offers/6311743")
        self.assertIs(browser.before, bounded)

    def test_application_list_pathname_offer_url_is_verified(self):
        browser, _ = self._reply_browser_for_application()
        card = self._card()
        card["offer_url"] = "/mypage/offers/6311743"
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(card)
        browser._read_offer_page = lambda url: self._offer()
        context, _ = browser.read_before()
        self.assertEqual(context["verified_application"]["offer_url"], "https://coconala.com/mypage/offers/6311743")

    def test_offer_url_rejects_noncanonical_origins_and_suffixes(self):
        for value in ("//coconala.com/mypage/offers/1", "https://evil.example/mypage/offers/1", "https://coconala.com/mypage/offers/1?x=1", "https://coconala.com/mypage/offers/1#x"):
            with self.subTest(value=value):
                self.assertIsNone(self.browser.CoconalaCdpReplyBrowser._canonical_offer_url(value))

    def test_application_list_pagination_scans_all_pages_before_detail_and_fails_ambiguity(self):
        page2 = f"{self.browser.APPLIED_APPLICATIONS_URL}?page=2"
        pages = {
            self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(offer_id="6311743"), next_href=page2),
            page2: self._application_page(self._card(offer_id="6311744"), url=page2),
        }
        browser, _ = self._reply_browser_for_application()
        list_calls, detail_calls = [], []
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: list_calls.append(url) or pages[url]
        browser._read_offer_page = lambda url: detail_calls.append(url) or self._offer(offer_id=url.rsplit("/", 1)[-1])
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "ambiguous_application"):
            browser.read_before()
        self.assertEqual(list_calls, [self.browser.APPLIED_APPLICATIONS_URL, page2])
        self.assertEqual(detail_calls, [])

        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: pages[url]
        browser._read_offer_page = lambda url: self._offer(
            offer_id=url.rsplit("/", 1)[-1],
            request_id="5205196" if url.endswith("6311743") else "5205197",
        )
        applications = browser._find_verified_applications("6231861", "/users/9999999")
        self.assertEqual([row["offer_id"] for row in applications], ["6311743", "6311744"])

    def test_application_list_jump_page_is_rejected(self):
        page3 = f"{self.browser.APPLIED_APPLICATIONS_URL}?page=3"
        pages = {
            self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(), next_href=page3),
            page3: self._application_page(self._card(), url=page3),
        }
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: pages[url]
        browser._read_offer_page = lambda url: self._offer()
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application_pagination"):
            browser.read_before()

    def test_application_list_empty_or_error_terminal_is_not_absence(self):
        for title, cards in (("応募・スカウト管理 | ココナラ", ()), ("エラー | ココナラ", (self._card(),))):
            with self.subTest(title=title):
                browser, _ = self._reply_browser_for_application()
                browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL, title=title, cards=cards: self._application_page(*cards, title=title)
                with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application"):
                    browser.read_before()

    def test_valid_nonempty_terminal_page_verifies(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(), next_href=None)
        browser._read_offer_page = lambda url: self._offer()
        context, _ = browser.read_before()
        self.assertEqual(context["verified_application"]["offer_id"], "6311743")

    def test_unrecognized_later_page_cannot_be_accepted_as_terminal(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(
            self._card(), next_href=None, later_page_present=True,
        )
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application_pagination"):
            browser.read_before()

    def test_application_list_target_on_later_page_verifies_only_that_detail(self):
        page2 = f"{self.browser.APPLIED_APPLICATIONS_URL}?page=2"
        pages = {
            self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(offer_id="6311742", buyer="9999998"), next_href=page2),
            page2: self._application_page(self._card(offer_id="6311743"), url=page2),
        }
        browser, _ = self._reply_browser_for_application()
        detail_calls = []
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: pages[url]
        browser._read_offer_page = lambda url: detail_calls.append(url) or self._offer()
        context, _ = browser.read_before()
        self.assertEqual(detail_calls, ["https://coconala.com/mypage/offers/6311743"])
        self.assertEqual(context["verified_application"]["offer_id"], "6311743")

    def test_detail_may_include_own_user_but_read_before_binds_it_transiently(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
        browser._read_offer_page = lambda url: self._offer(foreign="9999999")
        context, _ = browser.read_before()
        self.assertEqual(context["verified_application"]["requester_user_id"], "6231861")
        self.assertEqual(context["_own_user_path"], "/users/9999999")

    def test_application_list_invalid_next_or_missing_terminal_fails_closed(self):
        base = self.browser.APPLIED_APPLICATIONS_URL
        invalid_nexts = ("https://evil.example/mypage/job_matching/applied/offers?page=2", f"{base}?page=2&sort=new", base)
        for next_href in invalid_nexts:
            with self.subTest(next_href=next_href):
                browser, _ = self._reply_browser_for_application()
                browser._read_applied_page = lambda url=base, next_href=next_href: self._application_page(self._card(), next_href=next_href)
                browser._read_offer_page = lambda url: self._offer()
                with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application_pagination"):
                    browser.read_before()
        browser, _ = self._reply_browser_for_application()
        page = self._application_page(self._card())
        del page["next_href"]
        browser._read_applied_page = lambda url=base: page
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application_pagination"):
            browser.read_before()

    def test_application_pagination_budget_truncation_fails_closed(self):
        base = self.browser.APPLIED_APPLICATIONS_URL
        browser, _ = self._reply_browser_for_application()

        def page(url=base):
            index = int(url.split("page=")[-1]) if "page=" in url else 1
            next_href = f"{base}?page={index + 1}"
            return self._application_page(self._card(buyer="9999998"), url=url, next_href=next_href)

        browser._read_applied_page = page
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application_pagination_truncated"):
            browser.read_before()

    def test_application_card_without_exact_buyer_path_never_opens_detail(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(buyer=None))
        detail_calls = []
        browser._read_offer_page = lambda url: detail_calls.append(url) or self._offer()
        context, _ = browser.read_before()
        self.assertNotIn("verified_application", context)
        self.assertEqual(detail_calls, [])

    def test_application_dom_overflow_metadata_fails_closed(self):
        cases = ({"title_byte_length": 513, "title_overflow": True}, {"title_byte_length": 512, "title_overflow": False, "proposal_body_byte_length": 4097, "proposal_body_overflow": True})
        for metadata in cases:
            with self.subTest(metadata=metadata):
                browser, _ = self._reply_browser_for_application()
                card = self._card()
                card.update({key: value for key, value in metadata.items() if key.startswith("title")})
                detail = self._offer()
                detail.update({key: value for key, value in metadata.items() if key.startswith("proposal")})
                browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL, card=card: self._application_page(card)
                browser._read_offer_page = lambda url, detail=detail: detail
                context, _ = browser.read_before()
                self.assertNotIn("verified_application", context)

    def test_application_detail_path_overflow_metadata_rejects_seventeenth_user(self):
        browser, _ = self._reply_browser_for_application()
        detail = self._offer()
        detail.update({"user_paths_count": 17, "user_paths_overflow": True})
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
        browser._read_offer_page = lambda url: detail
        context, _ = browser.read_before()
        self.assertNotIn("verified_application", context)

    def test_unrelated_buyer_message_skips_application_lookup_and_navigation(self):
        for body in ("こんにちは", "ありがとうございます", "動画編集できますか"):
            with self.subTest(body=body):
                browser = self.browser.CoconalaCdpReplyBrowser(Path("/tmp/cdp-helper"), self.url)
                raw = self.raw()
                raw["messages"][-1]["body"] = body
                initial = self.browser.thread_state(raw, self.url)
                reads = iter((initial,))
                browser._read = lambda: next(reads)
                browser._read_applied_page = lambda: (_ for _ in ()).throw(AssertionError("application lookup was not skipped"))
                navigated = []
                browser._navigate_to = lambda url: navigated.append(url)
                context, _ = browser.read_before()
                self.assertNotIn("verified_application", context)
                self.assertEqual(navigated, [])

    def test_application_page_overflow_fails_closed_instead_of_slicing(self):
        browser, _ = self._reply_browser_for_application()
        cards = [self._card(offer_id=str(6311000 + index), buyer="9999998") for index in range(self.browser.MAX_APPLICATION_CARDS + 1)]
        cards[-1] = self._card(offer_id="6311743")
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(*cards)
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "application_page_truncated"):
            browser.read_before()

    def test_offer_detail_with_target_and_foreign_user_is_rejected(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
        browser._read_offer_page = lambda url: self._offer(foreign="7777777")
        context, _ = browser.read_before()
        self.assertNotIn("verified_application", context)

    def test_invalid_date_or_4097_byte_proposal_is_rejected(self):
        for changes in ({"expire_date": "2026-02-30"}, {"proposal_body": "x" * 4097}):
            with self.subTest(changes=changes):
                browser, _ = self._reply_browser_for_application()
                browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
                browser._read_offer_page = lambda url, changes=changes: self._offer(**changes)
                context, _ = browser.read_before()
                self.assertNotIn("verified_application", context)

    def test_652_byte_production_proposal_is_preserved_exactly(self):
        proposal = "x" * 652
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
        browser._read_offer_page = lambda url: self._offer(proposal_body=proposal)
        context, _ = browser.read_before()
        self.assertEqual(context["verified_application"]["proposal_body"], proposal)

    def test_1142_byte_official_proposal_is_preserved_exactly(self):
        proposal = "x" * 1142
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
        browser._read_offer_page = lambda url: self._offer(proposal_body=proposal)
        context, _ = browser.read_before()
        self.assertEqual(context["verified_application"]["proposal_body"], proposal)

    def test_same_name_or_title_with_different_user_id_never_verifies(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(buyer="9999998", title="同じ案件"))
        browser._read_offer_page = lambda url: self._offer(requester="9999998")
        context, _ = browser.read_before()
        self.assertNotIn("verified_application", context)

    def test_zero_candidates_is_safe_and_multiple_exact_candidates_fail_closed(self):
        browser, _ = self._reply_browser_for_application()
        browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(
            self._card(buyer="9999998")
        )
        browser._read_offer_page = lambda url: self._offer(requester="9999998")
        context, _ = browser.read_before()
        self.assertNotIn("verified_application", context)
        ambiguous, _ = self._reply_browser_for_application()
        ambiguous._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card(offer_id="6311743"), self._card(offer_id="6311744"))
        ambiguous._read_offer_page = lambda url: self._offer(
            offer_id=url.rsplit("/", 1)[-1]
        )
        with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "ambiguous"):
            ambiguous.read_before()

    def test_changed_thread_fingerprint_or_sender_blocks_before_composition(self):
        for key, value in (("fingerprint", "f" * 64), ("last_sender", "seller")):
            changed = self.browser.thread_state(self.raw(), self.url)
            changed[1][key] = value
            browser, _ = self._reply_browser_for_application(after=changed)
            browser._read_applied_page = lambda url=self.browser.APPLIED_APPLICATIONS_URL: self._application_page(self._card())
            browser._read_offer_page = lambda url: self._offer()
            with self.assertRaisesRegex(self.browser.collector.CollectorUnhealthy, "thread_changed"):
                browser.read_before()

    def test_missing_own_identity_is_unhealthy_not_assumed(self):
        cases = (("own_user_path", None, "missing_sender_identity"),
                 ("own_user_path", "/users/not-a-number", "sender"),
                 ("buyer_path", "/users/not-a-number", "counterparty"),
                 ("multiple", "/users/6231862", "counterparty"))
        for kind, value, reason in cases:
            raw = self.raw()
            if kind == "own_user_path": raw["own_user_path"] = value
            elif kind == "buyer_path": raw["messages"][0]["author_path"] = value
            else: raw["messages"].insert(1, {"author_path": value, "sent_at": "2026-07-22 15:06:30", "body": "another buyer"})
            with self.assertRaisesRegex(Exception, reason): self.browser.thread_state(raw, self.url)

    def test_the_raised_failure_keeps_the_diagnosis_the_page_returned(self):
        # fill_expression was taught to return the page's candidates, and the failure still
        # read "missing_message_input" and nothing else: _evaluate raised
        # str(value["error"]) and dropped every other key. A diagnosis nobody can see is the
        # same as no diagnosis -- eight buyers stayed unanswered either way.
        message = self.browser.evaluate_failure_message({
            "ok": False,
            "error": "missing_message_input",
            "location": "https://coconala.com/mypage/direct_message/93000002",
            "title": "ログイン | ココナラ",
            "candidates": [{"tag": "TEXTAREA", "id": "Body", "name": "body"}],
            "forms": ["/users/login"],
        })

        self.assertIn("missing_message_input", message)
        self.assertIn("direct_message/93000002", message)
        self.assertIn("ログイン", message)
        self.assertIn("TEXTAREA", message)
        self.assertIn("/users/login", message)

    def test_a_failure_without_extra_keys_reads_exactly_as_before(self):
        message = self.browser.evaluate_failure_message({"ok": False, "error": "boom"})
        self.assertEqual(message, "boom")

    def test_a_failure_with_no_error_at_all_is_still_named(self):
        message = self.browser.evaluate_failure_message({"ok": False})
        self.assertTrue(message)

    def test_a_missing_input_reports_what_the_page_actually_had(self):
        # 2026-08-05/06: eight buyers sat unanswered, the oldest since 08-01, and every
        # attempt failed with the bare string "missing_message_input". The selector is a
        # legacy CakePHP id/name pair, so if Coconala reshapes the direct-message page the
        # lane fails forever and the evidence says only that something was missing -- never
        # what the page contained instead, which is the one fact needed to fix it.
        fill = self.browser.fill_expression("bounded reply")

        self.assertIn("missing_message_input", fill)
        # The failure has to carry the page's real candidates back with it.
        self.assertIn("candidates", fill)
        self.assertIn("textarea", fill)
        self.assertIn("location.href", fill)

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
        original_navigation = browser._fresh_navigation
        navigation_failures = []

        async def fail_navigation(timeout):
            navigation_failures.append(timeout)
            raise RuntimeError("fresh navigation failed")

        async def fake_evaluate(ws, expression):
            return {
                "ok": True,
                "textarea_length": 12,
                "button_disabled": False,
                "visible_error_count": 0,
                "url_path": "/mypage/direct_message/42",
            }

        self.browser._evaluate = fake_evaluate
        browser._fresh_navigation = fail_navigation
        try:
            result = browser.read_after()
        finally:
            self.browser._evaluate = original_evaluate
            browser._fresh_navigation = original_navigation

        self.assertIn("send_diagnostic", result)
        self.assertEqual(result["status"], "read_failed")
        self.assertEqual(len(navigation_failures), 1)

    def test_read_after_refreshes_stale_dom_before_accepting_exact_delta(self):
        browser = self.browser.CoconalaCdpReplyBrowser(
            Path("/tmp/cdp-helper"), self.url,
            verify_attempts=2, verify_timeout_seconds=1.0,
        )
        outgoing_hash = self.browser.outgoing_sha256("bounded reply")
        browser.before = {"seller_count": 0, "seller_message_hashes": []}
        browser.outgoing_hash = outgoing_hash
        browser.send_network = [{"method": "POST", "path": "/mypage/direct_message_ajax/42",
                                 "status": 200, "outcome": "finished"}]
        browser.tab = type("Tab", (), {"ws": "ws://example.test/page"})()
        stale = {"seller_count": 0, "seller_message_hashes": []}
        fresh = {
            **stale,
            "seller_count": 1,
            "seller_message_hashes": [outgoing_hash],
        }
        connect_calls = []
        navigate_calls = []

        def fake_read():
            return ({}, fresh if navigate_calls else stale)

        class FakeConnection:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *args):
                return None

        async def fake_call(ws, request_id, method, params):
            if method == "Page.navigate":
                navigate_calls.append((ws, request_id, params))
            return {}

        def fake_connect(ws_url, **kwargs):
            connect_calls.append(ws_url)
            return FakeConnection()

        original_call = self.browser.collector.call
        original_connect = self.browser.websockets.connect
        browser._read = fake_read
        self.browser.collector.call = fake_call
        self.browser.websockets.connect = fake_connect
        try:
            result = browser.read_after()
        finally:
            self.browser.collector.call = original_call
            self.browser.websockets.connect = original_connect

        self.assertEqual(connect_calls, ["ws://example.test/page"])
        self.assertEqual(navigate_calls[0][1:], (1, {"url": self.url}))
        self.assertEqual(len(navigate_calls), 1)
        self.assertEqual(result["seller_count"], 1)
        self.assertEqual(result["seller_message_hashes"], [outgoing_hash])
        self.assertEqual(result["send_network"], browser.send_network)

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

    def test_read_after_rechecks_deadline_after_fresh_navigation(self):
        browser = self.browser.CoconalaCdpReplyBrowser(
            Path("/tmp/cdp-helper"), self.url,
            verify_attempts=2, verify_timeout_seconds=0.30,
        )
        browser.before = {"seller_count": 0, "seller_message_hashes": []}
        browser.outgoing_hash = self.browser.outgoing_sha256("bounded reply")
        browser.tab = type("Tab", (), {"ws": "ws://example.test/page"})()
        stale = {"seller_count": 0, "seller_message_hashes": []}
        reads, refreshes, sleeps = [], [], []
        clock = [0.0]

        def fake_read():
            reads.append(clock[0])
            return ({}, stale)

        async def fake_navigation(timeout):
            refreshes.append(timeout)
            clock[0] = 0.31

        original_monotonic = self.browser.time.monotonic
        original_sleep = self.browser.time.sleep
        original_evaluate = self.browser._evaluate
        original_navigation = browser._fresh_navigation
        browser._read = fake_read
        browser._fresh_navigation = fake_navigation
        self.browser.time.monotonic = lambda: clock[0]
        self.browser.time.sleep = lambda seconds: sleeps.append(seconds)
        self.browser._evaluate = lambda ws, expression: {"ok": True}
        try:
            result = browser.read_after()
        finally:
            self.browser.time.monotonic = original_monotonic
            self.browser.time.sleep = original_sleep
            self.browser._evaluate = original_evaluate
            browser._fresh_navigation = original_navigation

        self.assertEqual(len(reads), 1)
        self.assertEqual(len(refreshes), 1)
        self.assertEqual(refreshes[0], browser.verify_timeout_seconds)
        self.assertEqual(sleeps, [])
        self.assertEqual(result["status"], "read_failed")
        self.assertIn("send_diagnostic", result)

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
