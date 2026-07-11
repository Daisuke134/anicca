#!/usr/bin/env python3
"""no_naked.py — PURE decision functions that keep the Polymarket loops from ever holding a
naked single-leg position (SPEC-no-naked-fills.md, §9 R2 / map M7).

A binary market's YES+NO tokens resolve to exactly $1 together. Holding BOTH legs (a "bundle")
is risk-free; holding exactly ONE leg is a naked directional bet that rides to resolution and is
what bled pUSD 12.79 -> 4.19 (-$8.60). These functions decide, from plain data only, (a) which
holdings are naked and (b) the cheapest way to neutralize each one. NO network, wallet, LLM, or
I/O is reachable here — everything is unit-testable with mock dicts.
"""
from __future__ import annotations

EPS = 1e-9


def _size(v) -> float:
    try:
        return max(0.0, float(v or 0.0))
    except (TypeError, ValueError):
        return 0.0


def naked_legs(holdings, pairs):
    """Return the list of naked single-leg positions.

    holdings: list[dict] with at least {"asset": <clobTokenId str>, "size": <shares>}.
    pairs:    list[dict] with {"market": <name>, "yes_token": <str>, "no_token": <str>}.

    A market is naked iff EXACTLY ONE of its two legs is held with size > 0 (xor). Markets with
    both legs held (bundle) or neither held are NOT naked. Output rows:
      {"market", "held_token", "held_size", "missing_token"}.
    Pure: reads only its two plain-data arguments.
    """
    sizes = {}
    for h in holdings or []:
        if not isinstance(h, dict):
            continue
        a = h.get("asset")
        if a is None:
            continue
        sizes[str(a)] = sizes.get(str(a), 0.0) + _size(h.get("size"))

    out = []
    for p in pairs or []:
        if not isinstance(p, dict):
            continue
        yes = str(p.get("yes_token"))
        no = str(p.get("no_token"))
        ys = sizes.get(yes, 0.0)
        ns = sizes.get(no, 0.0)
        y_held = ys > EPS
        n_held = ns > EPS
        if y_held == n_held:  # both held (bundle) or neither -> not naked
            continue
        if y_held:
            out.append({"market": p.get("market"), "held_token": yes,
                        "held_size": ys, "missing_token": no})
        else:
            out.append({"market": p.get("market"), "held_token": no,
                        "held_size": ns, "missing_token": yes})
    return out


def plan_naked_fix(naked_leg, books):
    """Decide the cheapest way to neutralize ONE naked leg.

    naked_leg: a row from naked_legs().
    books: {"missing_ask": <price or None>, "held_bid": <price or None>}.

    Two ways to flatten the directional risk, compared by terminal value PER SHARE (the already-paid
    cost of the held leg is sunk and identical either way, so it drops out):
      - "complete": buy the missing leg at its ask -> hold a full bundle -> guaranteed $1/share at
        resolution. Terminal value per share = (1 - missing_ask).
      - "sell": sell the held leg now at its bid. Terminal value per share = held_bid.
    Choose the larger. Missing/blocked liquidity forces the only feasible side; if neither is
    feasible, return action "none" (caller MUST then refuse to add new quotes — fail-closed).
    Returns {"action": "complete"|"sell"|"none", "token", "size", "price", "reason"}.
    """
    size = _size((naked_leg or {}).get("held_size"))
    missing_ask = (books or {}).get("missing_ask")
    held_bid = (books or {}).get("held_bid")

    complete_ok = missing_ask is not None and float(missing_ask) < 1.0
    sell_ok = held_bid is not None and float(held_bid) > 0.0

    if not complete_ok and not sell_ok:
        return {"action": "none", "token": None, "size": size, "price": None,
                "reason": "no feasible completing-ask (<1) or selling-bid (>0)"}

    complete_val = (1.0 - float(missing_ask)) if complete_ok else float("-inf")
    sell_val = float(held_bid) if sell_ok else float("-inf")

    if complete_val >= sell_val:
        return {"action": "complete", "token": naked_leg["missing_token"], "size": size,
                "price": float(missing_ask),
                "reason": f"complete keeps {complete_val:.3f}/sh >= sell {sell_val if sell_ok else 0:.3f}/sh"}
    return {"action": "sell", "token": naked_leg["held_token"], "size": size,
            "price": float(held_bid),
            "reason": f"sell keeps {sell_val:.3f}/sh > complete {complete_val if complete_ok else 0:.3f}/sh"}


def plan_arb_unwind(legs):
    """For the sequential-FOK bundle_arb path: given the per-leg fill results, decide whether a
    leg must be unwound so no naked position survives.

    legs: list[dict] {"token": <str>, "filled": <bool>} in the order they were sent.
    - both filled  -> [] (risk-free bundle, keep).
    - none filled  -> [] (nothing to undo).
    - exactly one filled -> [{"action": "unwind", "token": <the filled leg's token>}].
    Pure.
    """
    filled = [l for l in (legs or []) if isinstance(l, dict) and l.get("filled")]
    if len(filled) == len(legs or []) or not filled:
        return []
    # partial fill: unwind every leg that filled (there is no complete bundle)
    return [{"action": "unwind", "token": l.get("token")} for l in filled]
