#!/usr/bin/env python3
"""Which paid talkrooms exist, and which have a buyer waiting — spec §0.1.6 (P1a-3).

The paid-buyer lane starts from external truth: the marketplace snapshot's `orders`, which
is the buyer-visible list of paid work. `reply_queue.py` reads the same list and then skips
every room in it (`if talkroom_id in paid_talkroom_ids: continue`), which is the first of
the three locks that left paying customers with no owner. This module is the other half of
that decision — it treats those rooms as the subject rather than the exclusion.

The load-bearing risk was named before any code was written: this enumerator is the single
point of blindness. A room that is never enumerated never grows a liability, and the result
is the identical 24-pass silence with more machinery and more confidence behind it. So this
returns counts and errors, not just rows: an order that cannot be read becomes an error, an
empty `orders` list is flagged as a suspect collector rather than read as "no customers",
and the caller can compare `orders_seen` against `rooms_enumerated` on every pass.

Known limit, stated rather than papered over: the snapshot carries no `last_outbound_ts`,
so "the buyer spoke more recently than we did" cannot be computed here. What it does carry
is `buyer_feedback_pending_artifact` — the collector's own judgement that the buyer is
waiting on something — plus whether anything is buyer-visible and whether formal delivery
happened. Liability is derived from those three. Adding a real last-outbound timestamp to
the collector would make this stricter and is the natural follow-up.
"""

from __future__ import annotations

from typing import Any

# The identity of the buyer message a liability is about. Keying on it means a *new* buyer
# message opens a new liability instead of being absorbed by one we already closed.
_KEY_FIELD = "buyer_feedback_sha256"


def _liability_open(order: dict[str, Any]) -> bool:
    """True when a paying buyer is waiting and nothing has reached them.

    Deliberately not keyed on `status`: the real 90000005 row carries `status: "unknown"`
    while being fully delivered, and the real 買い手C row carries `status: "paid"` while
    nothing exists. Delivery observations describe the buyer's side; `status` describes
    ours, and it was ours that kept saying everything was fine.
    """
    if order.get("formal_delivery_observed") is True:
        return False
    if order.get("buyer_visible_artifact_observed") is True:
        return False
    return order.get("buyer_feedback_pending_artifact") is True


def enumerate_paid_talkrooms(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Enumerate paid rooms from a marketplace snapshot.

    Returns rooms, plus everything needed to notice that the enumeration itself failed:
    `orders_seen`, `rooms_enumerated`, `dropped`, `errors`, `collector_suspect`.
    """
    orders = snapshot.get("orders") or []
    rooms: list[dict[str, Any]] = []
    errors: list[str] = []

    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            errors.append(f"orders[{index}] is not an object and cannot be enumerated")
            continue
        talkroom_id = order.get("talkroom_id")
        if talkroom_id in (None, ""):
            # Never `continue` quietly here. A row we cannot key is exactly how a paying
            # customer disappears from the lane's field of view.
            errors.append(
                f"orders[{index}] has no talkroom_id "
                f"(title={order.get('title')!r}, price_jpy={order.get('price_jpy')!r}) "
                "— cannot enumerate, so it cannot grow a liability"
            )
            continue

        talkroom_id = str(talkroom_id)
        key_value = order.get(_KEY_FIELD) or "none"
        rooms.append(
            {
                "talkroom_id": talkroom_id,
                "contract_id": order.get("contract_id"),
                "title": order.get("title"),
                "order_value_jpy": order.get("price_jpy"),
                "observed_at": order.get("talkroom_observed_at"),
                "buyer_feedback_stage": order.get("buyer_feedback_stage"),
                "liability_open": _liability_open(order),
                "liability_key": f"{talkroom_id}:{key_value}",
            }
        )

    orders_seen = len(orders)
    return {
        "rooms": rooms,
        "errors": errors,
        "orders_seen": orders_seen,
        "rooms_enumerated": len(rooms),
        "dropped": orders_seen - len(rooms),
        # An empty orders list is what a broken collector produces, and it is
        # indistinguishable from "no paying customers" unless it is said out loud.
        "collector_suspect": orders_seen == 0,
    }
