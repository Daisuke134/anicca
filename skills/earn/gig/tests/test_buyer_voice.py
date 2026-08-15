"""The buyer must not be able to tell that a machine wrote to them.

Everything here is anchored to one measured artifact: the message order 91000002 actually
received at 2026-08-06T19:04:49Z, recorded in
gig-pass-1786042804-16185/agent-PAID_QUEUE_DELIVERY/formal-delivery-evidence.json under
seller_message_readback. It is quoted verbatim below and must never pass again.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import buyer_voice  # noqa: E402


def load(name: str, alias: str | None = None):
    spec = importlib.util.spec_from_file_location(alias or name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. The message that was actually sent
# ---------------------------------------------------------------------------

SENT_TO_91000002 = """お世話になっております。ご注文いただいた制作物が仕上がりました。
確認した内容は以下のとおりです。
・現在確認できる買い手からのメッセージと取引情報を確認資料としてまとめました。
・記載のない制作内容は推測せず、未確認の条件として明記しました。
・作業を始める前に必要な確認事項を買い手向けにまとめました。
制作物を正式に納品いたします。内容のご確認をお願いいたします。

添付: delivery-sample.md
パッケージSHA-256: f0ce97066e7f441f5c91c0799131d2c750e6d0d5ee2b65bcc7a6918ec0474680"""


def test_the_message_the_buyer_actually_received_is_refused() -> None:
    violations = buyer_voice.check_style(SENT_TO_91000002)
    assert violations, "the 2026-08-06 message must not be sendable again"
    assert "sha256_digest" in violations
    assert "package_sha_label" in violations


# ---------------------------------------------------------------------------
# 2. No false positives on real customer prose
# ---------------------------------------------------------------------------

HUMAN_MESSAGES = [
    # A delivery, written the way a freelancer writes one.
    "お世話になっております。\nご依頼いただいた件が仕上がりましたので、お届けいたします。\n"
    "今回対応したのは「トップページの画像差し替え」です。\n\n"
    "添付のファイルをご確認ください。気になるところがあればお知らせください。\n\n"
    "添付: delivery-sample.md",
    # A sales reply.
    "お問い合わせありがとうございます。ご希望の内容で対応可能です。"
    "ご購入後、当日中に初稿をお送りします。ご不明な点があればお気軽にどうぞ。",
    # A question to a buyer who has already paid.
    "着手が遅れており申し訳ございません。仕様を確定したく、"
    "①ご希望の成果物の形式 ②参考サイト ③素材データ をお送りいただけますでしょうか。",
    # Ordinary words that merely look like internal tokens.
    "パスワードの再設定はこちらから可能です。",
    "審査に合格しました。",
    "This pass is included in the plan.",
    "納期は8月11日、金額は2,500円です。",
]


@pytest.mark.parametrize("message", HUMAN_MESSAGES)
def test_a_human_written_message_passes_clean(message: str) -> None:
    # A false positive here silently blocks a paid delivery, which is worse than the leak
    # this gate exists to stop. The rules must only fire on things that are objectively not
    # customer language.
    assert buyer_voice.check_style(message) == []


def test_the_gate_ignores_case_where_it_should_and_respects_it_where_it_must() -> None:
    assert buyer_voice.check_style("sha-256 を確認") == ["sha256_label"]
    # Shouted PASS/FAIL are ours; lowercase english words are the buyer's.
    assert buyer_voice.check_style("ステータス: PASS") == ["pass_token"]
    assert buyer_voice.check_style("FAIL") == ["fail_token"]
    assert buyer_voice.check_style("the build failed") == []
    assert buyer_voice.check_style("FAILED") == []


def test_local_paths_never_reach_a_customer() -> None:
    assert buyer_voice.check_style("/workspace/gig/x を見てください") == ["local_path"]
    assert buyer_voice.check_style("~/gig/projects に置きました") == ["local_path"]


def test_empty_text_is_not_a_style_violation() -> None:
    # Emptiness is refused by the contracts that own it, each with its own error.
    assert buyer_voice.check_style("") == []
    assert buyer_voice.check_style(None) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. normalize_for_match
# ---------------------------------------------------------------------------

def test_normalize_deletes_whitespace_rather_than_collapsing_it() -> None:
    # Deleting, not collapsing. innerText injects whitespace where we sent none (the
    # measurement recorded on coconala_paid_progress_browser._normalized_text), and a
    # single injected space would break a prefix match on a delivery that succeeded.
    assert buyer_voice.normalize_for_match("  a\n\n b \t c  ") == "abc"
    assert buyer_voice.normalize_for_match("お世話に　 なって\nおります") == "お世話になっております"
    assert buyer_voice.normalize_for_match("") == ""
    assert buyer_voice.normalize_for_match(None) == ""  # type: ignore[arg-type]


def test_a_row_survives_whitespace_the_dom_injected_where_we_sent_none() -> None:
    # The exact failure mode that made collapsing unsafe.
    sent = "お世話になっております。修正版をお届けします。"
    rendered = "お世話に なって おります。\n\n修正版を お届けします。"
    assert buyer_voice.normalize_for_match(rendered) == buyer_voice.normalize_for_match(sent)


# ---------------------------------------------------------------------------
# 4. PERSONA
# ---------------------------------------------------------------------------

def test_the_persona_says_who_is_speaking_and_what_is_forbidden() -> None:
    # application_planner had no persona line at all; the others said only
    # 「ココナラの営業返信担当」, which is a role, not a voice.
    persona = buyer_voice.PERSONA
    assert "個人" in persona
    assert "お客様" in persona
    # The bullet work-report is the specific shape that got us caught.
    assert "作業報告" in persona
    assert "箇条書き" in persona
    # Internal vocabulary named explicitly, so the model can recognise it.
    for word in ("検証", "PASS", "パッケージ", "ハッシュ", "エビデンス", "ステータス"):
        assert word in persona, word
    assert "内部処理" in persona
    # A closing instruction elsewhere owns the word 「最後」; the persona must not
    # borrow it, or every follow-up would read as a break-up message.
    assert "最後" not in persona


def planner_snapshot() -> dict:
    """A real, hash-bound envelope -- validate_decisions rejects anything less.

    Same collector input the atomic-boundary suite uses, run through the canonical
    builder, so this exercises the actual contract rather than a hand-made dict.
    """
    snapshot_module = load("application_snapshot", "application_snapshot_buyer_voice")
    return snapshot_module.build_envelope({
        "pass_id": "gig-pass-buyer-voice-test",
        "lease_fence": {
            "task": "gig-pass-buyer-voice-test-B2",
            "token": "0123456789abcdef0123456789abcdef",
            "generation": 7,
        },
        "observed_at": "2026-08-02T12:00:00Z",
        "objective": {
            "target_applications": 4,
            "max_applications": 7,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": ["91000032"],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [{
            "request_id": "91000032",
            "canonical_url": "https://coconala.com/job_matching/requests/91000032",
            "title": "AI 調査",
            "category": "リサーチ",
            "visible_text": "募集内容",
            "accepting_applications": True,
            "budget_min_jpy": 1000,
            "budget_max_jpy": 5000,
            "applicants_count": 0,
            "contracted_count": 0,
            "observed_at": "2026-08-02T12:00:00Z",
        }],
        "already_applied_ids": [],
    })


def test_every_buyer_facing_prompt_carries_the_persona() -> None:
    head = buyer_voice.PERSONA.splitlines()[0]

    assert head in load("reply_composer").composition_prompt(
        {"conversation": [{"side": "buyer", "body": "お願いします"}]}
    )
    assert head in load("followup_draft").followup_prompt(
        conversation=[{"side": "buyer", "body": "検討します"}],
        followups_sent=0,
        silent_days=4.0,
    )
    assert head in load("ask_buyer").question_prompt(state={"checks": []})
    # The planner is the one that had no persona line at all before 2026-08-07.
    planner = load("application_planner", "application_planner_persona")
    assert head in planner.planner_prompt(planner_snapshot())


# ---------------------------------------------------------------------------
# 5. matching_delivery -- the identity that replaced the sha256
# ---------------------------------------------------------------------------

def formal():
    return load("coconala_formal_delivery_browser", "formal_delivery_buyer_voice")


def delivered_row(text: str, attachment: str = "deliverable.zip") -> dict:
    return {"side": "seller", "text": text, "attachments": [attachment]}


def test_our_delivery_is_identified_by_text_with_no_sha_anywhere() -> None:
    m = formal()
    message = m.delivery_message("deliverable.zip", ["トップページの画像を差し替えた"])
    assert buyer_voice.check_style(message) == []
    contract = {"artifact": Path("/tmp/deliverable.zip"), "message": message}

    # The row as the site renders it back: whitespace reflowed, tail truncated behind
    # 「続きを読む」 -- which is exactly why the key is the head and not the tail.
    rendered = message.replace("\n", " \n\n ")[:150]
    state = {"seller_messages": [delivered_row(rendered)]}
    assert m.matching_delivery(state, contract) is not None


def test_someone_elses_row_is_never_mistaken_for_ours() -> None:
    m = formal()
    message = m.delivery_message("deliverable.zip", ["画像を差し替えた"])
    contract = {"artifact": Path("/tmp/deliverable.zip"), "message": message}

    # Right file, different words: not the message this run composed.
    other_words = {"seller_messages": [
        delivered_row("先にご質問への回答をお送りします。添付: deliverable.zip")
    ]}
    assert m.matching_delivery(other_words, contract) is None

    # Right words, different file: not this artifact, so dedupe must not fire.
    other_file = {"seller_messages": [delivered_row(message, attachment="other.zip")]}
    assert m.matching_delivery(other_file, contract) is None

    # Nothing at all.
    assert m.matching_delivery({"seller_messages": []}, contract) is None


def test_an_empty_message_never_matches_everything() -> None:
    # startswith("") is True for every row, which would make an empty contract message
    # claim the buyer's own posts as our delivery.
    m = formal()
    contract = {"artifact": Path("/tmp/deliverable.zip"), "message": "   "}
    state = {"seller_messages": [delivered_row("買い手の投稿です")]}
    assert m.matching_delivery(state, contract) is None


# ---------------------------------------------------------------------------
# 6. The rewritten delivery text
# ---------------------------------------------------------------------------

# The acceptance_delta that produced the 2026-08-06 bullets, verbatim.
REAL_DELTA_91000002 = [
    "現在確認できる買い手からのメッセージと取引情報を確認資料としてまとめました。",
    "記載のない制作内容は推測せず、未確認の条件として明記しました。",
    "作業を始める前に必要な確認事項を買い手向けにまとめました。",
]


def test_the_delivery_text_is_no_longer_a_build_report() -> None:
    m = formal()
    message = m.delivery_message("delivery-sample.md", REAL_DELTA_91000002)
    # The shapes Dais named as making it read as a bot.
    assert "確認した内容は以下のとおりです" not in message
    assert "・" not in message
    assert "パッケージSHA" not in message
    # What must survive: the buyer still knows which file is theirs.
    assert "添付: delivery-sample.md" in message
    assert buyer_voice.check_style(message) == []


def test_a_long_delta_drops_the_scope_line_instead_of_writing_an_unreadable_one() -> None:
    # These three items quote out to 69 characters in a single sentence -- the bullet
    # report wearing a different hat. No person writes that, so the line is omitted and
    # the attachment plus the invitation to reply carry the message.
    m = formal()
    message = m.delivery_message("delivery-sample.md", REAL_DELTA_91000002)
    assert "今回対応したのは" not in message
    assert "確認資料に整理しました" not in message
    # Still a complete, sendable message.
    assert message.startswith("お世話になっております。")
    assert "添付: delivery-sample.md" in message


def test_a_short_delta_still_tells_the_buyer_what_was_done() -> None:
    # The normal case for a real deliverable. Dropping the scope line always would lose
    # the honest answer to "what did I just get".
    m = formal()
    message = m.delivery_message("a.zip", ["トップページの画像を差し替え"])
    assert "今回対応したのは「トップページの画像を差し替え」です。" in message


def test_at_most_two_items_are_quoted_and_the_rest_become_hoka() -> None:
    m = formal()
    message = m.delivery_message("a.zip", ["一", "二", "三", "四", "五"])
    assert "今回対応したのは「一」「二」ほかです。" in message
    assert "「三」" not in message
    assert "「五」" not in message
    assert "・" not in message


def test_a_delivery_with_no_delta_still_reads_as_a_sentence() -> None:
    m = formal()
    message = m.delivery_message("a.zip", [])
    assert "今回対応したのは" not in message
    assert "添付: a.zip" in message
    assert buyer_voice.check_style(message) == []


def test_no_google_doc_link_reproduces_the_message_byte_for_byte() -> None:
    # §EM' (2026-08-09): the default parameter must not change any delivery that
    # existed before this capability -- the overwhelming majority, which never call
    # google_docs_publisher.py.
    m = formal()
    with_default = m.delivery_message("a.zip", ["画像を差し替えた"])
    explicit_none = m.delivery_message("a.zip", ["画像を差し替えた"], None)
    assert with_default == explicit_none
    assert "docs.google.com" not in with_default


def test_a_google_doc_link_is_appended_after_the_attachment_line() -> None:
    m = formal()
    link = "https://docs.google.com/document/d/1abc/edit"
    message = m.delivery_message("sample-game-guide-v1.docx", ["概要を整理した"], link)
    assert message.endswith(f"Googleドキュメント（閲覧・コメント可）: {link}")
    assert "添付: sample-game-guide-v1.docx" in message
    assert buyer_voice.check_style(message) == []


# ---------------------------------------------------------------------------
# 7. The send-time gates
# ---------------------------------------------------------------------------

def manual_args(tmp_path: Path, message: str) -> argparse.Namespace:
    root = tmp_path / "project"
    root.mkdir()
    artifact = root / "deliverable.zip"
    artifact.write_bytes(b"final artifact bytes")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    acceptance = root / "acceptance.json"
    acceptance.write_text(
        json.dumps({"status": "PASS", "package": {"sha256": digest}}), encoding="utf-8"
    )
    return argparse.Namespace(
        project_id="91000002",
        talkroom_id="90000004",
        talkroom_url="https://coconala.com/talkrooms/90000004",
        project_root=root,
        artifact=artifact,
        artifact_sha256=digest,
        acceptance=acceptance,
        message=message,
        artifact_version="v1",
        acceptance_delta=["画像を差し替えた"],
    )


def test_manual_delivery_refuses_an_internal_token(tmp_path) -> None:
    m = formal()
    args = manual_args(tmp_path, "納品します。検証PASSしました。")
    with pytest.raises(ValueError, match="buyer_style_violation"):
        m.validate(args)


def test_manual_delivery_no_longer_appends_the_sha_to_the_buyers_text(tmp_path) -> None:
    m = formal()
    args = manual_args(tmp_path, "お世話になっております。修正版をお届けします。")
    contract = m.validate(args)

    assert "添付: deliverable.zip" in contract["message"]
    assert contract["artifact_sha256"] not in contract["message"]
    assert "パッケージSHA" not in contract["message"]
    # The sha is still the identity everywhere it was ever the proof.
    assert contract["event_key"] == f"coconala:formal:91000002:{contract['artifact_sha256']}"


def queue_fixture(tmp_path: Path, delta: list[str]):
    root = tmp_path / "project"
    root.mkdir()
    artifact = root / "deliverable.zip"
    artifact.write_bytes(b"final artifact bytes")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    acceptance = root / "acceptance.json"
    acceptance.write_text(
        json.dumps({"status": "PASS", "package": {"sha256": digest}}), encoding="utf-8"
    )
    manifest = {
        "status": "ok",
        "acceptance_status": "PASS",
        "project_root": str(root),
        "artifact_path": str(artifact),
        "artifact_version": "v1",
        "acceptance_evidence_path": str(acceptance),
        "acceptance_delta": delta,
        "package_sha256": digest,
    }
    queue = {
        "delivery_action": "formal",
        "formal_delivery_checkbox": True,
        "delivery_evidence": {
            key: manifest[key]
            for key in (
                "artifact_path", "artifact_version", "acceptance_evidence_path",
                "acceptance_status", "acceptance_delta", "package_sha256",
            )
        },
        "talkroom_id": "90000004",
        "request_id": "91000002",
        "marketplace_url": "https://coconala.com/talkrooms/90000004",
    }
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return queue_path, manifest_path, root, digest


def test_queue_delivery_produces_buyer_language_and_keeps_the_sha_internal(tmp_path) -> None:
    m = formal()
    queue_path, manifest_path, root, digest = queue_fixture(
        tmp_path, ["トップページの画像を差し替えた"]
    )
    contract = m.validate_queue_contract(queue_path, manifest_path, root)

    assert digest not in contract["message"]
    assert "確認した内容は以下のとおりです" not in contract["message"]
    assert "・" not in contract["message"]
    assert "添付: deliverable.zip" in contract["message"]
    assert "トップページの画像を差し替えた" in contract["message"]
    # Unchanged: the evidence identity and the dedupe key.
    assert contract["artifact_sha256"] == digest
    assert contract["event_key"] == f"coconala:formal:91000002:{digest}"


def test_queue_delivery_refuses_a_delta_that_leaks_an_internal_token(tmp_path) -> None:
    # The delta is written by the build agent, so it is a real path for internal
    # vocabulary to reach the buyer -- this is how the bullets in the 91000002 message
    # were produced.
    m = formal()
    queue_path, manifest_path, root, _ = queue_fixture(
        tmp_path, ["検証PASSを確認した"]
    )
    with pytest.raises(ValueError, match="buyer_style_violation"):
        m.validate_queue_contract(queue_path, manifest_path, root)


def planner_decision(proposal: str) -> dict:
    return {"decisions": [{
        "request_id": "91000032",
        "eligibility": "eligible",
        "reason_codes": ["async_text_work"],
        "proposal_text": proposal,
        "price_jpy": 5000,
        "deliver_date": "2026-08-11",
    }]}


def test_a_clean_proposal_is_accepted_by_the_planner() -> None:
    # Establishes that the fixture is otherwise valid, so the next test's failure can only
    # be the style gate.
    planner = load("application_planner", "application_planner_clean")
    proposal = "ご依頼の内容、対応可能です。" * 20

    assert planner.validate_decisions(planner_snapshot(), planner_decision(proposal)) == []


def test_the_planner_refuses_a_proposal_carrying_an_internal_token() -> None:
    # proposal_text is read by the buyer deciding whether to hire us.
    planner = load("application_planner", "application_planner_buyer_voice")
    proposal = "ご依頼の内容、対応可能です。" * 20 + "acceptance は PASS です。"

    errors = planner.validate_decisions(planner_snapshot(), planner_decision(proposal))

    style = [item for item in errors if "buyer_style_violation" in item]
    assert style, errors
    assert "acceptance" in style[0]
