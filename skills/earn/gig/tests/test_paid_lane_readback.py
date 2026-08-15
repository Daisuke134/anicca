from __future__ import annotations

import importlib.util
from pathlib import Path


# P1a-9a (spec §0.1.6). Turn observed talkroom state into close decisions.
#
# `coconala_reply_browser.thread_state()` already produces the right primitive from live DOM:
# `seller_sent_at`, `latest_buyer_sent_at`, `last_sender`, and a fingerprint over every
# message. Nothing was consuming it for paid rooms, so `close()` had no reachable input and
# the disposer could only ever refuse.
#
# Closing needs both halves and neither alone. An intent without a landing is "we tried" —
# the send may have been rejected, and this loop has recorded `submit_rejected_sending_
# unavailable` as recently as today. A landing without an intent is someone else's message,
# or our own from a previous pass, and claiming it would close a liability we never answered.
#
# Timestamps decide, not `last_sender`, because the buyer can speak again after us within the
# same observation and the ordering is what the customer actually experiences.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "paid_lane_readback.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_lane_readback", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KEY = "90000004:9292841a"
OPEN = [{"liability_key": KEY, "talkroom_id": "90000004", "order_value_jpy": 2500}]

# Shaped exactly like the evidence half of thread_state()'s return value.
def state(seller: str | None, buyer: str | None, last_sender: str = "seller") -> dict:
    return {
        "talkroom_id": "90000004",
        "url": "https://coconala.com/mypage/direct_message/90000004",
        "fingerprint": "f" * 64,
        "seller_count": 1,
        "seller_message_hashes": ["a" * 64],
        "seller_messages": [{"body_sha256": "a" * 64, "sent_at": seller or ""}],
        "seller_sent_at": seller,
        "latest_buyer_sent_at": buyer,
        "last_sender": last_sender,
    }


INTENT = {KEY: "ask_buyer"}


# --- both halves, or nothing ---------------------------------------------------------------


def test_speaking_after_the_buyer_with_an_intent_closes_it() -> None:
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state("2026-08-05T03:00:00+00:00", "2026-08-05T01:00:00+00:00")},
        intents=INTENT,
    )
    assert readbacks[KEY]["action"] == "ask_buyer"
    assert readbacks[KEY]["posted_at"] == "2026-08-05T03:00:00+00:00"
    assert readbacks[KEY]["fingerprint"] == "f" * 64


def test_an_intent_that_never_landed_does_not_close() -> None:
    # submit_rejected_sending_unavailable is a real error this loop produced today.
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state("2026-08-04T09:00:00+00:00", "2026-08-05T01:00:00+00:00")},
        intents=INTENT,
    )
    assert KEY not in readbacks


def test_a_message_we_never_intended_does_not_close() -> None:
    # Our own reply from an earlier pass, or a message from elsewhere. Claiming it would
    # close a liability nobody answered this pass.
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state("2026-08-05T03:00:00+00:00", "2026-08-05T01:00:00+00:00")},
        intents={},
    )
    assert KEY not in readbacks


def test_no_observation_of_the_room_does_not_close() -> None:
    m = load_module()
    assert m.decide_readbacks(OPEN, thread_states={}, intents=INTENT) == {}


def test_a_room_where_we_have_never_spoken_does_not_close() -> None:
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state(None, "2026-08-05T01:00:00+00:00")},
        intents=INTENT,
    )
    assert KEY not in readbacks


def test_a_buyer_who_has_never_spoken_is_not_a_liability_we_can_close() -> None:
    # If we cannot see when the buyer spoke, we cannot claim to have answered them.
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state("2026-08-05T03:00:00+00:00", None)},
        intents=INTENT,
    )
    assert KEY not in readbacks


def test_an_unparsable_timestamp_refuses_to_guess() -> None:
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state("yesterday afternoon", "2026-08-05T01:00:00+00:00")},
        intents=INTENT,
    )
    assert KEY not in readbacks


def test_an_action_outside_the_four_is_not_an_intent() -> None:
    m = load_module()
    readbacks = m.decide_readbacks(
        OPEN,
        thread_states={"90000004": state("2026-08-05T03:00:00+00:00", "2026-08-05T01:00:00+00:00")},
        intents={KEY: "observed"},
    )
    assert KEY not in readbacks


# --- it must compose with the disposer, which is the whole point ---------------------------


def test_the_disposer_closes_the_liability_from_this_readback(tmp_path) -> None:
    m = load_module()
    def load(name):
        path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    sl = load("silence_liability")
    disp = load("paid_lane_dispose")
    store = tmp_path / "sl.jsonl"
    sl.observe(store, [{**OPEN[0], "liability_open": True, "title": "t"}], pass_id="pass-1")

    readbacks = m.decide_readbacks(
        sl.open_liabilities(store),
        thread_states={"90000004": state("2026-08-05T03:00:00+00:00", "2026-08-05T01:00:00+00:00")},
        intents=INTENT,
    )
    result = disp.dispose(store, pass_id="pass-1", readbacks=readbacks)
    assert result["closed"] == 1
    assert sl.open_liabilities(store) == []
