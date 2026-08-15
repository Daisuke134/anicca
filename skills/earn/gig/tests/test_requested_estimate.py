"""Focused contracts for the requested-estimate lane.

These tests deliberately load the production modules by path, matching the rest of the
Gig suite.  No browser, provider, network, Telegram, or production database is touched.
"""

from __future__ import annotations

import importlib.util
import json
import asyncio
import os
import sqlite3
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _resolve_global_node_modules() -> str | None:
    """Use the repository's existing jsdom test convention without new deps."""
    try:
        completed = subprocess.run(
            ["npm", "root", "-g"], capture_output=True, text=True, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


NODE_GLOBAL_MODULES = _resolve_global_node_modules()
JSDOM_AVAILABLE = bool(NODE_GLOBAL_MODULES) and (Path(NODE_GLOBAL_MODULES) / "jsdom").is_dir()

DIRECT_MESSAGE_JS_HARNESS = r'''
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { JSDOM } = require("jsdom");
let input = "";
for await (const chunk of process.stdin) input += chunk;
const payload = JSON.parse(input);
const dom = new JSDOM(`<!doctype html>
<div class="sidebar-profile"><a href="/users/2564121">自分</a></div>
  <div class="platform-notice">${payload.sendingUnavailable ? "相手の方は現在ココナラの利用を制限されているため、メッセージのやりとりができません。" : ""}</div>
  <div class="js_thread-wrapper">
    <div class="threadColomun" id="message-6311423" data-message-id="message-6311423">
      <div class="threadUser"><a href="/users/2564121">seller</a></div>
      <div class="threadPostTime">2026-08-12 12:47:55</div>
      <div class="threadMessage">
        <p class="message-customize">見積り提案をしました</p>
        <a class="customize-title-link" href="/mypage/direct_offers/6311423">詳細</a>
        <p class="customize-title">バイマ出品作業 12件</p>
        <p>購入期限8/19 提案額 500円 完了予定日8/26</p>
        <p class="customize-content wa_add-mt-4">BUYMAへの商品登録作業12件を、ご指定の内容に沿って対応します。
          完了予定日：2026-08-26（2週間後）</p>
      </div>
    </div>
  </div>`, {url: payload.location, runScripts: "outside-only"});
Object.defineProperty(dom.window.HTMLElement.prototype, "innerText", {
  configurable: true,
  get() { return this.textContent || ""; },
});
const result = dom.window.eval(payload.expression);
process.stdout.write(JSON.stringify(result));
'''


def run_direct_message_expression(expression: str, *, sending_unavailable: bool = False) -> dict:
    if not JSDOM_AVAILABLE:
        pytest.skip("node + global jsdom not available")
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", DIRECT_MESSAGE_JS_HARNESS],
        input=json.dumps({
            "location": "https://coconala.com/mypage/direct_message/10074114",
            "expression": expression,
            "sendingUnavailable": sending_unavailable,
        }),
        text=True,
        capture_output=True,
        check=True,
        cwd=ROOT.parents[1],
        env={**os.environ, "NODE_PATH": NODE_GLOBAL_MODULES},
    )
    return json.loads(completed.stdout)


def load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"requested_estimate_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def estimate():
    return load("requested_estimate")


def msg(side: str, body: str, *, message_id: str | None = None, sent_at: str = "2026-08-12T00:00:00+00:00"):
    return {
        "side": side,
        "body": body,
        "message_id": message_id,
        "sent_at": sent_at,
    }


def source_dom(messages, *, url="https://coconala.com/mypage/direct_message/10074114",
               estimate_url="https://coconala.com/direct_offers/add/5993046", structured_offers=None,
               sending_unavailable=False):
    return {
        "url": url,
        "title": "メッセージ詳細 | マイページ | ココナラ",
        "container_present": True,
        "not_found_present": False,
        "error_present": False,
        "own_user_path": "/users/seller",
        "estimate_url": estimate_url,
        "structured_offers": structured_offers or [],
        "sending_unavailable": sending_unavailable,
        "messages": messages,
    }


def direct_source_dom(messages, *, url="https://coconala.com/mypage/direct_message/10074114",
                      sending_unavailable=False, estimate_url="https://coconala.com/direct_offers/add/5993046"):
    rows = []
    for row in messages:
        value = dict(row)
        value["author_path"] = "/users/seller" if value.get("side") == "seller" else "/users/buyer"
        rows.append(value)
    return source_dom(rows, url=url, sending_unavailable=sending_unavailable, estimate_url=estimate_url)


def na15_terms():
    return {
        "title": "バイマ出品作業　12件",
        "content": "バイマ出品作業12件を対応します。ご購入後に作業を開始します。",
        "price_jpy": 500,
        "purchase_plan": "single",
        "delivery_days": 14,
        "master_category_label": "ビジネス代行・事務代行",
        "sub_category_label": "ECサイト運用代行",
        "category_type_label": "EC商品登録代行",
    }


def test_buyer_last_explicit_request_is_estimate_only_and_has_no_raw_body(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "バイマ出品作業　12件を500円、2週間でお願いします。見積りよろしくお願いいたします。", message_id="buyer-1"),
    ]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["estimate_required"] is True
    assert result["estimate_url"] == "https://coconala.com/direct_offers/add/5993046"
    assert result["reply_required"] is False
    assert result["next_action"] == "requested_estimate"
    assert result["buyer_request_identity"] == "buyer-1"
    assert "バイマ" not in json.dumps(result, ensure_ascii=False)
    assert "body" not in result


def test_historical_request_before_estimate_rollout_is_observation_only(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg(
            "buyer",
            "バイマ出品作業　12件を500円、2週間でお願いします。見積りよろしくお願いいたします。",
            message_id="historical-buyer",
            sent_at="2026-07-21T15:29:24+00:00",
        ),
    ], url="https://coconala.com/mypage/direct_message/9997237"),
        "https://coconala.com/mypage/direct_message/9997237")

    assert result["estimate_required"] is False
    assert result["reply_required"] is False
    assert result["next_action"] == "estimate_pre_adoption"


def test_coconala_naive_message_time_is_jst_not_utc(estimate):
    parsed = estimate._timestamp("2026-08-12 09:18:29")
    assert parsed is not None
    assert parsed.isoformat() == "2026-08-12T09:18:29+09:00"


def test_seller_last_unfulfilled_commitment_remains_actionable(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "バイマ出品作業12件を500円、2週間でお願いします。見積りよろしくお願いします。", message_id="buyer-1"),
        msg("seller", "内容を確認しました。見積りをお送りします。", message_id="seller-1", sent_at="2026-08-12T00:01:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["estimate_required"] is True
    assert result["last_message_side"] == "seller"
    assert result["reply_required"] is False
    assert result["next_action"] == "requested_estimate"


def test_no_explicit_request_does_not_push_an_estimate(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "サービスの内容を教えてください。", message_id="buyer-1"),
    ]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["estimate_required"] is False
    assert result["reply_required"] is True
    assert result["next_action"] == "reply"


@pytest.mark.parametrize(
    ("body", "intent"),
    [
        ("サービスの内容を教えてください。", "question"),
        ("ありがとうございます。少し検討します。", "unclear"),
        ("条件をもう少し確認したいです。", "clarify"),
        ("600円、3日でお願いできますか？", "counter"),
        ("今回は見積りをお願いしません。", "reject"),
        ("今後の連絡は控えてください。", "stop"),
        ("AIの自動応答に見えるので、取引を中止します。", "concern"),
    ],
)
def test_latest_buyer_move_is_projected_without_unsolicited_estimate(estimate, body, intent):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id=f"buyer-{intent}")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )

    assert result["negotiation_intent"] == intent
    assert result["estimate_required"] is False


def test_explicit_estimate_request_is_ready_and_keeps_existing_executor_route(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "バイマ出品作業12件を500円、2週間でお願いします。見積りを送ってください。",
            message_id="buyer-explicit"),
    ]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is True
    assert result["next_action"] == "requested_estimate"


def test_complete_terms_and_purchase_intent_are_ready_but_wait_for_generic_executor(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "タイトル：画像加工 12件\n500円、納期14日、単発でお願いします。",
            message_id="buyer-ready"),
    ]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is False
    assert result["reply_required"] is False
    assert result["next_action"] == "ready_to_estimate"


