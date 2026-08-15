from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


# P1a-9b (spec §0.1.6). Read a paid talkroom well enough to prove we answered.
#
# Paid rooms and pre-purchase DMs are different pages with different URL families:
# /talkrooms/<id> versus /mypage/direct_message/<id>. thread_state() in the reply browser
# hard-requires the second and raises unexpected_url on the first, so none of the existing
# readback machinery could ever see a paying customer's room.
#
# The paid extractor that does exist keeps only `side === 'seller'` and carries no
# timestamps, so "did we speak after the buyer" was not answerable from it either. DOM order
# is chronological though, which is enough: if the last message that is not a system notice
# is ours, the buyer has our answer below theirs. Ordering, not clocks.
#
# System rows are excluded from that judgement deliberately. Coconala injects 納品 and
# 検収 notices into the thread, and letting one of those count as "we spoke" would close a
# liability that nobody answered.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_thread_state.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_thread_state", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dom(*messages, url="https://coconala.com/talkrooms/90000004") -> dict:
    return {
        "url": url,
        "title": "トークルーム",
        "messages": [
            {"side": side, "text": text, "attachments": list(attachments)}
            for side, text, *rest in messages
            for attachments in [rest[0] if rest else []]
        ],
    }


BUYER = ("buyer", "73ページのリンクが違います", [])
SELLER = ("seller", "修正しました。ご確認ください", [])
SYSTEM = ("system", "納品されました", [])


# --- the page must be the one we think it is ----------------------------------------------


def test_a_pre_purchase_dm_url_is_refused() -> None:
    m = load_module()
    with pytest.raises(m.NotAPaidTalkroom):
        m.paid_thread_state(dom(BUYER, url="https://coconala.com/mypage/direct_message/9926596"), "90000004")


def test_another_talkroom_is_refused() -> None:
    # Reading room B and closing room A's liability is the worst possible bug here.
    m = load_module()
    with pytest.raises(m.NotAPaidTalkroom):
        m.paid_thread_state(dom(BUYER), "90000005")


# --- who spoke last, ignoring the platform's own notices -----------------------------------


def test_our_reply_below_theirs_means_they_have_our_answer() -> None:
    m = load_module()
    state = m.paid_thread_state(dom(BUYER, SELLER), "90000004")
    assert state["seller_after_buyer"] is True
    assert state["last_sender"] == "seller"


def test_their_message_below_ours_means_they_are_waiting_again() -> None:
    m = load_module()
    state = m.paid_thread_state(dom(SELLER, BUYER), "90000004")
    assert state["seller_after_buyer"] is False


def test_a_delivery_notice_is_not_us_speaking() -> None:
    # 納品されました is the platform talking. Counting it would close a silence nobody broke.
    m = load_module()
    state = m.paid_thread_state(dom(BUYER, SYSTEM), "90000004")
    assert state["seller_after_buyer"] is False
    assert state["last_sender"] == "buyer"


def test_a_room_where_the_buyer_never_spoke_cannot_prove_an_answer() -> None:
    m = load_module()
    state = m.paid_thread_state(dom(SELLER), "90000004")
    assert state["seller_after_buyer"] is False


def test_an_empty_room_is_not_an_answered_room() -> None:
    m = load_module()
    state = m.paid_thread_state(dom(), "90000004")
    assert state["seller_after_buyer"] is False
    assert state["last_sender"] is None


# --- the fingerprint has to move when the conversation moves -------------------------------


def test_the_fingerprint_changes_when_a_message_is_added() -> None:
    m = load_module()
    before = m.paid_thread_state(dom(BUYER), "90000004")["fingerprint"]
    after = m.paid_thread_state(dom(BUYER, SELLER), "90000004")["fingerprint"]
    assert before != after


def test_the_fingerprint_covers_attachments() -> None:
    # A message whose text is identical but which now carries the deliverable is a different
    # conversation state, and the ledger must be able to tell them apart.
    m = load_module()
    plain = m.paid_thread_state(dom(BUYER, ("seller", "どうぞ", [])), "90000004")["fingerprint"]
    with_file = m.paid_thread_state(dom(BUYER, ("seller", "どうぞ", ["v23.zip"])), "90000004")["fingerprint"]
    assert plain != with_file


# --- it must satisfy the readback decision, which is the reason it exists -------------------


def test_it_closes_a_liability_through_the_existing_readback_path() -> None:
    m = load_module()
    path = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_readback.py"
    spec = importlib.util.spec_from_file_location("paid_lane_readback", path)
    readback = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(readback)

    state = m.paid_thread_state(dom(BUYER, SELLER), "90000004")
    decided = readback.decide_readbacks(
        [{"liability_key": "90000004:abc", "talkroom_id": "90000004"}],
        thread_states={"90000004": state},
        intents={"90000004:abc": "ask_buyer"},
    )
    assert decided["90000004:abc"]["action"] == "ask_buyer"


def test_it_refuses_to_close_when_the_buyer_spoke_last() -> None:
    m = load_module()
    path = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_readback.py"
    spec = importlib.util.spec_from_file_location("paid_lane_readback", path)
    readback = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(readback)

    state = m.paid_thread_state(dom(SELLER, BUYER), "90000004")
    decided = readback.decide_readbacks(
        [{"liability_key": "90000004:abc", "talkroom_id": "90000004"}],
        thread_states={"90000004": state},
        intents={"90000004:abc": "ask_buyer"},
    )
    assert decided == {}
