"""A5: the marketplace's own cancellation clock, and what it must do to the queue.

An order purchased on 2026-08-07 22:38 carried a banner coconala renders itself:

    48時間以内に出品者がトークルーム内で連絡をしない場合、自動的に取引がキャンセルされます。
    期限：8/9 23:00

Nothing in the loop held that clock. The delivery date said 8/20, so the order looked
comfortable, while a different clock -- the platform's, the one that is actually enforced
-- was two days from deleting it. These tests pin both halves: the deadline is READ from
the banner rather than recomputed from a purchase time, and an order with a live clock and
no seller message outranks work that is merely in progress until contact is made.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


delivery_queue = _load("delivery_queue")
collector = _load("coconala_queue_snapshot")

BANNER = (
    "48時間以内に出品者がトークルーム内で連絡をしない場合、自動的に取引がキャンセルされます。\n"
    "期限：8/9 23:00"
)
OBSERVED = "2026-08-07T14:07:56.781212+00:00"  # 2026-08-07 23:07 JST


# --------------------------------------------------------------------------------------
# Reading the deadline off the platform
# --------------------------------------------------------------------------------------

_contact_deadline_from_notice = collector.contact_deadline_from_notice


def test_the_deadline_is_the_one_the_banner_states_not_purchase_time_plus_48h():
    # 22:38 + 48h would be 8/9 22:38. The banner says 23:00, and the banner is what
    # coconala enforces. Any drift between the two is the platform's to define, not ours.
    assert _contact_deadline_from_notice(BANNER, OBSERVED) == "2026-08-09T23:00:00+09:00"


def test_no_banner_means_no_deadline():
    assert _contact_deadline_from_notice(None, OBSERVED) is None
    assert _contact_deadline_from_notice("取引中\nメッセージを入力", OBSERVED) is None


def test_a_year_end_banner_rolls_into_the_next_year():
    assert (
        _contact_deadline_from_notice("期限：1/2 09:00", "2026-12-31T05:00:00+00:00")
        == "2027-01-02T09:00:00+09:00"
    )


def test_an_explicit_year_on_the_banner_wins_over_the_observation():
    assert (
        _contact_deadline_from_notice("期限：2027/1/2 09:00", "2026-12-31T05:00:00+00:00")
        == "2027-01-02T09:00:00+09:00"
    )


# --------------------------------------------------------------------------------------
# What the clock does to the queue
# --------------------------------------------------------------------------------------

def _order(**overrides):
    base = {
        "contract_id": "offer:1",
        "talkroom_id": "1",
        "buyer": "buyer",
        "title": "t",
        "price_jpy": 5000,
        "price_source": "structured_order_label",
        "delivery_date": "2026-08-20",
        "status": "paid",
        "buyer_feedback_pending_artifact": True,
        "buyer_visible_artifact_observed": False,
        "buyer_agreement_observed": False,
        "buyer_reply_after_artifact_observed": False,
        "buyer_attachments": [],
        "formal_delivery_observed": False,
        "talkroom_state": "取引中",
        "seller_message_observed": False,
        "contact_deadline": None,
        "buyer_feedback_stage": "initial_request",
    }
    base.update(overrides)
    return base


def _build(tmp_path, orders, captured_at=OBSERVED):
    snapshot = {"captured_at": captured_at, "orders": orders, "quotes": []}
    return delivery_queue.build(snapshot, tmp_path / "no-evidence", date(2026, 8, 7))


UNCONTACTED = dict(
    contract_id="offer:92000015", talkroom_id="90000001", buyer="買い手A",
    delivery_date="2026-08-20",
    seller_message_observed=False, contact_deadline="2026-08-09T23:00:00+09:00",
)
MID_REVISION = dict(
    contract_id="offer:92000013", talkroom_id="90000002", buyer="買い手B",
    delivery_date="2026-08-11", buyer_feedback_stage="revision",
    buyer_reply_after_artifact_observed=True,
    seller_message_observed=True, contact_deadline=None,
)


def test_an_uncontacted_order_with_a_live_clock_outranks_a_mid_revision_order(tmp_path):
    queue = _build(tmp_path, [_order(**MID_REVISION), _order(**UNCONTACTED)])
    order = [item["buyer"] for item in queue["items"]]
    assert order == ["買い手A", "買い手B"], order
    top = queue["items"][0]
    assert top["priority"] == delivery_queue.FIRST_CONTACT_PRIORITY
    assert top["first_contact_at_risk"] is True
    # The escalation must not invent a class: gig_pass.sh's `case "$TOP_CLASS"` arm lists
    # the paid classes by name, and an unknown string would match nothing and act on
    # nothing. Reaching the top has to mean reaching a lane that exists.
    assert top["queue_class"] in delivery_queue.QUEUE_PRIORITY


def test_without_the_clock_the_mid_revision_order_still_leads(tmp_path):
    """The defect as measured on the live 23:07 snapshot, before the clock existed."""
    queue = _build(
        tmp_path,
        [_order(**MID_REVISION), _order(**{**UNCONTACTED, "contact_deadline": None})],
    )
    assert [item["buyer"] for item in queue["items"]] == ["買い手B", "買い手A"]


def test_once_we_have_spoken_the_order_drops_back_to_normal_priority(tmp_path):
    """A deadline that is met stops mattering -- from either live fact, independently."""
    # a) our own capture sees a seller message, even while the banner is still cached
    contacted = _build(
        tmp_path,
        [_order(**MID_REVISION), _order(**{**UNCONTACTED, "seller_message_observed": True})],
    )
    assert [item["buyer"] for item in contacted["items"]] == ["買い手B", "買い手A"]
    assert contacted["items"][1]["first_contact_at_risk"] is False
    assert contacted["items"][1]["priority"] == delivery_queue.QUEUE_PRIORITY[
        contacted["items"][1]["queue_class"]
    ]

    # b) coconala stops rendering the banner, which is how it says the rule is satisfied
    retracted = _build(
        tmp_path,
        [_order(**MID_REVISION), _order(**{**UNCONTACTED, "contact_deadline": None})],
    )
    assert [item["buyer"] for item in retracted["items"]] == ["買い手B", "買い手A"]
    assert retracted["items"][1]["first_contact_at_risk"] is False


def test_a_deadline_already_past_does_not_pin_the_order_to_the_top(tmp_path):
    """Past the deadline the order is gone; starving live work for it helps nobody."""
    queue = _build(
        tmp_path,
        [_order(**MID_REVISION), _order(**UNCONTACTED)],
        captured_at="2026-08-10T00:00:00+00:00",
    )
    assert [item["buyer"] for item in queue["items"]] == ["買い手B", "買い手A"]
    assert queue["items"][1]["first_contact_at_risk"] is False


def test_two_expiring_orders_are_ordered_by_cancellation_not_delivery_date(tmp_path):
    sooner = _order(
        **{**UNCONTACTED, "contract_id": "offer:2", "talkroom_id": "2", "buyer": "sooner",
           "delivery_date": "2026-09-30", "contact_deadline": "2026-08-08T09:00:00+09:00"}
    )
    later = _order(**{**UNCONTACTED, "buyer": "later", "delivery_date": "2026-08-08"})
    queue = _build(tmp_path, [later, sooner])
    assert [item["buyer"] for item in queue["items"]] == ["sooner", "later"]


def test_a_snapshot_without_a_usable_capture_time_never_escalates(tmp_path):
    """No comparable 'now' is not permission to pin an order to the top forever."""
    for captured in ("", "2026-08-07T23:07:56"):  # missing, then naive
        queue = _build(tmp_path, [_order(**MID_REVISION), _order(**UNCONTACTED)], captured)
        assert [item["buyer"] for item in queue["items"]] == ["買い手B", "買い手A"]


# --------------------------------------------------------------------------------------
# The collector persists the banner it read
# --------------------------------------------------------------------------------------

def test_a_silent_new_order_is_kept_in_the_queue_by_its_cancellation_clock(tmp_path):
    """The buyer paid and wrote nothing. Without the clock this order vanishes entirely."""
    silent = _order(
        **{**UNCONTACTED, "status": "unknown", "buyer_feedback_pending_artifact": False,
           "buyer_feedback_stage": None, "buyer": "silent"}
    )
    assert delivery_queue.is_active_paid_order(silent) is True
    queue = _build(tmp_path, [_order(**MID_REVISION), silent])
    assert [item["buyer"] for item in queue["items"]] == ["silent", "買い手B"]

    # And with no clock it is dropped, which is the behaviour this closes.
    assert delivery_queue.is_active_paid_order({**silent, "contact_deadline": None}) is False


def test_the_banner_survives_minimize_and_reaches_the_order(tmp_path):
    """End to end through the collector's own functions: raw DOM -> minimized -> order."""
    raw = {
        "url": "https://coconala.com/talkrooms/90000001",
        "transaction_state": "取引中",
        "delivery_date": "2026/08/20",
        "auto_cancel_notice": BANNER,
        "messages": [{"side": "buyer", "text": "よろしくお願いします。", "attachments": []}],
    }
    minimized = collector.minimize_talkroom_dom(raw, "90000001", OBSERVED)
    assert minimized["contact_deadline"] == "2026-08-09T23:00:00+09:00"
    assert minimized["seller_message_observed"] is False
    # The sentence we parsed is kept beside the value, so a later reader can check the
    # parse against its source instead of trusting a bare timestamp.
    assert "自動的に取引がキャンセル" in minimized["auto_cancel_notice"]

    order: dict = {}
    collector.enrich_order(order, minimized, None)
    assert order["contact_deadline"] == "2026-08-09T23:00:00+09:00"
    assert order["seller_message_observed"] is False
    assert delivery_queue.first_contact_at_risk(
        order, __import__("datetime").datetime.fromisoformat(OBSERVED)
    ) is True


def test_any_seller_message_counts_as_contact_even_with_no_attachment():
    """The platform's rule is 'the seller wrote something', not 'the seller sent a file'."""
    raw = {
        "url": "https://coconala.com/talkrooms/1",
        "transaction_state": "取引中",
        "auto_cancel_notice": BANNER,
        "messages": [
            {"side": "buyer", "text": "よろしくお願いします。", "attachments": []},
            {"side": "seller", "text": "ご購入ありがとうございます。", "attachments": []},
        ],
    }
    minimized = collector.minimize_talkroom_dom(raw, "1", OBSERVED)
    assert minimized["seller_message_observed"] is True
    # The artifact-visibility fact is a different question and correctly still says no.
    assert minimized["buyer_visible_artifact_observed"] is False


def test_both_talkroom_expressions_capture_the_banner():
    source = (SCRIPTS / "coconala_queue_snapshot.py").read_text(encoding="utf-8")
    assert source.count("auto_cancel_notice:((document.body.innerText.match(") == 2, (
        "the banner must be captured by the full-history expression AND the incremental "
        "one, or the field appears and disappears depending on which capture ran"
    )