def test_purchase_readiness_requires_an_explicit_purchase_plan(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "タイトル：画像加工 12件\n500円、納期14日で購入します。",
            message_id="buyer-missing-plan"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "clarify"
    assert result["reply_required"] is True
    assert result["estimate_required"] is False


def test_generic_readiness_never_combines_terms_across_negotiation_cycles(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "タイトル：ロゴ作成\n500円、納期14日、単発でお願いします。", message_id="old"),
        msg("buyer", "別件の動画編集を1,000円、納期7日で購入します。", message_id="new",
            sent_at="2026-08-12T00:01:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "clarify"
    assert result["reply_required"] is True
    assert result["estimate_required"] is False


def test_purchase_intent_with_incomplete_terms_requests_clarification_not_estimate(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "その内容でお願いします。", message_id="buyer-incomplete"),
    ]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["negotiation_intent"] == "clarify"
    assert result["estimate_required"] is False
    assert result["reply_required"] is True
    assert result["next_action"] == "reply"


@pytest.mark.parametrize("body", [
    "タイトル：画像加工12件。500円、納期14日、単発です。見積りをお願いできるか教えてください。",
    "見積りをお願いした場合の流れを教えてください。",
])
def test_estimate_questions_are_questions_not_proposal_requests(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-question")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] == "question"
    assert result["estimate_required"] is False
    assert result["reply_required"] is True


def test_acknowledgement_does_not_hide_later_explicit_estimate_request(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "ありがとうございます。条件を確認しました。見積りを送ってください。",
            message_id="buyer-ack-request"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is True


@pytest.mark.parametrize("body", [
    "「今後の連絡は控えてください」とは言っていません。",
    "見積りは不要ではありません。",
])
def test_negated_stop_or_refusal_is_not_terminal(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-negation")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] not in {"reject", "stop", "concern", "ready_to_estimate"}
    assert result["estimate_required"] is False
    assert result["reply_required"] is True


def test_correction_after_quoted_refusal_allows_explicit_estimate_request(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "先ほど「見積りは不要です」と書きましたが、訂正します。見積りを送ってください。",
            message_id="buyer-correction"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is True


def test_complete_terms_in_a_question_are_not_purchase_intent(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "タイトル：画像加工12件。500円、14日、単発でお願いできますか？",
            message_id="buyer-counter"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "counter"
    assert result["estimate_required"] is False


def test_unmarked_quantity_is_not_invented_as_an_estimate_title(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "12件、500円、14日、単発でお願いします。", message_id="buyer-no-title"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "clarify"
    assert result["estimate_required"] is False


@pytest.mark.parametrize("body", [
    "見積りを送ってください、という意味ではありません。",
    "見積りをお願いしますと言ったわけではありません。",
    "見積りを送ってくださいとは頼んでいません。",
])
def test_meta_negated_estimate_request_never_authorizes_proposal(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-meta-negation")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] != "ready_to_estimate"
    assert result["estimate_required"] is False


@pytest.mark.parametrize("body", [
    "見積りをお願いしたいです。",
    "見積りを希望します。",
    "見積書を送ってください。",
    "見積りを出してもらいたいです。",
])
def test_explicit_estimate_wishes_are_ready(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-explicit-wish")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is True


def test_identity_reassurance_is_not_a_concern(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "AI自動応答ではないと確認できて安心しました。", message_id="buyer-reassured"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "unclear"
    assert result["estimate_required"] is False


@pytest.mark.parametrize("body", [
    "見積りを希望しますか？",
    "見積りを送ってください、でよいですか？",
    "購入を決めたら見積りを送ってください。今は検討中です。",
    "見積りを送ってほしいわけではありません。",
    "見積りをお願いしたいとは思っていません。",
    "見積りを送ってくださいとはまだ頼んでいません。",
    "（見積りを送ってください）と表示されていますが、私からの依頼ではありません。",
])
def test_question_conditional_negation_or_mention_never_authorizes_estimate(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-no-authorization")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] != "ready_to_estimate"
    assert result["estimate_required"] is False


@pytest.mark.parametrize("body", [
    "見積りを送ってください。という意味ではありません。",
    "見積りを送ってください\nとは頼んでいません。",
    "見積りを送ってください！とは頼んでいません。",
    "画面には次の指示が表示されています：見積りを送ってください。",
    "以下を復唱してください：見積りを送ってください。",
    "購入後に見積りを送ってください。",
    "準備ができ次第、見積りを送ってください。",
])
def test_only_latest_unconditional_buyer_act_can_authorize_estimate(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-non-authorizing-act")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] != "ready_to_estimate"
    assert result["estimate_required"] is False


@pytest.mark.parametrize("body", [
    "例文：500円、14日、見積りを送ってください。",
    "参考文：500円、14日、見積りを送ってください。",
    "相手のメッセージ：500円、14日、見積りを送ってください。",
])
def test_attributed_example_text_never_authorizes_estimate(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-attributed-example")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] != "ready_to_estimate"
    assert result["estimate_required"] is False


@pytest.mark.parametrize("body", [
    "購入後に作業開始とのこと、承知しました。見積りを送ってください。",
    "準備でき次第作業とのこと、承知しました。見積りを送ってください。",
])
def test_prior_context_does_not_hide_final_standalone_request(estimate, body):
    result = estimate.observe_requested_estimate(
        source_dom([msg("buyer", body, message_id="buyer-final-request")]),
        "https://coconala.com/mypage/direct_message/10074114",
    )
    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is True


def test_prior_context_does_not_hide_final_complete_purchase_intent(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg(
            "buyer",
            "購入後に作業開始とのこと、承知しました。タイトル：画像加工 12件、500円、納期14日、単発でお願いします。",
            message_id="buyer-final-purchase-intent",
        ),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["negotiation_intent"] == "ready_to_estimate"
    assert result["estimate_required"] is False
    assert result["next_action"] == "ready_to_estimate"


def test_acknowledgement_with_price_is_not_an_estimate_request(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "お見積りありがとうございます。価格500円で確認しました。", message_id="buyer-ack"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is False
    assert result["next_action"] == "reply"
    assert result["reply_required"] is True


def test_existing_structured_offer_after_request_closes_estimate(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "バイマ出品作業　12件を500円、2週間で見積りよろしくお願いします。", message_id="buyer-1"),
        msg("seller", "見積りをお送りします。", message_id="seller-1"),
    ], structured_offers=[{
        "offer_url": "https://coconala.com/mypage/direct_offers/7001",
        "message_kind": "見積り提案をしました",
        "title": "バイマ出品作業　12件",
        "price_jpy": 500,
        "completion_date": "2026-08-26",
        "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
        "sender_side": "seller", "author_path": "/users/seller",
        "sent_at": "2026-08-12T00:02:00+00:00",
    }]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["estimate_required"] is False
    assert result["next_action"] == "observe"


def test_exact_request_card_closes_estimate(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "バイマ出品作業　12件を500円、2週間で見積りよろしくお願いします。", message_id="buyer-1"),
    ], structured_offers=[{
        "offer_url": "https://coconala.com/mypage/direct_offers/7001",
        "message_kind": "見積り提案をしました",
        "title": "バイマ出品作業　12件", "price_jpy": 500,
        "completion_date": "2026-08-26",
        "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
        "sender_side": "seller", "author_path": "/users/seller",
        "sent_at": "2026-08-12T00:02:00+00:00",
    }]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is False
    assert result["next_action"] == "observe"


def test_post_adoption_card_after_request_closes_when_form_url_disappeared(estimate):
    """The official seller card is the durable proof after the form URL vanishes."""
    result = estimate.observe_requested_estimate(source_dom([
        msg(
            "buyer",
            "バイマ出品作業　12件を500円、2週間で見積りよろしくお願いします。",
            message_id="buyer-post-adoption",
            sent_at="2026-08-12T03:00:00+00:00",
        ),
    ], estimate_url=None, structured_offers=[{
        "offer_url": "https://coconala.com/mypage/direct_offers/6311423",
        "message_kind": "見積り提案をしました",
        "title": "バイマ出品作業 12件", "price_jpy": 500,
        "completion_date": "2026-08-26",
        "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
        "sender_side": "seller", "author_path": "/users/seller",
        "sent_at": "2026-08-12T03:47:55+00:00",
    }]), "https://coconala.com/mypage/direct_message/10074114")

    assert result["next_action"] == "observe"
    assert result["reply_required"] is False
    assert result["estimate_required"] is False
    assert result.get("estimate_blocked") is None
    assert result.get("estimate_failure") is None


def test_arbitrary_or_unrendered_card_does_not_close_current_request(estimate):
    request = [msg("buyer", "バイマ出品作業　12件を500円、2週間で見積りよろしくお願いします。", message_id="buyer-1")]
    base_card = {
        "offer_url": "https://coconala.com/mypage/direct_offers/7001",
        "message_kind": "見積り提案をしました", "title": "バイマ出品作業　12件",
        "price_jpy": 500, "completion_date": "2026-08-26",
        "sent_at": "2026-08-12T00:02:00+00:00",
    }
    for card in (
        {**base_card, "message_kind": "通常メッセージ"},
        {**base_card, "offer_url": ""},
        {**base_card, "title": "別の作業 12件"},
        {**base_card, "content": "納期：2026-08-27（購入日から14日後）"},
    ):
        result = estimate.observe_requested_estimate(
            source_dom(request, structured_offers=[card]),
            "https://coconala.com/mypage/direct_message/10074114",
        )
        assert result["estimate_required"] is True
        assert result["next_action"] == "requested_estimate"


@pytest.mark.parametrize("bad_url", [None, "https://evil.example/direct_offers/add/5993046"])
def test_missing_or_unsafe_estimate_url_fails_closed(estimate, bad_url):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="buyer-1"),
    ], estimate_url=bad_url), "https://coconala.com/mypage/direct_message/10074114")

    assert result["estimate_required"] is False
    assert result["next_action"] == "estimate_failed"
    assert result["reply_required"] is False
    assert result["estimate_failure"] in {"missing_estimate_url", "unsafe_estimate_url"}


def test_estimate_url_query_and_fragment_fail_closed(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="buyer-1"),
    ], estimate_url="https://coconala.com/direct_offers/add/5993046?token=secret#x"),
        "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is False
    assert result["next_action"] == "estimate_failed"


def test_relative_estimate_url_is_canonicalized(estimate):
    assert estimate.sanitize_estimate_url("/direct_offers/add/5993046") == "https://coconala.com/direct_offers/add/5993046"
    assert estimate.sanitize_estimate_url("https://evil.example/direct_offers/add/5993046?secret=x") is None
    assert estimate.sanitize_estimate_url("https://coconala.com:444/direct_offers/add/5993046") is None
    assert estimate.sanitize_estimate_url("https://user:pass@coconala.com/direct_offers/add/5993046") is None


def test_live_title_brackets_are_normalized(estimate):
    context = {
        "buyer_messages": [msg("buyer", "タイトル：【バイマ出品作業　12件】\n500円、2週間、単発でお願いします。見積りください。", message_id="buyer-1")],
        "live_form": {"categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}}},
    }
    validated = estimate.validate_estimate_terms(na15_terms(), context)
    assert validated["title"] == "バイマ出品作業　12件"


def test_normal_queue_excludes_estimate_failed_and_stop_contact_rows(estimate):
    queue = load("reply_queue")
    snapshot = {
        "captured_at": "2026-08-12T00:00:00+00:00", "orders": [], "quotes": [],
        "inquiries": [
            {"talkroom_id": "1", "talkroom_url": "https://coconala.com/mypage/direct_message/1",
             "reply_required": False, "next_action": "estimate_failed", "last_message_side": "buyer"},
            {"talkroom_id": "2", "talkroom_url": "https://coconala.com/mypage/direct_message/2",
             "reply_required": False, "next_action": "stop_contact", "last_message_side": "buyer"},
            {"talkroom_id": "3", "talkroom_url": "https://coconala.com/mypage/direct_message/3",
             "reply_required": False, "next_action": "officially_unrepliable", "last_message_side": "buyer",
             "sending_unavailable": True, "reply_unavailable_reason": "counterparty_restricted"},
        ],
    }
    result = queue.build_queue(snapshot)
    assert result["items"] == []


def test_missing_estimate_url_is_actionable_failed_estimate_not_healthy_zero(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database_path = tmp_path / "outbox.sqlite3"
    snapshot = {"inquiries": [{
        "talkroom_id": "10074114", "talkroom_url": "https://coconala.com/mypage/direct_message/10074114",
        "reply_required": False, "estimate_required": False, "next_action": "estimate_failed",
        "estimate_blocked": True, "estimate_failure": "missing_estimate_url",
    }]}
    result = estimate.process_snapshot(
        snapshot, database_path=database_path, manifest=manifest,
        runner=ROOT / "scripts" / "agent_runner.py", schema=ROOT / "schemas" / "estimate_composition.schema.json",
        workdir=tmp_path, helper=None, owner="estimate-test", now=100,
        browser_factory=lambda *args, **kwargs: pytest.fail("blocked URL must not open browser"),
        composer=lambda *_: pytest.fail("blocked URL must not compose"),
    )
    assert result["estimate_required"] == 1
    assert result["estimate_failed"] == 1
    database = outbox.ConnectorOutbox(database_path, manifest)
    assert database.estimate_pending_actions() == []
    assert database.estimate_reconciliation_actions() == []


def test_complete_purchase_readiness_routes_to_existing_estimate_executor(tmp_path, estimate, monkeypatch):
    seen = []
    item = {
        "talkroom_id": "10080001",
        "talkroom_url": "https://coconala.com/mypage/direct_message/10080001",
        "last_message_side": "buyer",
        "negotiation_intent": "ready_to_estimate",
        "reply_required": False,
        "estimate_required": False,
        "next_action": "ready_to_estimate",
        "estimate_url": "https://coconala.com/direct_offers/add/7000001",
        "estimate_request_identity": "buyer-ready-1",
        "estimate_request_sent_at": "2026-08-12T12:00:00+00:00",
    }

    def execute(candidate, **_kwargs):
        seen.append(candidate)
        return {
            "thread_id": candidate["talkroom_id"], "status": "verified",
            "event_key": "coconala:estimate:v1:10080001:buyer-ready-1",
            "effect": 1, "official_readback": 1, "pending": 0,
            "failed": 0, "click": 1, "errors": [],
        }

    monkeypatch.setattr(estimate, "execute_requested_estimate", execute)
    result = estimate.process_snapshot(
        {"inquiries": [item]}, database_path=tmp_path / "outbox.sqlite3",
        manifest=ROOT / "config" / "connectors" / "coconala.json",
        runner=ROOT / "scripts" / "agent_runner.py",
        schema=ROOT / "schemas" / "estimate_composition.schema.json",
        workdir=tmp_path, helper=None, owner="generic-estimate-test", now=123,
        browser_factory=lambda *_args: pytest.fail("fake executor owns browser"),
        composer=lambda *_args: pytest.fail("fake executor owns composer"),
    )

    assert seen == [item]
    assert result["estimate_required"] == 1
    assert result["estimate_effect"] == 1
    assert result["estimate_readback"] == 1


def test_pending_scan_failure_keeps_postclick_reconcile_truth(tmp_path, estimate, monkeypatch):
    item = {
        "talkroom_id": "10080009",
        "talkroom_url": "https://coconala.com/mypage/direct_message/10080009",
        "reply_required": False,
        "estimate_required": True,
        "next_action": "requested_estimate",
        "semantic_context_sha256": "a" * 64,
        "semantic_estimate_terms": na15_terms(),
    }

    class Database:
        def estimate_pending_actions(self):
            raise sqlite3.OperationalError("database is locked")

        def estimate_reconciliation_actions(self):
            return []

    monkeypatch.setattr(estimate.outbox, "ConnectorOutbox", lambda *_args: Database())
    monkeypatch.setattr(estimate, "execute_requested_estimate", lambda *_args, **_kwargs: {
        "thread_id": item["talkroom_id"], "status": "reconcile_pending",
        "event_key": "coconala:estimate:v1:10080009:buyer-ready",
        "effect": 0, "official_readback": 0, "pending": 1,
        "failed": 0, "click": 1, "errors": [],
    })

    result = estimate.process_snapshot(
        {"inquiries": [item]}, database_path=tmp_path / "outbox.sqlite3",
        manifest=ROOT / "config" / "connectors" / "coconala.json",
        runner=ROOT / "scripts" / "agent_runner.py",
        schema=ROOT / "schemas" / "estimate_composition.schema.json",
        workdir=tmp_path, helper=None, owner="estimate-test", now=123,
    )

    assert result["estimate_pending"] == 1
    assert result["estimate_failed"] == 1
    assert result["estimate_events"][0]["status"] == "reconcile_pending"
    assert result["errors"] == ["estimate_pending_scan_failed:OperationalError"]


def test_fresh_buyer_cancellation_blocks_estimate_before_form_open(tmp_path, estimate):
    outbox = load("connector_outbox")
    database = outbox.ConnectorOutbox(
        tmp_path / "outbox.sqlite3", ROOT / "config" / "connectors" / "coconala.json",
    )
    item = {
        "talkroom_id": "10080002",
        "talkroom_url": "https://coconala.com/mypage/direct_message/10080002",
        "estimate_url": "https://coconala.com/direct_offers/add/7000002",
        "estimate_request_identity": "buyer-ready",
        "estimate_request_sha256": estimate._body_hash(
            "タイトル：画像加工12件。500円、14日、単発でお願いします。"
        ),
        "estimate_request_sent_at": "2026-08-12T12:00:00+00:00",
    }

    class Browser:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read_thread_context(self):
            return ({"buyer_messages": [
                msg("buyer", "タイトル：画像加工12件。500円、14日、単発でお願いします。",
                    message_id="buyer-ready"),
                msg("buyer", "今回は見積りをお願いしません。", message_id="buyer-cancelled"),
            ]}, {"structured_offers": []})
        def open_form(self):
            raise AssertionError("cancelled buyer intent must block before form open")

    result = estimate.execute_requested_estimate(
        item, database=database,
        composer=lambda *_args: pytest.fail("cancelled buyer intent must not compose"),
        browser_factory=lambda *_args, **_kwargs: Browser(), helper=None,
        owner="fresh-cancellation-test", now=100, hidden=True,
    )
    assert result["status"] == "failed"
    assert result["effect"] == 0
    assert result["click"] == 0
    assert result["errors"] == ["estimate_request_changed"]


def test_buyer_cancellation_during_composition_blocks_final_click(tmp_path, estimate):
    outbox = load("connector_outbox")
    database = outbox.ConnectorOutbox(
        tmp_path / "outbox.sqlite3", ROOT / "config" / "connectors" / "coconala.json",
    )
    terms = na15_terms()
    body = "タイトル：バイマ出品作業　12件\n500円、14日、単発でお願いします。"
    form = {
        "url": "https://coconala.com/direct_offers/add/7000003", "origin": "https://coconala.com",
        "path": "/direct_offers/add/7000003", "title": "提案内容を入力する", "method": "POST",
        "action": "https://coconala.com/direct_offers/add/7000003",
        "controls": list(estimate.EXPECTED_CONTROLS), "submit_text": "提案内容を確認する",
        "categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}},
    }
    clicks = []

    class Browser:
        def __enter__(self): return self
        def __exit__(self, *_args): return None
        def read_thread_context(self):
            return ({"buyer_messages": [msg("buyer", body, message_id="buyer-ready")]}, {
                "structured_offers": [], "own_user_path": "/users/seller",
            })
        def fresh_thread_context(self, expected_own_user_path):
            assert expected_own_user_path == "/users/seller"
            return {"own_user_path": "/users/seller", "buyer_messages": [
                msg("buyer", body, message_id="buyer-ready"),
                msg("buyer", "今回は見積りをお願いしません。", message_id="buyer-cancelled"),
            ]}
        def open_form(self): return form
        def select_master(self, *_args):
            return {**form, "categories": {
                "master": [{"label": terms["master_category_label"], "value": "13"}],
                "sub": [{"label": terms["sub_category_label"], "value": "668"}],
                "type": [{"label": terms["category_type_label"], "value": "293"}],
            }}
        def fill(self, *_args):
            return {"selected_categories": {
                "master": {"label": terms["master_category_label"], "value": "13"},
                "sub": {"label": terms["sub_category_label"], "value": "668"},
                "type": {"label": terms["category_type_label"], "value": "293"},
            }}
        def read_form(self):
            return {**form, "categories": {
                "master": [{"label": terms["master_category_label"], "value": "13", "selected": True}],
                "sub": [{"label": terms["sub_category_label"], "value": "668", "selected": True}],
                "type": [{"label": terms["category_type_label"], "value": "293", "selected": True}],
            }}
        def first_submit(self): return None
        def read_confirmation(self):
            return {
                "title": "提案内容を確認する", "title_value": terms["title"],
                "price_jpy": 500, "purchase_plan": "single", "completion_date": "2026-08-26",
                "content": "BUYMAへの商品登録作業12件を、ご指定の内容に沿って対応します。\n完了予定日：2026-08-26（2週間後）",
                "final_submit_text": "提案を送る",
            }
        def final_submit(self, *_args, **_kwargs): clicks.append(1)

    result = estimate.execute_requested_estimate(
        {
            "talkroom_id": "10080003", "talkroom_url": "https://coconala.com/mypage/direct_message/10080003",
            "estimate_url": "https://coconala.com/direct_offers/add/7000003",
            "estimate_request_identity": "buyer-ready", "estimate_request_sent_at": "2026-08-12T00:00:00+00:00",
            "estimate_terms": terms, "next_action": "ready_to_estimate",
        },
        database=database, composer=lambda *_args: pytest.fail("terms hint avoids compose"),
        browser_factory=lambda *_args, **_kwargs: Browser(), helper=None,
        owner="final-freshness-test", now=int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp()), hidden=True,
    )
    assert clicks == []
    assert result["status"] == "failed"
    assert result["click"] == 0
    assert result["errors"] == ["estimate_request_changed"]


def test_replied_estimate_lifecycle_closes_without_source_url(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    thread_url = "https://coconala.com/mypage/direct_message/10074114"
    base = int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp())
    event_key = estimate.coconala_estimate_event_key("10074114", "buyer-1")
    action = database.enqueue_estimate(
        event_key=event_key, thread_id="10074114", thread_url=thread_url, observed_at=base,
    )
    terms = estimate.materialize_delivery_content(na15_terms(), date(2026, 8, 12))
    database.close_already_delivered(
        int(action["action_id"]), thread_url=thread_url,
        outgoing_hash=estimate.offer_terms_hash(terms), seller_sent_at=base + 1,
        observed_at=base + 2,
    )

    def fail_enqueue(**kwargs):
        raise AssertionError("replied lifecycle must not enqueue again")

    database.enqueue_estimate = fail_enqueue
    result = estimate.execute_requested_estimate(
        {
            "talkroom_id": "10074114", "talkroom_url": thread_url,
            "estimate_url": None, "estimate_request_identity": "buyer-1",
        },
        database=database,
        composer=lambda *_: pytest.fail("replied lifecycle must not compose"),
        browser_factory=lambda *args, **kwargs: pytest.fail("replied lifecycle must not open browser"),
        helper=None, owner="estimate-recovery", now=base + 86400, hidden=True,
    )
    assert result == {
        "thread_id": "10074114", "status": "already_delivered",
        "event_key": event_key, "effect": 0, "official_readback": 1,
        "pending": 0, "failed": 0, "click": 0, "errors": [],
    }


def test_verified_estimate_after_request_fences_changed_event_identity(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    thread_id = "10074114"
    thread_url = f"https://coconala.com/mypage/direct_message/{thread_id}"
    base = int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp())
    terms = estimate.materialize_delivery_content(na15_terms(), date(2026, 8, 12))
    action = database.enqueue_estimate(
        event_key=estimate.coconala_estimate_event_key(thread_id, "buyer-old"),
        thread_id=thread_id, thread_url=thread_url, observed_at=base,
    )
    claim = database.claim(
        owner="estimate-first", now=base + 1, lease_seconds=100,
        action_id=action["action_id"],
    )
    intent = database.prepare_intent(
        action["action_id"], owner="estimate-first",
        fencing_token=claim["fencing_token"],
        outgoing_body=estimate.canonical_offer_terms(terms), now=base + 2,
        origin_at=base, store_outgoing_body=True,
    )
    database.mark_click_started(
        action["action_id"], intent["revision"], owner="estimate-first",
        fencing_token=claim["fencing_token"], now=base + 3,
    )
    database.record_delivery_unknown(
        action["action_id"], owner="estimate-first",
        fencing_token=claim["fencing_token"], now=base + 4,
    )
    database.reconcile(
        action["action_id"], thread_url=thread_url,
        outgoing_hash=estimate.offer_terms_hash(terms), seller_sent_at=base + 10,
        last_sender="seller", observed_at=base + 11, authoritative_absent=False,
    )

    new_key = estimate.coconala_estimate_event_key(thread_id, "buyer-new-identity")
    result = estimate.execute_requested_estimate(
        {
            "talkroom_id": thread_id, "talkroom_url": thread_url,
            "estimate_url": "/direct_offers/add/5993046",
            "estimate_request_identity": "buyer-new-identity",
            "estimate_request_sent_at": datetime.fromtimestamp(base, timezone.utc).isoformat(),
        },
        database=database, composer=lambda *_: pytest.fail("must not compose"),
        browser_factory=lambda *args, **kwargs: pytest.fail("must not open browser"),
        helper=None, owner="estimate-second", now=base + 20, hidden=True,
    )

    assert result["status"] == "already_delivered"
    assert result["effect"] == 0
    assert result["click"] == 0
    assert result["official_readback"] == 1
    assert database.action_lifecycle_for_event(new_key, thread_id)["state"] == "replied"
    assert database.verified_estimate_after_request(thread_id, base + 12) is None


def test_preclick_estimate_orphans_follow_current_semantic_truth(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database_path = tmp_path / "outbox.sqlite3"
    database = outbox.ConnectorOutbox(database_path, manifest)
    base = int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp())
    rows = []
    for thread_id, current in (("10070001", True), ("10070002", False)):
        event_key = estimate.coconala_estimate_event_key(thread_id, f"buyer-{thread_id}")
        database.enqueue_estimate(
            event_key=event_key, thread_id=thread_id,
            thread_url=f"https://coconala.com/mypage/direct_message/{thread_id}",
            observed_at=base,
        )
        rows.append({
            "talkroom_id": thread_id,
            "talkroom_url": f"https://coconala.com/mypage/direct_message/{thread_id}",
            "reply_required": False,
            "estimate_required": False,
            "next_action": "observe" if current else "semantic_pending",
            "semantic_failure": None if current else "semantic_receipt_pending",
            "semantic_context_sha256": "a" * 64,
        })

    result = estimate.process_snapshot(
        {"inquiries": rows}, database_path=database_path, manifest=manifest,
        runner=ROOT / "scripts" / "agent_runner.py",
        schema=ROOT / "schemas" / "estimate_composition.schema.json",
        workdir=tmp_path, helper=None, owner="orphan-repair", now=base + 10,
        browser_factory=lambda *args, **kwargs: pytest.fail("must not open browser"),
        composer=lambda *_: pytest.fail("must not compose"),
    )

    assert [(row["thread_id"], row["status"]) for row in result["estimate_events"]] == [
        ("10070001", "invalidated"), ("10070002", "honestly_pending"),
    ]
    assert result["estimate_effect"] == 0
    assert result["estimate_pending"] == 1
    assert [row["thread_id"] for row in database.estimate_pending_actions()] == ["10070002"]


def test_postclick_estimate_readback_dead_letters_after_five_no_click_passes(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    thread_id = "10074114"
    thread_url = f"https://coconala.com/mypage/direct_message/{thread_id}"
    base = int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp())
    terms = estimate.materialize_delivery_content(na15_terms(), date(2026, 8, 12))
    action = database.enqueue_estimate(
        event_key=estimate.coconala_estimate_event_key(thread_id, "buyer-1"),
        thread_id=thread_id, thread_url=thread_url, observed_at=base,
    )
    claim = database.claim(
        owner="estimate-click", now=base + 1, lease_seconds=100,
        action_id=action["action_id"],
    )
    intent = database.prepare_intent(
        action["action_id"], owner="estimate-click",
        fencing_token=claim["fencing_token"],
        outgoing_body=estimate.canonical_offer_terms(terms), now=base + 2,
        origin_at=base, store_outgoing_body=True,
    )
    database.mark_click_started(
        action["action_id"], intent["revision"], owner="estimate-click",
        fencing_token=claim["fencing_token"], now=base + 3,
    )
    database.record_delivery_unknown(
        action["action_id"], owner="estimate-click",
        fencing_token=claim["fencing_token"], now=base + 4,
    )

    class Browser:
        reads = 0
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read_after(self):
            self.reads += 1
            return {"structured_offers": [], "own_user_path": "/users/seller"}
        def open_form(self): raise AssertionError("reconcile must not open form")
        def final_submit(self, *args, **kwargs): raise AssertionError("reconcile must not click")

    browser = Browser()
    results = []
    for attempt in range(1, 6):
        pending = database.estimate_reconciliation_action_for_thread(thread_id)
        results.append(estimate._reconcile_existing(
            action=pending,
            item={"talkroom_id": thread_id, "talkroom_url": thread_url},
            terms=None, database=database,
            browser_factory=lambda *args, **kwargs: browser,
            helper=None, hidden=True, now=base + 10 + attempt,
        ))

    assert [row["status"] for row in results] == [
        "reconcile_pending", "reconcile_pending", "reconcile_pending",
        "reconcile_pending", "dlq",
    ]
    assert browser.reads == 5
    assert results[-1]["pending"] == 0
    assert results[-1]["failed"] == 1
    assert database.estimate_reconciliation_actions() == []
    assert database.dlq_actions()[0]["unresolved_attempts"] == 5


def test_existing_reconcile_precedes_missing_source_validation(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    thread_url = "https://coconala.com/mypage/direct_message/10074114"
    base = int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp())
    action = database.enqueue_estimate(
        event_key=estimate.coconala_estimate_event_key("10074114", "buyer-1"),
        thread_id="10074114", thread_url=thread_url, observed_at=base,
    )
    claim = database.claim(
        owner="estimate-recovery", now=base + 1, lease_seconds=100,
        action_id=action["action_id"],
    )
    terms = estimate.materialize_delivery_content(na15_terms(), date(2026, 8, 12))
    intent = database.prepare_intent(
        action["action_id"], owner="estimate-recovery",
        fencing_token=claim["fencing_token"],
        outgoing_body=estimate.canonical_offer_terms(terms), now=base + 2,
        origin_at=base, store_outgoing_body=True,
    )
    database.mark_click_started(
        action["action_id"], intent["revision"], owner="estimate-recovery",
        fencing_token=intent["fencing_token"], now=base + 3,
    )
    database.record_delivery_unknown(
        action["action_id"], owner="estimate-recovery",
        fencing_token=intent["fencing_token"], now=base + 4,
    )
    card = {
        "offer_url": "/mypage/direct_offers/6311423",
        "message_kind": "見積り提案をしました",
        "title": "バイマ出品作業 12件",
        "price_jpy": terms["price_jpy"],
        "completion_date": "2026-08-26",
        "content": terms["content"],
        "sender_side": "seller", "author_path": "/users/2564121",
        "sent_at": datetime.fromtimestamp(base + 10, timezone.utc).isoformat(),
    }

    class Browser:
        read_count = 0

        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read_after(self):
            self.read_count += 1
            return {"structured_offers": [card], "own_user_path": "/users/2564121"}
        def open_form(self): raise AssertionError("reconciliation must not open the form")
        def fill(self, *args): raise AssertionError("reconciliation must not fill")
        def first_submit(self): raise AssertionError("reconciliation must not submit")
        def final_submit(self, *args, **kwargs): raise AssertionError("reconciliation must not click")

    browser = Browser()
    result = estimate.process_snapshot(
        {"inquiries": [{
            "talkroom_id": "10074114", "talkroom_url": thread_url,
            "reply_required": False, "estimate_required": True,
            "next_action": "requested_estimate", "estimate_url": None,
            "estimate_request_identity": "buyer-1",
        }]},
        database_path=tmp_path / "outbox.sqlite3", manifest=manifest,
        runner=ROOT / "scripts" / "agent_runner.py", schema=ROOT / "schemas" / "estimate_composition.schema.json",
        workdir=tmp_path, helper=None, owner="estimate-recovery", now=base + 86400,
        browser_factory=lambda *args, **kwargs: browser,
        composer=lambda *_: pytest.fail("reconciliation must not compose"),
    )
    assert browser.read_count == 1
    assert result["estimate_effect"] == 0
    assert result["estimate_readback"] == 1
    assert result["estimate_pending"] == 0
    assert result["estimate_failed"] == 0
    assert database.estimate_reconciliation_actions() == []


def test_detector_merge_reports_estimate_effect_pending_and_failure_separately():
    detector = load("reply_detector")
    base = {"status": "completed", "actionable": 2, "effect": 1,
            "official_readback": 1, "pending": 0, "failed": 0, "errors": []}
    merged = detector.merge_estimate_metrics(
        base,
        {"estimate_required": 1, "estimate_effect": 1, "estimate_readback": 1,
         "estimate_pending": 0, "estimate_failed": 0, "estimate_events": [], "errors": []},
        normal_actionable=2,
    )
    assert merged["actionable"] == 3
    assert merged["effect"] == 2
    assert merged["official_readback"] == 2
    failed = detector.merge_estimate_metrics(
        {"status": "completed", "actionable": 0, "effect": 0,
         "official_readback": 0, "pending": 0, "failed": 0, "errors": []},
        {"estimate_required": 1, "estimate_effect": 0, "estimate_readback": 0,
         "estimate_pending": 1, "estimate_failed": 1, "estimate_events": [],
         "errors": ["estimate_form_identity_mismatch"]},
        normal_actionable=0,
    )
    assert failed["status"] == "failed"
    assert failed["pending"] == 1
    assert failed["failed"] == 1
    assert "estimate_form_identity_mismatch" in failed["errors"]


def test_requested_estimate_cli_runs_one_snapshot(tmp_path, estimate, capsys):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text('{"inquiries":[]}', encoding="utf-8")
    seen = {}

    def fake_process(value, **kwargs):
        seen.update({"snapshot": value, **kwargs})
        return {"estimate_required": 0, "estimate_effect": 0, "estimate_readback": 0}

    rc = estimate.main([
        "run", "--snapshot", str(snapshot),
        "--database", str(tmp_path / "outbox.sqlite3"),
        "--owner", "estimate-cli-test", "--now", "123",
    ], process=fake_process)
    assert rc == 0
    assert seen["snapshot"] == {"inquiries": []}
    assert seen["owner"] == "estimate-cli-test"
    assert seen["now"] == 123
    assert json.loads(capsys.readouterr().out)["estimate_effect"] == 0


def test_buyer_stop_after_request_prevents_estimate(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="buyer-1"),
        msg("buyer", "見積りは不要です。", message_id="buyer-2", sent_at="2026-08-12T00:02:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is False
    assert result["estimate_failure"] == "buyer_refused_estimate"


def test_same_message_refusal_is_terminal_and_not_normal_reply(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "見積りは不要ですので送らないでください。", message_id="buyer-stop"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is False
    assert result["reply_required"] is False
    assert result["next_action"] == "stop_contact"


def test_operational_report_after_request_is_terminal(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="buyer-1"),
        msg("buyer", "運営に報告しますので、見積りは不要です。", message_id="buyer-stop", sent_at="2026-08-12T00:02:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is False
    assert result["reply_required"] is False
    assert result["next_action"] == "stop_contact"


def test_restricted_notice_is_bounded_and_suppresses_buyer_reply(estimate):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10074114"
    result = collector.direct_message_event(
        direct_source_dom([msg("buyer", "サービスの内容を教えてください。", message_id="restricted-buyer")],
                          sending_unavailable=True),
        url,
    )
    assert result["reply_required"] is False
    assert result["next_action"] == "officially_unrepliable"
    assert result["sending_unavailable"] is True
    assert result["reply_unavailable_reason"] == "counterparty_restricted"
    assert "body" not in result


def test_restricted_estimate_request_is_not_estimate_eligible_or_cacheable(estimate):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10074114"
    result = collector.direct_message_event(
        direct_source_dom([msg(
            "buyer", "500円、2週間で見積りよろしくお願いします。", message_id="restricted-estimate",
        )], sending_unavailable=True),
        url,
    )
    assert result["next_action"] == "officially_unrepliable"
    assert result["reply_required"] is False
    assert result["estimate_required"] is False
    assert result["sending_unavailable"] is True
    assert result["reply_unavailable_reason"] == "counterparty_restricted"
    assert result.get("estimate_blocked") is None
    assert result.get("estimate_failure") is None
    assert estimate._estimate_items({"inquiries": [result]}) == []
    readback = {
        **result,
        "preview_sha256": "a" * 64,
        "last_message_identity_sha256": "b" * 64,
        "thread_read_at": "2026-08-12T00:03:00+00:00",
    }
    assert collector._valid_direct_readback(readback) is True


def test_restricted_blocked_estimate_fields_are_removed_from_terminal_event(estimate):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10074114"
    result = collector.direct_message_event(
        direct_source_dom([msg(
            "buyer", "500円、2週間で見積りよろしくお願いします。", message_id="restricted-blocked",
        )], sending_unavailable=True, estimate_url=None),
        url,
    )
    assert result["next_action"] == "officially_unrepliable"
    assert result.get("estimate_blocked") is None
    assert result.get("estimate_failure") is None


def test_same_buyer_message_without_restricted_notice_remains_normal_reply(estimate):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10074114"
    result = collector.direct_message_event(
        direct_source_dom([msg("buyer", "サービスの内容を教えてください。", message_id="normal-buyer")]),
        url,
    )
    assert result["reply_required"] is True
    assert result["next_action"] == "reply"


@pytest.mark.parametrize(
    ("messages", "last_message_side", "next_action", "reply_required", "reason"),
    [
        ([
            msg("buyer", "自動応答は今後はやめていただけますでしょうか。", message_id="identity-stop"),
            msg("seller", "承知しました。", sent_at="2026-08-12T00:01:00+00:00"),
        ], "seller", "stop_contact", False, "fraud_or_identity_concern"),
        ([
            msg("buyer", "自動応答をやめていただけますか。", message_id="identity-stop-yes"),
            msg("seller", "承知しました。", sent_at="2026-08-12T00:01:00+00:00"),
        ], "seller", "stop_contact", False, "fraud_or_identity_concern"),
        ([
            msg("buyer", "自動応答をやめていただけませんでしょうか。", message_id="identity-stop-negative"),
            msg("seller", "承知しました。", sent_at="2026-08-12T00:01:00+00:00"),
        ], "seller", "stop_contact", False, "fraud_or_identity_concern"),
        ([
            msg("buyer", "自動応答をやめていただく方法を教えてください。", message_id="identity-question"),
        ], "buyer", "reply", True, None),
    ],
)
def test_polite_identity_stop_request_is_bounded(
    estimate, messages, last_message_side, next_action, reply_required, reason,
):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10070627"
    result = collector.direct_message_event(direct_source_dom(messages, url=url), url)
    assert result["last_message_side"] == last_message_side
    assert result["next_action"] == next_action
    assert result["reply_required"] is reply_required
    assert result["estimate_required"] is False
    assert result.get("reply_unavailable_reason") == reason


@pytest.mark.parametrize("left, right", [("「", "」"), ("『", "』"), ('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’")])
def test_quoted_explicit_estimate_does_not_auto_propose(estimate, left, right):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10070627"
    body = f"{left}バイマ出品作業12件を500円、2週間で見積りよろしくお願いします。{right}"
    result = collector.direct_message_event(
        direct_source_dom([msg("buyer", body, message_id="quote-contract")], url=url), url,
    )
    assert result["estimate_required"] is False
    assert result["next_action"] != "requested_estimate"


@pytest.mark.parametrize(
    ("url", "messages", "next_action", "reply_required", "reason"),
    [
        ("https://coconala.com/mypage/direct_message/10027881", [
            msg("buyer", "まだ、最終的な話までしてませんが。それで先に請求画面って？ 他の方探して下さい。",
                message_id="stop-buyer"),
        ], "stop_contact", False, "buyer_refused"),
        ("https://coconala.com/mypage/direct_message/10070627", [
            msg("buyer", "AIの自動応答はやめてください。運営に報告します。", message_id="identity"),
            msg("seller", "承知しました。", message_id="seller-last",
                sent_at="2026-08-12T00:01:00+00:00"),
        ], "stop_contact", False, "fraud_or_identity_concern"),
        ("https://coconala.com/mypage/direct_message/10027881", [
            msg("buyer", "この機能のやめ方を教えてください", message_id="how-to-stop"),
        ], "reply", True, None),
        ("https://coconala.com/mypage/direct_message/10070627", [
            msg("buyer", "AIを使っていますか？", message_id="ai-question"),
        ], "reply", True, None),
        ("https://coconala.com/mypage/direct_message/10074114", [
            msg("buyer", "この内容で結構です。次の手順を教えてください。", message_id="ambiguous-1"),
        ], "reply", True, None),
        ("https://coconala.com/mypage/direct_message/10074114", [
            msg("buyer", "見送りますか？手続きを教えてください。", message_id="ambiguous-2"),
        ], "reply", True, None),
        ("https://coconala.com/mypage/direct_message/10074114", [
            msg("buyer", "やめる方法を教えてください。", message_id="ambiguous-3"),
        ], "reply", True, None),
        ("https://coconala.com/mypage/direct_message/10027881", [
            msg("buyer", "返信をやめてください。", message_id="old-stop"),
            msg("buyer", "サービス内容を教えてください。", message_id="new-question",
                sent_at="2026-08-12T00:01:00+00:00"),
        ], "reply", True, None),
    ],
)
def test_reply_conversation_state_source_contract(
    estimate, url, messages, next_action, reply_required, reason,
):
    collector = load("coconala_queue_snapshot")
    result = collector.direct_message_event(direct_source_dom(messages, url=url), url)
    assert result["next_action"] == next_action
    assert result["reply_required"] is reply_required
    assert result.get("reply_unavailable_reason") == reason


@pytest.mark.parametrize("body, reason", [
    ("今回は見積もりをお願いしません。", "buyer_refused"),
    ("今後の連絡は控えてください。", "buyer_requested_stop"),
    ("詐欺だと思うので、取引を中止します。", "fraud_or_identity_concern"),
])
def test_fresh_review_stop_boundaries(estimate, body, reason):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10027881"
    result = collector.direct_message_event(
        direct_source_dom([msg("buyer", body, message_id="review-boundary")], url=url), url,
    )
    assert result["next_action"] == "stop_contact"
    assert result["reply_required"] is False
    assert result["reply_unavailable_reason"] == reason
    assert result["estimate_required"] is False


def test_terminal_direct_readback_requires_bounded_reason(estimate):
    collector = load("coconala_queue_snapshot")
    base = {
        "last_message_side": "buyer", "buyer_sent_at": "2026-08-12T00:00:00+00:00",
        "message_id": "buyer-1", "reply_required": False,
    }
    restricted = {
        **base, "next_action": "officially_unrepliable", "sending_unavailable": True,
        "reply_unavailable_reason": "counterparty_restricted",
    }
    assert "sending_unavailable" in collector._DIRECT_READBACK_FIELDS
    assert "reply_unavailable_reason" in collector._DIRECT_READBACK_FIELDS
    assert collector._valid_direct_readback(restricted)
    assert not collector._valid_direct_readback({**restricted, "reply_unavailable_reason": None})
    assert not collector._valid_direct_readback({**restricted, "reply_unavailable_reason": "unknown"})
    assert collector._valid_direct_readback({
        **base, "next_action": "stop_contact", "sending_unavailable": False,
        "reply_unavailable_reason": "buyer_requested_stop",
    })


@pytest.mark.parametrize("side, sent_key, reason", [
    ("buyer", "buyer_sent_at", "buyer_refused"),
    ("buyer", "buyer_sent_at", "fraud_or_identity_concern"),
    ("buyer", "buyer_sent_at", "buyer_requested_stop"),
    ("seller", "seller_sent_at", "fraud_or_identity_concern"),
])
def test_terminal_direct_readback_accepts_bounded_stop_reasons(estimate, side, sent_key, reason):
    collector = load("coconala_queue_snapshot")
    readback = {
        "last_message_side": side, sent_key: "2026-08-12T00:00:00+00:00",
        "message_id": "buyer-bounded", "reply_required": False,
        "next_action": "stop_contact", "sending_unavailable": False,
        "reply_unavailable_reason": reason,
    }
    assert collector._valid_direct_readback(readback)
    assert not collector._valid_direct_readback({**readback, "reply_unavailable_reason": "unknown"})


def test_legacy_buyer_reply_cache_without_marker_is_revalidated(estimate):
    collector = load("coconala_queue_snapshot")
    legacy = {
        "last_message_side": "buyer", "buyer_sent_at": "2026-08-12T00:00:00+00:00",
        "message_id": "buyer-legacy", "reply_required": True, "next_action": "reply",
        "preview_sha256": "a" * 64, "last_message_identity_sha256": "b" * 64,
    }
    assert collector._valid_direct_readback(legacy) is False


def test_contradictory_reply_cache_with_restricted_marker_is_rejected(estimate):
    collector = load("coconala_queue_snapshot")
    contradictory = {
        "last_message_side": "buyer", "buyer_sent_at": "2026-08-12T00:00:00+00:00",
        "message_id": "buyer-contradictory", "reply_required": True, "next_action": "reply",
        "sending_unavailable": True, "reply_unavailable_reason": "counterparty_restricted",
    }
    assert collector._valid_direct_readback(contradictory) is False


def test_fresh_direct_events_emit_false_marker_for_normal_seller_and_estimate(estimate):
    collector = load("coconala_queue_snapshot")
    url = "https://coconala.com/mypage/direct_message/10074114"
    normal = collector.direct_message_event(
        direct_source_dom([msg("buyer", "サービスの内容を教えてください。", message_id="normal")]), url,
    )
    seller = collector.direct_message_event(
        direct_source_dom([msg("seller", "ご連絡ありがとうございます。", message_id="seller")]), url,
    )
    requested = collector.direct_message_event(
        direct_source_dom([msg(
            "buyer", "500円、2週間で見積りよろしくお願いします。", message_id="estimate",
        )]), url,
    )
    for result in (normal, seller, requested):
        assert result["sending_unavailable"] is False
        assert result.get("reply_unavailable_reason") is None
    assert normal["next_action"] == "reply"
    assert seller["next_action"] == "observe"
    assert requested["next_action"] == "requested_estimate"


def test_old_refusal_before_new_explicit_request_does_not_suppress_latest_request(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "見積りは不要です。", message_id="old-stop"),
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="new-request",
            sent_at="2026-08-12T00:02:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["estimate_required"] is True
    assert result["reply_required"] is False
    assert result["next_action"] == "requested_estimate"


def test_old_stop_before_new_normal_buyer_message_is_not_sticky(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "他の方探して下さい。", message_id="old-stop"),
        msg("buyer", "やはりサービス内容を教えてください。", message_id="new-normal",
            sent_at="2026-08-12T00:02:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["reply_required"] is True
    assert result["next_action"] == "reply"


def test_stop_after_request_then_new_normal_buyer_message_resets_estimate_state(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="request"),
        msg("buyer", "見積りは不要です。", message_id="stop",
            sent_at="2026-08-12T00:01:00+00:00"),
        msg("buyer", "やはりサービス内容を教えてください。", message_id="normal",
            sent_at="2026-08-12T00:02:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["reply_required"] is True
    assert result["next_action"] == "reply"
    assert result["estimate_required"] is False
    assert result.get("reply_unavailable_reason") is None


def test_stop_then_seller_then_new_normal_buyer_message_resets_estimate_state(estimate):
    result = estimate.observe_requested_estimate(source_dom([
        msg("buyer", "500円、2週間で見積りよろしくお願いします。", message_id="request"),
        msg("buyer", "見積りは不要です。", message_id="stop",
            sent_at="2026-08-12T00:01:00+00:00"),
        msg("seller", "承知しました。", message_id="seller",
            sent_at="2026-08-12T00:01:30+00:00"),
        msg("buyer", "やはりサービス内容を教えてください。", message_id="normal",
            sent_at="2026-08-12T00:02:00+00:00"),
    ]), "https://coconala.com/mypage/direct_message/10074114")
    assert result["reply_required"] is True
    assert result["next_action"] == "reply"
    assert result["estimate_required"] is False
    assert result.get("reply_unavailable_reason") is None


def test_structured_expression_does_not_read_template_script_as_offer(estimate):
    collector = load("coconala_queue_snapshot")
    expression = collector.DIRECT_MESSAGE_EXPRESSION
    assert "querySelectorAll('.message-customize')" in expression
    assert "querySelectorAll('script" not in expression


def test_direct_message_expression_reads_rendered_estimate_card(estimate):
    collector = load("coconala_queue_snapshot")
    dom = json.loads(run_direct_message_expression(collector.DIRECT_MESSAGE_EXPRESSION))
    assert dom["own_user_path"] == "/users/2564121"
    assert len(dom["structured_offers"]) == 1
    card = dom["structured_offers"][0]
    assert card["offer_url"] == "/mypage/direct_offers/6311423"
    assert card["title"] == "バイマ出品作業 12件"
    assert card["price_jpy"] == 500
    assert card["completion_date"] == "2026-08-26"
    assert card["content"] == (
        "BUYMAへの商品登録作業12件を、ご指定の内容に沿って対応します。"
        "\n          完了予定日：2026-08-26（2週間後）"
    )
    assert card["author_path"] == "/users/2564121"
    assert card["sender_side"] == "seller"
    assert estimate.match_official_offer_cards(
        [card], na15_terms(),
        click_started_at="2026-08-12 12:47:54",
        request_sent_at="2026-08-12 12:47:00",
        own_user_path="/users/2564121",
    ) == [card]


def test_direct_message_expression_emits_bounded_restricted_notice(estimate):
    collector = load("coconala_queue_snapshot")
    restricted = json.loads(run_direct_message_expression(
        collector.DIRECT_MESSAGE_EXPRESSION, sending_unavailable=True,
    ))
    normal = json.loads(run_direct_message_expression(collector.DIRECT_MESSAGE_EXPRESSION))
    assert restricted["sending_unavailable"] is True
    assert normal["sending_unavailable"] is False
    assert "相手の方は現在ココナラ" not in json.dumps(restricted)


def test_dynamic_category_options_must_contain_exact_labels(estimate):
    terms = na15_terms()
    form = {
        "url": "https://coconala.com/direct_offers/add/5993046", "origin": "https://coconala.com",
        "path": "/direct_offers/add/5993046", "title": "提案内容を入力する", "method": "POST",
        "action": "https://coconala.com/direct_offers/add/5993046", "controls": list(estimate.EXPECTED_CONTROLS),
        "submit_text": "提案内容を確認する",
        "categories": {"ビジネス代行・事務代行": {"other": ["EC商品登録代行"]}},
    }
    assert estimate.validate_form_identity(form, terms) is False


def test_completion_date_is_form_deadline_not_purchase_expiry(estimate):
    terms = na15_terms()
    materialized = estimate.materialize_delivery_content(terms, date(2026, 8, 12))
    assert "完了予定日：2026-08-26" in materialized["content"]
    assert "2週間後" in materialized["content"]
    assert "購入日から" not in materialized["content"]
    browser = load("coconala_estimate_browser")
    expression = browser.fill_expression(materialized, "2026-08-26")
    assert "2026-08-26" in expression
    assert "2026-08-19" not in expression


def test_completion_control_label_is_not_purchase_expiry(estimate):
    terms = na15_terms()
    form = {
        "url": "https://coconala.com/direct_offers/add/5993046", "origin": "https://coconala.com",
        "path": "/direct_offers/add/5993046", "title": "提案内容を入力する", "method": "POST",
        "action": "https://coconala.com/direct_offers/add/5993046",
        "controls": list(estimate.EXPECTED_CONTROLS),
        "submit_text": "提案内容を確認する", "completion_control_label": "完了予定日 ※必須",
        "categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}},
    }
    assert estimate.validate_form_contract(form) is True
    assert estimate.validate_form_contract({**form, "completion_control_label": "購入期限"}) is False


def test_dynamic_category_preflight_accepts_master_only_then_requires_postfill_ids(estimate):
    terms = na15_terms()
    context = {
        "buyer_messages": [msg(
            "buyer", "バイマ出品作業　12件を500円、2週間、単発で見積りお願いします。",
            message_id="buyer-1",
        )],
        "semantic_estimate_terms": {
            key: terms[key]
            for key in ("title", "content", "price_jpy", "purchase_plan", "delivery_days")
        },
        "live_form": {"categories": {
            "master": [{"label": terms["master_category_label"], "value": "13", "id": "13"}],
            "sub": [{"label": "選択してください", "value": "", "disabled": True}],
            "type": [{"label": "選択してください", "value": "", "disabled": True}],
        }},
    }
    assert estimate.validate_estimate_terms(terms, context)["delivery_days"] == 14
    selected = {
        "master": {"label": terms["master_category_label"], "value": "13", "id": "13"},
        "sub": {"label": terms["sub_category_label"], "value": "668", "id": "668"},
        "type": {"label": terms["category_type_label"], "value": "293", "id": "293"},
    }
    assert estimate.validate_selected_categories(selected, terms) is True
    assert estimate.validate_selected_categories({
        **selected,
        "type": {"label": terms["category_type_label"], "value": "777"},
    }, terms) is False
    assert estimate.validate_selected_categories(
        {**selected, "type": {"label": terms["category_type_label"], "value": ""}}, terms
    ) is False

    postfill = {
        "url": "https://coconala.com/direct_offers/add/5993046", "origin": "https://coconala.com",
        "path": "/direct_offers/add/5993046", "title": "提案内容を入力する", "method": "POST",
        "action": "https://coconala.com/direct_offers/add/5993046",
        "controls": list(estimate.EXPECTED_CONTROLS),
        "submit_text": "提案内容を確認する",
        "categories": {
            "master": [{"label": terms["master_category_label"], "value": "13", "selected": True}],
            "sub": [{"label": terms["sub_category_label"], "value": "668", "selected": True}],
            "type": [{"label": terms["category_type_label"], "value": "293", "selected": True}],
        },
    }
    assert estimate.validate_form_selection(postfill, terms) is True
    assert estimate.validate_form_selection({**postfill, "categories": {
        **postfill["categories"],
        "master": [{"label": terms["master_category_label"], "value": "999", "selected": True}],
    }}, terms) is False
    assert estimate.validate_form_selection({**postfill, "categories": {
        **postfill["categories"],
        "type": [{"label": terms["category_type_label"], "value": "293", "selected": False}],
    }}, terms) is False


def test_official_optional_category_type_requires_exact_mapping_and_dom_proof(estimate):
    terms = {
        **na15_terms(),
        "title": "簡単なピアノ譜をハンドベル譜に書き換えられる方　募集",
        "content": "小学3年生向けの3パート構成ハンドベル譜を作成し、各音符に階名を付記したPDFを納品します。",
        "price_jpy": 8000,
        "delivery_days": 3,
        "master_category_label": "音楽制作・ナレーション",
        "sub_category_label": "楽譜制作・耳コピ譜面作成",
        "category_type_label": None,
    }
    contract = {
        "mapping_loaded": True, "sub_value": "675", "mapping_has_sub": False,
        "mapped_option_count": 0, "control_disabled": True,
        "row_hidden": True, "enabled_option_count": 0,
    }
    form = {
        "url": "https://coconala.com/direct_offers/add/4234654",
        "origin": "https://coconala.com", "path": "/direct_offers/add/4234654",
        "title": "提案内容を入力する", "method": "POST",
        "action": "https://coconala.com/direct_offers/add/4234654",
        "controls": list(estimate.EXPECTED_CONTROLS),
        "submit_text": ["提案内容を確認する"],
        "category_type_contract": contract,
        "categories": {
            "master": [{"label": terms["master_category_label"], "value": "7", "selected": True}],
            "sub": [{"label": terms["sub_category_label"], "value": "675", "selected": True}],
            "type": [{"label": "選択してください", "value": "", "disabled": True}],
        },
    }
    context = {"semantic_estimate_terms": {
        key: terms[key] for key in ("title", "content", "price_jpy", "purchase_plan", "delivery_days")
    }, "live_form": form}
    assert estimate.validate_estimate_terms(terms, context)["category_type_label"] is None
    assert estimate.validate_form_identity(form, terms) is True
    assert estimate.validate_form_selection(form, terms) is True
    assert estimate.validate_selected_categories({
        "master": {"label": terms["master_category_label"], "value": "7"},
        "sub": {"label": terms["sub_category_label"], "value": "675"},
        "type": None,
    }, terms, contract) is True
    for mismatch in (
        {**contract, "mapping_loaded": False},
        {**contract, "mapped_option_count": 1},
        {**contract, "control_disabled": False},
        {**contract, "row_hidden": False},
        {**contract, "enabled_option_count": 1},
    ):
        bad = {**form, "category_type_contract": mismatch}
        assert estimate.validate_form_identity(bad, terms) is False
        with pytest.raises(estimate.TermsAmbiguous, match="optional_category_type_unverified"):
            estimate.validate_estimate_terms(terms, {**context, "live_form": bad})
    browser = load("coconala_estimate_browser")
    assert "mapped_option_count===0" in browser.select_sub_expression(terms["sub_category_label"])
    assert "optional_category_type_terms_mismatch" in browser.fill_expression(terms, "2026-08-18")


def test_browser_submit_contract_exposes_one_final_click(estimate):
    browser = load("coconala_estimate_browser")
    assert browser.final_submit_count(["提案を送る"]) == 1
    assert browser.final_submit_count(["提案を送る", "提案を送る"]) == 0
    assert browser.final_submit_count([]) == 0
    assert "単発購入" in browser.confirmation_expression()
    assert "定期購入" in browser.confirmation_expression()


def test_related_service_context_uses_verified_contract_model_and_exact_readback(estimate, tmp_path, monkeypatch):
    browser = load("coconala_estimate_browser")
    terms = na15_terms()
    scope = "BUYMA商品登録12件を対応します。価格は500円から個別見積です。"
    fields = {
        "service_id": "4330368", "public_url": "https://coconala.com/services/4330368",
        "title": "BUYMA出品作業", "state": "公開中", "price_jpy": 500,
        "category": "/".join((terms["master_category_label"], terms["sub_category_label"], terms["category_type_label"])),
        "public_content_sha256": estimate.hashlib.sha256(scope.encode()).hexdigest(),
    }
    version = estimate.hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    contract = {"version": 1, **fields, "scope_text": scope, "service_version_sha256": version, "observed_at": "now"}
    contracts = tmp_path / "offer-contracts.jsonl"
    contracts.write_text(json.dumps(contract, ensure_ascii=False) + "\n")

    def run(command, **kwargs):
        evidence = Path(command[command.index("--evidence-dir") + 1]); evidence.mkdir(parents=True)
        result = evidence / "result.json"; result.write_text(json.dumps({"label": "4330368"}))
        (evidence / "summary.json").write_text(json.dumps({"result_path": str(result)}))
        assert "price/scope contract" in kwargs["input"] and scope in kwargs["input"]
        return type("Done", (), {"returncode": 0})()

    monkeypatch.setattr(estimate.subprocess, "run", run)
    composer = estimate.RequestedEstimateComposer(
        runner=tmp_path / "runner", schema=tmp_path / "schema", workdir=tmp_path,
        contract_path=contracts,
    )
    selected = composer.select_related_service(terms)
    context = estimate.verified_related_service_context(selected, terms)
    observed = {
        "id": "4330368", "service_name": "OpenCV画像認識", "service_url": "/services/4330368",
        "master_category_label": terms["master_category_label"],
        "sub_category_label": terms["sub_category_label"],
        "category_type_label": terms["category_type_label"],
    }
    assert estimate.validate_related_service_observation(observed, terms, context)
    assert not estimate.validate_related_service_observation({**observed, "id": "4330369"}, terms, context)
    expression = browser.select_related_service_expression("4330368")
    assert "open.click()" in expression and "options[0].click()" in expression

    attribution = tmp_path / "attribution-map.jsonl"
    monkeypatch.setattr(estimate, "STOREFRONT_CONTRACTS_PATH", contracts)
    monkeypatch.setattr(estimate, "STOREFRONT_ATTRIBUTION_PATH", attribution)
    prepared = estimate._attribution_row(
        "prepared", context, event_key="coconala:estimate:v1:10:req", action_id=7,
        revision=1, observed_at=10,
    )
    assert estimate._append_attribution_once(prepared, attribution)
    assert estimate._prepared_related_service(prepared["event_key"], 7, 1, terms) == context
    assert estimate._prepared_related_service(prepared["event_key"], 7, 2, terms) is None
    accepted = estimate._attribution_row(
        "accepted", context, event_key=prepared["event_key"], action_id=7,
        revision=1, observed_at=11, offer_id="offer-1",
    )
    assert estimate._append_attribution_once(accepted, attribution)
    assert not estimate._append_attribution_once(accepted, attribution)
    assert attribution.stat().st_mode & 0o777 == 0o600

    contracts.write_text(json.dumps({**contract, "service_version_sha256": "a" * 64}) + "\n")
    with pytest.raises(ValueError, match="related_service_contract_invalid"):
        estimate.load_service_contracts(contracts)


def test_preclick_refresh_uses_a_separate_read_only_tab(estimate, monkeypatch):
    browser = load("coconala_estimate_browser")
    calls = []

    class Tab:
        ws = "ws://fresh-thread"

        def __init__(self, helper, url, *, hidden, background):
            calls.append((helper, url, hidden, background))

        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, *_args):
            calls.append("exit")

    async def inspect(ws, expression, url):
        assert ws == "ws://fresh-thread"
        assert expression == browser.collector.DIRECT_MESSAGE_EXPRESSION
        assert url == "https://coconala.com/mypage/direct_message/10074114"
        return {
            "url": "https://coconala.com/mypage/direct_message/10074114",
            "title": "メッセージ詳細", "container_present": True,
            "own_user_path": "/users/seller",
            "messages": [
                {"author_path": "/users/buyer", "body": "見積りをお願いします"},
                {"author_path": "/users/seller", "body": "承知しました"},
            ],
        }

    monkeypatch.setattr(browser.collector, "DefaultTab", Tab)
    monkeypatch.setattr(browser.collector, "inspect_message_page", inspect)
    instance = browser.CoconalaEstimateBrowser(
        Path("/tmp/helper"),
        "https://coconala.com/mypage/direct_message/10074114",
        "https://coconala.com/direct_offers/add/5993046",
    )
    primary = object()
    instance.tab = primary

    assert instance.fresh_thread_context("/users/seller") == {
        "own_user_path": "/users/seller", "buyer_messages": [{
        "author_path": "/users/buyer", "body": "見積りをお願いします", "side": "buyer",
    }]}
    assert instance.tab is primary
    assert calls == [
        (Path("/tmp/helper"), "https://coconala.com/mypage/direct_message/10074114", True, True),
        "enter", "exit",
    ]


def test_preclick_refresh_capability_is_mandatory(estimate):
    with pytest.raises(ValueError, match="estimate_fresh_read_unavailable"):
        estimate._fresh_context_before_click(object(), "/users/seller")


@pytest.mark.parametrize("own_user_path,author_path", [
    (None, "/users/seller"),
    ("/users/other-seller", "/users/buyer"),
    ("/users/seller", None),
])
def test_preclick_refresh_rejects_ambiguous_or_different_identity(
    estimate, monkeypatch, own_user_path, author_path,
):
    browser = load("coconala_estimate_browser")

    class Tab:
        ws = "ws://fresh-thread"
        def __init__(self, *_args, **_kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *_args): return None

    async def inspect(*_args):
        return {
            "url": "https://coconala.com/mypage/direct_message/10074114",
            "title": "メッセージ詳細", "container_present": True,
            "own_user_path": own_user_path,
            "messages": [{"author_path": author_path, "body": "見積りをお願いします"}],
        }

    monkeypatch.setattr(browser.collector, "DefaultTab", Tab)
    monkeypatch.setattr(browser.collector, "inspect_message_page", inspect)
    instance = browser.CoconalaEstimateBrowser(
        Path("/tmp/helper"),
        "https://coconala.com/mypage/direct_message/10074114",
        "https://coconala.com/direct_offers/add/5993046",
    )
    with pytest.raises(Exception):
        instance.fresh_thread_context("/users/seller")


def test_final_submit_waits_for_redirect_before_readback(estimate, monkeypatch):
    browser = load("coconala_estimate_browser")
    instance = browser.CoconalaEstimateBrowser(
        None,
        "https://coconala.com/mypage/direct_message/10074114",
        "https://coconala.com/direct_offers/add/5993046",
    )
    instance.tab = type("Tab", (), {"ws": "ws://default-tab"})()
    values = iter([
        {"ok": True},
        {"url": "https://coconala.com/direct_offers/add/5993046", "ready": "complete"},
        {"url": "https://coconala.com/mypage/direct_message/10074114", "ready": "complete"},
    ])
    calls = []
    async def fake_eval(*_args):
        calls.append(1)
        return next(values)
    monkeypatch.setattr(browser, "_eval", fake_eval)
    monkeypatch.setattr(browser.estimate, "validate_confirmation", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(browser.time, "sleep", lambda *_: None)
    instance.final_submit({"final_submit_labels": ["提案を送る"]}, na15_terms())
    assert instance.final_clicks == 1


def test_first_submit_waits_for_confirmation_page(estimate, monkeypatch):
    browser = load("coconala_estimate_browser")
    instance = browser.CoconalaEstimateBrowser(
        None,
        "https://coconala.com/mypage/direct_message/10074114",
        "https://coconala.com/direct_offers/add/5993046",
    )
    instance.tab = type("Tab", (), {"ws": "ws://default-tab"})()
    values = iter([
        {"ok": True},
        {"title": "提案内容を入力する", "final_submit_labels": []},
        {"title": "提案内容を確認する", "final_submit_labels": ["提案を送る"]},
    ])
    calls = []
    async def fake_eval(*_args):
        calls.append(1)
        return next(values)
    monkeypatch.setattr(browser, "_eval", fake_eval)
    monkeypatch.setattr(browser.time, "sleep", lambda *_: None)
    instance.first_submit()
    assert len(calls) == 3
    assert instance.network[-1]["phase"] == "confirmation"


def test_browser_eval_opens_ws_url_and_waits_for_dom_ready(estimate, monkeypatch):
    browser = load("coconala_estimate_browser")
    calls = []

    class Socket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def send(self, payload):
            calls.append(json.loads(payload))

        async def recv(self):
            request = calls[-1]
            if "ready:document.readyState" in request["params"]["expression"]:
                value = json.dumps({
                    "url": "https://coconala.com/direct_offers/add/5993046",
                    "ready": "complete",
                })
            else:
                value = json.dumps({"ok": True})
            return json.dumps({"id": request["id"], "result": {"result": {"value": value}}})

    def connect(*args, **kwargs):
        assert args == ("ws://default-tab",)
        assert kwargs["open_timeout"] == 15
        return Socket()

    monkeypatch.setattr(browser.websockets, "connect", connect)
    result = asyncio.run(browser._eval("ws://default-tab", "JSON.stringify({ok:true})"))
    assert result == {"ok": True}
    assert [call["id"] for call in calls] == [1, 2]


def test_browser_exposes_master_first_dynamic_category_step(estimate):
    browser = load("coconala_estimate_browser")
    assert hasattr(browser.CoconalaEstimateBrowser, "select_master")
    assert "master_category_option_missing_or_ambiguous" in browser.select_master_expression("ビジネス代行・事務代行")


def test_na15_composition_is_deterministic_and_does_not_call_model(estimate, monkeypatch, tmp_path):
    context = {"buyer_messages": [
        msg("buyer", "こちらのご契約でよろしければ、最初は12件500円からのご契約をさせて頂きたいのですがよろしいでしょうか？\n長期のご契約と思ってはいるのですが、最初は少額からご契約を結ばせていただければと思っています。\n作業に慣れて来られたら徐々に金額・件数を増やさせていただきます！\nこちらの条件でもよろしければ、\n\nタイトル：【バイマ出品作業　12件】\n金額：500円\nプラン：単発\n納期：2週間後\n\n上記内容で、見積もり提案からお手数ですがご提案をお願いできますでしょうか", message_id="na15-details"),
        msg("buyer", "Kosukeさんから見積り提案をしていただき、こちらが購入させていただければと思います！", message_id="na15-followup"),
        msg("buyer", "見積りよろしくお願いいたします", message_id="na15-request"),
    ]}
    form = {"categories": {
        "master": [{"label": "ビジネス代行・事務代行", "value": "13"}],
        "sub": [{"label": "選択してください", "value": "", "disabled": True}],
        "type": [{"label": "選択してください", "value": "", "disabled": True}],
    }}
    monkeypatch.setattr(estimate.subprocess, "run", lambda *_a, **_k: pytest.fail("model must not run"))
    composer = estimate.RequestedEstimateComposer(
        runner=tmp_path / "runner.py", schema=tmp_path / "schema.json", workdir=tmp_path,
    )
    terms = composer(context, form)
    assert terms == {
        "title": "バイマ出品作業　12件",
        "content": "BUYMAへの商品登録作業12件を、ご指定の内容に沿って対応します。",
        "price_jpy": 500,
        "purchase_plan": "single",
        "delivery_days": 14,
        "master_category_label": "ビジネス代行・事務代行",
        "sub_category_label": "ECサイト運用代行",
        "category_type_label": "EC商品登録代行",
    }


def test_other_buyer_terms_never_reuse_na15_price_or_count(estimate, monkeypatch, tmp_path):
    context = {"buyer_messages": [msg(
        "buyer",
        "タイトル：【BUYMA出品作業 20件】\n金額：800円\nプラン：単発\n納期：3週間後\n見積りをお願いします。",
        message_id="other-request",
    )]}
    form = {"categories": {
        "master": [{"label": "ビジネス代行・事務代行", "value": "13"}],
        "sub": [{"label": "選択してください", "value": "", "disabled": True}],
        "type": [{"label": "選択してください", "value": "", "disabled": True}],
    }}
    model_result = {
        "title": "BUYMA出品作業 20件",
        "content": "商品登録作業20件を、ご指定の内容に沿って対応します。",
        "price_jpy": 800,
        "purchase_plan": "single",
        "delivery_days": 21,
        "master_category_label": "ビジネス代行・事務代行",
        "sub_category_label": "ECサイト運用代行",
        "category_type_label": "EC商品登録代行",
    }
    calls = []
    def fake_run(command, **_kwargs):
        calls.append(command)
        evidence_dir = Path(command[command.index("--evidence-dir") + 1])
        evidence_dir.mkdir(parents=True, exist_ok=True)
        result_path = evidence_dir / "result.json"
        result_path.write_text(json.dumps(model_result, ensure_ascii=False), encoding="utf-8")
        (evidence_dir / "summary.json").write_text(
            json.dumps({"result_path": str(result_path)}), encoding="utf-8"
        )
        return type("Completed", (), {"returncode": 0})()
    monkeypatch.setattr(estimate.subprocess, "run", fake_run)
    composer = estimate.RequestedEstimateComposer(
        runner=tmp_path / "runner.py", schema=tmp_path / "schema.json", workdir=tmp_path,
    )
    composed = composer(context, form)
    assert len(calls) == 1
    assert composed["title"] == "BUYMA出品作業 20件"
    assert composed["price_jpy"] == 800
    assert composed["delivery_days"] == 21
    assert "20件" in composed["content"]
    assert "12件" not in composed["content"]
    # Validate the buyer-bound contract directly: another customer's terms do
    # not pass if any na15 value is reused.
    assert estimate.validate_estimate_terms(model_result, {**context, "live_form": form})["price_jpy"] == 800
    with pytest.raises(estimate.TermsAmbiguous, match="buyer_terms_mismatch"):
        estimate.validate_estimate_terms({**model_result, "price_jpy": 500}, {**context, "live_form": form})


def test_outbox_estimate_event_replaces_untouched_normal_action(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    db = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    normal = db.enqueue(event_key="coconala:message:v1:10074114:buyer-1", thread_id="10074114",
                        thread_url="https://coconala.com/mypage/direct_message/10074114", observed_at=1)
    created = db.enqueue_estimate(event_key=estimate.coconala_estimate_event_key("10074114", "buyer-2"),
                                  thread_id="10074114", thread_url="https://coconala.com/mypage/direct_message/10074114", observed_at=2)
    assert created["action_id"] != normal["action_id"]
    assert db.closed_actions(closure="nothing_to_say")[0]["reason"] == "nothing_to_say:requested_estimate"


def test_estimate_actions_are_invisible_to_normal_lane_before_and_after_click(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    db = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    url = "https://coconala.com/mypage/direct_message/10074114"
    key = estimate.coconala_estimate_event_key("10074114", "buyer-1")
    action = db.enqueue_estimate(event_key=key, thread_id="10074114", thread_url=url, observed_at=1)
    assert db.pending_actions() == []
    assert db.estimate_pending_actions()[0]["action_id"] == action["action_id"]
    claim = db.claim(owner="estimate-test", now=2, lease_seconds=100, action_id=action["action_id"])
    intent = db.prepare_intent(action["action_id"], owner="estimate-test", fencing_token=claim["fencing_token"], outgoing_body='{"delivery_days":14}', now=3)
    db.mark_click_started(action["action_id"], intent["revision"], owner="estimate-test", fencing_token=claim["fencing_token"], now=4)
    assert db.reconciliation_actions() == []
    assert db.estimate_reconciliation_actions()[0]["action_id"] == action["action_id"]


def test_estimate_and_normal_event_kinds_conflict_both_directions(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    url = "https://coconala.com/mypage/direct_message/10074114"
    db = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    db.enqueue_estimate(event_key=estimate.coconala_estimate_event_key("10074114", "buyer-1"), thread_id="10074114", thread_url=url, observed_at=1)
    with pytest.raises(outbox.OutboxError, match="estimate_event_conflict"):
        db.enqueue(event_key="coconala:message:v1:10074114:buyer-2", thread_id="10074114", thread_url=url, observed_at=2)
    db2 = outbox.ConnectorOutbox(tmp_path / "outbox2.sqlite3", manifest)
    normal = db2.enqueue(event_key="coconala:message:v1:10074114:buyer-2", thread_id="10074114", thread_url=url, observed_at=1)
    created = db2.enqueue_estimate(event_key=estimate.coconala_estimate_event_key("10074114", "buyer-3"), thread_id="10074114", thread_url=url, observed_at=2)
    assert created["action_id"] != normal["action_id"]


def test_preclick_normal_pending_is_closed_before_estimate_enqueue(tmp_path, estimate):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    url = "https://coconala.com/mypage/direct_message/10074114"
    db = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    normal = db.enqueue(event_key="coconala:message:v1:10074114:buyer-1", thread_id="10074114", thread_url=url, observed_at=1)
    estimate_action = db.enqueue_estimate(
        event_key=estimate.coconala_estimate_event_key("10074114", "buyer-2"),
        thread_id="10074114", thread_url=url, observed_at=2,
    )
    assert estimate_action["action_id"] != normal["action_id"]
    assert db.estimate_pending_actions()[0]["action_id"] == estimate_action["action_id"]
    assert db.pending_actions() == []
    assert db.closed_actions(closure="nothing_to_say")[0]["reason"] == "nothing_to_say:requested_estimate"


def test_estimate_event_key_is_thread_bound_and_dedupable(estimate):
    key = estimate.coconala_estimate_event_key("10074114", "buyer-1")
    assert key == "coconala:estimate:v1:10074114:buyer-1"
    assert estimate.validate_estimate_event_key(key, "10074114") == key
    with pytest.raises(ValueError, match="thread"):
        estimate.validate_estimate_event_key(key, "other-thread")
    with pytest.raises(ValueError):
        estimate.coconala_estimate_event_key("10074114", "buyer:1")


def test_estimate_schema_requires_exact_structured_terms(estimate):
    schema = json.loads((ROOT / "schemas" / "estimate_composition.schema.json").read_text())
    assert set(schema["required"]) == {
        "title", "content", "price_jpy", "purchase_plan", "delivery_days",
        "master_category_label", "sub_category_label", "category_type_label",
    }
    assert schema["additionalProperties"] is False
    assert schema["properties"]["purchase_plan"]["enum"] == ["single", "subscription"]
    assert schema["properties"]["price_jpy"]["minimum"] > 0
    assert schema["properties"]["delivery_days"]["minimum"] > 0


def test_ambiguous_or_missing_price_date_title_fails_before_click(estimate):
    context = {
        "buyer_messages": [msg("buyer", "見積りよろしくお願いします。", message_id="buyer-1")],
        "live_form": {"categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}}},
    }
    for terms in (
        {**na15_terms(), "price_jpy": None},
        {**na15_terms(), "delivery_days": None},
        {**na15_terms(), "title": ""},
        {**na15_terms(), "price_jpy": 500, "_buyer_price_candidates": [500, 700]},
    ):
        with pytest.raises(estimate.TermsAmbiguous):
            estimate.validate_estimate_terms(terms, context)


def test_na15_buyer_terms_override_later_seller_promise(estimate):
    terms = na15_terms()
    context = {
        "buyer_messages": [msg("buyer", "バイマ出品作業　12件、500円、2週間、単発でお願いします。", message_id="buyer-1")],
        "seller_messages": [msg("seller", "明日までに見積りを送ります。", message_id="seller-1")],
        "live_form": {"categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}}},
    }
    validated = estimate.validate_estimate_terms(terms, context)
    assert validated["price_jpy"] == 500
    assert validated["delivery_days"] == 14


def test_latest_buyer_term_update_replaces_prior_trial_without_cross_customer_default(estimate):
    context = {
        "buyer_messages": [
            msg("buyer", "タイトル：【バイマ出品作業　12件】\n金額：500円\nプラン：単発\n納期：2週間後\n見積りをお願いします。", message_id="trial"),
            msg("buyer", "次の契約条件は12件6,000円、単発、納期2週間でお願いします。", message_id="updated"),
            msg("buyer", "この条件で見積りをよろしくお願いします。", message_id="request"),
        ],
        "live_form": {"categories": {
            "master": [{"label": "ビジネス代行・事務代行", "value": "13"}],
            "sub": [{"label": "選択してください", "value": "", "disabled": True}],
            "type": [{"label": "選択してください", "value": "", "disabled": True}],
        }},
    }
    updated = {**na15_terms(), "price_jpy": 6000}
    assert estimate.validate_estimate_terms(updated, context)["price_jpy"] == 6000
    with pytest.raises(estimate.TermsAmbiguous, match="buyer_terms_mismatch"):
        estimate.validate_estimate_terms(na15_terms(), context)


def test_form_identity_and_controls_are_fail_closed(estimate):
    terms = na15_terms()
    valid = {
        "url": "https://coconala.com/direct_offers/add/5993046",
        "origin": "https://coconala.com",
        "path": "/direct_offers/add/5993046",
        "title": "提案内容を入力する",
        "method": "POST",
        "action": "https://coconala.com/direct_offers/add/5993046",
        "controls": ["RequestMasterCategory", "RequestSubCategory", "RequestMasterCategoryTypeId",
                      "RequestTitle", "OfferContent", "OfferIsSubscription0", "OfferIsSubscription1",
                      "OfferPrice", "OfferExpireDate", "data[Offer][expire_date]",
                      "OfferUnitTime"],
        "submit_text": "提案内容を確認する",
        "categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}},
    }
    assert estimate.validate_form_identity(valid, terms) is True
    for bad in (
        {**valid, "origin": "https://evil.example"},
        {**valid, "method": "GET"},
        {**valid, "controls": valid["controls"][:-1]},
        {**valid, "categories": {"wrong": {"sub": ["type"]}}},
    ):
        assert estimate.validate_form_identity(bad, terms) is False


def test_confirmation_mismatch_means_final_click_zero(estimate):
    terms = na15_terms()
    confirmation = {
        "title": "提案内容を確認する",
        "price_jpy": 500,
        "title_value": terms["title"],
        "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
        "completion_date": "2026-08-26",
        "purchase_plan": "single",
        "final_submit_text": "提案を送る",
    }
    assert estimate.validate_confirmation(confirmation, terms, today=date(2026, 8, 12)) is True
    assert estimate.validate_confirmation({**confirmation, "price_jpy": 700}, terms, today=date(2026, 8, 12)) is False
    assert estimate.validate_confirmation(
        {**confirmation, "completion_date": "2026-08-27", "delivery_date": "2026-08-27"},
        terms, today=date(2026, 8, 12),
    ) is False
    assert estimate.validate_confirmation(
        {**confirmation, "content": "完了予定日：2026-08-27（2週間後）"},
        terms, today=date(2026, 8, 12),
    ) is False
    assert estimate.validate_confirmation({**confirmation, "final_submit_text": ""}, terms, today=date(2026, 8, 12)) is False


def test_purchase_expiry_is_not_buyer_delivery_deadline(estimate):
    terms = na15_terms()
    confirmation = {
        "title": "提案内容を確認する", "price_jpy": 500,
        "title_value": terms["title"], "purchase_expire_date": "2026-08-19",
        "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
        "delivery_date": "2026-08-26", "purchase_plan": "single",
        "final_submit_labels": ["提案を送る"],
    }
    assert estimate.validate_confirmation(confirmation, terms, today=date(2026, 8, 12)) is True
    assert estimate.validate_confirmation({
        **confirmation, "delivery_date": "", "completion_date": "",
        "purchase_expire_date": "2026-08-26",
    }, terms, today=date(2026, 8, 12)) is False


def test_exception_after_authorize_is_delivery_unknown_once(estimate):
    terms = na15_terms()
    form = {
        "url": "https://coconala.com/direct_offers/add/5993046", "origin": "https://coconala.com",
        "path": "/direct_offers/add/5993046", "title": "提案内容を入力する", "method": "POST",
        "action": "https://coconala.com/direct_offers/add/5993046",
        "controls": list(estimate.EXPECTED_CONTROLS),
        "submit_text": ["提案内容を確認する"],
        "categories": {"ビジネス代行・事務代行": {"ECサイト運用代行": ["EC商品登録代行"]}},
    }
    item = {
        "talkroom_id": "10074114", "talkroom_url": "https://coconala.com/mypage/direct_message/10074114",
        "estimate_url": "/direct_offers/add/5993046", "estimate_request_identity": "buyer-1",
        "estimate_request_sent_at": "2026-08-12T00:00:00+00:00", "estimate_terms": terms,
    }
    body = "バイマ出品作業　12件を500円、2週間、単発で見積りお願いします。"

    class Browser:
        def __init__(self, *args, **kwargs):
            self.final_calls = 0
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read_thread_context(self):
            return ({"buyer_messages": [msg("buyer", body, message_id="buyer-1")]}, {
                "structured_offers": [], "own_user_path": "/users/seller",
            })
        def fresh_thread_context(self, expected_own_user_path):
            assert expected_own_user_path == "/users/seller"
            return {"own_user_path": "/users/seller", "buyer_messages": [
                msg("buyer", body, message_id="buyer-1"),
            ]}
        def open_form(self): return form
        def select_master(self, *args):
            return {**form, "categories": {
                "master": [{"label": terms["master_category_label"], "value": "13", "selected": True}],
                "sub": [{"label": terms["sub_category_label"], "value": "668", "selected": False}],
                "type": [{"label": "選択してください", "value": "", "disabled": True}],
            }}
        def fill(self, *args):
            return {"ok": True, "selected_categories": {
                "master": {"label": terms["master_category_label"], "value": "13"},
                "sub": {"label": terms["sub_category_label"], "value": "668"},
                "type": {"label": terms["category_type_label"], "value": "293"},
            }}
        def read_form(self):
            return {**form, "categories": {
                "master": [{"label": terms["master_category_label"], "value": "13", "selected": True}],
                "sub": [{"label": terms["sub_category_label"], "value": "668", "selected": True}],
                "type": [{"label": terms["category_type_label"], "value": "293", "selected": True}],
            }}
        def first_submit(self): return None
        def read_confirmation(self):
            return {"title": "提案内容を確認する", "title_value": terms["title"], "price_jpy": 500,
                    "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
                    "purchase_plan": "single", "completion_date": "2026-08-26",
                    "final_submit_labels": ["提案を送る"]}
        def final_submit(self, *args, **kwargs):
            self.final_calls += 1
            raise RuntimeError("cdp_lost_after_authorize")

    class DB:
        def __init__(self): self.unknown = 0
        def action_lifecycle_for_event(self, event_key, thread_id): return None
        def enqueue_estimate(self, **kwargs):
            return {"action_id": 1, "thread_id": "10074114", "thread_url": item["talkroom_url"], "state": "pending", "revision": 1}
        def claim(self, **kwargs):
            return {"action_id": 1, "thread_id": "10074114", "thread_url": item["talkroom_url"], "state": "claimed", "revision": 1, "owner": "estimate-test", "fencing_token": 1}
        def prepare_intent(self, action_id, **kwargs):
            return {"action_id": 1, "revision": 1, "owner_id": "estimate-test", "fencing_token": 1, "outgoing_hash": estimate.offer_terms_hash(terms)}
        def mark_click_started(self, action_id, revision, **kwargs): return {"state": "reconcile_pending"}
        def record_delivery_unknown(self, action_id, **kwargs): self.unknown += 1; return {"state": "reconcile_pending"}

    database = DB()
    result = estimate.execute_requested_estimate(
        item, database=database, composer=lambda *_: terms,
        browser_factory=lambda *args, **kwargs: Browser(), helper=None,
        owner="estimate-test", now=1786492800, hidden=True,
    )
    assert result["status"] == "reconcile_pending", result
    assert result["failed"] == 0
    assert database.unknown == 1


def test_official_readback_requires_exact_card(estimate):
    terms = na15_terms()
    cards = [{
        "offer_url": "https://coconala.com/mypage/direct_offers/7001",
        "message_kind": "見積り提案をしました",
        "title": terms["title"], "price_jpy": 500,
        "completion_date": "2026-08-26",
        "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
        "sender_side": "seller", "author_path": "/users/seller",
        "sent_at": "2026-08-12T00:05:00+00:00",
    }]
    assert estimate.match_official_offer_cards(cards, terms, click_started_at=1, request_sent_at="2026-08-12T00:00:00+00:00") == cards
    assert estimate.match_official_offer_cards([{**cards[0], "price_jpy": 700}], terms, click_started_at=1, request_sent_at="2026-08-12T00:00:00+00:00") == []
    assert estimate.match_official_offer_cards([{**cards[0], "title": "wrong"}], terms, click_started_at=1, request_sent_at="2026-08-12T00:00:00+00:00") == []
    assert estimate.match_official_offer_cards([{**cards[0], "completion_date": "2026-08-27"}], terms, click_started_at=1, request_sent_at="2026-08-12T00:00:00+00:00") == []
    assert estimate.match_official_offer_cards([{**cards[0], "sender_side": "buyer"}], terms, click_started_at=None, request_sent_at="2026-08-12T00:00:00+00:00") == []
    assert estimate.match_official_offer_cards([{**cards[0], "sent_at": "2026-08-11T23:59:00+00:00"}], terms, click_started_at=None, request_sent_at="2026-08-12T00:00:00+00:00") == []
    assert estimate.match_official_offer_cards(
        [{**cards[0], "content": "納期：2026-08-27（購入日から14日後）"}],
        terms, click_started_at=1,
    ) == []


def test_preexisting_matching_card_closes_without_click(estimate):
    result = estimate.classify_delivery(
        pre_click_cards=[{"message_kind": "見積り提案をしました", "title": na15_terms()["title"], "price_jpy": 500,
                          "completion_date": "2026-08-26", "sent_at": "2026-08-12T00:01:00+00:00",
                          "offer_url": "https://coconala.com/mypage/direct_offers/7001",
                          "content": "バイマ出品作業12件を対応します。完了予定日：2026-08-26（2週間後）",
                          "sender_side": "seller", "author_path": "/users/seller"}],
        post_click_cards=[], terms=na15_terms(), click_started_at=None,
        request_sent_at="2026-08-12T00:00:00+00:00",
    )
    assert result["status"] == "already_delivered"
    assert result["click"] == 0


def test_post_click_unknown_is_reconcile_pending_and_never_blind_retries(estimate):
    result = estimate.classify_delivery(pre_click_cards=[], post_click_cards=[], terms=na15_terms(), click_started_at=10)
    assert result == {"status": "reconcile_pending", "click": 1, "blind_retry": 0}
    verified = estimate.classify_delivery(
        pre_click_cards=[], post_click_cards=[{"message_kind": "見積り提案をしました", "title": na15_terms()["title"],
            "price_jpy": 500, "completion_date": "2026-08-26", "sent_at": "2026-08-12T00:05:00+00:00",
            "offer_url": "https://coconala.com/mypage/direct_offers/7001",
            "content": "完了予定日：2026-08-26（2週間後）", "sender_side": "seller", "author_path": "/users/seller"}], terms=na15_terms(), click_started_at=10,
    )
    assert verified["status"] == "verified"
    assert verified["click"] == 1
    second_wake = estimate.classify_delivery(pre_click_cards=verified.get("cards", []), post_click_cards=[], terms=na15_terms(), click_started_at=None)
    assert second_wake["click"] == 0


def test_restart_reconciles_stored_estimate_when_source_disappears(tmp_path, estimate, monkeypatch):
    outbox = load("connector_outbox")
    manifest = ROOT / "config" / "connectors" / "coconala.json"
    database = outbox.ConnectorOutbox(tmp_path / "outbox.sqlite3", manifest)
    thread_url = "https://coconala.com/mypage/direct_message/10074114"
    key = estimate.coconala_estimate_event_key("10074114", "buyer-1")
    base = int(datetime(2026, 8, 12, tzinfo=timezone.utc).timestamp())
    action = database.enqueue_estimate(
        event_key=key, thread_id="10074114", thread_url=thread_url, observed_at=base
    )
    claim = database.claim(
        owner="estimate-recovery", now=base + 1, lease_seconds=100,
        action_id=action["action_id"],
    )
    terms = estimate.materialize_delivery_content(na15_terms(), date(2026, 8, 12))
    intent = database.prepare_intent(
        action["action_id"], owner="estimate-recovery",
        fencing_token=claim["fencing_token"],
        outgoing_body=estimate.canonical_offer_terms(terms), now=base + 2,
        origin_at=base, store_outgoing_body=True,
    )
    database.mark_click_started(
        action["action_id"], intent["revision"], owner="estimate-recovery",
        fencing_token=claim["fencing_token"], now=base + 3,
    )
    database.record_delivery_unknown(
        action["action_id"], owner="estimate-recovery",
        fencing_token=claim["fencing_token"], now=base + 4,
    )
    scope = "BUYMA商品登録12件を個別見積で対応します。"
    fields = {
        "service_id": "4330368", "public_url": "https://coconala.com/services/4330368",
        "title": "BUYMA出品作業", "state": "公開中", "price_jpy": 500,
        "category": "/".join((terms["master_category_label"], terms["sub_category_label"], terms["category_type_label"])),
        "public_content_sha256": estimate.hashlib.sha256(scope.encode()).hexdigest(),
    }
    version = estimate.hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    contract_path, attribution_path = tmp_path / "offer-contracts.jsonl", tmp_path / "attribution-map.jsonl"
    contract_path.write_text(json.dumps({"version": 1, **fields, "scope_text": scope, "service_version_sha256": version}) + "\n")
    monkeypatch.setattr(estimate, "STOREFRONT_CONTRACTS_PATH", contract_path)
    monkeypatch.setattr(estimate, "STOREFRONT_ATTRIBUTION_PATH", attribution_path)
    related = {"related_service_id": "4330368", "related_service_version_sha256": version,
               "related_service_terms_sha256": estimate.offer_terms_hash(terms)}
    estimate._append_attribution_once(estimate._attribution_row(
        "prepared", related, event_key=key, action_id=action["action_id"],
        revision=int(intent["revision"]), observed_at=base + 3,
    ))
    card = {
        "offer_url": "https://coconala.com/mypage/direct_offers/7001",
        "message_kind": "見積り提案をしました", "title": terms["title"],
        "price_jpy": terms["price_jpy"], "completion_date": "2026-08-26",
        "content": terms["content"],
        "sender_side": "seller", "author_path": "/users/seller",
        "sent_at": datetime.fromtimestamp(base + 10, timezone.utc).isoformat(),
    }

    class Browser:
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def read_after(self): return {"structured_offers": [card], "own_user_path": "/users/seller"}
        def open_form(self): raise AssertionError("recovery must not open the form")
        def fill(self, *args): raise AssertionError("recovery must not fill")
        def first_submit(self): raise AssertionError("recovery must not submit")
        def final_submit(self, *args, **kwargs): raise AssertionError("recovery must not click")

    result = estimate.process_snapshot(
        {"inquiries": []}, database_path=tmp_path / "outbox.sqlite3", manifest=manifest,
        runner=ROOT / "scripts" / "agent_runner.py", schema=ROOT / "schemas" / "estimate_composition.schema.json",
        workdir=tmp_path, helper=None, owner="estimate-recovery", now=base + 86400,
        browser_factory=lambda *args, **kwargs: Browser(), composer=lambda *_: pytest.fail("no compose on recovery"),
    )
    assert result["estimate_required"] == 0
    assert result["estimate_effect"] == 0
    assert result["estimate_readback"] == 1
    assert result["estimate_pending"] == 0
    assert result["estimate_events"][0]["attribution"]["offer_id"] == "7001"
    assert json.loads(attribution_path.read_text().splitlines()[-1])["status"] == "accepted"
    assert database.estimate_reconciliation_actions() == []
