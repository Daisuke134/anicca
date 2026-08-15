#!/usr/bin/env python3
"""The last gate before a buyer is contacted again."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import stop_signal  # noqa: E402

# Quoted exactly from ~/gig/reply-transcripts.jsonl. The buyer left because we showed an
# invoice before anything was agreed.
MEASURED_REFUSAL = "まだ、最終的な話までしてませんが。 それで先に請求画面って？ 他の方探して下さい。"


def test_the_measured_refusal_stops_the_thread():
    assert stop_signal.stop_reason(MEASURED_REFUSAL) == "other_seller"


def test_considering_is_not_a_refusal():
    # The state follow-ups exist to serve. Calling it a stop would empty the pipeline.
    assert stop_signal.stop_reason("社内で検討しますので少しお待ちください") is None


def test_a_polite_maybe_survives_a_refusal_word():
    # 「見送る」 and 「検討」 in one breath is a maybe, and a maybe is worth a follow-up.
    assert stop_signal.stop_reason("今回は見送る方向で検討していますが、また相談します") is None


def test_each_refusal_shape_is_recognised():
    cases = {
        "申し訳ありませんが今回はお断りします": "declined",
        "結構です": "no_thanks",
        "興味ありません": "not_interested",
        "募集を終了しました": "cancelled",
        "自分で対応しましたので大丈夫です": "already_solved",
        "今後のご連絡は不要です": "stop_contact",
    }
    for text, reason in cases.items():
        assert stop_signal.stop_reason(text) == reason, text


def test_ambiguous_opener_is_not_a_refusal():
    # 「今回は」 opens both a refusal and an order.
    assert stop_signal.stop_reason("今回はぜひお願いしたいです") is None


def test_empty_and_non_text_read_as_open():
    assert stop_signal.stop_reason("") is None
    assert stop_signal.stop_reason(None) is None
    assert stop_signal.stop_reason(42) is None


def test_our_own_words_cannot_stop_the_thread():
    conversation = [
        {"sender": "seller", "text": "他の方を探されますか？"},
        {"sender": "buyer", "text": "いえ、お願いしたいです"},
    ]
    assert stop_signal.stopped_by(conversation) is None
    assert stop_signal.is_stopped(conversation) is False


def test_a_refusal_buried_under_our_later_messages_still_counts():
    conversation = [
        {"sender": "buyer", "text": MEASURED_REFUSAL},
        {"sender": "seller", "text": "承知しました"},
        {"sender": "seller", "text": "その後いかがでしょうか"},
    ]
    stopped = stop_signal.stopped_by(conversation)
    assert stopped["reason"] == "other_seller"
    assert "他の方探して下さい" in stopped["text"]


def test_conversation_may_be_a_dict_or_bare_strings():
    assert stop_signal.is_stopped({"messages": [{"sender": "buyer", "text": "結構です"}]})
    assert stop_signal.is_stopped(["結構です"])
    assert stop_signal.is_stopped(None) is False
