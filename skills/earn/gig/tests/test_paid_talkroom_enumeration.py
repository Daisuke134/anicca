from __future__ import annotations

import importlib.util
from pathlib import Path


# P1a-3 (spec §0.1.6). Enumerate the paid talkrooms and say which ones have a buyer waiting.
#
# The lane starts from external truth rather than from what the agent did. reply_queue.py
# does the opposite on purpose — it collects `paid_talkroom_ids` from the snapshot's orders
# and then `continue`s past every one of them (line ~163), which is the first of the three
# locks that left paying customers with no owner.
#
# The fixtures below are the two real orders from pass gig-pass-1785888005-99487, copied
# field for field. 90000004 is 買い手C: the buyer's initial request is pending an artifact,
# nothing is buyer-visible, nothing was formally delivered. It has been open since 08-03.
# 90000005 was delivered and is sitting at 納品確認待ち. A correct enumerator separates them.
#
# The load-bearing risk, named in §0.1.6 before any code existed: this enumerator is the
# single point of blindness. If a room is never enumerated, no liability is ever born and
# you get the identical 24-pass silence with more machinery and more confidence. So a row
# that cannot be enumerated has to surface as an error, never as an absence.

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "paid_talkroom_enumeration.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("paid_talkroom_enumeration", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


KITTY = {
    "talkroom_id": "90000004",
    "contract_id": "direct-offer:92000010",
    "title": "ウェブ画像の更新と軽微な調整",
    "price_jpy": 2500,
    "status": "paid",
    "talkroom_state": "unknown",
    "buyer_feedback_pending_artifact": True,
    "buyer_feedback_stage": "initial_request",
    "buyer_feedback_sha256": "9292841a9cb4bd01aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "buyer_visible_artifact_observed": False,
    "formal_delivery_observed": False,
    "talkroom_observed_at": "2026-08-05T00:03:48.428808+00:00",
    "delivery_date": None,
}

DELIVERED = {
    "talkroom_id": "90000005",
    "contract_id": "offer:92000012",
    "title": "生成AI活用 画面キャプチャの多言語化（4枚）",
    "price_jpy": 4200,
    "status": "unknown",
    "talkroom_state": "納品確認待ち",
    "buyer_feedback_pending_artifact": False,
    "buyer_feedback_stage": None,
    "buyer_feedback_sha256": None,
    "buyer_visible_artifact_observed": True,
    "formal_delivery_observed": True,
    "talkroom_observed_at": "2026-08-05T00:03:48.428808+00:00",
    "delivery_date": "2026-08-02",
}


def snapshot(*orders):
    return {"captured_at": "2026-08-05T00:03:48.428808+00:00", "orders": list(orders)}


# --- paid rooms are the subject, not the exclusion ---------------------------------------


def test_paid_rooms_are_enumerated_rather_than_skipped() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY, DELIVERED))
    assert {r["talkroom_id"] for r in result["rooms"]} == {"90000004", "90000005"}


def test_the_order_value_travels_with_the_room() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY, DELIVERED))
    values = {r["talkroom_id"]: r["order_value_jpy"] for r in result["rooms"]}
    assert values == {"90000004": 2500, "90000005": 4200}


# --- who is waiting -----------------------------------------------------------------------


def test_a_buyer_waiting_on_an_artifact_is_an_open_liability() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY, DELIVERED))
    open_ids = {r["talkroom_id"] for r in result["rooms"] if r["liability_open"]}
    assert open_ids == {"90000004"}


def test_a_delivered_room_awaiting_confirmation_is_not_a_liability() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(DELIVERED))
    assert result["rooms"][0]["liability_open"] is False


def test_the_liability_is_keyed_to_the_specific_buyer_message() -> None:
    # Keyed by (talkroom_id, buyer_feedback_sha256) so a *new* buyer message opens a new
    # liability instead of being swallowed by the one we already closed.
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY))
    assert result["rooms"][0]["liability_key"] == (
        "90000004:9292841a9cb4bd01aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


# --- blindness must be loud ---------------------------------------------------------------


def test_a_row_without_a_talkroom_id_becomes_an_error_not_an_absence() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY, {"price_jpy": 9000}))
    assert result["errors"], "an unenumerable order must be reported"
    assert any("talkroom_id" in e for e in result["errors"])


def test_the_counts_are_reported_so_a_silent_drop_is_visible() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY, DELIVERED, {"price_jpy": 9000}))
    assert result["orders_seen"] == 3
    assert result["rooms_enumerated"] == 2
    assert result["dropped"] == 1


def test_an_empty_orders_list_is_reported_rather_than_read_as_healthy() -> None:
    # `orders: []` is exactly what a broken collector produces, and it is indistinguishable
    # from "no paying customers" unless it is called out.
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot())
    assert result["orders_seen"] == 0
    assert result["collector_suspect"] is True


def test_orders_present_means_the_collector_is_not_suspect() -> None:
    m = load_module()
    result = m.enumerate_paid_talkrooms(snapshot(KITTY))
    assert result["collector_suspect"] is False
