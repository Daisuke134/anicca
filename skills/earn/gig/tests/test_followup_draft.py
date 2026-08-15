from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


# A follow-up goes to a real buyer on a platform that can suspend the account, so the
# things Coconala forbids are checked by code rather than hoped for:
#   外部サービスへの誘導      https://coconala-support.zendesk.com/hc/ja/articles/218179168
#   プラットフォーム外決済    https://coconala-support.zendesk.com/hc/ja/articles/10003485737881
# And the lesson that produced this whole line of work: kiki_1115 was told the deliverable
# would arrive 本日中, free, with no purchase gate -- and went silent.


def load():
    spec = importlib.util.spec_from_file_location(
        "followup_draft", SCRIPTS / "followup_draft.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_prompt_carries_the_purchase_gate() -> None:
    # Same rule P3-1 put in the first reply. A follow-up that promises free work repeats
    # the exact mistake that created the silence it is trying to break.
    m = load()
    prompt = m.followup_prompt(
        conversation=[{"side": "buyer", "body": "Canvaで作れますか"}],
        followups_sent=0,
        silent_days=13.5,
    )
    assert "ご購入後" in prompt
    assert "購入前" in prompt


def test_the_prompt_forbids_repeating_the_previous_message() -> None:
    # 「the buyer saw it and did not act」-- restating the same offer adds no new basis for
    # a decision, and reads as not having noticed the silence.
    m = load()
    prompt = m.followup_prompt(
        conversation=[{"side": "seller", "body": "前回の提案"}],
        followups_sent=1,
        silent_days=8.0,
    )
    assert "繰り返さない" in prompt
    assert "新しい" in prompt


def test_the_last_allowed_followup_is_told_to_close_gracefully() -> None:
    # Yesware's break-up form: give the buyer an exit that needs no reply, rather than a
    # fourth ask that cannot legally come.
    m = load()
    prompt = m.followup_prompt(
        conversation=[{"side": "buyer", "body": "検討します"}],
        followups_sent=2,
        silent_days=20.0,
    )
    assert "最後" in prompt


def test_an_earlier_followup_is_not_told_to_close() -> None:
    m = load()
    prompt = m.followup_prompt(
        conversation=[{"side": "buyer", "body": "検討します"}],
        followups_sent=0,
        silent_days=4.0,
    )
    assert "最後" not in prompt


def test_a_draft_with_an_external_link_is_refused() -> None:
    m = load()
    verdict = m.check_draft("詳しくは https://example.com をご覧ください。")
    assert verdict["ok"] is False
    assert "external_link" in verdict["violations"]


def test_a_draft_with_contact_details_is_refused() -> None:
    m = load()
    for body, code in (
        ("ご連絡は sales@example.com まで。", "external_contact"),
        ("お電話 090-1234-5678 までどうぞ。", "external_contact"),
        ("LINEのIDをお伝えします。", "external_contact"),
    ):
        verdict = m.check_draft(body)
        assert verdict["ok"] is False, body
        assert code in verdict["violations"], body


def test_a_draft_steering_payment_off_platform_is_refused() -> None:
    m = load()
    verdict = m.check_draft("お支払いは銀行振込で直接お願いします。")
    assert verdict["ok"] is False
    assert "off_platform_payment" in verdict["violations"]


def test_a_clean_follow_up_passes() -> None:
    m = load()
    verdict = m.check_draft(
        "先日のご相談の件、その後いかがでしょうか。ご購入後すぐに着手し、"
        "ご購入当日から翌日中を目安に初稿をご提出します。"
    )
    assert verdict["ok"] is True
    assert verdict["violations"] == []


def test_an_empty_draft_is_refused() -> None:
    # Never send silence dressed as a message.
    m = load()
    assert m.check_draft("")["ok"] is False
    assert m.check_draft(None)["ok"] is False


def test_promising_delivery_without_a_purchase_gate_is_refused() -> None:
    # The exact message that lost kiki_1115: a deliverable promised 本日中, free, with no
    # purchase anywhere in the sentence. The prompt already forbids this, but a prompt is
    # a request and this is a rule -- and the whole reason this follow-up exists is that
    # the request was not enough the first time.
    m = load()
    verdict = m.check_draft(
        "最短で本日中に、初回の環境構成案と生成設定・プロンプト例をお送りします。"
    )
    assert verdict["ok"] is False
    assert "unpaid_delivery_promise" in verdict["violations"]


def test_the_same_promise_with_a_gate_passes() -> None:
    # The message that closed 買い手B: identical intent, gated on purchase.
    m = load()
    verdict = m.check_draft(
        "ご購入後はまず、元画像のレイアウトと使用しているフォントを確認したうえで、Canvaでの再現作業に着手します。"
        "最短でご購入当日から翌日中を目安に初稿をご提出します。"
    )
    assert verdict["ok"] is True


def test_a_message_that_promises_nothing_needs_no_gate() -> None:
    # A short nudge is the recommended first follow-up. Demanding a purchase gate in a
    # sentence that offers nothing would block exactly the message most likely to work.
    m = load()
    verdict = m.check_draft("先日のご相談の件、その後いかがでしょうか。")
    assert verdict["ok"] is True
    assert verdict["violations"] == []


def test_a_break_up_message_needs_no_gate() -> None:
    m = load()
    verdict = m.check_draft(
        "その後ご状況いかがでしょうか。またご入用の際にお声がけいただければ幸いです。"
    )
    assert verdict["ok"] is True
