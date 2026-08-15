import importlib.util
import json
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(f"semantic_test_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def estimate():
    return load("requested_estimate")


@pytest.fixture
def rows():
    return [
        {"message_id": "b1", "role": "buyer", "sent_at": "2026-08-13T00:00:00+00:00", "body": "対応できますか。"},
        {"message_id": "s1", "role": "seller", "sent_at": "2026-08-13T00:01:00+00:00", "body": "確認します。"},
        {"message_id": "b2", "role": "buyer", "sent_at": "2026-08-13T00:02:00+00:00", "body": "お願いします。"},
    ]


def reply_payload():
    return {
        "conversation_state": "question",
        "next_action": "reply",
        "cycle_start_message_id": "b1",
        "evidence_message_ids": ["b1", "b2"],
        "required_official_context": "none",
        "estimate_terms": None,
        "reply_body": "対応可能です。",
        "reply_audit": {
            "answered_buyer_message_ids": ["b2"],
            "unanswered_questions": [],
            "unsupported_claims": [],
            "unrequested_cta": False,
            "repeats_seller_message": False,
            "off_platform_contact": False,
        },
        "uncertainty": [],
    }


def estimate_payload():
    return {
        "conversation_state": "ready_to_buy",
        "next_action": "send_estimate",
        "cycle_start_message_id": "b1",
        "evidence_message_ids": ["b1", "b2"],
        "required_official_context": "estimate_form",
        "estimate_terms": {
            "title": "記事とSNS投稿の作成",
            "content": "記事1本とSNS投稿1本を作成します。",
            "quantity": 2,
            "price_jpy": 2000,
            "delivery_days": 1,
            "purchase_plan": "single",
            "title_evidence_message_ids": ["b1"],
            "content_evidence_message_ids": ["b1"],
            "quantity_evidence_message_ids": ["b1"],
            "price_evidence_message_ids": ["b2"],
            "delivery_evidence_message_ids": ["b2"],
            "purchase_plan_evidence_message_ids": ["b2"],
        },
        "reply_body": None,
        "reply_audit": {
            "answered_buyer_message_ids": [],
            "unanswered_questions": [],
            "unsupported_claims": [],
            "unrequested_cta": False,
            "repeats_seller_message": False,
            "off_platform_contact": False,
        },
        "uncertainty": [],
    }


def test_strict_reply_accepts_only_current_buyer_evidence(estimate, rows):
    assert estimate.validate_semantic_judgement(reply_payload(), rows)["reply_body"] == "対応可能です。"
    invalid = reply_payload()
    invalid["evidence_message_ids"] = ["s1"]
    with pytest.raises(estimate.SemanticJudgementError, match="semantic_evidence_invalid"):
        estimate.validate_semantic_judgement(invalid, rows)


def test_unknown_or_external_url_cannot_authorize_reply(estimate, rows):
    external = reply_payload()
    external["reply_body"] = "詳しくは https://evil.example をご覧ください。"
    with pytest.raises(estimate.SemanticJudgementError, match="external_url"):
        estimate.validate_semantic_judgement(external, rows)
    uncertain = reply_payload()
    uncertain["uncertainty"] = ["根拠不足"]
    with pytest.raises(estimate.SemanticJudgementError, match="not_authorized"):
        estimate.validate_semantic_judgement(uncertain, rows)


def test_buyer_last_wait_requires_a_real_blocker(estimate, rows):
    waiting = reply_payload()
    waiting.update({
        "conversation_state": "considering", "next_action": "wait",
        "evidence_message_ids": ["b2"], "reply_body": None,
        "reply_audit": {
            "answered_buyer_message_ids": [], "unanswered_questions": [],
            "unsupported_claims": [], "unrequested_cta": False,
            "repeats_seller_message": False, "off_platform_contact": False,
        },
    })
    with pytest.raises(estimate.SemanticJudgementError, match="buyer_last_wait_without_blocker"):
        estimate.validate_semantic_judgement(waiting, rows)
    waiting.update({
        "conversation_state": "question", "required_official_context": "application",
        "uncertainty": ["公式応募条件が必要"],
    })
    assert estimate.validate_semantic_judgement(waiting, rows)["next_action"] == "wait"


def test_legacy_receipts_are_incompatible_after_v14(estimate):
    for version in ("reply-negotiate-v11", "reply-negotiate-v12", "reply-negotiate-v13"):
        assert not estimate.semantic_prompt_compatible({
            "prompt_version": version, "judgement": reply_payload(),
        })


def test_cached_current_pending_restores_reply_and_seller_wait(estimate):
    context_sha256 = "a" * 64
    receipt = {
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "context_sha256": context_sha256,
        "judgement": reply_payload(),
    }
    row = {"semantic_context_sha256": context_sha256}
    reply = estimate.restore_cached_semantic_projection(row, receipt)
    assert reply is not None
    assert (reply["next_action"], reply["reply_required"]) == ("reply", True)
    assert reply["semantic_reply_body"] == "対応可能です。"
    assert reply["semantic_failure"] is None

    receipt["judgement"] = {
        **reply_payload(), "conversation_state": "seller_last", "next_action": "wait",
        "reply_body": None, "evidence_message_ids": [],
    }
    seller_wait = estimate.restore_cached_semantic_projection(row, receipt)
    assert seller_wait is not None
    assert (seller_wait["next_action"], seller_wait["reply_required"]) == ("observe", False)


def test_cached_current_pending_restores_structured_estimate_only_with_official_source(estimate):
    context_sha256 = "b" * 64
    receipt = {
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "context_sha256": context_sha256,
        "judgement": estimate_payload(),
    }
    row = {
        "semantic_context_sha256": context_sha256,
        "estimate_url": "https://coconala.com/direct_offers/add/99",
        "estimate_request_identity": "b2",
        "estimate_request_sent_at": "2026-08-13T00:02:00+00:00",
    }
    restored = estimate.restore_cached_semantic_projection(row, receipt)
    assert restored is not None
    assert (restored["next_action"], restored["estimate_required"]) == (
        "requested_estimate", True,
    )
    assert restored["semantic_estimate_terms"]["price_jpy"] == 2000
    assert estimate.restore_cached_semantic_projection(
        {**row, "estimate_url": None}, receipt,
    ) is None


def test_cached_legacy_unblocked_buyer_wait_remains_pending_for_rejudgement(estimate):
    context_sha256 = "c" * 64
    receipt = {
        "prompt_version": "reply-negotiate-v11",
        "context_sha256": context_sha256,
        "judgement": {
            **reply_payload(), "conversation_state": "considering", "next_action": "wait",
            "reply_body": None, "evidence_message_ids": ["b2"],
        },
    }
    assert estimate.restore_cached_semantic_projection(
        {"semantic_context_sha256": context_sha256}, receipt,
    ) is None


def test_reply_audit_blocks_incomplete_or_spammy_body(estimate, rows):
    incomplete = reply_payload()
    incomplete["reply_audit"]["unanswered_questions"] = ["利用可能なアカウントへの回答がない"]
    with pytest.raises(estimate.SemanticJudgementError, match="audit_failed"):
        estimate.validate_semantic_judgement(incomplete, rows)
    repeated = reply_payload()
    repeated["reply_audit"]["repeats_seller_message"] = True
    with pytest.raises(estimate.SemanticJudgementError, match="audit_failed"):
        estimate.validate_semantic_judgement(repeated, rows)


def test_verified_seller_facts_excludes_non_whitelisted_private_fields(estimate, tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(
        '{"facts":['
        '{"id":"agent_club","claim":"Claude Codeを教えている。","evidence":"user_statement"},'
        '{"id":"profile.mailing_address","claim":"private address","evidence":"private"}'
        ']}',
        encoding="utf-8",
    )
    assert estimate.verified_seller_facts(profile) == [{
        "id": "agent_club",
        "claim": "Claude Codeを教えている。",
        "evidence": "user_statement",
    }]


def test_seller_last_agreement_projects_structured_estimate(estimate):
    dom = {
        "url": "https://coconala.com/mypage/direct_message/42",
        "title": "メッセージ詳細",
        "container_present": True,
        "own_user_path": "/users/seller",
        "estimate_url": "https://coconala.com/direct_offers/add/99",
        "messages": [
            {"message_id": "b1", "author_path": "/users/buyer", "sent_at": "2026-08-13T00:00:00+00:00", "body": "記事とSNS投稿をお願いします。"},
            {"message_id": "b2", "author_path": "/users/buyer", "sent_at": "2026-08-13T00:01:00+00:00", "body": "2,000円、翌日納期で購入します。"},
            {"message_id": "s1", "author_path": "/users/seller", "sent_at": "2026-08-13T00:02:00+00:00", "body": "ありがとうございます。"},
        ],
    }
    rows = estimate.semantic_conversation(dom)
    payload = estimate_payload()
    receipt = {
        "version": estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "schema_sha256": "a" * 64,
        "runner_profile": estimate.SEMANTIC_RUNNER_PROFILE,
        "context_sha256": estimate.semantic_context_sha256(rows),
        "latest_message_identity": "s1",
        "judgement": payload,
    }
    projected = estimate.project_semantic_receipt(dom, dom["url"], receipt)
    assert projected["last_message_side"] == "seller"
    assert projected["next_action"] == "requested_estimate"
    assert projected["estimate_required"] is True
    assert projected["estimate_request_identity"] == "b2"


def test_collector_bulkhead_and_cutover_are_effect_zero(estimate):
    collector = load("coconala_queue_snapshot")
    dom = {
        "url": "https://coconala.com/mypage/direct_message/42",
        "title": "メッセージ詳細", "container_present": True,
        "own_user_path": "/users/seller",
        "messages": [{"message_id": "b1", "author_path": "/users/buyer", "sent_at": "2026-08-13T00:00:00+00:00", "body": "対応できますか。"}],
    }

    def failed(*_args):
        raise TimeoutError("model timeout")

    result = collector.direct_message_event(dom, dom["url"], semantic_judge=failed)
    assert (result["next_action"], result["reply_required"], result["estimate_required"]) == (
        "semantic_failed", False, False,
    )

    rows = estimate.semantic_conversation(dom)
    receipt = {
        "version": estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "schema_sha256": "a" * 64,
        "runner_profile": estimate.SEMANTIC_RUNNER_PROFILE,
        "context_sha256": estimate.semantic_context_sha256(rows),
        "latest_message_identity": "b1",
        "judgement": {
            **reply_payload(), "evidence_message_ids": ["b1"], "cycle_start_message_id": "b1",
            "reply_audit": {
                "answered_buyer_message_ids": ["b1"], "unanswered_questions": [],
                "unsupported_claims": [], "unrequested_cta": False,
                "repeats_seller_message": False, "off_platform_contact": False,
            },
        },
    }
    pending = collector.direct_message_event(dom, dom["url"], semantic_judge=lambda *_: receipt)
    assert pending["semantic_candidate_action"] == "reply"
    assert (pending["next_action"], pending["reply_required"]) == ("semantic_pending", False)


def test_collector_reruns_judge_with_structured_application_context(estimate):
    collector = load("coconala_queue_snapshot")
    dom = {
        "url": "https://coconala.com/mypage/direct_message/42",
        "title": "メッセージ詳細", "container_present": True,
        "own_user_path": "/users/seller", "estimate_url": None,
        "messages": [{"message_id": "b1", "author_path": "/users/buyer", "sent_at": "2026-08-13T00:00:00+00:00", "body": "条件を確認できますか。"}],
    }
    rows = estimate.semantic_conversation(dom)
    base = {
        "version": estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "schema_sha256": "a" * 64,
        "runner_profile": estimate.SEMANTIC_RUNNER_PROFILE,
        "context_sha256": estimate.semantic_context_sha256(rows),
        "latest_message_identity": "b1",
        "official_context_sha256": "a" * 64,
    }
    first = {
        **reply_payload(), "next_action": "wait", "conversation_state": "question",
        "required_official_context": "application", "reply_body": None,
        "uncertainty": ["応募条件が必要"], "evidence_message_ids": ["b1"],
        "cycle_start_message_id": "b1",
        "reply_audit": {
            "answered_buyer_message_ids": [], "unanswered_questions": [],
            "unsupported_claims": [], "unrequested_cta": False,
            "repeats_seller_message": False, "off_platform_contact": False,
        },
    }
    second = {
        **reply_payload(), "evidence_message_ids": ["b1"],
        "cycle_start_message_id": "b1", "reply_body": "確認済みの条件で対応可能です。",
        "reply_audit": {
            "answered_buyer_message_ids": ["b1"], "unanswered_questions": [],
            "unsupported_claims": [], "unrequested_cta": False,
            "repeats_seller_message": False, "off_platform_contact": False,
        },
    }
    calls = []

    def judge(*_args, official_context=None):
        calls.append(official_context)
        return {**base, "judgement": first if official_context is None else second}

    application = {"application": {"offer_id": "9", "price_jpy": 2000}}
    result = collector.direct_message_event(
        dom, dom["url"], semantic_judge=judge,
        official_context_provider=lambda _url: application,
    )
    assert calls == [None, application]
    assert result["semantic_candidate_action"] == "reply"
    assert result["next_action"] == "semantic_pending"


def test_collector_preserves_application_requirement_when_second_judgement_fails(estimate):
    collector = load("coconala_queue_snapshot")
    dom = {
        "url": "https://coconala.com/mypage/direct_message/42",
        "title": "メッセージ詳細", "container_present": True,
        "own_user_path": "/users/seller", "estimate_url": None,
        "messages": [{
            "message_id": "b1", "author_path": "/users/buyer",
            "sent_at": "2026-08-13T00:00:00+00:00", "body": "条件を確認できますか。",
        }],
    }
    rows = estimate.semantic_conversation(dom)
    first_judgement = {
        **reply_payload(), "next_action": "wait", "reply_body": None,
        "required_official_context": "application", "uncertainty": ["応募条件が必要"],
        "evidence_message_ids": ["b1"], "cycle_start_message_id": "b1",
        "reply_audit": {
            "answered_buyer_message_ids": [], "unanswered_questions": [],
            "unsupported_claims": [], "unrequested_cta": False,
            "repeats_seller_message": False, "off_platform_contact": False,
        },
    }
    receipt = {
        "version": estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "schema_sha256": "a" * 64,
        "runner_profile": estimate.SEMANTIC_RUNNER_PROFILE,
        "context_sha256": estimate.semantic_context_sha256(rows),
        "latest_message_identity": "b1", "official_context_sha256": "a" * 64,
        "judgement": first_judgement,
    }
    calls = 0

    def judge(*_args, official_context=None):
        nonlocal calls
        calls += 1
        if official_context is not None:
            raise RuntimeError("semantic_runner_failed_rc_1")
        return receipt

    result = collector.direct_message_event(
        dom, dom["url"], semantic_judge=judge,
        official_context_provider=lambda _url: {"application": {"offer_id": "9"}},
    )
    assert calls == 2
    assert result["next_action"] == "semantic_failed"
    assert result["reply_required"] is False
    assert result["semantic_receipt"] == receipt
    assert result["semantic_official_context_required"] == "application"


def test_collector_retries_one_fast_invalid_application_judgement_in_same_wake(estimate):
    collector = load("coconala_queue_snapshot")
    semantic = collector._requested_estimate_module()
    dom = {
        "url": "https://coconala.com/mypage/direct_message/42",
        "title": "メッセージ詳細", "container_present": True,
        "own_user_path": "/users/seller", "estimate_url": None,
        "messages": [{
            "message_id": "b1", "author_path": "/users/buyer",
            "sent_at": "2026-08-13T00:00:00+00:00", "body": "条件を確認できますか。",
        }],
    }
    rows = estimate.semantic_conversation(dom)
    base = {
        "version": estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "schema_sha256": "a" * 64, "runner_profile": estimate.SEMANTIC_RUNNER_PROFILE,
        "context_sha256": estimate.semantic_context_sha256(rows),
        "latest_message_identity": "b1", "official_context_sha256": "a" * 64,
    }
    first = {
        **reply_payload(), "next_action": "wait", "conversation_state": "question",
        "required_official_context": "application", "reply_body": None,
        "uncertainty": ["応募条件が必要"], "evidence_message_ids": ["b1"],
        "cycle_start_message_id": "b1",
        "reply_audit": {"answered_buyer_message_ids": [], "unanswered_questions": [],
                        "unsupported_claims": [], "unrequested_cta": False,
                        "repeats_seller_message": False, "off_platform_contact": False},
    }
    second = {
        **reply_payload(), "evidence_message_ids": ["b1"],
        "cycle_start_message_id": "b1", "reply_body": "確認済みの条件で対応可能です。",
        "reply_audit": {"answered_buyer_message_ids": ["b1"], "unanswered_questions": [],
                        "unsupported_claims": [], "unrequested_cta": False,
                        "repeats_seller_message": False, "off_platform_contact": False},
    }
    application = {"application": {"offer_id": "9", "price_jpy": 2000}}
    calls = []

    def judge(*_args, official_context=None):
        calls.append(official_context)
        if official_context is None:
            return {**base, "judgement": first}
        if calls.count(application) == 1:
            raise semantic.SemanticJudgementError("semantic_reply_audit_failed")
        return {**base, "judgement": second}

    result = collector.direct_message_event(
        dom, dom["url"], semantic_judge=judge,
        official_context_provider=lambda _url: application,
    )
    assert calls == [None, application, application]
    assert result["semantic_candidate_action"] == "reply"

    failed_calls = []

    def always_invalid(*_args, official_context=None):
        failed_calls.append(official_context)
        if official_context is None:
            return {**base, "judgement": first}
        raise semantic.SemanticJudgementError("semantic_reply_audit_failed")

    failed = collector.direct_message_event(
        dom, dom["url"], semantic_judge=always_invalid,
        official_context_provider=lambda _url: application,
    )
    assert failed_calls == [None, application, application]
    assert failed["next_action"] == "semantic_failed"
    assert failed["reply_required"] is False


def test_verified_application_identity_supplies_official_estimate_route(estimate):
    collector = load("coconala_queue_snapshot")
    context = {"application": {"requester_user_id": "4470725"}}
    assert collector._estimate_url_from_verified_application(
        context, estimate,
    ) == "https://coconala.com/direct_offers/add/4470725"
    assert collector._estimate_url_from_verified_application(
        {"application": {"requester_user_id": "../evil"}}, estimate,
    ) is None
    assert collector._estimate_url_from_verified_application({
        "applications": [
            {"requester_user_id": "4470725", "offer_id": "1"},
            {"requester_user_id": "4470725", "offer_id": "2"},
        ],
    }, estimate) == "https://coconala.com/direct_offers/add/4470725"
    assert collector._estimate_url_from_verified_application({
        "applications": [
            {"requester_user_id": "4470725"},
            {"requester_user_id": "9999999"},
        ],
    }, estimate) is None


def test_unchanged_current_receipt_is_reused_without_model_regeneration(estimate):
    collector = load("coconala_queue_snapshot")
    dom = {
        "own_user_path": "/users/seller",
        "messages": [{
            "message_id": "b1", "author_path": "/users/buyer",
            "sent_at": "2026-08-13T00:00:00+00:00", "body": "購入します。",
        }],
    }
    receipt = {
        "context_sha256": estimate.semantic_context_sha256(
            estimate.semantic_conversation(dom)
        ),
        "judgement": {"required_official_context": "estimate_form"},
    }

    class Judge:
        @staticmethod
        def receipt_current(value):
            return value is receipt

    assert collector.reusable_semantic_receipt(
        {"semantic_receipt": receipt}, dom, Judge(), estimate,
    ) is receipt
    changed = {**dom, "messages": [*dom["messages"], {
        "message_id": "b2", "author_path": "/users/buyer",
        "sent_at": "2026-08-13T00:01:00+00:00", "body": "条件を変更します。",
    }]}
    assert collector.reusable_semantic_receipt(
        {"semantic_receipt": receipt}, changed, Judge(), estimate,
    ) is None


def test_seller_last_cannot_retain_unprocessed_buyer_evidence(estimate, rows):
    payload = reply_payload()
    payload.update({
        "conversation_state": "seller_last", "next_action": "wait",
        "reply_body": None, "evidence_message_ids": ["b1"],
        "reply_audit": {
            "answered_buyer_message_ids": [], "unanswered_questions": [],
            "unsupported_claims": [], "unrequested_cta": False,
            "repeats_seller_message": False, "off_platform_contact": False,
        },
    })
    with pytest.raises(estimate.SemanticJudgementError, match="seller_last_evidence_conflict"):
        estimate.validate_semantic_judgement(payload, rows)


def test_send_estimate_without_dom_anchor_reads_official_route_once(estimate):
    collector = load("coconala_queue_snapshot")
    dom = {
        "url": "https://coconala.com/mypage/direct_message/42",
        "title": "メッセージ詳細", "container_present": True,
        "own_user_path": "/users/seller", "estimate_url": None,
        "messages": [
            {"message_id": "b1", "author_path": "/users/buyer", "sent_at": "2026-08-13T00:00:00+00:00", "body": "記事とSNS投稿をお願いします。"},
            {"message_id": "b2", "author_path": "/users/buyer", "sent_at": "2026-08-13T00:01:00+00:00", "body": "2,000円、翌日納期で購入します。"},
            {"message_id": "s1", "author_path": "/users/seller", "sent_at": "2026-08-13T00:02:00+00:00", "body": "ありがとうございます。"},
        ],
    }
    rows = estimate.semantic_conversation(dom)
    receipt = {
        "version": estimate.SEMANTIC_RECEIPT_VERSION,
        "prompt_version": estimate.SEMANTIC_PROMPT_VERSION,
        "schema_sha256": "a" * 64,
        "runner_profile": estimate.SEMANTIC_RUNNER_PROFILE,
        "context_sha256": estimate.semantic_context_sha256(rows),
        "latest_message_identity": "s1", "official_context_sha256": "a" * 64,
        "judgement": estimate_payload(),
    }
    judge_calls, route_calls = [], []

    def judge(*_args, official_context=None):
        judge_calls.append(official_context)
        return receipt

    def route(_url):
        route_calls.append(_url)
        return {"application": {"requester_user_id": "4470725"}}

    result = collector.direct_message_event(
        dom, dom["url"], semantic_judge=judge, official_context_provider=route,
    )
    assert judge_calls == [None]
    assert route_calls == [dom["url"]]
    assert result["estimate_url"] == "https://coconala.com/direct_offers/add/4470725"
    assert result["semantic_candidate_action"] == "requested_estimate"
    assert result["next_action"] == "semantic_pending"


def test_semantic_terms_override_language_extraction(estimate):
    source = estimate_payload()["estimate_terms"]
    terms = {
        "title": source["title"], "content": source["content"],
        "price_jpy": source["price_jpy"], "delivery_days": source["delivery_days"],
        "purchase_plan": source["purchase_plan"],
        "master_category_label": "ライティング・翻訳",
        "sub_category_label": "記事作成",
        "category_type_label": "記事・Webコンテンツ作成",
    }
    context = {
        "semantic_estimate_terms": source,
        "buyer_messages": [{"side": "buyer", "body": "金額も納期も本文には書かない言い換え"}],
        "live_form": {"categories": {"master": [{"label": "ライティング・翻訳", "value": "1"}]}},
    }
    assert estimate.validate_estimate_terms(terms, context)["price_jpy"] == 2000


def test_category_mapper_uses_only_observed_selected_option(estimate, tmp_path):
    composer = estimate.RequestedEstimateComposer(
        runner=tmp_path / "runner", schema=tmp_path / "schema", workdir=tmp_path,
    )
    source = estimate_payload()["estimate_terms"]
    form = {"categories": {"master": [
        {"label": "ライティング・翻訳", "value": "7", "selected": True},
        {"label": "動画・アニメーション", "value": "8", "selected": False},
    ]}}
    label = composer.select_category(
        "master", {"semantic_estimate_terms": source}, form,
    )
    assert label == "ライティング・翻訳"
    terms = composer.terms_with_categories(
        {"semantic_estimate_terms": source},
        master=label, sub="記事作成", typ="記事・Webコンテンツ作成",
    )
    assert terms["price_jpy"] == 2000
    assert terms["content"] == source["content"]


def test_semantic_judge_loads_exact_service_contract_from_buyer_url(estimate, tmp_path, monkeypatch):
    service_url = "https://coconala.com/services/4313386"

    def contract(service_id, title, scope_text, observed_at):
        fields = {
            "service_id": service_id,
            "public_url": f"https://coconala.com/services/{service_id}",
            "title": title,
            "state": "公開中",
            "price_jpy": 6000,
            "category": "IT相談・システム開発/業務自動化",
            "public_content_sha256": estimate.hashlib.sha256(scope_text.encode()).hexdigest(),
        }
        version = estimate.hashlib.sha256(json.dumps(
            fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        return {"version": 1, **fields, "scope_text": scope_text,
                "service_version_sha256": version, "observed_at": observed_at}

    stale = contract("4313386", "古いVBA出品", "旧スコープ", "stale")
    current = contract(
        "4313386", "請求書・日報のVBA自動化", "番号照合と複数列転記を含む現行スコープ", "current",
    )
    decoy = contract("4313999", "別サービス", "別サービスのスコープ", "decoy")
    contracts = tmp_path / "offer-contracts.jsonl"
    contracts.write_text("\n".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        for row in (stale, decoy, current)
    ) + "\n", encoding="utf-8")
    monkeypatch.setattr(estimate, "STOREFRONT_CONTRACTS_PATH", contracts)

    dom = {
        "url": "https://coconala.com/mypage/direct_message/10083449",
        "title": "メッセージ詳細", "container_present": True,
        "own_user_path": "/users/seller",
        "messages": [
            {
                "message_id": "s1", "author_path": "/users/seller",
                "sent_at": "2026-08-14T23:59:00+00:00",
                "body": "別候補 https://coconala.com/services/4313999 も確認しました。",
            },
            {
                "message_id": "b1", "author_path": "/users/buyer",
                "sent_at": "2026-08-15T00:00:00+00:00",
                "body": f"この出品 {service_url} のVBAについて質問です。",
            },
        ],
    }
    payload = {
        "conversation_state": "question", "next_action": "clarify",
        "cycle_start_message_id": "b1", "evidence_message_ids": ["b1"],
        "required_official_context": "none", "estimate_terms": None,
        "reply_body": "確認したい処理内容を教えてください。",
        "reply_audit": {
            "answered_buyer_message_ids": ["b1"], "unanswered_questions": [],
            "unsupported_claims": [], "unrequested_cta": False,
            "repeats_seller_message": False, "off_platform_contact": False,
        },
        "uncertainty": [],
    }
    packets = []

    def run(command, **kwargs):
        packet = json.loads(kwargs["input"].split("official_thread=", 1)[1])
        packets.append(packet)
        evidence = Path(command[command.index("--evidence-dir") + 1])
        evidence.mkdir(parents=True, exist_ok=True)
        result = evidence / "result.json"
        result.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        (evidence / "summary.json").write_text(json.dumps({
            "status": "success", "result_path": str(result),
        }), encoding="utf-8")
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(estimate.subprocess, "run", run)
    schema = tmp_path / "schema.json"
    schema.write_text("{}", encoding="utf-8")
    judge = estimate.SemanticJudge(
        runner=tmp_path / "runner.py", schema=schema, workdir=tmp_path,
        evidence_root=tmp_path / "evidence", timeout_seconds=1,
    )

    receipt = judge(dom, dom["url"])
    assert packets[0]["verified_official_context"]["service"] == current
    assert receipt["service_id"] == "4313386"
    assert receipt["service_version_sha256"] == current["service_version_sha256"]
    assert judge.receipt_current(receipt)
    newer = contract(
        "4313386", "請求書・日報のVBA自動化 改訂版", "改訂された現行スコープ", "newer",
    )
    contracts.write_text(json.dumps(newer, ensure_ascii=False) + "\n", encoding="utf-8")
    assert not judge.receipt_current(receipt)
